from io import StringIO
from urllib.parse import urljoin

import pandas as pd
import requests


class IOPAC:
    def __init__(self, username: str, password: str, url: str):
        self.username = username
        self.password = password
        self.url = url

    def login(self) -> pd.DataFrame:
        uri = urljoin(self.url, 'cgi-bin/di.exe')
        payload = {
            'sleKndNr': self.username,
            'slePw': self.password,
            'pshLogin': 'Login'
        }
        response = requests.post(uri, data=payload)
        buffer = StringIO(response.text)

        df = pd.read_html(buffer, header=0, index_col=None,
                          encoding='utf-8',
                          attrs={"class": 'SEARCH_LESER'})[0]
        df["Rückgabe am"] = pd.to_datetime(
            df["Rückgabe am"], format="%d.%m.%Y")
        return df
