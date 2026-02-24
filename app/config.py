from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

# Naik 1 level dari file ini
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"

# print(ENV_PATH)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding='utf-8')
    database_hostname: str 
    database_port: str 
    database_password: str 
    database_name: str 
    database_username: str 
    secret_key: str 
    algorithm: str 
    access_token_expire_minutes: int 
    database_url: str = ''

settings = Settings()