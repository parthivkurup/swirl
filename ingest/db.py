import os

import psycopg
from dotenv import load_dotenv


def connect():
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set (copy .env.example to .env)")
    return psycopg.connect(dsn)
