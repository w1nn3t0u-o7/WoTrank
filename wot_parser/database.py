import sqlite3


def connect_to_db(db_path):
    return sqlite3.connect(db_path)


def create_tables(conn):

    cursor = conn.cursor()

    # TODO: teams table, LiquipediaDB access needed i think

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY,
        tournament_id INTEGER,
        name TEXT NOT NULL,
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        FOREIGN KEY (match_id) REFERENCES matches(id)
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS performances (
        id INTEGER PRIMARY KEY,

        )"""
    )

    conn.commit()
