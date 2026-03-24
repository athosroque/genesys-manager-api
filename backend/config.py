from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    GENESYS_CLIENT_ID: str = os.getenv("GENESYS_CLIENT_ID", "")
    GENESYS_CLIENT_SECRET: str = os.getenv("GENESYS_CLIENT_SECRET", "")
    GENESYS_REGION: str = os.getenv("GENESYS_REGION", "sae1.pure.cloud")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    
    # Autenticação JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 480))
    
    # Ambiente e Cookies
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "")

settings = Settings()

# Constantes reais do projeto
REGION = settings.GENESYS_REGION
DOMAIN = "@corp.caixa.gov.br"
BASE_URL = f"https://api.{REGION}/api/v2"
AUTH_URL = f"https://login.{REGION}/oauth/token"
DIVISION_ID = "ef58437f-9318-4f09-ac15-30dce09296f2"
ROLE_ID = "1663985f-b69b-45d1-b51d-e7f8cbc61d74"

GRUPOS_MIGRACAO = [
    {"nome": "G_AZ_OCX_AG_FISICA_SUPERVISOR", "id": "2b6c6b09-0d89-465b-aa12-dface3e14433"},
    {"nome": "G_AZ_OCX_AG_FISICA_ATENDENTE",  "id": "c7a589dd-35bb-4537-a960-7b44eaeec170"},
    {"nome": "G_AZ_OCX_AG_FISICA_GGR",        "id": "e39099c4-1530-4605-a418-19414f87e292"},
]
