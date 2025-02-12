from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()

# TODO: pensar en 2 alternativas de mostrar tratamientos sequenciales
# Alt. 1: Crear diferentes session configs por cada T
# Alt. 2: Crear cada session config por cada order de T
# TODO: (antes del history) ver qué Treatments ya se pueden poner en el SC y qué Treatments no (ver cuánto tomaría hacerlo) - asumiendo que los tratamientos van separados

# TODO: preguntas de sesión: testear contribución exógena?
SESSION_CONFIGS = [
    dict(
        name='public_goods_simultaneous',
        display_name='T1_public_goods_simultaneous',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Treatment configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=True, # True: chat and trasactions
        resource_allocation=False, # True: P.O. decides how to allocate the public resources
    ),
    dict(
        name='public_goods_sequencial',
        display_name='T1_public_goods_sequencial',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Aditional configs
        sequential_decision=True, # True: first interaction, then contribution | False: both at same time
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=True, # True: chat and trasactions
        resource_allocation=False, # True: P.O. decides how to allocate the public resources
    ),
    dict(
        name='BL1_public_goods',
        display_name='BL1_public_goods',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=False, # True: chat and trasactions
        resource_allocation=False, # True: P.O. decides how to allocate the public resources
    ),
    dict(
        name='BL2_public_goods',
        display_name='BL2_public_goods',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=False, # True: chat and trasactions
        resource_allocation=True, # True: P.O. decides how to allocate the public resources
    ),
    dict(
        name='T2_public_goods',
        display_name='T2_public_goods',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=True, # True: chat and trasactions
        resource_allocation=True, # True: P.O. decides how to allocate the public resources
    ),
    dict(
        name='T3_public_goods',
        display_name='T3_public_goods',
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        random_multiplier=True, # True: multiplier is a random value between 1.5 or 2.5 (T3)
        private_interaction=True, # True: chat and trasactions
        resource_allocation=True, # True: P.O. decides how to allocate the public resources
    ),
]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = ['segment']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'es'

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