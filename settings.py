from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()


SESSION_CONFIGS = [
    dict(
        name='public_goods_demo',
        display_name='All treatments',
        app_sequence=['introduction', 'public_goods', 'final_questionnaire', 'final_payoff'],
        treatment_order=['BL1', 'BL2', 'T1', 'T2', 'T3', 'T4'],
        num_rounds=2, # NOTE: change num of rounds per treatment
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=140, # Default endowment for P.O.
        # participation_fee=12.00, # Default participation fee
        exchange_rate=10, # Default exchange rate bewteen experimental points and soles
        c1_endowment=150, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        private_interaction_duration=180, # Default time for deactivate private interaction: 180 seconds
        public_interaction_activation=60, # Default time for activate public interaction: 60 seconds
        sequential_decision=True, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=True # True: chat only between citizens and officer | False: chat with everyone
    ),
    dict(
        name='public_goods',
        display_name='Public Goods T1 y T2',
        app_sequence=['introduction', 'public_goods', 'final_questionnaire', 'final_payoff'],
        treatment_order=['T1', 'T2'],
        num_rounds=6, # NOTE: change num of rounds per treatment
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=140, # Default endowment for P.O.
        # participation_fee=12.00, # Default participation fee
        exchange_rate=10, # Default exchange rate bewteen experimental points and soles
        c1_endowment=150, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        private_interaction_duration=180, # Default time for deactivate private interaction: 180 seconds
        public_interaction_activation=60, # Default time for activate public interaction: 60 seconds
        sequential_decision=True, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=True # True: chat only between citizens and officer | False: chat with everyone
    ),
    dict(
        name='public_goods2',
        display_name='Public Goods T2 y T1',
        app_sequence=['introduction', 'public_goods', 'final_questionnaire', 'final_payoff'],
        treatment_order=['T2', 'T1'],
        num_rounds=6, # NOTE: change num of rounds per treatment
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=140, # Default endowment for P.O.
        # participation_fee=12.00, # Default participation fee
        exchange_rate=10, # Default exchange rate bewteen experimental points and soles
        c1_endowment=150, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        private_interaction_duration=180, # Default time for deactivate private interaction: 180 seconds
        public_interaction_activation=60, # Default time for activate public interaction: 60 seconds
        sequential_decision=True, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=True # True: chat only between citizens and officer | False: chat with everyone
    ),
]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=12.00, doc=""
)

PARTICIPANT_FIELDS = ['treatment_round', 'segment', 'treatment', 'session_payoff']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'es'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'PEN'
USE_POINTS = True

ROOMS = [
    dict(
        name='e2labup',
        display_name="E²LabUP Session",
        participant_label_file='_rooms/e2labup-room.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""


SECRET_KEY = '6974100366510'

INSTALLED_APPS = ['otree']