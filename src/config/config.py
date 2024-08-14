from pydantic import ConfigDict, field_validator, EmailStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    secret_key: str = "secret_key"
    algorithm: str = "HS256"
    mail_username: str = "admin"
    mail_password: str = "secretPassword"
    mail_from: EmailStr = "example@meta.ua"
    mail_port: str = "465"
    mail_server: str = "smtp.meta.ua"
    mail_from_name: str = "Desired Name"
    mail_starttls: str = "False"
    use_credentials: str = "True"
    validate_serts: str = "True"
    template_folder: str = "templates"
    redis_host: str = "localhost"
    redis_port: str = "6379"
    redis_password: str = "secretPassword"
    cloud_name: str = "cld_name"
    api_key: str = "api_key"
    api_secret: str = "your_api_secret"

    model_config = ConfigDict(extra="allow", env_file = '.env', env_file_encoding = 'utf-8')

    @field_validator("algorithm")
    def validate_algorithm(cls, v: str) -> str:
        if v not in ["HS256", "HS512"]:
            raise ValueError("Algorithm must be HS256 or HS512")
        return v


settings = Settings()
