import random
import discord
import logging
import asyncio

import commands
import on_message
import salsa_settings as ss

from datetime import datetime
from typing_tracker import TypingTracker
from typing_insulter import TypingInsulter


class SalsaClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self._typing_tracker = TypingTracker(self)
        self._typing_insulter = TypingInsulter()

    async def on_ready(self):
        print('We have logged in as {0.user}'.format(self))

    async def on_message(self, message):
        if message.author == self.user:
            return

        self._typing_tracker.on_message(message.author)

        # Don't do other things if this message was a command request
        if await commands.handle(self, message):
            return

        # Do all other message processing
        await on_message.handle(self, message)

    async def on_reaction_add(self, reaction, user):
        if user == self.user:
            return

        # Automatically upvote shrimp
        if ss.SHOW_SHRIMP_SUPPORT and reaction.emoji == "🦐":
            await reaction.message.add_reaction("🦐")

    async def on_voice_state_update(self, member, before, after):
        if member == self.user:
            return

        newly_joined = before.channel is None and after.channel is not None
        current_datetime = datetime.now()

        # Sometimes send messages when people join VC
        if ss.WELCOME_GARON_HOME and member.id == ss.NAME_TO_ID["Garon"] and newly_joined and\
                current_datetime.weekday() in ss.WELCOME_GARON_HOME_DAYS and \
                random.random() < ss.WELCOME_GARON_HOME_PROBABILITY and \
                ss.WELCOME_GARON_HOME_TIME_RANGE[0] <= current_datetime.time() <= ss.WELCOME_GARON_HOME_TIME_RANGE[1]:
            await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(f'Welcome home {member.mention}! How was work?')
        elif ss.check_enabled(ss.JOIN_MESSAGES, ss.JOIN_MESSAGES_WHITELIST, member.id) and newly_joined and \
                (random.random() < ss.JOIN_MESSAGES_LIST[member.id][1]):
            await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(ss.JOIN_MESSAGES_LIST[member.id][0])

    async def on_typing(self, channel, user, when):
        if user == self.user:
            return

        await self._typing_tracker.on_typing(user, channel)

    async def user_started_typing(self, user, channel):
        await asyncio.gather(self.start_shadow_typing(user, channel),
                             self._typing_insulter.user_started_typing(user, channel))

    async def user_stopped_typing(self, user, channel):
        self._typing_insulter.user_stopped_typing(user)

    # Make the bot type while other people are typing
    async def start_shadow_typing(self, user, channel):
        if not ss.check_enabled(ss.SHADOW_TYPING_ENABLED, ss.SHADOW_TYPING_WHITELIST, user.id):
            return

        async with channel.typing():
            await self._typing_tracker.wait_until_stopped_typing(user)


def main():
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)

    # Create Intents
    intents = discord.Intents().default()
    intents.members = True

    # Start the SalsaClient
    client = SalsaClient(intents=intents)
    client.run(ss.TOKEN)


if __name__ == '__main__':
    main()
