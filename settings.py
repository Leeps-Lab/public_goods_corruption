from os import environ


SESSION_CONFIGS = [
    dict(
        name='new_public_goods',
        display_name="new_public_goods",
        app_sequence=['new_public_goods'],
        num_demo_participants=4,
        # Aditional configs
        random_multiplier=False, # If multiplier is random (T3)
        multiplier=2, # Multiplier value when it is not random
        sequential_decision=True, # False for simultaneous decisions (interaction and contribution at same time)
    ),
    dict(
        name='public_goods_simple',
        display_name="public_goods_simple",
        app_sequence=['public_goods_simple'],
        num_demo_participants=4,
        exchange_point_betwen_players = True,
        equitable_distribution_of_officials_to_citizens = False,
        endowment_comun = False,
    ),
    dict(
        name='public_goods_simple_T1',
        display_name="public goods simple T1",
        app_sequence=['public_goods_simple'],
        num_demo_participants=4,
        exchange_point_betwen_players = True,
        equitable_distribution_of_officials_to_citizens = True,
        endowment_comun = False,
    ),
    dict(
        name='public_goods_simple_BL1',
        display_name="public goods simple BL1",
        app_sequence=['public_goods_simple'],
        num_demo_participants=4,
        exchange_point_betwen_players = False,
        equitable_distribution_of_officials_to_citizens = False,
        endowment_comun = False,
    ),
    dict(
        name='public_goods_simple_BL2',
        display_name="public goods simple BL2",
        app_sequence=['public_goods_simple'],
        num_demo_participants=4,
        exchange_point_betwen_players = False,
        equitable_distribution_of_officials_to_citizens = True,
        endowment_comun = False,
    ),
    dict(
        name='public_goods_simple_T2',
        display_name="public goods simple T2",
        app_sequence=['public_goods_simple'],
        num_demo_participants=4,
        exchange_point_betwen_players = True,
        equitable_distribution_of_officials_to_citizens = False,
        endowment_comun = True,
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