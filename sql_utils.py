import sqlite3
from os import environ
from dotenv import load_dotenv # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore

load_dotenv()

DB_PATH = environ.get('DATABASE_URL')

def connect_to_db(db_path=DB_PATH):
    """
    Establishes a connection to the PostgreSQL database and sets the search path to 'game_data'.
    """
    try:
        conn = psycopg2.connect(db_path)
        cur = conn.cursor()
        cur.execute("SET search_path TO game_data, public;")  # Ensure it looks in game_data first
        conn.commit()
        print("Connected to PostgreSQL and set search path to 'game_data'.")
        return conn, cur
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None, None
    

def create_tables(db_path=DB_PATH):
    """
    Creates tables inside the 'game_data' schema in PostgreSQL.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return

    # Create transactions table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_data.transactions (
            transaction_id SERIAL PRIMARY KEY,
            session_code TEXT NOT NULL,
            segment INTEGER NOT NULL,
            round INTEGER NOT NULL,
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

    # Create status table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_data.status (
            status_id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL REFERENCES game_data.transactions(transaction_id),
            status TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Create history table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_data.history (
            id SERIAL PRIMARY KEY,
            session_code TEXT NOT NULL,
            segment INTEGER NOT NULL,
            round INTEGER NOT NULL,
            participant_code TEXT NOT NULL,
            endowment INTEGER NOT NULL,
            contribution INTEGER,
            public_good_raw_gain INTEGER,
            total_transfers_received INTEGER NOT NULL,
            total_transfers_given INTEGER NOT NULL,
            payment INTEGER NOT NULL
        );
    ''')
            # FOREIGN KEY (participant_code) REFERENCES public.otree_participant(code) This makes error

    conn.commit()
    conn.close()

    print("Tables created successfully inside 'game_data' schema.")


def insert_row(data, table, db_path=DB_PATH):
    """
    Inserts a row into a specified table in the 'game_data' schema.
    """
    try:
        allowed_tables = {'transactions', 'status', 'history'}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")

        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        # Determine the ID column to return
        id_column = "transaction_id" if table in {'transactions', 'status'} else "id"

        query = sql.SQL("INSERT INTO game_data.{table} ({columns}) VALUES ({values}) RETURNING {id_column}").format(
            table=sql.Identifier(table),
            columns=sql.SQL(', ').join(map(sql.Identifier, data.keys())),
            values=sql.SQL(', ').join(sql.Placeholder() * len(data)),
            id_column=sql.Identifier(id_column)
        )

        cur.execute(query, list(data.values()))
        inserted_id = cur.fetchone()[0] if table in {'transactions', 'status'} else None  # Avoid returning an ID for history

        conn.commit()
        print(f"Row inserted into '{table}' with ID {inserted_id}" if inserted_id else f"Row inserted into '{table}'")
        return inserted_id

    except psycopg2.Error as e:
        print(f"Database error while inserting into '{table}': {e}")
    finally:
        conn.close()


def get_points(transaction_id, db_path=DB_PATH):
    """
    Retrieves the points associated with a given transaction ID from 'game_data.transactions'.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return None

    try:
        cur.execute("SELECT points FROM game_data.transactions WHERE transaction_id = %s", (transaction_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def get_action(transaction_id, db_path=DB_PATH):
    """
    Retrieves the points associated with a given transaction ID from 'game_data.transactions'.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return None

    try:
        cur.execute("SELECT action FROM game_data.transactions WHERE transaction_id = %s", (transaction_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def add_balance(data, db_path=DB_PATH):
    """
    Updates initiator_balance and receiver_balance in 'game_data.transactions'.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return

    try:
        cur.execute("""
            UPDATE game_data.transactions
            SET initiator_balance = %s, receiver_balance = %s
            WHERE transaction_id = %s
        """, (data['initiator_balance'], data['receiver_balance'], data['transaction_id']))
        
        conn.commit()
        print(f"Balance updated for transaction {data['transaction_id']}")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def filter_transactions(data, db_path=DB_PATH):
    """
    Filters transactions for a given participant, round, segment, and session.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return []

    try:
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
                "Jugador": row[0],
                "Acción": row[1],
                "A": row[2],
                "Puntos": row[3],
                "¿Se aceptó?": row[5],
                "Balance": row[4],
            }
            for row in results
        ]

        return transactions 

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return []
    
    finally:
        conn.close()


def filter_history(data, db_path=DB_PATH):
    """
    Retrieves the full history of a participant within a given segment across all rounds.

    :param data: Dictionary containing 'session_code', 'segment', 'participant_code'.
    :return: List of dictionaries containing the player's history for all rounds in the segment.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return []

    try:
        query = """
        SELECT 
            segment, 
            round, 
            participant_code, 
            endowment, 
            contribution, 
            public_good_raw_gain, 
            total_transfers_received, 
            total_transfers_given, 
            payment
        FROM game_data.history
        WHERE session_code = %s
        AND segment = %s
        AND participant_code = %s
        ORDER BY round ASC;  -- Ensure rounds are in chronological order
        """

        cur.execute(query, (
            data['session_code'],
            data['segment'],
            data['participant_code']
        ))

        results = cur.fetchall()

        history_records = [
            {
                "Segment": row[0],
                "Round": row[1],
                "Participant": row[2],
                "Endowment": row[3],
                "Contribution": row[4],
                "PublicGoodRawGain": row[5],
                "TotalTransfersReceived": row[6],
                "TotalTransfersGiven": row[7],
                "Payment": row[8]
            }
            for row in results
        ]

        return history_records if history_records else []

    except psycopg2.Error as e:
        print(f"Database error in filter_history: {e}")
        return []

    finally:
        conn.close()


def get_last_transaction_status(participant_code, round_number, segment, session_code, db_path=DB_PATH):
    """
    Retrieves the latest transaction ID for a participant in the current session, round, and segment,
    ensuring that it is still 'Iniciado' and has not been closed.

    :param participant_code: The participant's unique code.
    :param round_number: The current round number.
    :param segment: The current segment.
    :param session_code: The session code.
    :return: Dictionary with transaction details if 'Iniciado' and not closed, otherwise None.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return None

    try:
        # Find the latest transaction where the participant is the initiator or receiver
        query = """
        SELECT 
            t.transaction_id,
            t.initiator_id,
            t.receiver_id,
            t.action,
            t.points,
            s.status,
            COUNT(*) FILTER (WHERE s.status = 'Iniciado') AS status_count
        FROM game_data.transactions t
        JOIN game_data.status s ON t.transaction_id = s.transaction_id
        WHERE (t.initiator_code = %s OR t.receiver_code = %s)
        AND t.session_code = %s
        AND t.round = %s
        AND t.segment = %s
        GROUP BY t.transaction_id, t.initiator_id, t.receiver_id, t.action, t.points, s.status
        ORDER BY t.transaction_id DESC  -- Get the latest transaction in this session/round/segment
        LIMIT 1;
        """

        cur.execute(query, (participant_code, participant_code, session_code, round_number, segment))
        result = cur.fetchone()

        if result:
            transaction_id, initiator_id, receiver_id, action, points, status, status_count = result
            print(f"Last Transaction in Current Round & Segment: {result}")

            # The transaction is open if its only status is 'Iniciado'
            if status == 'Iniciado' and status_count == 1:
                return {
                    'transactionId': transaction_id,
                    'initiatorId': initiator_id,
                    'receiverId': receiver_id,
                    'action': action,
                    'value': points
                }

        return None  # No active transaction in this session/round/segment

    except psycopg2.Error as e:
        print(f"Database error while fetching last transaction: {e}")
        return None

    finally:
        conn.close()


def total_transfers_per_player(data, db_path=DB_PATH):
    """
    Retrieves the total number of transfers received and given for a player 
    in a specific segment, round, and session, ensuring that:
    
    - If `receiver_code` and `action = 'Ofrece'`, it counts as `transfers_received`.
    - If `receiver_code` and `action = 'Solicita'`, it counts as `transfers_given`.
    - If `initiator_code` and `action = 'Ofrece'`, it counts as `transfers_given`.
    - If `initiator_code` and `action = 'Solicita'`, it counts as `transfers_received`.

    :param data: Dictionary containing 'segment', 'round', 'participant_code', 'session_code'.
    :return: Dictionary with total_transfers_received and total_transfers_given.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return {'transfers_received': 0, 'transfers_given': 0}

    try:
        query = """
        SELECT 
            COALESCE(SUM(
                CASE 
                    WHEN t.receiver_code = %s AND t.action = 'Ofrece' THEN t.points  -- Receiver gains from 'Ofrece'
                    WHEN t.initiator_code = %s AND t.action = 'Solicita' THEN t.points  -- Initiator gains from 'Solicita'
                    ELSE 0 
                END
            ), 0) AS transfers_received,

            COALESCE(SUM(
                CASE 
                    WHEN t.initiator_code = %s AND t.action = 'Ofrece' THEN t.points  -- Initiator loses from 'Ofrece'
                    WHEN t.receiver_code = %s AND t.action = 'Solicita' THEN t.points  -- Receiver loses from 'Solicita'
                    ELSE 0 
                END
            ), 0) AS transfers_given

        FROM game_data.transactions t
        JOIN game_data.status s ON t.transaction_id = s.transaction_id
        WHERE t.segment = %s
        AND t.round = %s
        AND t.session_code = %s
        AND s.status = 'Aceptado';  -- Only include completed transactions
        """

        cur.execute(query, (
            data['participant_code'],  # Receiver: Ofrece (Received)
            data['participant_code'],  # Initiator: Solicita (Received)
            data['participant_code'],  # Initiator: Ofrece (Given)
            data['participant_code'],  # Receiver: Solicita (Given)
            data['segment'],
            data['round'],
            data.get('session_code', '')  # Ensure session_code is included
        ))

        result = cur.fetchone()
        return {
            'transfers_received': result[0],
            'transfers_given': result[1]
        }

    except psycopg2.Error as e:
        print(f"Database error in total_transfers_per_player: {e}")
        return {'transfers_received': 0, 'transfers_given': 0}

    finally:
        conn.close()
