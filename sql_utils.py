"""
Storage for the custom `game_data` schema (PostgreSQL).

oTree keeps its own models in the `public` schema; everything here lives in
`game_data`, which `otree resetdb` does not touch. Every row carries the keys
needed to join it back to the oTree export (see LINKAGE_COLUMNS), so the data
stays usable after a reset or across many sessions.

Tables:
    sessions            One row per session: config, treatment order, demo flag.
    transactions        One row per offer/request between two players.
    status              Status events per transaction (Iniciado, then Aceptado /
                        Rechazado / Cancelado / Fallido). The latest row is the
                        current status.
    history             One row per participant per round: payoff breakdown.
    calculator_history  Every calculator operation typed by the officer.
    messages            Every chat and system (TransferInfo) message.
"""

from contextlib import contextmanager
from os import environ
from pathlib import Path
import copy
import functools
import json

from dotenv import load_dotenv # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
from psycopg2 import pool as pg_pool # type: ignore
from psycopg2.extras import RealDictCursor # type: ignore

load_dotenv()

DB_PATH = environ.get('DATABASE_URL')

with open(Path(__file__).with_name('translation.json'), encoding='utf-8') as f:
    role_mapping = json.load(f)['role_terms']

CITIZENS = (1, 2, 3)
OFFICER = 4


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# Primary key of each table. Also the whitelist of tables insert_row() accepts.
TABLE_KEYS = {
    'sessions': 'session_code',
    'transactions': 'transaction_id',
    'status': 'status_id',
    'history': 'id',
    'calculator_history': 'id',
    'messages': 'id',
}

# Tables as first deployed. Columns added later live in LINKAGE_COLUMNS, so the
# same code both creates a fresh database and upgrades an existing one.
_CREATE_TABLES = '''
    CREATE SCHEMA IF NOT EXISTS game_data;

    CREATE TABLE IF NOT EXISTS game_data.sessions (
        session_code TEXT PRIMARY KEY,
        config_name TEXT,
        label TEXT,
        is_demo BOOLEAN,
        num_participants INTEGER,
        treatment_order TEXT,
        rounds_per_treatment INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS game_data.transactions (
        transaction_id SERIAL PRIMARY KEY,
        session_code TEXT NOT NULL,
        segment INTEGER NOT NULL,
        round INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        initiator_code TEXT NOT NULL,
        receiver_code TEXT NOT NULL,
        initiator_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        points INTEGER NOT NULL,
        initiator_initial_endowment INTEGER,  -- balance when the transaction was opened
        receiver_initial_endowment INTEGER,
        initiator_balance INTEGER,            -- balance when it was closed
        receiver_balance INTEGER
    );

    CREATE TABLE IF NOT EXISTS game_data.status (
        status_id SERIAL PRIMARY KEY,
        transaction_id INTEGER NOT NULL REFERENCES game_data.transactions(transaction_id),
        status TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS game_data.history (
        id SERIAL PRIMARY KEY,
        session_code TEXT NOT NULL,
        segment INTEGER NOT NULL,
        round INTEGER NOT NULL,
        participant_code TEXT NOT NULL,
        endowment INTEGER NOT NULL,
        contribution INTEGER,
        total_public_goods FLOAT,
        public_good_gross_gain FLOAT,
        public_interaction_payoff FLOAT NOT NULL,
        total_transfers_received INTEGER NOT NULL,
        total_transfers_given INTEGER NOT NULL,
        private_interaction_payoff INTEGER NOT NULL,
        payment FLOAT NOT NULL,
        timeout_penalty BOOLEAN NOT NULL,
        corruption_punishment BOOLEAN NOT NULL
    );

    CREATE TABLE IF NOT EXISTS game_data.calculator_history (
        id SERIAL PRIMARY KEY,
        session_code TEXT NOT NULL,
        segment INTEGER NOT NULL,
        round INTEGER NOT NULL,
        participant_code TEXT NOT NULL,
        operation TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS game_data.messages (
        id SERIAL PRIMARY KEY,
        session_code TEXT NOT NULL,
        segment INTEGER NOT NULL,
        round INTEGER NOT NULL,
        round_number INTEGER NOT NULL,
        treatment TEXT NOT NULL,
        group_id INTEGER NOT NULL,
        group_id_in_subsession INTEGER NOT NULL,
        channel TEXT NOT NULL,
        sender_code TEXT NOT NULL,
        recipient_code TEXT NOT NULL,
        sender_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        text TEXT,
        transaction_id INTEGER REFERENCES game_data.transactions(transaction_id),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
'''

