import asyncio
import logging
import os

from aiohttp.client_exceptions import ClientResponseError
from dotenv import dotenv_values

from iopac2calendar.config import Config
from iopac2calendar.ics_calendar import Calendar
from iopac2calendar.iopac import IOPAC
from iopac2calendar.server import Server

log = logging.getLogger("iopac2calendar")


async def make_calendar(ics_file: str, event_name: str, config_file: str = "config.yaml", timeout: float = 30.0):
    log.info("Scraping IOPAC...")
    config = Config(config_file)
    calendar = Calendar(ics_file)

    async with IOPAC(timeout) as iopac:
        for name, konto in config.konten.items():
            bib = config.bibliotheken.get(konto.Bibliothek)
            if not bib:
                log.error(f"Unknown library: {konto.Bibliothek}")
                continue
            await iopac.get_data(name, konto.Kundennummer, konto.Passwort, bib.URL)

        for _, row in iopac.df.iterrows():
            calendar.add_event(event_name, row["Rückgabe am"], row["Beschreibung"])

    calendar.write()


async def main():
    env = {**dotenv_values(), **os.environ}

    port = int(env.get("PORT", 8080))
    host = env.get("HOST", "localhost")
    sleep_time = int(env.get("SLEEP_TIME", 600))
    ics_file = env.get("ICS_FILE", "iopac.ics")
    ics_path = env.get("ICS_PATH", "/iopac.ics")
    event_name = env.get("EVENT_NAME", "Bücherei Rückgabe")
    config_file = env.get("CONFIG_FILE", "config.yaml")
    timeout = float(env.get("TIMEOUT", 30.0))
    debug = env.get("DEBUG") in ["True", "true", "1"]

    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("aiohttp").setLevel(log_level)

    await make_calendar(ics_file, event_name, config_file, timeout)

    server = Server(host, port, ics_file, ics_path)

    log.info("Starting server...")
    await server.start()
    log.info(f"ICS file available at http://{host}:{port}{ics_path}")

    while True:
        try:
            await asyncio.sleep(sleep_time)
            await make_calendar(ics_file, event_name, config_file, timeout)
        except asyncio.CancelledError:
            break
        except ClientResponseError as exc:
            log.error(exc)
        except asyncio.TimeoutError:
            log.error("IOPAC request Timeout")
        except Exception as exc:
            log.error(exc)

    log.info("Stopping server...")
    await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
