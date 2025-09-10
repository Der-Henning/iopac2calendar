use anyhow::Result;
use axum::{Router, extract::State, http::HeaderMap, response::IntoResponse, routing};
use chrono::{Datelike, Days, Local, TimeZone};
use clap::Parser;
use icalendar::{Alarm, Calendar, Class, Component, Event, EventLike};
use itertools::Itertools;
use log::{debug, error, info};
use reqwest::StatusCode;
use std::str::FromStr;
use std::{collections::HashMap, sync::Arc};
use tokio::{net::TcpListener, sync::RwLock};
use uuid::Uuid;

use crate::config::IopacConfig;
use crate::iopac::{Iopac, IopacData};

mod config;
mod iopac;

#[derive(Parser, Debug)]
#[command(version, about)]
struct Args {
    /// Port to listen on
    #[arg(long, short = 'P', env = "PORT", default_value_t = 8080)]
    port: u16,

    /// Config file path
    #[arg(long, short, env = "CONFIG_FILE", default_value_t = {"config.yaml".to_string()})]
    config: String,

    /// Web path for ics file
    #[arg(long, short, env = "ICS_PATH", default_value_t = {"/iopac.ics".to_string()})]
    path: String,

    /// Sleep time between consecutive iopac checks
    #[arg(long, short, env = "SLEEP_TIME", default_value_t = 30)]
    sleep_time: u64,

    /// iCalendar event name
    #[arg(long, short, env = "EVENT_NAME", default_value_t = {"Bücherei Rückgabe".to_string()})]
    name: String,

    /// Perform health check on localhost
    #[arg(long, short = 'H')]
    health_check: bool,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logger
    env_logger::builder().format_target(false).init();

    // Read command line arguments and environment variables
    let args = Args::parse();

    // Run health check
    if args.health_check {
        info!("Performing health check");
        reqwest::get(format!("http://localhost:{}/health", args.port))
            .await?
            .error_for_status()?;
        info!("OK");
        return Ok(());
    }

    // Read config
    let config = IopacConfig::try_new(args.config)?;
    debug!("{:#?}", config);

    // Initialize data storage and iopac connector
    let data: Arc<RwLock<IopacData>> = Arc::new(RwLock::new(HashMap::new()));
    let iopac = Iopac::new(config, data.clone());

    // Run update data once and check for errors
    iopac.update_data().await?;

    // Create background worker that updates the data every x seconds
    let background_task = Arc::new(tokio::spawn(async move {
        polling_task(iopac, args.sleep_time).await
    }));

    // Define routers
    let router = Router::new()
        .route("/health", routing::get(health_check))
        .with_state(background_task.clone())
        .route(&args.path, routing::get(get_calendar))
        .with_state((data, args.name));

    // Start web-server
    let listener = TcpListener::bind(format!("0.0.0.0:{}", args.port)).await?;
    info!("listening on: {}", listener.local_addr().unwrap());
    axum::serve(listener, router)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    // Cleanup
    info!("Shutdown");
    background_task.abort();
    Ok(())
}

/// Waits for a shutdown signal:
/// - On Unix: SIGTERM (typical in Docker), SIGINT, or SIGQUIT
/// - Elsewhere: Ctrl+C
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{SignalKind, signal};
        let mut sigterm =
            signal(SignalKind::terminate()).expect("failed to install SIGTERM handler");
        let mut sigint = signal(SignalKind::interrupt()).expect("failed to install SIGINT handler");
        let mut sigquit = signal(SignalKind::quit()).expect("failed to install SIGQUIT handler");

        tokio::select! {
            _ = sigterm.recv() => {
                debug!("received SIGTERM");
            }
            _ = sigint.recv() => {
                debug!("received SIGINT");
            }
            _ = sigquit.recv() => {
                debug!("received SIGQUIT");
            }
        }
    }

    #[cfg(not(unix))]
    {
        let _ = signal::ctrl_c().await;
        debug!("received Ctrl+C");
    }
}

type AppState = (Arc<RwLock<IopacData>>, String);

// Calender .ics file endpoint handler
async fn get_calendar(State(state): State<AppState>) -> impl IntoResponse {
    // Read data and build ics file
    let guard = state.0.read().await;
    let ics = build_calendar(&guard, &state.1).to_string();
    drop(guard);

    // Create response
    let mut headers = HeaderMap::new();
    headers.insert(
        reqwest::header::CONTENT_TYPE,
        "text/calendar; charset=utf-8".parse().unwrap(),
    );
    headers.insert(
        reqwest::header::CONTENT_DISPOSITION,
        "attachment; filename=\"iopac.ics\"".parse().unwrap(),
    );
    (StatusCode::OK, headers, ics).into_response()
}

// Health check endpoint handler
// Unhealthy when background task is not running
async fn health_check(State(state): State<Arc<tokio::task::JoinHandle<()>>>) -> impl IntoResponse {
    if state.is_finished() {
        (StatusCode::INTERNAL_SERVER_ERROR, "Background Task down").into_response()
    } else {
        (StatusCode::OK, "OK").into_response()
    }
}

// Background task that updates iopac data every x seconds
async fn polling_task(iopac: Iopac, sleep_time: u64) {
    let mut ticker = tokio::time::interval(std::time::Duration::from_secs(sleep_time));
    loop {
        ticker.tick().await;
        if let Err(error) = iopac.update_data().await {
            error!("{:?}", error)
        }
    }
}

// Generate repeatable uid
fn make_uid(data: &str) -> String {
    let md5 = format!("{:?}", md5::compute(data));
    Uuid::from_str(&md5).unwrap().to_string()
}

// Build ics calendar from iopac data
fn build_calendar(data: &IopacData, event_name: &str) -> Calendar {
    let event_name = std::env::var("EVENT_NAME").unwrap_or(event_name.to_string());
    let mut cal = Calendar::new();
    cal.name("IOPAC");

    // Create a single event for all items with the same return date
    for (return_on, items) in data {
        // Aggregate items to list for event body
        let description = items
            .iter()
            .map(|r| {
                let reserved = if r.reserved { " RESERVIERT" } else { "" };
                format!("{}: {} [{}]{}", r.account, r.title, r.media_type, reserved)
            })
            .join("\n");
        // Calculate alarm datetime at 09:00 the day before the return date
        let prev_day = return_on.checked_sub_days(Days::new(1)).unwrap();
        let alarm_dt = Local
            .with_ymd_and_hms(prev_day.year(), prev_day.month0(), prev_day.day0(), 9, 0, 0)
            .unwrap()
            .to_utc();
        // Create the alarm for the event
        let alarm = Alarm::display("Reminder", alarm_dt)
            .uid(&make_uid(&(return_on.to_string() + &alarm_dt.to_string())))
            .done();
        // Create and push the Event to the calendar
        cal.push(
            Event::new()
                .uid(&make_uid(&return_on.to_string()))
                .summary(&event_name)
                .description(&description)
                .class(Class::Public)
                .all_day(*return_on)
                .alarm(alarm)
                .done(),
        );
    }

    cal
}
