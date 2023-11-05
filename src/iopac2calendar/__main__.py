import os
from time import sleep

from dotenv import dotenv_values

from iopac2calendar.config import Config
from iopac2calendar.ics_calendar import Calendar
from iopac2calendar.iopac import IOPAC
from iopac2calendar.server import Server


def make_calendar(file: str):
    config = Config()
    for name, konto in config.konten.items():
        iopac = IOPAC(konto.get("Kundenummer"),
                      konto.get("Passwort"),
                      config.bibliotheken.get(
                          konto.get("Bibliothek")).get("URL"))
        df = iopac.login()
        calendar = Calendar(file)
        for _, row in df.iterrows():
            event_name = f"{name}: '{row['Titel']}'"
            calendar.add_event(event_name, row['Rückgabe am'])
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
