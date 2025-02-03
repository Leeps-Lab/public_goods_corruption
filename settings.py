from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()

# TODO: pensar en 2 alternativas de mostrar tratamientos sequenciales
# Alt. 1: Crear diferentes session configs por cada T
# Alt. 2: Crear cada session config por cada order de T
# TODO: (antes del history) ver qué Treatments ya se pueden poner en el SC y qué Treatments no (ver cuánto tomaría hacerlo) - asumiendo que los tratamientos van separados
SESSION_CONFIGS = [
    dict(
        name='public_goods_simultaneous',
        display_name="public_goods_simultaneous",
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        # Aditional configs
        random_multiplier=False, # If multiplier is random (T3)
        multiplier=2, # Multiplier value when it is not random
        sequential_decision=False, # False for simultaneous decisions (interaction and contribution at same time)
    ),
    dict(
        name='public_goods_sequencial',
        display_name="public_goods_sequencial",
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        # Aditional configs
        random_multiplier=False, # If multiplier is random (T3)
        multiplier=2, # Multiplier value when it is not random
        sequential_decision=True, # False for simultaneous decisions (interaction and contribution at same time)
    ),
]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = ['segment']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
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