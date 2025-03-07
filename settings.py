from os import environ
from dotenv import load_dotenv # type: ignore

load_dotenv()

# TODO: preguntas de sesión: testear contribución exógena?
SESSION_CONFIGS = [
    dict(
        name='BL1_public_goods',
        display_name='BL1_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        random_multiplier=False, # If multiplier is random (T3)
        multiplier=2, # Multiplier value when it is not random
        sequential_decision=True, # False for simultaneous decisions (interaction and contribution at same time)
    ),
    dict(
        name='BL2_public_goods',
        display_name='BL2_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default heterogenous detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=False, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T1_public_goods_simultaneous',
        display_name='T1_public_goods_simultaneous',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Treatment configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=False, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T1_public_goods_sequencial',
        display_name='T1_public_goods_sequencial',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=True, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=False, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T2_public_goods',
        display_name='T2_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T3_public_goods',
        display_name='T3_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=True, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T4_public_goods',
        display_name='T4_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=True, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T6_public_goods',
        display_name='T6_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=True, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=False # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T7_public_goods',
        display_name='T7_public_goods',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=False, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=True # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='T7_public_goods_chat_only_officer',
        display_name='T7_public_goods_chat_only_officer',
        app_sequence=['introduction', 'new_public_goods', 'final_questionnaire', 'final_payoff'],
        num_demo_participants=4,
        multiplier=2, # Default multiplier value when it is not random
        officer_endowment=700, # Default endowment for P.O.
        participation_fee=7.50, # Default participation fee
        exchange_rate=1000, # Default exchange rate bewteen experimental points and soles
        c1_endowment=600, # Default heterogenous endowment for Citizen 1 (T3)
        audit_probability=0.2, # Default detection probability of corruption action (T6)
        # Aditional configs
        sequential_decision=False, # True: first interaction, then contribution | False: both at same time
        chat_only_officer=True, # True: chat only between citizens and officer | False: chat with everyone
        private_interaction=True, # True: chat and trasactions (BL)
        resource_allocation=True, # True: P.O. decides how to allocate the public resources (T2)
        heterogenous_citizens=False, # True: Citizen one will have different endowment (T3)
        random_multiplier=False, # True: multiplier is a random value between 1.5 or 2.5 (T4)
        random_audits=False, # True: there is a chance of random audits and punishments (T6)
        officer_interactions_public=True # True: all private interactions with officer becomes public (T7)
    ),
    dict(
        name='final_questionnaire',
        display_name='final_questionnaire',
        app_sequence=['final_questionnaire'],
        num_demo_participants=2
    ),
]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = ['segment', 'session_payoff']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

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