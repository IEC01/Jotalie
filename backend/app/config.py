from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    blink_mock: bool = True
    blink_api_url: str = "https://api.blink.sv/graphql"
    blink_api_key: str = ""
    blink_btc_wallet_id: str = ""
    database_url: str = "sqlite:///./jotali.db"


settings = Settings()
