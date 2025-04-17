from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()


SESSION_CONFIGS = [
    dict(
        name='public_goods',
        display_name='public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        treatment_order=['BL1', 'BL2'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=140, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=20, # Default exchange rate bewteen experimental points and soles
        c1_endowment=120, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=True # True: chat only between citizens and officer | False: chat with everyone
    ),
]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = ['treatment_round', 'segment', 'session_payoff']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'es'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'PEN'
USE_POINTS = True

ROOMS = [
    dict(
        name='econ101',
        display_name='Econ 101 class',
        participant_label_file='_rooms/econ101.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""


SECRET_KEY = '6974100366510'

INSTALLED_APPS = ['otree']