from otree.api import *
# import os
# from openai import OpenAI # type: ignore
# from dotenv import load_dotenv # type: ignore

# load_dotenv()
# api_key = os.getenv("API_KEY")
# client = OpenAI(api_key=api_key)


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
    # chatGPT vars
    TEMP = 1 # temperature (range 0 - 2)
    MODEL = "gpt-4o"


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
    def js_vars(player: Player):
        return dict(
            my_id=player.id_in_group,
            other_ids=[p.id_in_group for p in player.get_others_in_group()]
        )

    @staticmethod
    def live_method(player: Player, data):
        my_id = player.id_in_group
        others = player.get_others_in_group()
        group = player.group

        if 'text' in data and 'recipient' in data:
            recipient_id = data['recipient']

            channel = f'{min(my_id, recipient_id)}{max(my_id, recipient_id)}'

            print(f'recipient_id: {recipient_id}')
            print(f'channel: {channel}')
            print(f'group.get_player_by_id(my_id): {group.get_player_by_id(my_id)}')
            print(f'group.get_player_by_id(recipient_id): {group.get_player_by_id(recipient_id)}')
            
            text=data['text']

            msg = Message.create(
                group=group,
                sender=group.get_player_by_id(my_id),
                recipient=group.get_player_by_id(recipient_id),
                channel=channel,
                text=data['text']
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