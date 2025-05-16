from os import environ
from dotenv import load_dotenv # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
import json

load_dotenv()

DB_PATH = environ.get('DATABASE_URL')

# Load role translations from translation.json
with open("translation.json", "r", encoding="utf-8") as f:
    translations = json.load(f)

role_mapping = translations["role_terms"]


def connect_to_db(db_path=DB_PATH):
    """
    Establish a connection to the PostgreSQL database and set the search path to 'game_data'.

    Args:
        db_path (str): Connection string for the database. Defaults to the `DATABASE_URL` environment variable.

    Returns:
        tuple: (connection, cursor) if successful; otherwise (None, None).
    """

    try:
        conn = psycopg2.connect(db_path)
        cur = conn.cursor()
        cur.execute("SET search_path TO game_data, public;")
        conn.commit()
        print("Connected to PostgreSQL and set search path to 'game_data'.")
        return conn, cur
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None, None
    

def create_tables(db_path=DB_PATH):
    """
    Create all required tables inside the 'game_data' schema in PostgreSQL.

    Args:
        db_path (str): Connection string to the database.
    """

    conn, cur = connect_to_db(db_path)
    if not conn:
        return
    
    try:
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
        print("Tables created successfully inside 'game_data' schema.")
    
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()

    finally:
        conn.close()


