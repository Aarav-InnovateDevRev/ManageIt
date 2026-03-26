import psycopg2
import os

def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL is None:
        raise ValueError("DATABASE_URL is missing!")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(DATABASE_URL, sslmode="require")
