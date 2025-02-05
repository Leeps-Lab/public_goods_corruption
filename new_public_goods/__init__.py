from otree.api import *
from sql_utils import create_tables, insert_row, add_balance, get_points, get_action, filter_transactions, filter_history, get_last_transaction_status, total_transfers_per_player
import math
import time
import random

# TODO: división del chat por cada ronda
# TODO: Que el chat del funcionario salga primero (siempre izq)

create_tables() # Creates additional tables

class C(BaseConstants):
    NAME_IN_URL = 'interaccion'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3
    ENDOWMENT = 500
    CITIZEN1_ROLE = 'Ciudadano 1'
    CITIZEN2_ROLE = 'Ciudadano 2'
    CITIZEN3_ROLE = 'Ciudadano 3'
    OFFICER_ROLE = 'Funcionario'

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    multiplier = models.FloatField(initial=0)
    total_initial_points = models.IntegerField(initial=0)
    total_contribution = models.IntegerField()
    individual_share = models.FloatField() # TODO: Allow decimals? or round to int

class Player(BasePlayer):
    current_points = models.IntegerField(initial=C.ENDOWMENT)
    contribution_points = models.IntegerField() # TODO: hacer que sea obligatorio?


# FUNCTIONS
def creating_session(subsession):
    for player in subsession.get_players():
        player.participant.segment = 1 # Initialize segment value to 1
        player.group.total_initial_points += player.current_points # Set total points between all participants per group
        if subsession.session.config['endowment_unequally'] == False:
            player.participant.initial_points = C.ENDOWMENT

def public_good_raw_gain(group):
    players = [p for p in group.get_players() if p.id_in_group != 4]  # Exclude player with id 4 (Funcionario)
    group.total_contribution = sum(p.contribution_points for p in players)
    group.individual_share = (group.total_contribution * group.multiplier / (C.PLAYERS_PER_GROUP - 1)) # TODO: confirmar si se divide solo entre los ciudadanos

def set_payoffs(player):
    total_transfers = total_transfers_per_player({
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.round_number,
        'participant_code': player.participant.code,
    }) 
    if player.id_in_group != 4: # TODO: confirmar
        player.payoff = player.participant.initial_points - player.contribution_points - total_transfers.get('transfers_given', 0) + player.group.individual_share + total_transfers.get('transfers_received', 0)
    else:
        player.payoff = player.participant.initial_points - total_transfers.get('transfers_given', 0) + total_transfers.get('transfers_received', 0)

def insert_history(group):
    for player in group.get_players():
        set_payoffs(player)
        total_transfers = total_transfers_per_player({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
        }) 
        history_data = {
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
            'endowment': player.participant.initial_points,
            'contribution': player.field_maybe_none('contribution_points'),
            'public_good_raw_gain': player.group.individual_share,
            'total_transfers_received': total_transfers.get('transfers_received', 0),
            'total_transfers_given': total_transfers.get('transfers_given', 0),
            'payment': float(player.payoff)
        }
        print(f"history data: {history_data}")
        insert_row(data=history_data, table='history')
    

# PAGES
class Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1
    

class FirstWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        """ Set multiplier value per groups and per rounds """
        if group.session.config['random_multiplier']:
            group.multiplier = random.choice([1.5, 2.5])  # Assign the random multiplier to the group
        else:
            group.multiplier = group.session.config['multiplier']  # Use fixed multiplier


