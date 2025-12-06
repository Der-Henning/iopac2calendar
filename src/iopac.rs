use anyhow::Result;
use chrono::NaiveDate;
// use encoding::{DecoderTrap::Ignore, Encoding, all::ISO_8859_1};
use itertools::Itertools;
use log::info;
use regex::Regex;
use serde::Serialize;
use std::{collections::HashMap, sync::Arc};
use tokio::sync::RwLock;

use crate::config::IopacConfig;

#[derive(Debug, Clone)]
pub struct IopacDatum {
    pub account: String,
    pub title: String,
    pub media_type: String,
    pub return_on: NaiveDate,
    pub reserved: bool,
}

impl IopacDatum {
    fn from_row(account: String, row: IopacRow) -> Self {
        Self {
            account,
            title: row.title,
            media_type: row.media_type,
            return_on: row.return_on,
            reserved: row.reserved,
        }
    }
}

#[derive(Debug, Clone)]
struct IopacRow {
    title: String,
    media_type: String,
    return_on: NaiveDate,
    reserved: bool,
}

fn extract_text(html: &str) -> String {
    let s = scraper::Html::parse_fragment(html)
        .select(&scraper::Selector::parse("*").unwrap())
        .flat_map(|el| el.text())
        .collect::<String>();
    s.trim().to_string()
}

impl IopacRow {
    fn try_from(row: table_extract::Row<'_>) -> Result<Self> {
        Ok(IopacRow {
            title: extract_text(
                row.get("Titel")
                    .ok_or(IopacError::new("Couldn't find title column"))?,
            ),
            media_type: extract_text(
                row.get("Medientyp")
                    .ok_or(IopacError::new("Couldn't find media type column"))?,
            ),
            return_on: {
                let txt = extract_text(
                    row.get("Fällig")
                        .ok_or(IopacError::new("Couldn't find return date column"))?,
                );
                NaiveDate::parse_from_str(
                    {
                        Regex::new(r"(\d\d.\d\d.\d\d\d\d)")
                            .unwrap()
                            .captures(&txt)
                            .ok_or(IopacError::new("Couldn't find date in date column"))?
                            .get(0)
                            .unwrap()
                            .into()
                    },
                    "%d.%m.%Y",
                )?
            },
            reserved: extract_text(
                row.get("Verlängern")
                    .ok_or(IopacError::new("Couldn't find return reserved column"))?,
            )
            .contains("resev."),
        })
    }
}

pub type IopacData = HashMap<NaiveDate, Vec<IopacDatum>>;

pub struct Iopac {
    client: reqwest::Client,
    config: IopacConfig,
    data: Arc<RwLock<IopacData>>,
}

impl Iopac {
    const ENDPOINT_PATH: &str = "cgi-bin/koha/opac-user.pl";
    const TIMEOUT: u64 = 30;

    pub fn new(config: IopacConfig, data: Arc<RwLock<IopacData>>, ignore_ssl: bool) -> Self {
        Self {
            client: reqwest::Client::builder()
                .danger_accept_invalid_certs(ignore_ssl)
                .build()
                .unwrap(),
            config,
            data,
        }
    }

    async fn post(&self, url: &String, body: String) -> Result<reqwest::Response, reqwest::Error> {
        self.client
            .post(url)
            .body(body)
            .timeout(std::time::Duration::from_secs(Iopac::TIMEOUT))
            .send()
            .await
    }

    // Fetch and update data
    pub async fn update_data(&self) -> Result<()> {
        info!("Updating IOPAC data ...");

        // Fetch data of all accounts in parallel
        let result = futures::future::join_all(self.config.accounts.iter().map(
            async |(account_name, account)| {
                let library = self.config.libraries.get(&account.library).unwrap();
                (
                    account_name,
                    self.fetch_data(&library.url, &account.user_id, &account.password)
                        .await,
                )
            },
        ))
        .await;

        // Extract errors from results
        let (errors, results): (Vec<_>, Vec<_>) =
            result.into_iter().partition(|row| row.1.is_err());

        // Aggregate data and update data storage
        let mut iopac_data: HashMap<NaiveDate, Vec<IopacDatum>> = HashMap::new();
        results
            .into_iter()
            .flat_map(|(account, data)| {
                data.into_iter().flat_map(|rows| {
                    rows.into_iter()
                        .flatten()
                        .map(|row| IopacDatum::from_row(account.clone(), row))
                })
            })
            .for_each(|data| {
                iopac_data
                    .entry(data.return_on)
                    .and_modify(|vec| vec.push(data.clone()))
                    .or_insert(vec![data]);
            });

        let mut guard = self.data.write().await;
        *guard = iopac_data;

        // Return error if any occured
        match errors.into_iter().next() {
            Some(err) => Err(err.1.err().unwrap()),
            _ => Ok(()),
        }
    }

    // Fetch and parse table
    async fn fetch_data(
        &self,
        base_url: &str,
        user_id: &str,
        password: &str,
    ) -> Result<Option<Vec<IopacRow>>> {
        let url = base_url.to_string() + Iopac::ENDPOINT_PATH;
        let body = IopacRequestBody::new(user_id.to_string(), password.to_string());
        let body_str = serde_html_form::to_string(body).unwrap();

        // Login and return html page containing lend media
        // let response = self.post(&url, body_str).await?.bytes().await?;
        // let response_text = ISO_8859_1.decode(&response, Ignore).unwrap();
        let response_text = self.post(&url, body_str).await?.text().await?;

        // Parse html table
        // Return error when login failed
        let html = scraper::Html::parse_document(&response_text);

        if html
            .root_element()
            .text()
            .any(|ele| ele.trim() == "Login fehlgeschlagen")
        {
            Err(IopacError(format!("Login failed for account {}", user_id)).into())
        } else {
            parse_table(html)
        }
    }
}

fn parse_table(html: scraper::Html) -> Result<Option<Vec<IopacRow>>> {
    // Extract table html
    let selector = scraper::Selector::parse("#checkoutst").unwrap();
    let tab_html = match html.select(&selector).next() {
        Some(ele) => ele,
        _ => return Ok(None),
    };

    // Parse table
    let table = match table_extract::Table::find_first(&tab_html.html()) {
        Some(table) => table,
        _ => return Ok(None),
    };

    // Convert table to Vec<IopacRow>
    let data = table
        .into_iter()
        .map(|row| IopacRow::try_from(row))
        .try_collect()?;
    Ok(Some(data))
}

#[derive(Debug, Serialize)]
struct IopacRequestBody {
    #[serde(rename = "userid")]
    user_id: String,

    #[serde(rename = "password")]
    password: String,
    //     #[serde(rename = "pshLogin")]
    //     login: String,
}

impl IopacRequestBody {
    fn new(user_id: String, password: String) -> Self {
        Self {
            user_id,
            password,
            // login: "Login".to_string(),
        }
    }
}

#[derive(Debug)]
pub struct IopacError(pub String);

impl IopacError {
    fn new(message: &str) -> Self {
        Self(message.to_string())
    }
}

impl std::error::Error for IopacError {}

impl std::fmt::Display for IopacError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