def insert_row(data, table, db_path=DB_PATH):
    """
    Inserts a row into a specified table in the 'game_data' schema.

    Args:
        data (dict): The column-value pairs to insert.
        table (str): The name of the target table.
        db_path (str): Database connection string (defaults to DB_PATH).

    Returns:
        transaction_id (int) or None: The inserted ID for tables that have a return column, otherwise None.
    """

    conn = cur = None  # Ensure conn is defined for finally block

    try:
        allowed_tables = {'transactions', 'status', 'history', 'calculator_history'}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")

        conn, cur = connect_to_db(db_path)
        if not conn:
            return None

        # ID column only applies to specific tables
        id_column = "transaction_id" if table in {'transactions', 'status'} else "id"

        query = sql.SQL("""
            INSERT INTO game_data.{table} ({columns}) 
            VALUES ({values}) 
            RETURNING {id_column}
        """).format(
            table=sql.Identifier(table),
            columns=sql.SQL(', ').join(map(sql.Identifier, data.keys())),
            values=sql.SQL(', ').join(sql.Placeholder() * len(data)),
            id_column=sql.Identifier(id_column)
        )

        cur.execute(query, list(data.values()))
        inserted_id = cur.fetchone()[0] if table in {'transactions', 'status'} else None

        conn.commit()
        print(
            f"Row inserted into '{table}' with ID {inserted_id}" 
            if inserted_id else f"Row inserted into '{table}'"
        )
        return inserted_id

    except psycopg2.Error as e:
        print(f"Database error while inserting into '{table}': {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


def get_points(transaction_id, db_path=DB_PATH):
    """
    Retrieve the number of points for a given transaction ID 
    from the 'game_data.transactions' table.

    Args:
        transaction_id (int): The ID of the transaction to look up.
        db_path (str): Connection string to the PostgreSQL database.

    Returns:
        int or None: The number of points, or None if not found or error occurs.
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
        print(f"Database error: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


def get_action(transaction_id, db_path=DB_PATH):
    """
    Retrieve the action associated with a given transaction ID 
    from the 'game_data.transactions' table.

    Args:
        transaction_id (int): The transaction ID to query.
        db_path (str): Optional PostgreSQL connection string.

    Returns:
        action (str) or None: The action (e.g. 'Ofrece', 'Solicita'), or None if not found or error.
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
        print(f"Database error: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


def add_balance(data, db_path=DB_PATH):
    """
    Update initiator and receiver balances in the 'game_data.transactions' table.

    Args:
        data (dict): Must include 'transaction_id', 'initiator_balance', and 'receiver_balance'.
        db_path (str): PostgreSQL connection string (optional).
    """

    conn = cur = None

    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return
        
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
        print(f"Balance updated for transaction {data['transaction_id']}")

    except psycopg2.Error as e:
        print(f"Database error while updating balance: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


def filter_transactions(data, db_path=DB_PATH):
    """
    Filters and retrieves transactions for a given participant in an oTree experiment,
    replacing initiator and receiver IDs with their corresponding role names.

    Args:
        data (dict): Must include:
            - 'participant_code' (str)
            - 'round' (int)
            - 'segment' (int)
            - 'session_code' (str)
        db_path (str): PostgreSQL connection string (default: DB_PATH)

    Returns:
        list of dict: Transactions with keys:
            - "Jugador": Role name of the initiator
            - "Acción": Action taken ("Ofrece", "Solicita")
            - "A": Role name of the receiver
            - "Puntos": Points transferred
            - "¿Se aceptó?": Final status ("Aceptado" or "Rechazado")
            - "Balance": Player's balance after transaction (if available)
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
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        return []

    
    finally:
        if conn:
            conn.close()


def filter_history(data, db_path=DB_PATH):
    """
    Retrieve the full round-by-round history of a participant within a segment.

    Args:
        data (dict): Must include:
            - 'session_code' (str)
            - 'segment' (int)
            - 'participant_code' (str)
        db_path (str): PostgreSQL connection string (default: DB_PATH)

    Returns:
        list of dict: One entry per round, with payoff breakdown and flags for timeout and audit.
    """
    
    conn = cur = None

    try:
        conn, cur = connect_to_db(db_path)
        if not conn:
            return []
    
        query = """
            SELECT 
                segment, 
                round, 
                participant_code, 
                endowment, 
                contribution, 
                public_good_gross_gain, 
                total_transfers_received, 
                total_transfers_given, 
                public_interaction_payoff, 
                private_interaction_payoff, 
                payment,
                timeout_penalty,  -- New field
                corruption_punishment  -- New field
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

        return [
            {
                "Segment": row[0],
                "Round": row[1],
                "Participant": row[2],
                "Endowment": row[3],
                "Contribution": row[4] or 0,
                "PublicGoodRawGain": row[5],
                "TotalTransfersReceived": row[6],
                "TotalTransfersGiven": row[7],
                "PublicInteractionPayoff": row[8],
                "PrivateInteractionPayoff": row[9],
                "Payment": row[10],
                "Timeout": row[11],
                "Audited": row[12]
            }
            for row in results
        ]

    except psycopg2.Error as e:
        print(f"Database error in filter_history: {e}")
        if conn:
            conn.rollback()
        return []

    finally:
        if conn:
            conn.close()


def get_last_transaction_status(participant_code, treatment_round, segment, session_code, db_path=DB_PATH):
    """
    Retrieves the latest transaction for a participant in the given session, round, and segment,
    ONLY if the most recent status is 'Iniciado' (i.e., still open).

    Args:
        participant_code (str): The participant's unique code.
        treatment_round (int): The round number within the treatment.
        segment (int): The experiment segment number.
        session_code (str): The session code identifier.
        db_path (str): PostgreSQL connection string (default: DB_PATH)

    Returns:
        dict: Dictionary with transaction details if the latest status is 'Iniciado',
            otherwise None.
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
            LIMIT 1;
        """

        cur.execute(query, (participant_code, participant_code, session_code, treatment_round, segment))
        result = cur.fetchone()

        if result:
            transaction_id, initiator_id, receiver_id, action, points, _ = result
            print(f"Last open transaction: {result}")
            return {
                'transactionId': transaction_id,
                'initiatorId': initiator_id,
                'receiverId': receiver_id,
                'action': action,
                'value': points
            }

        return None

    except psycopg2.Error as e:
        print(f"Database error while fetching last transaction: {e}")
        if conn:
            conn.rollback()
        return None

    finally:
        if conn:
            conn.close()


def total_transfers_per_player(data, db_path=DB_PATH):
    """
    Retrieves the total number of points received and given by a participant in a specific
    round, segment, and session. Only accepted transactions are included.

    Logic:
        - If participant is receiver and action is 'Ofrece' → received
        - If participant is initiator and action is 'Solicita' → received
        - If participant is initiator and action is 'Ofrece' → given
        - If participant is receiver and action is 'Solicita' → given

    Args:
        data (dict): Must include:
            - 'participant_code' (str)
            - 'round' (int)
            - 'segment' (int)
            - 'session_code' (str)
        db_path (str): PostgreSQL connection string (default: DB_PATH)

    Returns:
        dict: {
            'transfers_received': int,
            'transfers_given': int
        }
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
        AND s.status = 'Aceptado';
        """

        cur.execute(query, (
            data['participant_code'], # Receiver: Ofrece (Received)
            data['participant_code'], # Initiator: Solicita (Received)
            data['participant_code'], # Initiator: Ofrece (Given)
            data['participant_code'], # Receiver: Solicita (Given)
            data['segment'],
            data['round'],
            data.get('session_code', '') # Ensure session_code is included
        ))

        result = cur.fetchone()
        return {
            'transfers_received': result[0],
            'transfers_given': result[1]
        }

    except psycopg2.Error as e:
        print(f"Database error in total_transfers_per_player: {e}")
        if conn:
            conn.rollback()
        return {'transfers_received': 0, 'transfers_given': 0}

    finally:
        if conn:
            conn.close()


def check_corruption(data, db_path=DB_PATH):
    """
    Identifies potentially corrupt transfers between citizens (players 1, 2, 3) and 
    the public officer (player 4), considering only accepted transactions.

    Args:
        data (dict): Must include:
            - 'segment' (int)
            - 'round' (int)
            - 'session_code' (str)
            - 'group_id' (int)
        db_path (str): PostgreSQL connection string (default: DB_PATH)

    Returns:
        dict: For each citizen (1, 2, 3), reports:
            - 'transfers_from_citizen_to_officer' (int)
            - 'transfers_from_officer_to_citizen' (int)
        or:
            {'error': str} if something goes wrong
    """

    conn = cur = None

    CITIZENS = [1, 2, 3]
    OFFICER = 4

    corruption_data = {
        citizen_id: {
            'transfers_from_citizen_to_officer': 0,
            'transfers_from_officer_to_citizen': 0
        } for citizen_id in CITIZENS
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
            (t.initiator_id IN (1, 2, 3) AND t.receiver_id = 4) OR
            (t.initiator_id = 4 AND t.receiver_id IN (1, 2, 3))
          );
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

        for initiator_id, receiver_id, action, points in cur.fetchall():
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
        print(f"Database error in check_corruption: {e}")
        if conn:
            conn.rollback()
        return {'error': str(e)}

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()