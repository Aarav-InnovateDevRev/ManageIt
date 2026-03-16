import psycopg2
import os

DB_URL = os.environ.get("DATABASE_URL")

def connect():
    return psycopg2.connect(DB_URL, sslmode="require")