# Columns that let every row be joined back to the oTree export
# (`subsession.round_number`, `group.id_in_subsession`, `player.id_in_group`)
# even after `otree resetdb` wipes oTree's own tables. `group_id` is oTree's
# internal database key: fine for live lookups, but it is not in the export and
# restarts after a reset. These were added after the first sessions were run,
# so rows written before then have NULL in them.
_ROUND_COLUMNS = [
    ('round_number', 'INTEGER'),            # oTree round (1..NUM_ROUNDS), not the round within the treatment
    ('treatment', 'TEXT'),
    ('group_id_in_subsession', 'INTEGER'),  # = group.id_in_subsession in the oTree export
]
_PLAYER_COLUMNS = _ROUND_COLUMNS + [
    ('group_id', 'INTEGER'),
    ('id_in_group', 'INTEGER'),
]
LINKAGE_COLUMNS = {
    'transactions': _ROUND_COLUMNS + [('timestamp', 'TIMESTAMP')],
    'history': _PLAYER_COLUMNS + [('timestamp', 'TIMESTAMP')],
    'calculator_history': _PLAYER_COLUMNS,
}

# Indexes for the lookups the live game runs on every action, plus one rule
# the data must obey. NULLs never collide in a unique index, so rows from
# before round_number existed don't block it.
_CREATE_INDEXES = '''
    CREATE INDEX IF NOT EXISTS status_by_transaction
        ON game_data.status (transaction_id, status_id);
    CREATE INDEX IF NOT EXISTS transactions_by_round
        ON game_data.transactions (session_code, segment, round);
    CREATE INDEX IF NOT EXISTS history_by_participant
        ON game_data.history (session_code, segment, participant_code);
    CREATE UNIQUE INDEX IF NOT EXISTS history_one_row_per_round
        ON game_data.history (session_code, round_number, participant_code);
'''


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

# Live gameplay hits the database on every offer/accept/reject/chat message,
# so connections are pooled rather than opened per call. One pool, created
# lazily on first use, is shared for the life of the process.
#
# oTree runs requests and live methods one at a time per process, so only one
# connection is in use at any moment. The cap is a ceiling, kept low so that
# every process's pool plus oTree's own connections stay under small hosted
# Postgres plans' connection limits (about 20 on Heroku's smallest plans).
_POOL_MIN_CONNECTIONS = 2
_POOL_MAX_CONNECTIONS = 5
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pg_pool.ThreadedConnectionPool(_POOL_MIN_CONNECTIONS, _POOL_MAX_CONNECTIONS, DB_PATH)
    return _pool


@contextmanager
def _cursor():
    """
    Borrow a pooled connection for one database transaction. Commits if the
    block succeeds, rolls back if it raises, and always returns the connection.
    Rows are returned as dicts keyed by column name.
    """

    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        # A connection the server dropped (e.g. Postgres restarted) is discarded
        # instead of being handed to the next caller.
        pool.putconn(conn, close=bool(conn.closed))


