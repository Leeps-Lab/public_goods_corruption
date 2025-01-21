import sqlite3

# TODO: 1. Función para establecer conexión con sqlite3 de otree .env (por ahora al local)


# TODO: 2. Función para crear tablas base

# Connect to databases (if dbs don't exist, creates them)
conn_participants = sqlite3.connect('databases/participants.db')
conn_transactions = sqlite3.connect('databases/transactions.db')
conn_history = sqlite3.connect('databases/history.db')

# Create cursors for each database
cur_participants = conn_participants.cursor()
cur_transactions = conn_transactions.cursor()
cur_history = conn_history.cursor()

# Create the participants table
cur_participants.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_code TEXT NOT NULL,
        participant_code TEXT NOT NULL,
        participant_id INTEGER NOT NULL,
        participant_label TEXT NOT NULL,
        player_id_in_group INTEGER NOT NULL,
        player_role TEXT NOT NULL,
        group_id INTEGER NOT NULL,
    )
''')

# Create transactions.db in psql_tools
cur_transactions.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_code TEXT NOT NULL, 
        # app_name TEXT NON NULL, # Necesario en ambas
        treatment INTEGER NOT NULL, 
        # treatment_name TEXT NOT NULL, 
        round INTEGER NOT NULL, 
        transaction_id INTEGER NOT NULL,
        initiator_id INTEGER NOT NULL, # Participant id
        receiver_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        points INTEGER NOT NULL,
        success TEXT NOT NULL,
        initiator_total INTEGER NOT NULL,
        receiver_total INTEGER NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (initiator_id) REFERENCES participants(participant_id),
        FOREIGN KEY (receiver_id) REFERENCES participants(participant_id),
    )
''')

# Create history.db in psql_tools
cur_history.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_code TEXT NOT NULL,
        # app_name TEXT NON NULL, # Necesario en ambas
        treatment INTEGER NOT NULL,
        # treatment_name TEXT NOT NULL, 
        round INTEGER NOT NULL,
        participant_id INTEGER NOT NULL,
        endowment INTEGER NOT NULL,
        contribution INTEGER NOT NULL,
        public_good_raw_gain INTEGER NOT NULL,
        total_transfers_received INTEGER NOT NULL,
        total_transfers_given INTEGER NOT NULL,
        round_payment INTEGER NOT NULL
    )
''')