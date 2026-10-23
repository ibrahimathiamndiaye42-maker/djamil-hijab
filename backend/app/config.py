import os
from dotenv import load_dotenv
load_dotenv()

def _db_url():
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/djamil_hijab")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url.replace("postgresql://", "postgresql+psycopg2://", 1) if url.startswith("postgresql://") else url

class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "480"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") or None
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_REGION = os.getenv("S3_REGION", "auto")
    S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "")
