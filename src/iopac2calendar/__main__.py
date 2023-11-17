import logging
import os
from functools import partial
from time import sleep

import pandas as pd
from dotenv import dotenv_values

from iopac2calendar.config import Config
from iopac2calendar.ics_calendar import Calendar
from iopac2calendar.iopac import IOPAC
from iopac2calendar.server import Server

log = logging.getLogger("iopac2calendar")


def join_events(row: pd.Series):
    return f"{row['Konto']}: {row['Titel']} [{row['Medientyp']}]"


def make_calendar(ics_file: str, event_name: str):
    log.info("Scraping IOPAC...")
    config = Config()
    iopac = IOPAC()
    for name, konto in config.konten.items():
        iopac.login(konto.get("Kundenummer"),
                    konto.get("Passwort"),
                    config.bibliotheken.get(
            konto.get("Bibliothek")).get("URL"),
            name)
    calendar = Calendar(ics_file)

    df = (iopac.df
          .assign(Beschreibung=lambda df_: df_.apply(join_events, axis=1))
          .groupby("Rückgabe am")["Beschreibung"]
          .agg(lambda x: "\n".join(x))
          .reset_index())

    for _, row in df.iterrows():
        calendar.add_event(event_name, row['Rückgabe am'], row['Beschreibung'])
    calendar.write()


def main():
    env = {
        **dotenv_values(),
        **os.environ
    }

    port = env.get("PORT", 8080)
    sleep_time = env.get("SLEEP_TIME", 600)
    ics_file = env.get("ICS_FILE", "iopac.ics")
    ics_path = env.get("ICS_PATH", "/iopac.ics")
    event_name = env.get("EVENT_NAME", "Bücherei Rückgabe")
    debug = env.get("DEBUG") in ["True", "true", "1"]

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    make_cal = partial(make_calendar, ics_file, event_name)
    make_cal()

    log.info("Starting server...")
    server = Server(port, ics_file, ics_path)
    server.start()
    log.info(f"Server started on port {port}")
    log.info(f"ICS file available at http://localhost:{port}{ics_path}")

    while True:
        try:
            sleep(sleep_time)
            make_cal()
        except KeyboardInterrupt:
            break

    log.info("Stopping server...")
    server.stop()


if __name__ == '__main__':
    main()
