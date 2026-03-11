from dataclasses import dataclass

from src.core.config import settings

@dataclass(frozen=True, slots=True)
class ARIConfig:
    host: str
    port: int
    username: str
    password: str
    app_name: str

    @property
    def rest_base_url(self) -> str:
        return f"http://{self.host}:{self.port}/ari"

    @property
    def ws_url(self) -> str:
        return (
            f"ws://{self.host}:{self.port}/ari/events"
            f"?app={self.app_name}&api_key={self.username}:{self.password}"
        )

    @classmethod
    def from_settings(cls) -> "ARIConfig":
        return cls(
            host=settings.ASTERISK_HOST,
            port=settings.ASTERISK_PORT,
            username=settings.ASTERISK_ARI_USER,
            password=settings.ASTERISK_ARI_PASSWORD,
            app_name=settings.ASTERISK_ARI_APP,
        )
