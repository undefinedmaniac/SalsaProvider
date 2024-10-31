import random
import utilities
import private_settings as ps
from datetime import time

# The settings below are 'private settings'. They are stored in a different file because they contain sensitive info
# Discord API Token
TOKEN = ps.DISCORD_API_TOKEN

THE_TUNNEL_ID = ps.THE_TUNNEL_ID

# Known users, for targeting purposes
ID_TO_NAME = ps.ID_TO_NAME
NAME_TO_ID = ps.NAME_TO_ID

TEXT_CHANNEL_IDS = ps.TEXT_CHANNEL_IDS

VOICE_CHANNEL_IDS = ps.VOICE_CHANNEL_IDS
BIG_BOSS_ROLE_ID = ps.BIG_BOSS_ROLE_ID
BOBS_BRIAN_ID = ps.BOBS_BRIAN_ID


# Birthdays
BIRTHDAYS = ps.BIRTHDAYS


# Shadow Typing settings - Makes the bot type while users are typing
SHADOW_TYPING_ENABLED = True
SHADOW_TYPING_WHITELIST = []  # Blank list means everyone is victim

# Typing Insults settings - Insults users for taking too long to type
TYPING_INSULTS_ENABLED = True
TYPING_INSULTS_WHITELIST = []
TYPING_INSULTS_TIMEOUTS = [30]*4


# Shrimp Provider settings
RANDOM_SHRIMP_INJECTION = True
SHRIMP_INJECTION_PROBABILITY = 1.0/70.0  # 1 in 70 chance

# Should the bot automatically upvote shrimp emoji
SHOW_SHRIMP_SUPPORT = True

# Always add shrimp to shrimp
SHRIMP_ON_SHRIMP_ACTION = True


# Randomly upvote/downvote messages
UPVOTE_DOWNVOTE_MESSAGES = True
UPVOTE_DOWNVOTE_PROBABILITY = 1.0/70.0  # 1 in 70 chance
UPVOTE_TO_DOWNVOTE_RATIO = 1  # 1:1

# Override the upvote:downvote ratio for specific users
TARGETED_UPVOTE_TO_DOWNVOTE_RATIOS = {NAME_TO_ID["Tanner"]: 1/3, NAME_TO_ID["Ivy"]: 1/2, NAME_TO_ID["Delena"]: 2,
                                      NAME_TO_ID["Garon"]: 3/4}


# Call reddit users virgins
REDDIT_VIRGIN_DETECTOR = True
REDDIT_VIRGIN_DETECTOR_WHITELIST = [user_id for user_id in ID_TO_NAME.keys()
                                    if ID_TO_NAME[user_id] not in ["Ivy", "Delena"]]
REDDIT_VIRGIN_RESPONSE_PROBABILITY = 1.0/10.0  # 1 in 10 chance


# Call Youtube users losers
YOUTUBE_LOSER_DETECTOR = True
YOUTUBE_LOSER_DETECTOR_WHITELIST = []
YOUTUBE_LOSER_RESPONSE_PROBABILITY = 1.0/10.0  # 1 in 10 chance


# MUG MOMENT
MUG_MOMENTS_ENABLED = True
MUG_MOMENT_PROBABILITY = 1.0/1000.0
MUG_MOMENT_GIF = 'https://c.tenor.com/LwGE9-Fggt8AAAAC/mug-root-beer-mug.gif'


# Misspell Ivy's Name (and spell it correctly rarely, after all, we don't want to make her sad)
MISSPELL_IVY = True
IVY_EMOJI_MISSPELLINGS = [utilities.convert_to_regional_indicators(name) for name in
                          ['IV', 'IY', 'AIVi', 'ICYMi', 'IVY', "IViE"]]
MISSPELL_IVY_PROBABILITY = 1.0/15.0


# Ivy Psycho Alert
CALL_IVY_A_PSYCHO = True
CALL_IVY_A_PSYCHO_PROBABILITY = 1.0/15.0


# Ivy likes knives
IVY_ADD_KNIVES = True
IVY_ADD_KNIVES_PROBABILITY = 1.0/15.0


# Dels
DELS = True
DELS_PROBABILITY = 1.0/12.0


