import sqlite3

CREATE_TABLE_QUESTS = """CREATE TABLE IF NOT EXISTS quests (
    id integer PRIMARY KEY,
    player text NOT NULL,
    description text NULL,
    reward text NULL
);"""


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn


def create_table(conn) -> None:
    try:
        c = conn.cursor()
        c.execute(CREATE_TABLE_QUESTS)
    except sqlite3.Error as e:
        print(e)


def create_request(conn, player) -> int:
    sql = """INSERT INTO quests(player, description, reward)
             VALUES(?,?,?)"""
    cur = conn.cursor()

    # Check if there is an existing record with the same player and null description and reward
    existing_sql = """SELECT * FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
    cur.execute(existing_sql, (player,))
    existing_record = cur.fetchone()

    if existing_record:
        # Print the existing record and return -1
        print("Existing record:")
        for i, col in enumerate(existing_record):
            print(f"{cur.description[i][0]}: {col}")
        return -1

    # Insert new record with NULL description and reward
    cur.execute(sql, (player, None, None))
    conn.commit()

    # Return the id of the new record
    return cur.lastrowid


def get_users_with_pending_requests(conn) -> list:
    sql = """SELECT player FROM quests WHERE description IS NULL AND reward IS NULL"""
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    return [row[0] for row in rows]


def get_user_request_id(conn, player) -> int:
    sql = """SELECT id FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
    cur = conn.cursor()
    cur.execute(sql, (player,))
    row = cur.fetchone()
    return row[0] if row else None


def get_user_active_quests(conn, player) -> list:
    sql = """SELECT * FROM quests WHERE player=? AND description IS NOT NULL AND reward IS NOT NULL"""
    cur = conn.cursor()
    cur.execute(sql, (player,))
    rows = cur.fetchall()
    return rows


def update_request(conn, player, description, reward) -> None:
    sql = """UPDATE quests
             SET description = ?,
                 reward = ?
             WHERE id = ?"""
    request_id = get_user_request_id(conn, player)
    cur = conn.cursor()
    cur.execute(sql, (description, reward, request_id))
    conn.commit()
