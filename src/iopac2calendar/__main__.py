import os
from time import sleep

import pandas as pd
from dotenv import dotenv_values

from iopac2calendar.config import Config
from iopac2calendar.ics_calendar import Calendar
from iopac2calendar.iopac import IOPAC
from iopac2calendar.server import Server


def join_events(df: pd.DataFrame):
    if len(df) > 1:
        description = "\n".join(
            [f"{row['Konto']}: '{row['Titel']}'" for _, row in df.iterrows()])
        return pd.DataFrame([["diverse", description]],
                            columns=["Titel", "Beschreibung"])
    else:
        return pd.DataFrame(
            [[f"{df.iloc[0]['Konto']}: '{df.iloc[0]['Titel']}'", ""]],
            columns=["Titel", "Beschreibung"])


def make_calendar(ics_path: str):
    config = Config()
    iopac = IOPAC()
    for name, konto in config.konten.items():
        iopac.login(konto.get("Kundenummer"),
                    konto.get("Passwort"),
                    config.bibliotheken.get(
            konto.get("Bibliothek")).get("URL"),
            name)
    calendar = Calendar(ics_path)

    df = (iopac.df
          .groupby(["Rückgabe am"])
          .apply(join_events)
          .droplevel(1)
          .reset_index())

    for _, row in df.iterrows():
        event_name = row['Titel']
        calendar.add_event(event_name, row['Rückgabe am'], row['Beschreibung'])
    calendar.write()


def main():
    env = {
        **dotenv_values(),
        **os.environ
    }

    port = env.get("PORT", 8080)
    sleep_time = env.get("SLEEP_TIME", 600)
    ics_path = env.get("ICS_PATH", "iopac.ics")

    server = Server(port)
    server.start()
    while True:
        try:
            make_calendar(ics_path)
            sleep(sleep_time)
        except KeyboardInterrupt:
            break
    server.stop()


if __name__ == '__main__':
    main()
