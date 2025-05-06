from os import environ
from dotenv import load_dotenv # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
import json

load_dotenv()

DB_PATH = environ.get('DATABASE_URL')

with open("translation.json", "r", encoding="utf-8") as f: # Load the role translations from translation.json
    translations = json.load(f)

role_mapping = translations["role_terms"]


def connect_to_db(db_path=DB_PATH):
    """
    Establishes a connection to the PostgreSQL database and sets the search path to 'game_data'.

    :params db_path: The path to the PostgreSQL database (default: `DB_PATH`).
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
    
    cur.execute('CREATE SCHEMA IF NOT EXISTS game_data')

    # Create transactions table
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
            public_good_raw_gain FLOAT,
            public_interaction_payoff FLOAT NOT NULL,
            total_transfers_received INTEGER NOT NULL,
            total_transfers_given INTEGER NOT NULL,
            private_interaction_payoff INTEGER NOT NULL,
            payment FLOAT NOT NULL,
            timeout_penalty BOOLEAN NOT NULL,
            corruption_punishment BOOLEAN NOT NULL
        );
    ''')

    # Create calculator history table
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
    conn.close()

    print("Tables created successfully inside 'game_data' schema.")


def insert_row(data, table, db_path=DB_PATH):
    """
    Inserts a row into a specified table in the 'game_data' schema.
    """
    try:
        allowed_tables = {'transactions', 'status', 'history', 'calculator_history'}
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
    Filters and retrieves transactions for a given participant in an oTree experiment,
    replacing initiator and receiver IDs with their corresponding role names.
    
    This function queries a PostgreSQL database to extract transaction records
    related to a specific participant, identified by `participant_code`, within
    a given round, segment, and session. It returns a list of formatted transactions,
    mapping player IDs to their respective roles.

    :params:
    -----------
    data : dict
        A dictionary containing the following keys:
        - `participant_code` (str): The unique identifier of the participant.
        - `round` (int): The round number of the experiment.
        - `segment` (int): The segment of the experiment.
        - `session_code` (str): The unique identifier of the session.
    db_path : str, optional
        The path to the PostgreSQL database (default: `DB_PATH`).

    :return Transactions:
    --------
    A list of transaction dictionaries with the following keys:
    - "Jugador" (str): The role name of the initiator.
    - "Acción" (str): The action taken.
    - "A" (str): The role name of the receiver.
    - "Puntos" (int): The number of points transferred.
    - "¿Se aceptó?" (str): The status of the transaction ('Aceptado' or 'Rechazado').
    - "Balance" (int or None): The participant's balance after the transaction, if applicable.

    Notes:
    ------
    - The function connects to a PostgreSQL database using `connect_to_db(db_path)`.
    - It filters transactions where the participant is either the initiator or the receiver.
    - Transactions are retrieved only if they belong to the specified round, segment,
      and session, and if their status is either 'Aceptado' or 'Rechazado'.
    - The function replaces player IDs with role names using `role_mapping`.
    - Any database errors are caught and printed, and an empty list is returned in case of failure.
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
                "Jugador": role_mapping.get(str(row[0]), f"Jugador {row[0]}"),  # Replace initiator_id with role
                "Acción": row[1],
                "A": role_mapping.get(str(row[2]), f"Jugador {row[2]}"),  # Replace receiver_id with role
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

    :param data: Dictionary containing `session_code`, `segment`, `participant_code`.
    :param db_path: Path to the PostSQL database.
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

        history_records = [
            {
                "Segment": row[0],
                "Round": row[1],
                "Participant": row[2],
                "Endowment": row[3],
                "Contribution": row[4] if row[4] is not None else 0,  # Handle None case
                "PublicGoodRawGain": row[5],
                "TotalTransfersReceived": row[6],
                "TotalTransfersGiven": row[7],
                "PublicInteractionPayoff": row[8],
                "PrivateInteractionPayoff": row[9],
                "Payment": row[10],
                "Timeout": row[11],  # Store timeout_penalty value
                "Audited": row[12]  # Store corruption_punishment value
            }
            for row in results
        ]

        return history_records if history_records else []

    except psycopg2.Error as e:
        print(f"Database error in filter_history: {e}")
        return []

    finally:
        conn.close()


def get_last_transaction_status(participant_code, treatment_round, segment, session_code, db_path=DB_PATH):
    """
    Retrieves the latest transaction for a participant in the current session, round, and segment,
    ONLY if its most recent status is 'Iniciado' (i.e., still open).

    :param participant_code: The participant's unique code.
    :param treatment_round: The current round number.
    :param segment: The current segment.
    :param session_code: The session code.
    :param db_path: Path to the PostSQL database.
    :return: Dictionary with transaction details if 'Iniciado', otherwise None.
    """
    conn, cur = connect_to_db(db_path)
    if not conn:
        return None

    try:
        # This query gets the latest transaction for the participant where the *most recent* status is 'Iniciado'
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
            ORDER BY status_id DESC  -- assuming status_id is incrementing
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
            transaction_id, initiator_id, receiver_id, action, points, status = result
            print(f"Last open transaction: {result}")
            return {
                'transactionId': transaction_id,
                'initiatorId': initiator_id,
                'receiverId': receiver_id,
                'action': action,
                'value': points
            }

        return None  # No open transaction

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
    :param db_path: Path to the PostSQL database.
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


def check_corruption(data, db_path=DB_PATH):
    """
    Identifies transactions between citizens (1, 2, 3) and the funcionario (4),
    filtering for accepted transactions ('Aceptado') and classifying them based on action type.

    :param data: Dictionary containing 'segment', 'round', 'session_code', 'group_id'.
    :param db_path: Path to the PostSQL database.
    :return: Dictionary with corruption details for each citizen.
    """
    
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

    corruption_data = {citizen_id: {
        'transfers_from_citizen_to_officer': 0,
        'transfers_from_officer_to_citizen': 0
    } for citizen_id in [1, 2, 3]}

    conn, cur = connect_to_db(db_path)  # Expecting a tuple (connection, cursor)
    
    if not conn:
        return {'error': 'Database connection failed'}

    try:
        cur.execute(query, (data['segment'], data['round'], data['session_code'], data['group_id']))
        results = cur.fetchall()

        for initiator_id, receiver_id, action, points in results:
            if initiator_id in [1, 2, 3] and receiver_id == 4:  # Citizen → Funcionario
                if action == 'Ofrece':
                    corruption_data[initiator_id]['transfers_from_citizen_to_officer'] += points
                elif action == 'Solicita':
                    corruption_data[initiator_id]['transfers_from_officer_to_citizen'] += points
            elif initiator_id == 4 and receiver_id in [1, 2, 3]:  # Funcionario → Citizen
                if action == 'Ofrece':
                    corruption_data[receiver_id]['transfers_from_officer_to_citizen'] += points
                elif action == 'Solicita':
                    corruption_data[receiver_id]['transfers_from_citizen_to_officer'] += points

        return corruption_data

    except psycopg2.Error as e:
        print(f"Database error: {e}")  # Replace with logging if necessary
        return {'error': str(e)}

    finally:
        cur.close()
        conn.close()