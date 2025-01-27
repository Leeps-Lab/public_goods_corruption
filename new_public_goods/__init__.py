from otree.api import *
from sql_utils import create_tables, insert_participant, insert_transaction, insert_status, insert_history
import time
import random
import pandas as pd

# Declare transactions db
# TODO: agregar columna con código de la sesión, participant id (string), label del jugador
column_names = ['transaction_id', 'round', 'group', 'initiator_id', 'receiver_id', 'action', 'points', 'success', 'initiator_total', 'receiver_total', 'status', 'time']
transactions = pd.DataFrame(columns=column_names)


class C(BaseConstants):
    NAME_IN_URL = 'interacción'
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
    total_points = models.IntegerField(initial=0)


class Player(BasePlayer):
    current_points = models.IntegerField(initial=C.ENDOWMENT)
    contribution_points = models.IntegerField(blank=True)


# FUNCTIONS
def creating_session(subsession):
    for player in subsession.get_players():
        player.participant.segment = 1 # Initialize segment value to 1
        player.group.total_points += player.current_points # Set total points between all participants per group
        
    if subsession.session.vars.get('initialized', False): # ?: Mejor forma de hacerlo? creating session se repite por c/ronda
        return 
    
    subsession.session.vars['initialized'] = True
    create_tables() 
    
    for player in subsession.get_players():
        participant_data = {
            'participant_code': player.participant.code,
            'session_code': player.session.code,
            'participant_id': player.participant.id_in_session,
            'player_id_in_group': player.id_in_group,
            'player_role': player.role,
            'group_id': player.group.id_in_subsession,
        }
        insert_participant(participant_data)


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
    # timeout_seconds = 60 * 3
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.role != 'Funcionario': # Display formfield 'contribution_points' only to citizens
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

        return dict(
            segment=player.participant.segment,
            others=others_info,
        )
    
    # Sendign the sequential decision session config to the frontend
    @staticmethod
    def js_vars(player):
        return dict(secuential_decision=player.session.config['sequential_decision'],)

    @staticmethod
    def live_method(player, data):
        print(f"data: {data}")
        static_columns = ['initiator_id', 'receiver_id', 'action', 'points', 'success'] # transaction columns for all the players

        def handle_contribution(contribution_points):
            """Validate and process contribution points."""
            if player.role != 'Funcionario':
                if not isinstance(contribution_points, int) or contribution_points != contribution_points:  # NaN check
                    return dict(contributionPointsValid=False)
                if 0 <= contribution_points <= player.current_points:
                    player.current_points -= contribution_points
                    player.contribution_points = contribution_points
                    return dict(contributionPointsValid=True, contributionPoints=contribution_points)
                return dict(contributionPointsValid=False)
            
        def reload_contribution():
            """Handle reloading page when already contributed."""
            contribution_points = player.field_maybe_none('contribution_points')
            if player.role != 'Funcionario' and contribution_points:
                return dict(contributionPointsReload=True, contributionPoints=contribution_points)
            return {}
        

        def new_transaction(success):
            """Log transaction in transactions.db and status in status.db"""
            transaction_data = {
                'segment': player.participant.segment,
                'round': player.group.round_number,
                'initiator_id': data['otherId'],
                'receiver_id': data['playerId'],
                'action': data['action'],
                'points': data['value'],
                'initiator_total': player.group.get_player_by_id(data['otherId']).current_points,
                'receiver_total': player.current_points,
            }
            print(transaction_data)
            insert_transaction(transaction_data) # Save the transaction

            transaction_id = 1 # TODO: usar el id que se creó en new_transaction
            status_data = {
                'transaction_id': transaction_id,
                'status': success,
                'timestamp': time.time(),
            }
            print(status_data)
            insert_status(status_data)


        def update_transaction(success):
            """Log transaction in transactions.db and status in status.db"""
            transaction_data = {
                'segment': player.participant.segment,
                'round': player.group.round_number,
                'initiator_id': data['otherId'],
                'receiver_id': data['playerId'],
                'action': data['action'],
                'points': data['value'],
                'initiator_total': player.group.get_player_by_id(data['otherId']).current_points,
                'receiver_total': player.current_points,
            }
            print(transaction_data)
            insert_transaction(transaction_data) # Save the transaction

            transaction_id = 1 # TODO: Search id of this transaction in status.db
            status_data = {
                'transaction_id': transaction_id,
                'status': success,
                'timestamp': time.time(),
            }
            print(status_data)
            insert_status(status_data)




        def process_relevant_rows(player_id, group):
            """Filter, process, and update relevant rows for a specific player within the same group."""
            relevant_rows = transactions[
                (
                    transactions[['initiator_id', 'receiver_id']].isin([player_id]).any(axis=1)
                ) & (transactions['group'] == group.id_in_subsession)  # Filter by group
            ].copy()

            # Filter relevant rows and dynamically append the appropriate 'total' value
            relevant_rows['total'] = relevant_rows.apply(
                lambda row: row['initiator_total'] if row['initiator_id'] == player_id else (
                    row['receiver_total'] if row['receiver_id'] == player_id else None
                ), axis=1
            )

            # Replace 'success' values
            relevant_rows['success'] = relevant_rows['success'].replace({'yes': 'Sí', 'no': 'No'})

            # Replace 'initiator_id' and 'receiver_id' with corresponding roles
            relevant_rows['initiator_id'] = relevant_rows['initiator_id'].apply(lambda x: group.get_player_by_id(x).role)
            relevant_rows['receiver_id'] = relevant_rows['receiver_id'].apply(lambda x: group.get_player_by_id(x).role)

            # Replace 'offer' and 'request' in the 'action' column
            relevant_rows['action'] = relevant_rows['action'].replace({'offer': 'Ofrece', 'request': 'Solicita'})

            return relevant_rows[static_columns + ['total']].to_dict(orient='records')
        

        def table_transactions_per_player():
            # Return filtered and formatted transactions for initiator and receiver
            return dict(
                initiator_transactions=process_relevant_rows(data['otherId'], player.group),
                receiver_transactions=process_relevant_rows(data['playerId'], player.group),
            )
        
        def update_transactions_per_player():
            # Return filtered and formatted transactions for initiator and receiver
            return process_relevant_rows(player.id_in_group, player.group)
        
        data_type = data.get('type')

        # When contributing to the common project
        if data_type == 'contributionPoints':
            return {player.id_in_group: handle_contribution(data['value'])}
        
        # When offering/requesting points to another player (as a initiator)
        elif data_type == 'offerPoints' or data_type == 'requestPoints':
            if 'offerPoints' in data['type']:
                offer_points = data.get('value')
                if offer_points <= player.current_points:
                    return {
                        player.id_in_group: dict(offerPoints=True, initiator=True, receiver=False, offerValue=data.get('value'), myId=data.get('playerId'), otherId=data.get('otherId')),
                        data.get('otherId'): dict(offerPoints=True, initiator=False, receiver=True, offerValue=data.get('value'), myId=data.get('otherId'), otherId=data.get('playerId')),
                    }
                else:
                    return {player.id_in_group: dict(offerPoints=False)} 
            elif 'requestPoints' in data['type']:
                if data.get('value') <= player.group.total_points:
                    return {
                            player.id_in_group: dict(requestPoints=True, initiator=True, receiver=False, requestValue=data.get('value'), myId=data.get('playerId'), otherId=data.get('otherId')),
                            data.get('otherId'): dict(requestPoints=True, initiator=False, receiver=True, requestValue=data.get('value'), myId=data.get('otherId'), otherId=data.get('playerId')),
                        }
                # TODO: alert msg for when requesting more than there is in total
                else:
                    return {player.id_in_group: dict(requestPoints=False, initiator=True)} 
        
        # When canceling the offer action (as a initiator)
        elif data_type == 'cancelAction':
            return {player.id_in_group: dict(cancelAction=True, otherId=data.get('otherId')),
                    data.get('otherId'): dict(cancelAction=True, otherId=player.id_in_group)}    

        # When declining offer/request from another player (as a receiver)
        elif data_type == 'declineAction':
            log_transaction('no')
            transactions_data = table_transactions_per_player()
            return {
                player.id_in_group: dict(updateTransactions=True, transactions=transactions_data['receiver_transactions'], otherId=data['otherId'], reload=False, update=True),
                data['otherId']: dict(updateTransactions=True, transactions=transactions_data['initiator_transactions'], otherId=data['playerId'], reload=False, update=True),
            }

        # When accepting offer/request from another player (as a receiver)
        elif data_type == 'acceptAction':
            other_player = player.group.get_player_by_id(data['otherId'])
            value = data['value']
            if data.get('action') == 'offer':
                other_player.current_points -= value
                player.current_points += value
            else:
                if value <= player.current_points:
                    other_player.current_points += value
                    player.current_points -= value
                else:
                    return {player.id_in_group: dict(requestPoints=False, initiator=False)} 

            
            log_transaction('yes')
            transactions_data = table_transactions_per_player()
            return {
                player.id_in_group: dict(updateTransactions=True, transactions=transactions_data['receiver_transactions'], otherId=data['otherId'], reload=False, update=True),
                data['otherId']: dict(updateTransactions=True, transactions=transactions_data['initiator_transactions'], otherId=data['playerId'], reload=False, update=True)
            }
        
        # When player reloads their page
        elif data_type == 'reloadPage':
            reload = reload_contribution()
            transactions_data = update_transactions_per_player()
            print(transactions)
            if not transactions.empty:
                reload.update({'updateTransactions':True, 'transactions':transactions_data, 'update': True})
                print(reload)
                return {player.id_in_group: reload}
            return {player.id_in_group: reload}
        

    # Ending the last round of the segment, update segment value
    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.round_number == C.NUM_ROUNDS:
            player.participant.segment += 1


page_sequence = [Instructions, FirstWaitPage, Interaction]