import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_POSTGRES = "postgresql://postgres:postgres@localhost:5432/foodflow"
DEFAULT_MONGO = "mongodb://localhost:27017"


def read_setting(name, default):
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return default


def postgres_url():
    return read_setting("DATABASE_URL", DEFAULT_POSTGRES)


def mongo_url():
    return read_setting("MONGO_URI", DEFAULT_MONGO)


def mongo_database():
    return read_setting("MONGO_DB", "foodflow")


PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
SQL_FOLDER = os.path.join(PROJECT_FOLDER, "sql")
BACKUP_FOLDER = os.path.join(PROJECT_FOLDER, "backups")