# Special messages when someone joins a VC
JOIN_MESSAGES = True
# ID: (Message, Probability)
JOIN_MESSAGES_LIST = {NAME_TO_ID["Reen"]: ("OMG bro, it's the sick gamer R33N!", 1.0/10.0),
                      NAME_TO_ID["David"]: ("Professional GAMER Kah-se-uh-g enters...", 1.0/5.0),
                      NAME_TO_ID["Vianey"]: ("Wow! It's the #1 Pro DPS Player:tm:, Vianey!", 1.0/5.0),
                      NAME_TO_ID["Ivy"]: ("Whoa, is that Ivy?", 8.0/10.0),
                      NAME_TO_ID["Delena"]: ("Everyone watch out! Delena has ENTERED The Tunnel", 1.0),
                      NAME_TO_ID["Jules"]: ("Holy crap!! It's Jules!! What a pleasant surprise :)", 1.0),
                      NAME_TO_ID["Tanner"]: ("Is that TTTripple T TTTanner??", 1.0/100.0),
                      NAME_TO_ID["Eric"]: ("The Wu has come for YOU", 1.0/100.0),
                      NAME_TO_ID["Ian"]: ("Can't think of anything to say for yourself, huh? Loser.", 1.0/100.0),
                      NAME_TO_ID["Alex"]: ("Welcome Alex! How has your day been?", 1.0),
                      NAME_TO_ID["Garon"]: ("Hello there, GruxDeluxe. I mean Garon 😅", 1.0/100.0)}
JOIN_MESSAGES_WHITELIST = JOIN_MESSAGES_LIST.keys()


# Bozo detection service
BOZO_DETECTION = True
BOZO_DETECTED_GIF = 'https://tenor.com/view/bozo-detected-bozo-detected-bozo-found-found-gif-23176259'
BOZO_DETECTION_SENSITIVITY = {NAME_TO_ID["Reen"]: 1/20.0, NAME_TO_ID["Garon"]: 1/25.0}


# Welcome Garon home from work
WELCOME_GARON_HOME = True
WELCOME_GARON_HOME_DAYS = [0, 1, 2, 3, 4, 5]
WELCOME_GARON_HOME_TIME_RANGE = (time(hour=17, minute=0), time(hour=18, minute=0))  # 5:00 - 6:00
WELCOME_GARON_HOME_PROBABILITY = 1.0/2.0


# Replies for thanks
REPLY_TO_THANK_YOU_MESSAGES = True
THANK_YOU_REPLY_TEMPLATES = ["You're welcome, {}!", "My pleasure, {}!", "No problem, {}!", "Happy to help!"]


# Salsa
HAVE_SALSA_INSTEAD_PROBABILITY = 1.0/25.0
MESS_UP_AND_GIVE_SHRIMP_PROBABILITY = 1.0/10.0
SALSA_IMAGES = ['https://thecozycook.com/wp-content/uploads/2021/06/Salsa-Recipe-f-500x375.jpg',
                'https://cookieandkate.com/images/2018/04/best-red-salsa-recipe.jpg',
                'https://dinnersdishesanddesserts.com/wp-content/uploads/2012/02/Chilis-Salsa-3-square.jpg',
                'https://www.muydelish.com/wp-content/uploads/2019/12/Salsa-Mexicana-4.jpg',
                'https://www.eatthis.com/wp-content/uploads/sites/4/2020/01/how-to-make-restaurant-salsa-6.jpg',
                'https://www.chilipeppermadness.com/wp-content/uploads/2020/01/Chile-de-Arbol-Salsa-Recipe1.jpg',
                'https://houseofyumm.com/wp-content/uploads/2021/06/Salsa-10-500x500.jpg',
                'https://cdn.discordapp.com/attachments/610280973740802059/1063758845547134986/Screen-Shot-2019-08-21-at-11.14.22-AM.png']

# Shrimp
SHRIMP_IMAGES = ['https://www.acouplecooks.com/wp-content/uploads/2018/09/Grilled-Shrimp-006.jpg',
                 'https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxzZWFyY2h8N3x8c2hyaW1wfGVufDB8fDB8fA%3D%3D&w=1000&q=80',
                 'https://www.tastingtable.com/img/gallery/sweet-and-spicy-grilled-shrimp-recipe/l-intro-1643120504.jpg']


# Fish gaming wednesday
FISH_GAMING_WEDNESDAY = True
FISH_GAMING_WEDNESDAY_LINK = 'https://www.youtube.com/watch?v=vEVGoSaJ9K8'

# Wizard101 news
W101_NEWS_NOTIFICATIONS = True
W101_NEWS_WEBPAGE = 'https://www.wizard101.com/game/news'

# Insults



def get_thank_you_reply(user):
    response = random.choice(THANK_YOU_REPLY_TEMPLATES)
    if "{}" in response:
        response = response.format(user.mention)
    return response


def check_enabled(enabled, whitelist, user_id):
    return enabled and (not whitelist or user_id in whitelist)
