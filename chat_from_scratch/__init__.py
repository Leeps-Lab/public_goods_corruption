from otree.api import *
from spanlp.palabrota import Palabrota # type: ignore

doc = """
Of course oTree has a readymade chat widget described here: 
https://otree.readthedocs.io/en/latest/multiplayer/chat.html

But you can use this if you want a chat box that is more easily customizable,
or if you want programmatic access to the chat messages. 

This app can also help you learn about live pages in general.
"""


class C(BaseConstants):
    NAME_IN_URL = 'chat_from_scratch'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


class Message(ExtraModel):
    group = models.Link(Group)
    channel = models.CharField(max_length=255)
    sender = models.Link(Player)
    recipient = models.Link(Player)
    text = models.StringField()


def to_dict(msg: Message):
    return dict(channel=msg.channel, sender=msg.sender.id_in_group, recipient=msg.recipient.id_in_group, text=msg.text)


# PAGES
class MyPage(Page):
    @staticmethod
    def vars_for_template(player):
        others = player.get_others_in_group()

        # Ensure Player 4 (id_in_group == 4) appears first for Players 1, 2, and 3
        if player.id_in_group != 4:
            others = sorted(others, key=lambda p: 0 if p.id_in_group == 4 else 1)

        return dict(
            other_ids=[p.id_in_group for p in others]
        )
    
    @staticmethod
    def js_vars(player: Player):
        return dict(
            my_id=player.id_in_group,
            other_ids=[p.id_in_group for p in player.get_others_in_group()]
        )

    @staticmethod
    def live_method(player: Player, data):
        my_id = player.id_in_group
        group = player.group

        if 'text' in data and 'recipient' in data:
            recipient_id = data['recipient']

            channel = f'{min(my_id, recipient_id)}{max(my_id, recipient_id)}'

            print(f'recipient_id: {recipient_id}')
            print(f'channel: {channel}')
            print(f'group.get_player_by_id(my_id): {group.get_player_by_id(my_id)}')
            print(f'group.get_player_by_id(recipient_id): {group.get_player_by_id(recipient_id)}')
            
            text_unfiltered = data['text']
            palabrota = Palabrota()
            print(f'contains bad word: {palabrota.contains_palabrota(text_unfiltered)}')
            if palabrota.contains_palabrota(text_unfiltered):
                text_filtered = palabrota.censor(text_unfiltered)
                print(f'text filtered: {text_filtered}')
            else:
                text_filtered = text_unfiltered

            msg = Message.create(
                group=group,
                sender=group.get_player_by_id(my_id),
                recipient=group.get_player_by_id(recipient_id),
                channel=channel,
                text=text_filtered
            )

            return {
                my_id: [to_dict(msg)],
                recipient_id: [to_dict(msg)]
            }

        return {
            my_id: [
                to_dict(msg)
                for msg in Message.filter(group=group)
                if msg.sender and msg.recipient and my_id in [msg.sender.id_in_group, msg.recipient.id_in_group]
            ]
        }

page_sequence = [MyPage]