def _logs_db_errors(fallback):
    """
    A database failure must never crash a live session, so the decorated
    function logs it and returns a copy of `fallback` instead.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except psycopg2.Error as e:
                print(f"Database error in {func.__name__}: {e}")
                return copy.copy(fallback)
        return wrapper
    return decorator


def _insert(cur, table, data, ignore_duplicates=False):
    """
    Insert one row inside an open transaction.

    Returns:
        The new row's primary key, or None if `ignore_duplicates` skipped it.
    """

    if table not in TABLE_KEYS:
        raise ValueError(f"Invalid table name: {table}")

    query = sql.SQL('INSERT INTO game_data.{table} ({columns}) VALUES ({values}) {conflict} RETURNING {key}').format(
        table=sql.Identifier(table),
        columns=sql.SQL(', ').join(map(sql.Identifier, data.keys())),
        values=sql.SQL(', ').join(sql.Placeholder() * len(data)),
        conflict=sql.SQL('ON CONFLICT DO NOTHING' if ignore_duplicates else ''),
        key=sql.Identifier(TABLE_KEYS[table]),
    )
    cur.execute(query, list(data.values()))
    row = cur.fetchone()
    return row[TABLE_KEYS[table]] if row else None


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

@_logs_db_errors(fallback=None)
def create_tables():
    """
    Create the 'game_data' schema, or upgrade an existing one in place. Safe to
    run on every server start.
    """

    with _cursor() as cur:
        cur.execute(_CREATE_TABLES)

        for table, columns in LINKAGE_COLUMNS.items():
            for column, column_type in columns:
                cur.execute(sql.SQL('ALTER TABLE game_data.{} ADD COLUMN IF NOT EXISTS {} ' + column_type).format(
                    sql.Identifier(table), sql.Identifier(column)
                ))
                # Set apart from ADD COLUMN so existing rows keep NULL instead
                # of being stamped with the time of the upgrade.
                if column == 'timestamp':
                    cur.execute(sql.SQL('ALTER TABLE game_data.{} ALTER COLUMN timestamp SET DEFAULT CURRENT_TIMESTAMP').format(
                        sql.Identifier(table)
                    ))

        cur.execute(_CREATE_INDEXES)

    print("Tables created successfully inside 'game_data' schema.")


@_logs_db_errors(fallback=None)
def insert_row(data, table):
    """
    Insert one row into a 'game_data' table.

    Args:
        data (dict): Column-value pairs to insert.
        table (str): One of TABLE_KEYS.

    Returns:
        The new row's primary key, or None on error.
    """

    with _cursor() as cur:
        return _insert(cur, table, data)


@_logs_db_errors(fallback=None)
def register_session(data):
    """
    Record a session's configuration. Later calls for the same session are ignored.

    Args:
        data (dict): Column-value pairs for 'game_data.sessions'; must include 'session_code'.
    """

    with _cursor() as cur:
        _insert(cur, 'sessions', data, ignore_duplicates=True)


@_logs_db_errors(fallback=None)
def open_transaction(data):
    """
    Record a new offer/request together with its 'Iniciado' status, atomically.

    Args:
        data (dict): Column-value pairs for 'game_data.transactions'.

    Returns:
        int or None: The new transaction_id, or None on error.
    """

    with _cursor() as cur:
        transaction_id = _insert(cur, 'transactions', data)
        _insert(cur, 'status', {'transaction_id': transaction_id, 'status': 'Iniciado'})
        return transaction_id


@_logs_db_errors(fallback=None)
def close_transaction(transaction_id, status, initiator_balance, receiver_balance):
    """
    Record how a transaction ended, and both players' balances at that moment,
    atomically.

    Args:
        transaction_id (int): The transaction being closed.
        status (str): 'Aceptado', 'Rechazado', 'Cancelado' or 'Fallido'.
        initiator_balance (int): Initiator's points after the transaction.
        receiver_balance (int): Receiver's points after the transaction.
    """

    with _cursor() as cur:
        cur.execute("""
            UPDATE game_data.transactions
            SET initiator_balance = %s, receiver_balance = %s
            WHERE transaction_id = %s
        """, (initiator_balance, receiver_balance, transaction_id))
        _insert(cur, 'status', {'transaction_id': transaction_id, 'status': status})


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

@_logs_db_errors(fallback=None)
def get_transaction(transaction_id):
    """
    Returns:
        dict or None: Keys 'points', 'action', 'initiator_id', 'receiver_id',
        'group_id' and 'status' (the latest one); None if not found or on error.
    """

    with _cursor() as cur:
        cur.execute("""
            SELECT t.points, t.action, t.initiator_id, t.receiver_id, t.group_id, latest.status
            FROM game_data.transactions t
            JOIN LATERAL (
                SELECT status
                FROM game_data.status
                WHERE transaction_id = t.transaction_id
                ORDER BY status_id DESC
                LIMIT 1
            ) latest ON true
            WHERE t.transaction_id = %s
        """, (transaction_id,))
        return cur.fetchone()


@_logs_db_errors(fallback=[])
def filter_transactions(data):
    """
    A participant's finished (accepted or rejected) transactions in one round,
    formatted for the transactions table on screen.

    Args:
        data (dict): Must include 'participant_code', 'round', 'segment', 'session_code'.

    Returns:
        list of dict: Keys "Jugador", "Acción", "A", "Puntos", "¿Se aceptó?", "Balance".
    """

    with _cursor() as cur:
        cur.execute("""
            SELECT
                t.initiator_id,
                t.action,
                t.receiver_id,
                t.points,
                CASE
                    WHEN t.initiator_code = %(participant_code)s THEN t.initiator_balance
                    ELSE t.receiver_balance
                END AS balance,
                s.status
            FROM game_data.transactions t
            JOIN game_data.status s ON t.transaction_id = s.transaction_id
            WHERE (t.initiator_code = %(participant_code)s OR t.receiver_code = %(participant_code)s)
              AND t.round = %(round)s
              AND t.segment = %(segment)s
              AND t.session_code = %(session_code)s
              AND s.status IN ('Aceptado', 'Rechazado')
            ORDER BY t.transaction_id
        """, data)

        return [
            {
                "Jugador": role_mapping.get(str(row['initiator_id']), f"Jugador {row['initiator_id']}"),
                "Acción": row['action'],
                "A": role_mapping.get(str(row['receiver_id']), f"Jugador {row['receiver_id']}"),
                "Puntos": row['points'],
                "¿Se aceptó?": row['status'],
                "Balance": row['balance'],
            }
            for row in cur.fetchall()
        ]


# Display label -> history column. Shared by filter_history() and by the
# per-participant history cache in public_goods, so both produce the same rows.
HISTORY_DISPLAY_FIELDS = {
    "Segment": 'segment',
    "Round": 'round',
    "Participant": 'participant_code',
    "Endowment": 'endowment',
    "Contribution": 'contribution',
    "TotalPublicGoods": 'total_public_goods',
    "PublicGoodGrossGain": 'public_good_gross_gain',
    "TotalTransfersReceived": 'total_transfers_received',
    "TotalTransfersGiven": 'total_transfers_given',
    "PublicInteractionPayoff": 'public_interaction_payoff',
    "PrivateInteractionPayoff": 'private_interaction_payoff',
    "Payment": 'payment',
    "Timeout": 'timeout_penalty',
    "Audited": 'corruption_punishment',
}


def history_display_row(row):
    """Convert a history row (dict keyed by column name) into its on-screen form."""

    display = {label: row[column] for label, column in HISTORY_DISPLAY_FIELDS.items()}
    display["Contribution"] = display["Contribution"] or 0
    return display


@_logs_db_errors(fallback=[])
def filter_history(data):
    """
    A participant's round-by-round history within one segment, oldest first.

    Args:
        data (dict): Must include 'session_code', 'segment', 'participant_code'.

    Returns:
        list of dict: One history_display_row() per round.
    """

    with _cursor() as cur:
        cur.execute(sql.SQL("""
            SELECT {columns}
            FROM game_data.history
            WHERE session_code = %(session_code)s
              AND segment = %(segment)s
              AND participant_code = %(participant_code)s
            ORDER BY round
        """).format(
            columns=sql.SQL(', ').join(map(sql.Identifier, HISTORY_DISPLAY_FIELDS.values()))
        ), data)

        return [history_display_row(row) for row in cur.fetchall()]


@_logs_db_errors(fallback=None)
def get_last_transaction_status(participant_code, treatment_round, segment, session_code):
    """
    The participant's most recent transaction in this round, but only if it is
    still open (its latest status is 'Iniciado'). Used to restore the UI after a
    page reload.

    Returns:
        dict or None: Keys 'transactionId', 'initiatorId', 'receiverId', 'action', 'value'.
    """

    with _cursor() as cur:
        cur.execute("""
            SELECT t.transaction_id, t.initiator_id, t.receiver_id, t.action, t.points
            FROM game_data.transactions t
            JOIN LATERAL (
                SELECT status
                FROM game_data.status
                WHERE transaction_id = t.transaction_id
                ORDER BY status_id DESC
                LIMIT 1
            ) latest ON true
            WHERE (t.initiator_code = %(code)s OR t.receiver_code = %(code)s)
              AND t.session_code = %(session_code)s
              AND t.round = %(round)s
              AND t.segment = %(segment)s
              AND latest.status = 'Iniciado'
            ORDER BY t.transaction_id DESC
            LIMIT 1
        """, {
            'code': participant_code,
            'session_code': session_code,
            'round': treatment_round,
            'segment': segment,
        })

        row = cur.fetchone()
        if not row:
            return None

        return {
            'transactionId': row['transaction_id'],
            'initiatorId': row['initiator_id'],
            'receiverId': row['receiver_id'],
            'action': row['action'],
            'value': row['points'],
        }


@_logs_db_errors(fallback={})
def check_corruption(data):
    """
    Total points each citizen gave to and received from the officer through
    accepted transactions in one round.

    Args:
        data (dict): Must include 'segment', 'round', 'session_code', 'group_id'.

    Returns:
        dict: {citizen_id: {'transfers_from_citizen_to_officer': int,
                            'transfers_from_officer_to_citizen': int}},
              or {} on error.
    """

    totals = {
        citizen: {'transfers_from_citizen_to_officer': 0, 'transfers_from_officer_to_citizen': 0}
        for citizen in CITIZENS
    }

    with _cursor() as cur:
        cur.execute("""
            SELECT t.initiator_id, t.receiver_id, t.action, t.points
            FROM game_data.transactions t
            JOIN game_data.status s ON t.transaction_id = s.transaction_id
            WHERE t.segment = %(segment)s
              AND t.round = %(round)s
              AND t.session_code = %(session_code)s
              AND t.group_id = %(group_id)s
              AND s.status = 'Aceptado'
        """, data)

        for row in cur.fetchall():
            # 'Ofrece': the initiator pays. 'Solicita': the initiator is paid.
            if row['action'] == 'Ofrece':
                payer, payee = row['initiator_id'], row['receiver_id']
            else:
                payer, payee = row['receiver_id'], row['initiator_id']

            if payer in CITIZENS and payee == OFFICER:
                totals[payer]['transfers_from_citizen_to_officer'] += row['points']
            elif payer == OFFICER and payee in CITIZENS:
                totals[payee]['transfers_from_officer_to_citizen'] += row['points']

    return totals
