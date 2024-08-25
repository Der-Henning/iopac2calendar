from dataclasses import dataclass

import omegaconf


@dataclass
class Konto:
    Kundennummer: str
    Passwort: str
    Bibliothek: str


@dataclass
class Bibliothek:
    URL: str


class Config:
    def __init__(self, config_file: str = "config.yaml"):
        self.config = omegaconf.OmegaConf.load(config_file)
        self.bibliotheken: dict[str, Bibliothek] = {
            name: Bibliothek(**bib) for name, bib in self.config.get("Bibliotheken", {}).items()
        }
        self.konten: dict[str, Konto] = {name: Konto(**konto) for name, konto in self.config.get("Konten", {}).items()}
