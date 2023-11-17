import os
from time import sleep

import pandas as pd
from dotenv import dotenv_values

from iopac2calendar.config import Config
from iopac2calendar.ics_calendar import Calendar
from iopac2calendar.iopac import IOPAC
from iopac2calendar.server import Server

EVENT_NAME = "Bücherei Rückgabe"


def join_events(row: pd.Series):
    return f"{row['Konto']}: {row['Titel']} [{row['Medientyp']}]"


def make_calendar(ics_file: str):
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
        calendar.add_event(EVENT_NAME, row['Rückgabe am'], row['Beschreibung'])
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

    make_calendar(ics_file)

    server = Server(port, ics_file, ics_path)
    server.start()
    while True:
        try:
            make_calendar(ics_file)
            sleep(sleep_time)
        except KeyboardInterrupt:
            break
    server.stop()


if __name__ == '__main__':
    main()
