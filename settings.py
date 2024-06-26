from os import environ


SESSION_CONFIGS = [
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

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
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
