import random
import utilities
import TOKEN
from datetime import time

# Discord API Token (the actual value is stored in a different file so that it will not be uploaded to Github)
TOKEN = TOKEN.DISCORD_API_TOKEN

# Known users, for targeting purposes
ID_TO_NAME = {241002474381508608: "Ian", 243501514721591298: "Tanner", 192855603385729025: "Eric",
              378790883082108929: "Garon", 326079163045773333: "Reen", 256950752734478338: "David",
              98218169587466240: "Ivy", 98217798500630528: "Delena", 554147249102258176: "Jules",
              241803924317667328: "Alex", 254421882005225473: "Vianey"}
NAME_TO_ID = dict(map(reversed, ID_TO_NAME.items()))

TEXT_CHANNEL_IDS = {"general": 610280973740802059,
                    "spam": 616097148785786902,
                    "wide-garon": 798627012138238064}

VOICE_CHANNEL_IDS = {"General": 610280973740802061,
                     "second": 610281598788698123,
                     "ahhpppfffkk": 618632979417268254,
                     "Library": 618638962923143188}
BIG_BOSS_ROLE_ID = 610282292539031554
BOBS_BRIAN_ID = 808422914223112214

# Shadow Typing settings - Makes the bot type while users are typing
SHADOW_TYPING_ENABLED = True
SHADOW_TYPING_WHITELIST = [NAME_TO_ID[name] for name in ["Ivy"]]  # Blank list means everyone is victim

# Typing Insults settings - Insults users for taking too long to type
TYPING_INSULTS_ENABLED = True
TYPING_INSULTS_WHITELIST = []
TYPING_INSULTS_TIMEOUTS = [30]*4


# Shrimp Provider settings
RANDOM_SHRIMP_INJECTION = True
SHRIMP_INJECTION_PROBABILITY = 1.0/60.0  # 1 in 60 chance

# Should the bot automatically upvote shrimp emoji
SHOW_SHRIMP_SUPPORT = True

# Always add shrimp to shrimp
SHRIMP_ON_SHRIMP_ACTION = True


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
                          ['IV', 'IY', 'AIVi', 'ICYMi', 'IVY']]
MISSPELL_IVY_PROBABILITY = 1.0/10.0


# Ivy Psycho Alert
CALL_IVY_A_PSYCHO = True
CALL_IVY_A_PSYCHO_PROBABILITY = 1.0/10.0


# Dels
DELS = True
DELS_PROBABILITY = 1.0/10.0


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


# Welcome Garon home from work
WELCOME_GARON_HOME = True
WELCOME_GARON_HOME_DAYS = [0, 2, 3, 4, 5]
WELCOME_GARON_HOME_TIME_RANGE = (time(hour=21, minute=30), time(hour=22, minute=30))  # 9:30 - 10:30
WELCOME_GARON_HOME_PROBABILITY = 3.0/4.0


# Replies for thanks
REPLY_TO_THANK_YOU_MESSAGES = True
THANK_YOU_REPLY_TEMPLATES = ["You're welcome, {}!", "My pleasure, {}!", "No problem, {}!", "Happy to help!"]


def get_thank_you_reply(user):
    response = random.choice(THANK_YOU_REPLY_TEMPLATES)
    if "{}" in response:
        response = response.format(user.mention)
    return response


def check_enabled(enabled, whitelist, user_id):
    return enabled and (not whitelist or user_id in whitelist)