class Interaction(Page):
    timeout_seconds = 60 * 3
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.role != C.OFFICER_ROLE: # Display formfield 'contribution_points' only to citizens
            return ['contribution_points']

    @staticmethod
    def vars_for_template(player):
        others = player.get_others_in_group()
        others_info = [
            {
                "id_in_group": other.id_in_group,
                "role": other.role,
                "channel": f"{min(player.id_in_group, other.id_in_group)}{max(player.id_in_group, other.id_in_group)}"
            }
            for other in others
        ]

        if player.round_number > 1:
            history = filter_history({
                'session_code': player.session.code,
                'segment': player.participant.segment,
                'participant_code': player.participant.code,
            })
        else:
            history = []

        return dict(
            segment=player.participant.segment,
            others=others_info,
            history=history,
        )

    @staticmethod
    def js_vars(player): # Sendign the sequential_decision session config to the frontend
        return dict(secuential_decision=player.session.config['sequential_decision'])

    @staticmethod
    def live_method(player, data):
        print(f"data: {data}")
        # static_columns = ['initiator_id', 'receiver_id', 'action', 'points', 'success'] # transaction columns for all the players

        def handle_contribution(contribution_points):
            """
            Validate and process contribution points
            """
            if player.role != C.OFFICER_ROLE:
                if not isinstance(contribution_points, int) or math.isnan(contribution_points): # Check if is float or NaN
                    return dict(contributionPointsValid=False)
                if 0 <= contribution_points <= player.current_points:
                    player.current_points -= contribution_points
                    player.contribution_points = contribution_points
                    return dict(contributionPointsValid=True, contributionPoints=contribution_points)
                return dict(contributionPointsValid=False)
            
        def reload_contribution():
            """
            Handle reloading page when already contributed
            """
            contribution_points = player.field_maybe_none('contribution_points')
            if player.role != C.OFFICER_ROLE and contribution_points:
                return dict(contributionPointsReload=True, contributionPoints=contribution_points)
            return {}
        
        def new_transaction():
            """
            Log the initial transaction in the transactions table and its status in the status table.
            Activates when the initiator clicks "offer" or "request".
            """
            transaction_data = {
                'session_code': player.session.code,
                'segment': player.participant.segment,
                'round': player.group.round_number,
                'initiator_code': player.group.get_player_by_id(data['initiatorId']).participant.code,
                'receiver_code': player.group.get_player_by_id(data['receiverId']).participant.code,
                'initiator_id': data['initiatorId'],
                'receiver_id': data['receiverId'],
                'action': data['action'],
                'points': data['value'],
                'initiator_initial_endowment': player.current_points,
                'receiver_initial_endowment': player.group.get_player_by_id(data['receiverId']).current_points,
            }
            print(f'transaction data: {transaction_data}')

            transaction_id = insert_row(data=transaction_data, table='transactions') # Save the transaction and get the transaction ID

            status_data = {
                'transaction_id': transaction_id,
                'status': 'Iniciado',
            }
            print(f'status data:{status_data}')
            insert_row(data=status_data, table='status')

            return transaction_id

        def closing_transaction(status, transaction_id):
            """
            Log the clausure of a transaction in the status table and update total in transactions table.
            Activates when the receiver clicks "yes" or "no", or the initiator cancels the transaction.
            """
            balance_data = {
                'transaction_id': transaction_id,
                'initiator_balance': player.group.get_player_by_id(data['initiatorId']).current_points,
                'receiver_balance': player.group.get_player_by_id(data['receiverId']).current_points,
            }
            print(balance_data)
            add_balance(data=balance_data)

            status_data = {
                'transaction_id': transaction_id,
                'status': status,
            }
            print(status_data)
            insert_row(data=status_data, table='status')

        data_type = data.get('type')

        # When contributing to the common project
        if data_type == 'contributionPoints':
            return {player.id_in_group: handle_contribution(data['value'])}
        
        # When offering/requesting points to another player (as a initiator)
        elif data_type == 'initiatingTransaction':
            transaction_id = new_transaction()
            if 'Ofrece' in data['action']:
                offer_points = data.get('value')
                if offer_points <= player.current_points:
                    return {
                        player.id_in_group: dict(offerPoints=True, initiator=True, receiver=False, offerValue=data.get('value'), myId=data.get('initiatorId'), otherId=data.get('receiverId'), transactionId=transaction_id),
                        data.get('receiverId'): dict(offerPoints=True, initiator=False, receiver=True, offerValue=data.get('value'), myId=data.get('receiverId'), otherId=data.get('initiatorId'), transactionId=transaction_id),
                    }
                else:
                    return {player.id_in_group: dict(offerPoints=False)} 
            elif 'Solicita' in data['action']:
                if data.get('value') <= player.group.total_initial_points:
                    return {
                            player.id_in_group: dict(requestPoints=True, initiator=True, receiver=False, requestValue=data.get('value'), myId=data.get('initiatorId'), otherId=data.get('receiverId'), transactionId=transaction_id),
                            data.get('receiverId'): dict(requestPoints=True, initiator=False, receiver=True, requestValue=data.get('value'), myId=data.get('receiverId'), otherId=data.get('initiatorId'), transactionId=transaction_id),
                        }
                else:
                    return {player.id_in_group: dict(requestPoints=False, initiator=True)} 
        
        # When accepting/canceling points to another player (as a receiver) or canceling transaction (as initiator)
        elif data_type == 'closingTransaction':
            if data['status'] == 'Cancelado':
                closing_transaction(data['status'], data['transactionId'])
                return {player.id_in_group: dict(cancelAction=True, otherId=data['receiverId']),
                        data['receiverId']: dict(cancelAction=True, otherId=player.id_in_group)}    

            elif data['status'] == 'Rechazado':
                closing_transaction(data['status'], data['transactionId'])
                print(f"initiator: {data['transactionId']}")
                print(f"receiver: {data['receiverId']}")
                initiator = player.group.get_player_by_id(data['initiatorId'])
                receiver = player.group.get_player_by_id(data['receiverId'])
                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.round_number,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.round_number,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })
                print(f"filter transactions initiator: {filter_transactions_i}")
                print(f"filter transactions receiver: {filter_transactions_r}")
                return {
                    player.id_in_group: dict(update=True, updateTransactions=True, transactions=filter_transactions_r, otherId=data['initiatorId'], reload=False),
                    data['initiatorId']: dict(update=True, updateTransactions=True, transactions=filter_transactions_i, otherId=data['receiverId'], reload=False),
                }
            
            elif data['status'] == 'Aceptado':
                other_player = player.group.get_player_by_id(data['initiatorId'])
                points = get_points(data['transactionId'])
                action = get_action(data['transactionId'])
                if action == 'Ofrece':
                    other_player.current_points -= points
                    player.current_points += points
                else:
                    if points <= player.current_points:
                        other_player.current_points += points
                        player.current_points -= points
                    else:
                        return {player.id_in_group: dict(requestPoints=False, initiator=False)} 
                
                closing_transaction(data['status'], data['transactionId'])
                initiator = player.group.get_player_by_id(data['initiatorId'])
                receiver = player.group.get_player_by_id(data['receiverId'])
                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.round_number,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.round_number,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })
                return {
                    player.id_in_group: dict(updateTransactions=True, transactions=filter_transactions_r, otherId=data['initiatorId'], reload=False, update=True),
                    data['initiatorId']: dict(updateTransactions=True, transactions=filter_transactions_i, otherId=data['receiverId'], reload=False, update=True)
                }
        
        # When player reloads their page
        elif data_type == 'reloadPage':
            # Get the last transaction of the player in the current session, round, and segment
            last_transaction = get_last_transaction_status(
                participant_code=player.participant.code,
                round_number=player.round_number,
                segment=player.participant.segment,
                session_code=player.session.code
            ) 

            # If the last transaction is still in process, send offer/request buttons again and filtered transactions
            if last_transaction:
                transaction_id = last_transaction['transactionId']
                initiator_id = last_transaction['initiatorId']
                receiver_id = last_transaction['receiverId']
                action = last_transaction['action']
                value = last_transaction['value']

                # Fetch the filtered transactions
                transactions_data = filter_transactions({
                    'participant_code': player.participant.code,
                    'round': player.round_number,
                    'segment': player.participant.segment,
                    'session_code': player.session.code,
                })

                # Debugging
                print("Transactions while reloading (with active transaction):", transactions_data)

                # Construct common response data
                response_data = {
                    'updateTransactions': True,
                    'transactions': transactions_data,  # Sending filtered transactions
                    'update': True,
                    'transactionId': transaction_id
                }

                if action == 'Ofrece':
                    return {
                        player.id_in_group: dict(
                            offerPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            offerValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ),
                        receiver_id: dict(
                            offerPoints=True,
                            initiator=False,
                            receiver=True,
                            offerValue=value,
                            myId=receiver_id,
                            otherId=initiator_id,
                            **response_data  # Merging transaction data
                        )
                    }
                elif action == 'Solicita':
                    return {
                        player.id_in_group: dict(
                            requestPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            requestValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ),
                        receiver_id: dict(
                            requestPoints=True,
                            initiator=False,
                            receiver=True,
                            requestValue=value,
                            myId=receiver_id,
                            otherId=initiator_id,
                            **response_data  # Merging transaction data
                        )
                    }

            reload = reload_contribution()
            transactions_data = filter_transactions({
                'participant_code': player.participant.code,
                'round': player.round_number,
                'segment': player.participant.segment,
                'session_code': player.session.code,
            })
            print(transactions_data)

            if transactions_data: # If it is not empty
                reload.update({'updateTransactions':True, 'transactions':transactions_data, 'update': True})
                print(reload)
                return {player.id_in_group: reload}
            
            return {player.id_in_group: reload}
        

    # Ending the last round of the segment, update segment value
    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.round_number == C.NUM_ROUNDS:
            player.participant.segment += 1


class LastWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        public_good_raw_gain(group)
        insert_history(group)


# Change if session.config['endowment_unequally'] == True
page_sequence = [Instructions, FirstWaitPage, Interaction, LastWaitPage]