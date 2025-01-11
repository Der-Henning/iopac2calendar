import logging
from io import StringIO
from urllib.parse import urljoin

import bs4
import pandas as pd
from aiohttp import ClientSession, ClientTimeout

COLUMNS = ["Titel", "Author", "Medientyp", "Verl.", "Rückgabe am", "Auswahl verlängern"]

log = logging.getLogger("iopac2calendar")


class IOPACError(Exception):
    pass


class IOPAC:
    def __init__(self, timeout: float = 30.0):
        self.session = ClientSession(timeout=ClientTimeout(total=timeout))
        self._df = pd.DataFrame(columns=COLUMNS)

    async def fetch_data(self, username: str, password: str, url: str) -> str:
        uri = urljoin(url, "cgi-bin/di.exe")
        payload = dict(sleKndNr=username, slePw=password, pshLogin="Login")
        log.debug(f"Fetching data from {uri}")
        log.debug(f"Payload: {payload}")
        async with self.session.post(uri, data=payload) as response:
            log.debug(f"Request headers: {response.request_info.headers}")
            log.debug(f"Response status: {response.status}")
            log.debug(f"Response headers: {response.headers}")
            response.raise_for_status()
            text = await response.text("latin-1")
            if bs4.BeautifulSoup(text, "html.parser").text.strip().startswith("Login fehlgeschlagen"):
                raise IOPACError(f"Login failed for {username}")
            return text

    @staticmethod
    def parse_html(html: str) -> pd.DataFrame:
        try:
            df = pd.read_html(StringIO(html), header=0, index_col=None, attrs={"class": "SEARCH_LESER"})[0]
        except ValueError:  # no data
            return pd.DataFrame(columns=COLUMNS)
        df["Reserviert"] = df["Rückgabe am"].str.contains("reserv.")
        df["Rückgabe am"] = pd.to_datetime(
            df["Rückgabe am"].str.extract(r"(\d\d.\d\d.\d\d\d\d)", expand=False), format="%d.%m.%Y"
        ).dt.date
        return df

    async def get_data(self, konto: str, username: str, password: str, url: str):
        html = await self.fetch_data(username, password, url)
        self._df = pd.concat([self._df, self.parse_html(html).assign(Konto=konto)], ignore_index=True)

    @staticmethod
    def join_events(row: pd.Series):
        event_str = f"{row['Konto']}: {row['Titel']} [{row['Medientyp']}]"
        if hasattr(row, "Reserviert") and row["Reserviert"]:
            event_str += " RESERVIERT"
        return event_str

    @property
    def df(self) -> pd.DataFrame:
        return (
            self._df.assign(Beschreibung=lambda df_: df_.apply(self.join_events, axis=1))
            .groupby("Rückgabe am")["Beschreibung"]
            .agg(lambda x: "\n".join(x))
            .reset_index()
        )

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False
