import sqlite3
from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()

# TODO:
# Crear un esquema que se llame game_data
# Que las funciones creen las tablas dentro del esquema
# Cambiar DB_PATH = 'postgres://otree_user:wyjhUf-vaxju0-fusvew@localhost:5432/otree_db' 
# DB_PATH = environ.get('DATABASE_URL')

# Optional columns:
# app_name TEXT NON NULL,
# segment_name TEXT NOT NULL,


DB_PATH = 'game_data.db'

def create_tables(db_path=DB_PATH):
    """
    Creates all necessary tables in game_data.db
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create transactions table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    ''')

    # Create status table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS status (
            status_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        )
    ''')

    conn.commit()
    conn.close()

    print("All tables created successfully.")


def insert_row(data, table, db_path=DB_PATH):
    """
    Inserts a row into a specified table.
    :param data: Dictionary containing the data to insert. Keys must match column names.
    :param table: Name of the table where the data will be inserted.
    :param db_path: Path to the SQLite database file.
    :return: The row ID of the inserted row (if applicable).
    """
    try:
        allowed_tables = {'transactions', 'status'}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())

        cur.execute(f'''
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
        ''', values)

        conn.commit()
        print(f"Row nº{cur.lastrowid} inserted successfully into '{table}'")
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting row into '{table}': {e}")
    finally:
        conn.close()


def get_points(transaction_id, db_path=DB_PATH):
    """
    Retrieves the points associated with a given transaction ID.
    :param transaction_id: The ID of the transaction.
    :param db_path: Path to the SQLite database.
    :return: The points value of the transaction, or None if not found.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT points FROM transactions WHERE transaction_id = ?", (transaction_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Database error while fetching points: {e}")
        return None
    finally:
        conn.close()


def get_action(transaction_id, db_path=DB_PATH):
    """
    Retrieves the action associated with a given transaction ID.
    :param transaction_id: The ID of the transaction.
    :param db_path: Path to the SQLite database.
    :return: The action of the transaction, or None if not found.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT action FROM transactions WHERE transaction_id = ?", (transaction_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Database error while fetching action: {e}")
        return None
    finally:
        conn.close()


def add_balance(data, db_path=DB_PATH):
    """
    Updates the initiator_balance and receiver_balance in the transactions table for a given transaction_id.
    :param data: Dictionary containing transaction_id, initiator_balance, and receiver_balance.
    :param db_path: Path to the SQLite database.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE transactions
            SET initiator_balance = ?, receiver_balance = ?
            WHERE transaction_id = ?
        """, (data['initiator_balance'], data['receiver_balance'], data['transaction_id']))
        
        conn.commit()
        print(f"Balance updated for transaction {data['transaction_id']}: Initiator {data['initiator_balance']}, Receiver {data['receiver_balance']}")
    except sqlite3.Error as e:
        print(f"Database error while updating balance: {e}")
    finally:
        conn.close()

# TODO: reemplazar ? por valor
def filter_transactions(data, db_path=DB_PATH):
    """
    Filters transactions for a given participant, round, segment, and session.
    Replaces participant_code with the corresponding role from 'db.sqlite3'.
    :param data: Dictionary containing participant_code, round, segment, session_code
    :return: Filtered transactions
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        query = """
            SELECT
                t.initiator_id,  
                t.action,        
                t.receiver_id,   
                t.points,        
                CASE 
                    WHEN t.initiator_code = ? THEN t.initiator_balance  
                    WHEN t.receiver_code = ? THEN t.receiver_balance  
                    ELSE NULL
                END AS total_balance,  
                s.status  
            FROM transactions t
            LEFT JOIN status s ON t.transaction_id = s.transaction_id
            WHERE (t.initiator_code = ? OR t.receiver_code = ?)
            AND t.round = ?
            AND t.segment = ?
            AND t.session_code = ?
            AND s.status IN ('Aceptado', 'Rechazado')
        """

        cur.execute(query, (
            data['participant_code'],  # First ? → Check if participant is initiator
            data['participant_code'],  # Second ? → Check if participant is receiver
            data['participant_code'],  # Third ? → Filtering transactions where participant is involved
            data['participant_code'],  # Fourth ? → Filtering transactions where participant is involved
            data['round'],
            data['segment'],
            data['session_code']
        ))

        results = cur.fetchall()

        # Convert results to a list of dictionaries (formatted as table rows)
        transactions = [
            {
                "Jugador": row[0],  # initiator_id
                "Acción": row[1],   # action
                "A": row[2],        # receiver_id
                "Puntos": row[3],   # points
                "¿Se aceptó?": row[5],  # success/status
                "Balance": row[4],  # total_balance
            }
            for row in results
        ]

        return transactions 

    except sqlite3.Error as e:
        print(f"Database error while filtering transactions: {e}")
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
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

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
            (SELECT COUNT(*) FROM status WHERE transaction_id = t.transaction_id) AS status_count
        FROM transactions t
        JOIN status s ON t.transaction_id = s.transaction_id
        WHERE (t.initiator_code = ? OR t.receiver_code = ?)
        AND t.session_code = ?
        AND t.round = ?
        AND t.segment = ?
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

    except sqlite3.Error as e:
        print(f"Database error while fetching last transaction: {e}")
        return None

    finally:
        conn.close()