# db_helpers.py
import os
import json
from dotenv import load_dotenv  # type: ignore
import psycopg2  # type: ignore
from psycopg2 import sql  # type: ignore

load_dotenv()

# Load role translations from translation.json
with open("translation.json", "r", encoding="utf-8") as f:
    translations = json.load(f)

role_mapping = translations.get("role_terms", {})

# Allowed tables and id column mapping
_ALLOWED_TABLES = {"transactions", "status", "history", "calculator_history"}
_ID_COLUMN_MAP = {
    "transactions": "transaction_id",
    "status": "status_id",
    "history": "id",
    "calculator_history": "id",
}


def get_db_path():
    """Obtain DATABASE_URL at runtime and validate."""
    db_path = os.environ.get("DATABASE_URL")
    if not db_path:
        raise RuntimeError("DATABASE_URL environment variable is not set or empty")
    return db_path


def _debug_print_prefix():
    """Return a short debug prefix with PID for logs."""
    return f"[DB PID={os.getpid()}]"


def connect_to_db(db_path=None):
    """
    Establish a new connection to PostgreSQL and set search_path to game_data.
    Returns (conn, cur) or (None, None) on failure.
    """
    try:
        if db_path is None:
            db_path = get_db_path()
    except Exception as e:
        print(_debug_print_prefix(), "Error obtaining DATABASE_URL:", e)
        return None, None

    # Debug: show a repr of db_path (safe for debugging; remove in prod if secret concerns)
    print(_debug_print_prefix(), "Connecting using db_path:", repr(db_path))

    try:
        conn = psycopg2.connect(db_path)
        cur = conn.cursor()
        # Set search path for this session/connection
        cur.execute("SET search_path TO game_data, public;")
        conn.commit()
        print(_debug_print_prefix(), "Connected to PostgreSQL and set search path to 'game_data'.")
        return conn, cur
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Error connecting to PostgreSQL database:", e)
        return None, None


