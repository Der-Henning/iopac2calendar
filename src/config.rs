use anyhow::{Context, Result};
use serde::Deserialize;
use std::{collections::HashMap, path::Path};

use crate::iopac::IopacError;

#[derive(Debug, Deserialize)]
pub struct Library {
    #[serde(rename = "URL")]
    pub url: String,
}

#[derive(Debug, Deserialize)]
pub struct Account {
    #[serde(rename = "Bibliothek")]
    pub library: String,

    #[serde(rename = "Kundennummer")]
    pub customer_id: String,

    #[serde(rename = "Passwort")]
    pub password: String,
}

#[derive(Debug, Deserialize)]
pub struct IopacConfig {
    #[serde(rename = "Bibliotheken")]
    pub libraries: HashMap<String, Library>,

    #[serde(rename = "Konten")]
    pub accounts: HashMap<String, Account>,
}

impl IopacConfig {
    pub fn try_new<P: AsRef<Path> + std::fmt::Display>(path: P) -> Result<Self> {
        let file = std::fs::File::open(&path).with_context(|| format!("reading {}", path))?;
        let config: IopacConfig = serde_yaml::from_reader(file)?;
        config.check()?;
        Ok(config)
    }

    fn check(&self) -> Result<(), IopacError> {
        for account in self.accounts.values() {
            if !self.libraries.contains_key(&account.library) {
                return Err(IopacError(format!("Missing library {}", account.library)));
            }
        }
        Ok(())
    }
}
