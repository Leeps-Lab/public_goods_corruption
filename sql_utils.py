import sqlite3

# Optional columns:
# app_name TEXT NON NULL,
# segment_name TEXT NOT NULL,


# TODO: 1. Función para establecer conexión con sqlite3 de otree .env (por ahora al local)
def connect_otree_database(db_path='db.sqlite3'):
    """
    Establishes a connection to the oTree database.
    """
    try:
        conn = sqlite3.connect(db_path)
        print(f"Connected to oTree database at {db_path}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to oTree database: {e}")
        return None


# TODO: 2. Función para crear tablas base
def create_tables(db_path='game_data.db'):
    """
    Creates all necessary tables in a single database.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # TODO: I could add participant.label (if considered neccesary)
    # # Create participants table
    # cur.execute('''
    #     CREATE TABLE IF NOT EXISTS participants (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         participant_code TEXT NOT NULL,
    #         session_code TEXT NOT NULL,
    #         participant_id INTEGER NOT NULL,
    #         player_id_in_group INTEGER NOT NULL,
    #         player_role TEXT NOT NULL,
    #         group_id INTEGER NOT NULL
    #     )
    # ''')

    # Create transactions table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code TEXT NOT NULL,
            segment INTEGER NOT NULL,
            round INTEGER NOT NULL,
            initiator_code TEXT NOT NULL,
            receiver_code TEXT NOT NULL,
            action TEXT NOT NULL,
            points INTEGER NOT NULL,
            initiator_total INTEGER NOT NULL,
            receiver_total INTEGER NOT NULL,
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

    # Create history table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment INTEGER NOT NULL,
            round INTEGER NOT NULL,
            participant_code TEXT NOT NULL,
            endowment INTEGER NOT NULL,
            contribution INTEGER NOT NULL,
            public_good_raw_gain INTEGER NOT NULL,
            total_transfers_received INTEGER NOT NULL,
            total_transfers_given INTEGER NOT NULL,
            payment INTEGER NOT NULL,
            FOREIGN KEY (participant_code) REFERENCES participants(participant_code)
        )
    ''')

    conn.commit()
    conn.close()

    print("All tables created successfully.")


def insert_participant(data, db_path='game_data.db'):
    """
    Inserts a single participant's data into the participants table.
    :param data: Dictionary containing participant data.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO participants (
            participant_code, session_code, participant_id, 
            player_id_in_group, player_role, group_id
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['participant_code'],
        data['session_code'],
        data['participant_id'],
        data['player_id_in_group'],
        data['player_role'],
        data['group_id'],
    ))

    conn.commit()
    conn.close()


def insert_transaction(data, db_path='game_data.db'):
    """
    Saves a transaction to the transactions table
    :param data: Dictionary containing transaction data.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())

        cur.execute(f'''
            INSERT INTO transactions ({columns})
            VALUES ({placeholders})
        ''', values)

        conn.commit()
        print("Transaction saved successfully.")
    except sqlite3.Error as e:
        print(f"Error saving transaction: {e}")
    finally:
        conn.close()


def insert_status(data, db_path='game_data.db'):
    """
    Inserts a status update into the status table.
    :param data: Dictionary containing status data.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO status (
            transaction_id, status, timestamp
        ) VALUES (?, ?, ?)
    ''', (
        data['transaction_id'],
        data['status'],
        data['timestamp'],
    ))

    conn.commit()
    conn.close()


def insert_history(data, db_path='game_data.db'):
    """
    Inserts a record into the history table.
    :param data: Dictionary containing history data.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO history (
            segment, round, participant_code, endowment, contribution,
            public_good_raw_gain, total_transfers_received,
            total_transfers_given, payment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['segment'],
        data['round'],
        data['participant_code'],
        data['endowment'],
        data['contribution'],
        data['public_good_raw_gain'],
        data['total_transfers_received'],
        data['total_transfers_given'],
        data['payment'],
    ))

    conn.commit()
    conn.close()