def create_tables(db_path=None):
    """
    Create required tables inside the 'game_data' schema.
    Uses short-lived connection via psycopg2.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return

        cur.execute('CREATE SCHEMA IF NOT EXISTS game_data')

        # Transactions table
        cur.execute('''
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
                initiator_initial_endowment INTEGER,
                receiver_initial_endowment INTEGER,
                initiator_balance INTEGER,
                receiver_balance INTEGER
            );
        ''')

        # Status table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_data.status (
                status_id SERIAL PRIMARY KEY,
                transaction_id INTEGER NOT NULL REFERENCES game_data.transactions(transaction_id),
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # History table
        cur.execute('''
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
        ''')

        # Calculator history table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_data.calculator_history (
                id SERIAL PRIMARY KEY,
                session_code TEXT NOT NULL,
                segment INTEGER NOT NULL,
                round INTEGER NOT NULL,
                participant_code TEXT NOT NULL,
                operation TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()
        print(_debug_print_prefix(), "Tables created successfully inside 'game_data' schema.")
    except Exception as e:
        print(_debug_print_prefix(), "Error creating tables:", e)
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def insert_row(data, table, db_path=None):
    """
    Inserts a row into a specified table in the 'game_data' schema.
    Returns the inserted id for tables that return one, otherwise None.
    """
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table}")

    if not data:
        raise ValueError("Data dictionary is empty")

    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        id_column = _ID_COLUMN_MAP.get(table, "id")
        columns = list(data.keys())
        values = list(data.values())

        query = sql.SQL("""
            INSERT INTO game_data.{table} ({columns})
            VALUES ({values})
            RETURNING {id_column}
        """).format(
            table=sql.Identifier(table),
            columns=sql.SQL(', ').join(map(sql.Identifier, columns)),
            values=sql.SQL(', ').join(sql.Placeholder() for _ in columns),
            id_column=sql.Identifier(id_column)
        )

        cur.execute(query, values)
        try:
            inserted_id = cur.fetchone()[0]
        except Exception:
            inserted_id = None

        conn.commit()

        if inserted_id is not None:
            print(_debug_print_prefix(), f"Row inserted into '{table}' with ID {inserted_id}")
        else:
            print(_debug_print_prefix(), f"Row inserted into '{table}' (no id returned)")

        return inserted_id
    except psycopg2.Error as e:
        print(_debug_print_prefix(), f"Database error while inserting into '{table}': {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_points(transaction_id, db_path=None):
    """
    Retrieve the number of points for a given transaction ID.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        cur.execute(
            "SELECT points FROM game_data.transactions WHERE transaction_id = %s",
            (transaction_id,)
        )
        result = cur.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in get_points:", e)
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_action(transaction_id, db_path=None):
    """
    Retrieve the action for a given transaction ID.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        cur.execute(
            "SELECT action FROM game_data.transactions WHERE transaction_id = %s",
            (transaction_id,)
        )
        result = cur.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in get_action:", e)
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def add_balance(data, db_path=None):
    """
    Update initiator and receiver balances in transactions.
    Expects data to contain 'transaction_id', 'initiator_balance', 'receiver_balance'.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return False

        cur.execute("""
            UPDATE game_data.transactions
            SET initiator_balance = %s, receiver_balance = %s
            WHERE transaction_id = %s
        """, (
            data['initiator_balance'],
            data['receiver_balance'],
            data['transaction_id']
        ))

        conn.commit()
        print(_debug_print_prefix(), f"Balance updated for transaction {data.get('transaction_id')}")
        return True
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error while updating balance:", e)
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def filter_transactions(data, db_path=None):
    """
    Return list of mapped transactions for a given participant/round/segment/session.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return []

        query = """
            SELECT
                t.initiator_id,
                t.action,
                t.receiver_id,
                t.points,
                CASE
                    WHEN t.initiator_code = %(participant_code)s THEN t.initiator_balance
                    WHEN t.receiver_code = %(participant_code)s THEN t.receiver_balance
                    ELSE NULL
                END AS total_balance,
                s.status
            FROM game_data.transactions t
            LEFT JOIN game_data.status s ON t.transaction_id = s.transaction_id
            WHERE (t.initiator_code = %(participant_code)s OR t.receiver_code = %(participant_code)s)
              AND t.round = %(round)s
              AND t.segment = %(segment)s
              AND t.session_code = %(session_code)s
              AND s.status IN ('Aceptado', 'Rechazado')
        """

        cur.execute(query, data)
        results = cur.fetchall()

        transactions = [
            {
                "Jugador": role_mapping.get(str(row[0]), f"Jugador {row[0]}"),
                "Acción": row[1],
                "A": role_mapping.get(str(row[2]), f"Jugador {row[2]}"),
                "Puntos": row[3],
                "¿Se aceptó?": row[5],
                "Balance": row[4],
            }
            for row in results
        ]
        return transactions
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in filter_transactions:", e)
        if conn:
            conn.rollback()
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def filter_history(data, db_path=None):
    """
    Retrieve participant history rows.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return []

        query = """
            SELECT 
                segment, round, participant_code, endowment, contribution,
                total_public_goods, public_good_gross_gain,
                total_transfers_received, total_transfers_given,
                public_interaction_payoff, private_interaction_payoff, payment,
                timeout_penalty, corruption_punishment
            FROM game_data.history
            WHERE session_code = %s
              AND segment = %s
              AND participant_code = %s
            ORDER BY round ASC
        """
        cur.execute(query, (
            data['session_code'],
            data['segment'],
            data['participant_code']
        ))
        results = cur.fetchall()

        return [
            {
                "Segment": row[0],
                "Round": row[1],
                "Participant": row[2],
                "Endowment": row[3],
                "Contribution": row[4] or 0,
                "TotalPublicGoods": row[5],
                "PublicGoodGrossGain": row[6],
                "TotalTransfersReceived": row[7],
                "TotalTransfersGiven": row[8],
                "PublicInteractionPayoff": row[9],
                "PrivateInteractionPayoff": row[10],
                "Payment": row[11],
                "Timeout": row[12],
                "Audited": row[13]
            }
            for row in results
        ]
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in filter_history:", e)
        if conn:
            conn.rollback()
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_last_transaction_status(participant_code, treatment_round, segment, session_code, db_path=None):
    """
    Retrieve latest open transaction for participant (status 'Iniciado').
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        query = """
            SELECT 
                t.transaction_id,
                t.initiator_id,
                t.receiver_id,
                t.action,
                t.points,
                s.status
            FROM game_data.transactions t
            JOIN LATERAL (
                SELECT status
                FROM game_data.status
                WHERE transaction_id = t.transaction_id
                ORDER BY status_id DESC
                LIMIT 1
            ) s ON true
            WHERE (t.initiator_code = %s OR t.receiver_code = %s)
              AND t.session_code = %s
              AND t.round = %s
              AND t.segment = %s
              AND s.status = 'Iniciado'
            ORDER BY t.transaction_id DESC
            LIMIT 1
        """
        cur.execute(query, (participant_code, participant_code, session_code, treatment_round, segment))
        result = cur.fetchone()

        if result:
            transaction_id, initiator_id, receiver_id, action, points, _ = result
            return {
                'transactionId': transaction_id,
                'initiatorId': initiator_id,
                'receiverId': receiver_id,
                'action': action,
                'value': points
            }
        return None
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in get_last_transaction_status:", e)
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def total_transfers_per_player(data, db_path=None):
    """
    Compute total transfers received and given by a participant in a round/segment/session.
    """
    conn = cur = None
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return {'transfers_received': 0, 'transfers_given': 0}

        query = """
            SELECT 
                COALESCE(SUM(
                    CASE 
                        WHEN t.receiver_code = %s AND t.action = 'Ofrece' THEN t.points
                        WHEN t.initiator_code = %s AND t.action = 'Solicita' THEN t.points
                        ELSE 0 
                    END
                ), 0) AS transfers_received,

                COALESCE(SUM(
                    CASE 
                        WHEN t.initiator_code = %s AND t.action = 'Ofrece' THEN t.points
                        WHEN t.receiver_code = %s AND t.action = 'Solicita' THEN t.points
                        ELSE 0 
                    END
                ), 0) AS transfers_given
            FROM game_data.transactions t
            JOIN game_data.status s ON t.transaction_id = s.transaction_id
            WHERE t.segment = %s
              AND t.round = %s
              AND t.session_code = %s
              AND s.status = 'Aceptado'
        """
        cur.execute(query, (
            data['participant_code'],
            data['participant_code'],
            data['participant_code'],
            data['participant_code'],
            data['segment'],
            data['round'],
            data.get('session_code', '')
        ))
        row = cur.fetchone()
        return {
            'transfers_received': row[0] or 0,
            'transfers_given': row[1] or 0
        }
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in total_transfers_per_player:", e)
        if conn:
            conn.rollback()
        return {'transfers_received': 0, 'transfers_given': 0}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def check_corruption(data, db_path=None):
    """
    Identify potentially corrupt transfers between citizens and the officer (player 4).
    """
    conn = cur = None
    CITIZENS = [1, 2, 3]
    OFFICER = 4

    corruption_data = {
        cid: {
            'transfers_from_citizen_to_officer': 0,
            'transfers_from_officer_to_citizen': 0
        } for cid in CITIZENS
    }

    query = """
        SELECT 
            t.initiator_id, t.receiver_id, t.action, t.points
        FROM game_data.transactions t
        JOIN game_data.status s ON t.transaction_id = s.transaction_id
        WHERE t.segment = %s
          AND t.round = %s
          AND t.session_code = %s
          AND t.group_id = %s
          AND s.status = 'Aceptado'
          AND (
            (t.initiator_id IN (1,2,3) AND t.receiver_id = 4) OR
            (t.initiator_id = 4 AND t.receiver_id IN (1,2,3))
          )
    """
    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return {'error': 'Database connection failed'}

        cur.execute(query, (
            data['segment'],
            data['round'],
            data['session_code'],
            data['group_id']
        ))
        rows = cur.fetchall()

        for initiator_id, receiver_id, action, points in rows:
            if initiator_id in CITIZENS and receiver_id == OFFICER:
                if action == 'Ofrece':
                    corruption_data[initiator_id]['transfers_from_citizen_to_officer'] += points
                elif action == 'Solicita':
                    corruption_data[initiator_id]['transfers_from_officer_to_citizen'] += points
            elif initiator_id == OFFICER and receiver_id in CITIZENS:
                if action == 'Ofrece':
                    corruption_data[receiver_id]['transfers_from_officer_to_citizen'] += points
                elif action == 'Solicita':
                    corruption_data[receiver_id]['transfers_from_citizen_to_officer'] += points

        return corruption_data
    except psycopg2.Error as e:
        print(_debug_print_prefix(), "Database error in check_corruption:", e)
        if conn:
            conn.rollback()
        return {'error': str(e)}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
