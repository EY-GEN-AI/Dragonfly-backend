from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartChat"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 2  # 2 hours
    #CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8000","http://localhost:3000","https://6vr1cmm1-8000.asse.devtunnels.ms/"]
    #CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8000"]
    #CORS_ORIGINS: List[str] = [ "http://localhost:3000"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3004","http://localhost:3080"]
 

    ALGORITHM: str = "HS256"
    
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    #MONGODB_DB: str = os.getenv("MONGODB_DB", "dragonfly")
    MONGODB_NAME:str =os.getenv("MONGODB_NAME", "dragonfly")

    #postgres settings
    POSTGRES_URL: str =os.getenv("POSTGRES_URL") #,"postgresql://postgres:test@localhost:5432/sid_db")
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Email settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "your-app-password")
    SMTP_TLS: bool = True
   
    MSSQL_URL: str = os.getenv("MSSQL_URL","DRIVER={ODBC Driver 17 for SQL Server};SERVER=XW5CG4244BBQ;DATABASE=DEMAND_PLANNING;Trusted_Connection=yes")

    #Azure 
    AZURE_API_KEY:str = os.getenv("AZURE_API_KEY")
    AZURE_API_BASE: str = os.getenv("AZURE_API_BASE")
    AZURE_API_VERSION: str = os.getenv("AZURE_API_VERSION")

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()
