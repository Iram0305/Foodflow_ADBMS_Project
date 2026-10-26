import time

import pandas as pd
import psycopg2
import psycopg2.extras

from core import config


def connect(autocommit=True):
    connection = psycopg2.connect(config.postgres_url(), connect_timeout=8)
    connection.autocommit = autocommit
    return connection


def run_query(sql, params=None):
    connection = connect()
    try:
        cursor = connection.cursor()
        start = time.perf_counter()
        cursor.execute(sql, params)
        elapsed = (time.perf_counter() - start) * 1000
        if cursor.description is None:
            return pd.DataFrame(), elapsed
        columns = []
        for column in cursor.description:
            columns.append(column[0])
        rows = cursor.fetchall()
        frame = pd.DataFrame(rows, columns=columns)
        for column in frame.columns:
            if frame[column].dtype == object and len(frame) > 0:
                first = frame[column].dropna()
                if len(first) > 0 and type(first.iloc[0]).__name__ == "Decimal":
                    frame[column] = frame[column].astype(float)
        return frame, elapsed
    finally:
        connection.close()


def render(sql, params):
    connection = connect()
    try:
        text = connection.cursor().mogrify(sql, params)
        return text.decode("utf-8")
    finally:
        connection.close()


def fetch(sql, params=None):
    frame, elapsed = run_query(sql, params)
    return frame


def fetch_value(sql, params=None):
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]
    finally:
        connection.close()


def execute(sql, params=None):
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount
    finally:
        connection.close()


def run_readonly(sql):
    connection = connect(autocommit=False)
    try:
        cursor = connection.cursor()
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("SET LOCAL statement_timeout = 15000")
        start = time.perf_counter()
        cursor.execute(sql)
        elapsed = (time.perf_counter() - start) * 1000
        if cursor.description is None:
            connection.rollback()
            return pd.DataFrame(), elapsed
        columns = []
        for column in cursor.description:
            columns.append(column[0])
        rows = cursor.fetchmany(2000)
        connection.rollback()
        return pd.DataFrame(rows, columns=columns), elapsed
    finally:
        connection.close()


def is_ready():
    try:
        value = fetch_value("SELECT to_regclass('public.orders') IS NOT NULL AND EXISTS (SELECT 1 FROM orders)")
        return bool(value)
    except Exception:
        return False


def can_connect():
    try:
        fetch_value("SELECT 1")
        return True, ""
    except Exception as error:
        return False, str(error)


def has_postgis():
    try:
        value = fetch_value("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'restaurant' AND column_name = 'geom')")
        return bool(value)
    except Exception:
        return False
