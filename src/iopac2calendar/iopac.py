from io import StringIO
from urllib.parse import urljoin

import pandas as pd
import requests


class IOPAC:
    def __init__(self):
        self.df = pd.DataFrame()

    def login(self, username: str, password: str, url: str, name: str) -> None:
        uri = urljoin(url, 'cgi-bin/di.exe')
        payload = {
            'sleKndNr': username,
            'slePw': password,
            'pshLogin': 'Login'
        }
        response = requests.post(uri, data=payload)
        buffer = StringIO(response.text)

        df = pd.read_html(buffer, header=0, index_col=None,
                          encoding='utf-8',
                          attrs={"class": 'SEARCH_LESER'})[0]
        df["Rückgabe am"] = pd.to_datetime(
            df["Rückgabe am"], format="%d.%m.%Y")
        df["Konto"] = name
        self.df = pd.concat([self.df, df])
