import random
import discord
import asyncio

import commands
import fridge
import on_message
from fridge import Fridge
import salsa_settings as ss

from datetime import datetime
from datetime import timedelta

import utilities
from typing_tracker import TypingTracker
from typing_insulter import TypingInsulter


class SalsaClient(discord.Client):
    def __init__(self, fridge, **options):
        super().__init__(**options)
        self._fridge: Fridge = fridge
        self._typing_tracker = TypingTracker(self)
        self._typing_insulter = TypingInsulter()
        self._long_term_scheduler = utilities.LongTermScheduler()
        self._has_run_scheduler = False
        self._update_connected_task = None

    def get_the_tunnel(self):
        return self.get_guild(ss.THE_TUNNEL_ID)

    async def update_connected(self):
        # We will update our last known connected timestamp every 5 minutes
        self._fridge.salsa_activity_update_connected()
        return self.update_connected(), datetime.now() + timedelta(minutes=5)

    async def run_daily(self):
        # Change which people get shadow typing day by day
        number_of_victims = round(len(ss.ID_TO_NAME) / 4)
        ss.SHADOW_TYPING_WHITELIST = random.sample(list(ss.NAME_TO_ID.values()), number_of_victims)

        return self.run_daily(), (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    async def birthday(self, user_id):
        # Send a birthday message
        user = self.get_user(user_id)
        if user is not None:
            await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(f"Happy Birthday, {user.mention}! :birthday:")

        await asyncio.sleep(1)
        return self.birthday(user_id), utilities.get_next_birthday(user_id)

    async def fish_gaming_wednesday(self):
        await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(ss.FISH_GAMING_WEDNESDAY_LINK)
        return self.fish_gaming_wednesday(), \
            (datetime.now() + timedelta(weeks=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    async def on_ready(self):
        print("We are connected and ready!")

        # Fill the fridge with the currently active members
        active_users = {}
        for member in self.get_the_tunnel().members:
            # Skip Salsa in this process
            if member == self.user or not isinstance(member, discord.Member):
                continue

            status: discord.Status = member.status
            if status != discord.Status.offline:
                active_users[member.id] = fridge.user_status_adjust_mobile(utilities.convert_user_status(status),
                                                                           member.is_on_mobile())
        self._fridge.user_activity_init(active_users)

        # We want to update the connected timestamp, so we will start the task if it is not already running
        if self._update_connected_task is None:
            self._update_connected_task = self._long_term_scheduler.schedule(self.update_connected(), datetime.now())

        # Prevent the scheduler from being run more than once
        if self._has_run_scheduler:
            return
        self._has_run_scheduler = True

        # Setup daily task
        self._long_term_scheduler.schedule(self.run_daily(), datetime.now())

        # Setup birthday tasks
        for user_id in ss.BIRTHDAYS.keys():
            self._long_term_scheduler.schedule(self.birthday(user_id), utilities.get_next_birthday(user_id))

        # Fish gaming Wednesday
        if ss.FISH_GAMING_WEDNESDAY:
            starting_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if starting_time.weekday() == 2:
                starting_time = starting_time + timedelta(days=1)
            while starting_time.weekday() != 2:
                starting_time = starting_time + timedelta(days=1)

            self._long_term_scheduler.schedule(self.fish_gaming_wednesday(), starting_time)

        # Allow long term tasks to be executed
        await self._long_term_scheduler.run()

    async def on_connect(self):
        pass

    async def on_disconnect(self):
        print("We have been disconnected!")
        # We have disconnected, stop updating the connected timestamp
        if self._update_connected_task is not None:
            self._update_connected_task.cancel()
            self._update_connected_task = None

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
        if ss.WELCOME_GARON_HOME and member.id == ss.NAME_TO_ID["Garon"] and newly_joined and \
                current_datetime.weekday() in ss.WELCOME_GARON_HOME_DAYS and \
                random.random() < ss.WELCOME_GARON_HOME_PROBABILITY and \
                ss.WELCOME_GARON_HOME_TIME_RANGE[0] <= current_datetime.time() <= ss.WELCOME_GARON_HOME_TIME_RANGE[1]:
            await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(f'Welcome home {member.mention}! How was work?')
        elif ss.check_enabled(ss.JOIN_MESSAGES, ss.JOIN_MESSAGES_WHITELIST, member.id) and newly_joined and \
                (random.random() < ss.JOIN_MESSAGES_LIST[member.id][1]):
            await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(ss.JOIN_MESSAGES_LIST[member.id][0])
        elif ss.BOZO_DETECTION and member.id in ss.BOZO_DETECTION_SENSITIVITY and newly_joined:
            # Bozo detection :)
            if random.random() < ss.BOZO_DETECTION_SENSITIVITY[member.id]:
                bozo_channel = self.get_channel(ss.VOICE_CHANNEL_IDS["Bozo's"])
                await member.move_to(bozo_channel)
                await self.get_channel(ss.TEXT_CHANNEL_IDS["general"]).send(ss.BOZO_DETECTED_GIF)

    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if before == self.user:
            return

        before_status = fridge.user_status_adjust_mobile(utilities.convert_user_status(before.status),
                                                         before.is_on_mobile())
        after_status = fridge.user_status_adjust_mobile(utilities.convert_user_status(after.status),
                                                        after.is_on_mobile())

        if before_status != after_status:
            self._fridge.user_activity_update(after.id, after_status)

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

    def about_to_shut_down(self):
        # Final db update of the last connected timestamp
        if self._update_connected_task is not None:
            self._fridge.salsa_activity_update_connected()


def main():
    # Create Intents
    intents = discord.Intents().default()
    intents.members = True
    intents.presences = True
    intents.message_content = True

    # Fridge is the SQLite3 database backend for SalsaProvider
    with Fridge('salsa.db') as fridge:
        # Start the SalsaClient
        client = SalsaClient(fridge, intents=intents)

        async def runner():
            async with client:
                try:
                    await client.start(ss.TOKEN, reconnect=True)
                finally:
                    client.about_to_shut_down()

        discord.utils.setup_logging()

        try:
            asyncio.run(runner())
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
