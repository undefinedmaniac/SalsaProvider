import random
import asyncio

import utilities
import salsa_settings as ss


async def handle(client, message):
    content_lower = message.content.lower()
    content_basic = content_lower.replace(" ", "")

    actions = [_shrimp, _upvote_downvote, _brian, _link_checks, _mug_moments, _ivy_features, _delena_features,
               _thank_you_replies]
    for action in actions:
        await action(client, message, content_lower, content_basic)


async def _shrimp(client, message, content_lower, content_basic):
    # Inject a shrimp emoji into messages randomly
    if (("🦐" in message.content or "shrimp" in content_lower) and ss.SHRIMP_ON_SHRIMP_ACTION) or \
            (random.random() < ss.SHRIMP_INJECTION_PROBABILITY):
        await message.add_reaction("🦐")


async def _upvote_downvote(client, message, content_lower, content_basic):
    if ss.UPVOTE_DOWNVOTE_MESSAGES and (random.random() < ss.UPVOTE_DOWNVOTE_PROBABILITY):
        ratio = ss.TARGETED_UPVOTE_TO_DOWNVOTE_RATIOS.get(message.author.id, ss.UPVOTE_TO_DOWNVOTE_RATIO)
        upvote_probability = ratio / (ratio + 1)
        await message.add_reaction("👍" if random.random() < upvote_probability else "👎")


async def _brian(client, message, content_lower, content_basic):
    # Attempt to get the custom emoji
    emoji = client.get_emoji(ss.BOBS_BRIAN_ID)
    if not emoji:
        return

    # Add Bob's Brian to related messages
    if any((item in content_basic) for item in (str(emoji), "brian", "brain")):
        await message.add_reaction(emoji)


async def _link_checks(client, message, content_lower, content_basic):
    # Call reddit users virgins randomly
    if ss.check_enabled(ss.REDDIT_VIRGIN_DETECTOR, ss.REDDIT_VIRGIN_DETECTOR_WHITELIST, message.author.id) \
            and "reddit.com" in content_lower and (random.random() < ss.REDDIT_VIRGIN_RESPONSE_PROBABILITY):
        for emoji in utilities.convert_to_regional_indicators("VIRGiN"):
            await message.add_reaction(emoji)
    # Call Youtube users losers randomly
    elif ss.check_enabled(ss.YOUTUBE_LOSER_DETECTOR, ss.YOUTUBE_LOSER_DETECTOR_WHITELIST, message.author.id) \
            and ("youtube.com" in content_lower or "youtu.be" in content_lower) and \
            (random.random() < ss.YOUTUBE_LOSER_RESPONSE_PROBABILITY):
        for emoji in utilities.convert_to_regional_indicators("LOSER"):
            await message.add_reaction(emoji)


async def _mug_moments(client, message, content_lower, content_basic):
    # MUG MOMENTS
    if ss.MUG_MOMENTS_ENABLED and content_basic in ("#mugmoment", "#certifiedmugmoment"):
        await message.channel.send(ss.MUG_MOMENT_GIF)
    elif ss.MUG_MOMENTS_ENABLED and random.random() < ss.MUG_MOMENT_PROBABILITY:
        await message.channel.send('What is this? :thinking:', delete_after=60)
        await asyncio.sleep(50)
        await message.channel.send('I think, I just sensed something...', delete_after=20)
        await asyncio.sleep(10)
        await message.channel.send('Could it be???', delete_after=15)
        await asyncio.sleep(5)
        await message.channel.send('IT IS', delete_after=15)
        await asyncio.sleep(5)
        await message.channel.send('THAT WAS A #CERTIFIEDMUGMOMENT')
        await message.channel.send(ss.MUG_MOMENT_GIF)


async def _ivy_features(client, message, content_lower, content_basic):
    if message.author.id != ss.NAME_TO_ID["Ivy"]:
        return

    # Ivy Misspellings
    if ss.MISSPELL_IVY and random.random() < ss.MISSPELL_IVY_PROBABILITY:
        for emoji in random.choice(ss.IVY_EMOJI_MISSPELLINGS):
            await message.add_reaction(emoji)

    # Call Ivy a psycho randomly
    if ss.CALL_IVY_A_PSYCHO and random.random() < ss.CALL_IVY_A_PSYCHO_PROBABILITY:
        await message.channel.send("Psycho", delete_after=3)

    # Add knives and blood because Ivy is evil >:)
    if ss.IVY_ADD_KNIVES and random.random() < ss.IVY_ADD_KNIVES_PROBABILITY:
        await message.add_reaction("🔪")
        await message.add_reaction("🩸")


async def _delena_features(client, message, content_lower, content_basic):
    # Dels
    if ss.DELS and message.author.id == ss.NAME_TO_ID["Delena"] and random.random() < ss.DELS_PROBABILITY:
        for emoji in utilities.convert_to_regional_indicators("DELS"):
            await message.add_reaction(emoji)


async def _thank_you_replies(client, message, content_lower, content_basic):
    # Reply to thank you messages
    if ss.REPLY_TO_THANK_YOU_MESSAGES:
        # Check if the message contains some variant of 'thanks'
        contains_thanks = any((pattern in content_basic) for pattern in ('ty', 'thx', 'thank'))

        # Check if the message contains 'salsa'
        if contains_thanks and 'salsa' in content_basic:
            await message.channel.send(ss.get_thank_you_reply(message.author))
            await message.add_reaction("👍")
