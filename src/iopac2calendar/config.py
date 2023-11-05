import omegaconf


class Config:
    def __init__(self, config_file: str = "config.yaml"):
        self.config = omegaconf.OmegaConf.load(config_file)
        self.bibliotheken: dict = self.config.get("Bibliotheken", {})
        self.konten: dict = self.config.get("Konten", {})
