import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(DATABASE_URL, sslmode="require")
