import random
import discord
import discord.ext.commands
import asyncio

import commands
import fridge
import on_message
from fridge import Fridge
from fridge import VoiceStatus
import salsa_settings as ss

from datetime import datetime
from datetime import timedelta

import utilities
from typing_tracker import TypingTracker
from typing_insulter import TypingInsulter


# 1. Christmas Eve is always the 24th of December
# 2. Christmas is always the 25th of December
# 3. Thanksgiving is the 4th Thursday of November
# 4. New years
# 5. Halloween is always October 31st
# 6. 'milk' -> did you mean cum? and then delete
# 7. Goodnight Garon
# 8. Message on leap day (February 29th)
# 9. Valentines day (February 14th)
# 10. 4th of July
# 11. Easter
# 12. Lock off
# 13. ToDo list / Reminders


class SalsaClient(discord.ext.commands.Bot):
    def __init__(self, fridge):
        # Create Intents
        intents = discord.Intents().default()
        intents.members = True
        intents.presences = True
        intents.message_content = True

        # I am the owner of the bot :)
        self.owner_id = ss.NAME_TO_ID['Ian']

        super().__init__(command_prefix=['$'], intents=intents)
        self._fridge: Fridge = fridge
        self._typing_tracker = TypingTracker(self)
        self._typing_insulter = TypingInsulter()
        self._long_term_scheduler = utilities.LongTermScheduler()
        self._has_run_scheduler = False
        self._update_connected_task = None

        # Used to track the w101 news that has been seen today
        self._w101_news_headers = set()

        # Used to track do not disturb and invisible users
        self._quiet_users = set()

    def get_the_tunnel(self) -> discord.Guild:
        return self.get_guild(ss.THE_TUNNEL_ID)

    async def update_connected(self):
        # We will update our last known connected timestamp every 5 minutes
        self._fridge.salsa_activity_update_connected()
        return self.update_connected(), datetime.now() + timedelta(minutes=5)

    async def run_daily(self):
        # Change which people get shadow typing day by day
        number_of_victims = round(len(ss.ID_TO_NAME) / 4)
        ss.SHADOW_TYPING_WHITELIST = random.sample(list(ss.NAME_TO_ID.values()), number_of_victims)

        # Clear news headers
        self._w101_news_headers.clear()

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

    async def w101_news_check(self):
        async for header, content in utilities.check_w101_news():
            if header in self._w101_news_headers:
                continue

            self._w101_news_headers.add(header)

            ian = self.get_user(ss.NAME_TO_ID["Ian"])
            if ian is not None:
                embed = discord.Embed(title=f"Wizard101 News: {header}", description=content)
                await ian.send(embed=embed)

        return self.w101_news_check(), datetime.now() + timedelta(hours=6)

    async def one_time_message(self, msg):
        general = self.get_channel(ss.TEXT_CHANNEL_IDS["general"])
        await general.send(msg)
        return None

    async def setup_hook(self):
        # Load app commands
        commands.load_app_commands(self)

    async def on_ready(self):
        print("We are connected and ready!")

        await self.on_ready_or_resume()

        # Prevent the scheduler from being run more than once
        if self._has_run_scheduler:
            return
        self._has_run_scheduler = True

        # Setup daily task
        self._long_term_scheduler.schedule(self.run_daily(), datetime.now())

        # Setup birthday tasks
        for user_id in ss.BIRTHDAYS.keys():
            self._long_term_scheduler.schedule(self.birthday(user_id), utilities.get_next_birthday(user_id))

        now = datetime.now()
        schedule_msg = lambda t, msg: self._long_term_scheduler.schedule(self.one_time_message(msg), t)

        # Fish gaming Wednesday
        if ss.FISH_GAMING_WEDNESDAY:
            starting_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if starting_time.weekday() == 2:
                starting_time = starting_time + timedelta(days=1)
            while starting_time.weekday() != 2:
                starting_time = starting_time + timedelta(days=1)

            self._long_term_scheduler.schedule(self.fish_gaming_wednesday(), starting_time)

        # Wizard101 news notifications
        if ss.W101_NEWS_NOTIFICATIONS:
            first_check = now + timedelta(hours=6)
            self._long_term_scheduler.schedule(self.w101_news_check(), first_check)

        # Christmas related messages
        before_christmas = now.replace(month=12, day=18, hour=0, minute=0, second=0, microsecond=0)
        before_christmas  = utilities.next_annual_event(before_christmas)

        christmas_eve = now.replace(month=12, day=24, hour=0, minute=0, second=0, microsecond=0)
        christmas_eve = utilities.next_annual_event(christmas_eve)

        christmas = now.replace(month=12, day=25, hour=0, minute=0, second=0, microsecond=0)
        christmas = utilities.next_annual_event(christmas)

        schedule_msg(before_christmas, "https://www.youtube.com/watch?v=M16CZ38PuFQ&"\
            "pp=ygUaY2hyaXN0bWFzIGp1c3QgYSB3ZWVrIGF3YXk%3D")

        schedule_msg(christmas_eve, "It's Christmas Eve! :santa: :cookie: :milk:")
        schedule_msg(christmas, "Merry Christmas Everyone! :christmas_tree: :gift:")

        # New years
        new_year = datetime(year=now.year + 1, month=1, day=1, hour=0, \
                minute=0, second=0, microsecond=0)

        schedule_msg(new_year, "Happy New Year! :fireworks: :sparkler: :champagne_glass:")

        # Halloween
        halloween = now.replace(month=10, day=31, hour=0, minute=0, second=0, microsecond=0)
        halloween = utilities.next_annual_event(halloween)

        schedule_msg(halloween, "It's spooky time... :skull: :headstone: :black_cat: :ladder:")

        # 4th of July
        fourth_of_july = now.replace(month=7, day=4, hour=0, minute=0, second=0, microsecond=0)
        fourth_of_july = utilities.next_annual_event(fourth_of_july)

        schedule_msg(fourth_of_july, "Happy 4th of July! :flag_us: :fireworks:")

        # Leap day
        def try_leap_day(datetime):
            try:
                return datetime.replace(month=2, day=29, hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                return None

        leap_day = try_leap_day(now)
        if leap_day is not None and now > leap_day:
            leap_day = None

        tries = 1
        while leap_day is None:
            leap_day = try_leap_day(now.replace(year=now.year + tries))
            tries += 1

        schedule_msg(leap_day, "It's a leap day! :frog: This doesn't happen very often, so enjoy while it lasts!")

        # Thanksgiving
        def find_thanksgiving(year):
            thanksgiving = datetime(year=year, month=11, day=1, hour=0, minute=0, second=0, microsecond=0)
            while thanksgiving.weekday() != 3:
                thanksgiving += timedelta(days=1)

            thanksgiving += timedelta(weeks=3)
            return thanksgiving

        thanksgiving = find_thanksgiving(now.year)
        if now > thanksgiving:
            thanksgiving = find_thanksgiving(now.year + 1)

        schedule_msg(thanksgiving, "Have a great Thanksgiving everyone! :turkey: And eat well :yum:")

        # Allow long term tasks to be executed
        await self._long_term_scheduler.run()

    async def on_resumed(self):
        await self.on_ready_or_resume()

    async def on_ready_or_resume(self):
        print(f'Ready or Resume. {datetime.now()}')

        # Reset quiet users
        self._quiet_users.clear()

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

            # Fill quiet users
            self._quiet_users_update(member)

        self._fridge.user_activity_init(active_users)

        # Fill the fridge with the members who are currently in VC
        active_users = {}
        temp = None
        accompanied = False
        for channel in self.get_the_tunnel().voice_channels:
            if channel == self.get_the_tunnel().afk_channel:
                for member in channel.members:
                    active_users[member.id] = VoiceStatus.AFK
            else:
                for member in channel.members:
                    if temp is None:
                        temp = member
                    else:
                        accompanied = True
                        active_users[member.id] = VoiceStatus.Accompanied

        if temp is not None:
            active_users[temp.id] = VoiceStatus.Accompanied if accompanied else VoiceStatus.Unaccompanied

        self._fridge.voice_activity_init(active_users)

        # We want to update the connected timestamp, so we will start the task if it is not already running
        if self._update_connected_task is None:
            self._update_connected_task = self._long_term_scheduler.schedule(self.update_connected(), datetime.now())

    async def on_disconnect(self):
        print("We have been disconnected!")
        # We have disconnected, stop updating the connected timestamp
        if self._update_connected_task is not None:
            self._update_connected_task.cancel()
            self._update_connected_task = None

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        self._typing_tracker.on_message(message.author)

        # We must call this to ensure that discord.Bot commands work properly
        await self.process_commands(message)

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

    async def deafen_quiet_user(self, member, voice_state, general_channel):
        if voice_state is None:
            return

        # Deafen people who are using the status incorrectly
        if voice_state.channel is not None and not voice_state.deaf and member.id in self._quiet_users:
            await member.edit(deafen=True)

            status_text = 'Do Not Distrub' if member.status == discord.Status.dnd else 'Invisible'
            message = f"The user {member.display_name} has their status set to `{status_text}`! Please do not bother " \
                      f"them! They will be automatically deafened until their status has changed :grin:"
            content = discord.Embed(title=':exclamation: Invalid Status Detected!', description=message,
                                    color=discord.Color.dark_red())
            await general_channel.send(embed=content, delete_after=10)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if member == self.user:
            return

        # Ensure quiet user data is up-to-date
        self._quiet_users_update(member)

        # The handle to the general channel
        general_channel = self.get_channel(ss.TEXT_CHANNEL_IDS["general"])

        # Deafen the user if their status is dnd or invisible
        await self.deafen_quiet_user(member, after, general_channel)

        newly_joined = before.channel is None and after.channel is not None
        current_datetime = datetime.now()

        # Ensure there was a channel change
        if before.channel != after.channel:
            normal_channels = set(channel for channel in self.get_the_tunnel().voice_channels if
                                  channel != self.get_the_tunnel().afk_channel)
            group_size = sum(len(channel.members) for channel in normal_channels)

            # First update the status of other user who may be in the 'normal' voice channels (non-AFK)
            left_normal_channel = before.channel in normal_channels
            joined_normal_channel = after.channel in normal_channels
            if left_normal_channel ^ joined_normal_channel and group_size == int(joined_normal_channel) + 1:
                for channel in normal_channels:
                    for existing_member in channel.members:
                        if existing_member == member:
                            continue

                        # Update this special member's status
                        status = VoiceStatus.Unaccompanied if left_normal_channel else VoiceStatus.Accompanied
                        print(f"Update {existing_member.name}'s status to {status.name}")
                        self._fridge.voice_activity_update(existing_member.id, status, current_datetime)
                        break

            # Then update our own status
            status = None
            if after.channel is None:
                status = VoiceStatus.Disconnected
            elif after.afk:
                status = VoiceStatus.AFK
            elif joined_normal_channel and not left_normal_channel:
                status = VoiceStatus.Unaccompanied if group_size == 1 else VoiceStatus.Accompanied

            # Update our own status
            if status is not None:
                print(f"Update {member.name}'s status to {status.name}")
                self._fridge.voice_activity_update(member.id, status, current_datetime)

        if newly_joined:
            # Sometimes send messages when people join VC
            if ss.WELCOME_GARON_HOME and member.id == ss.NAME_TO_ID["Garon"] and current_datetime.weekday() \
                    in ss.WELCOME_GARON_HOME_DAYS and random.random() < ss.WELCOME_GARON_HOME_PROBABILITY and \
                    ss.WELCOME_GARON_HOME_TIME_RANGE[0] <= current_datetime.time() <= \
                    ss.WELCOME_GARON_HOME_TIME_RANGE[1]:
                await general_channel.send(f'Welcome home {member.mention}! How was work?')
            elif ss.check_enabled(ss.JOIN_MESSAGES, ss.JOIN_MESSAGES_WHITELIST, member.id) and \
                    (random.random() < ss.JOIN_MESSAGES_LIST[member.id][1]):
                await general_channel.send(ss.JOIN_MESSAGES_LIST[member.id][0])
            elif ss.BOZO_DETECTION and member.id in ss.BOZO_DETECTION_SENSITIVITY:
                # Bozo detection :)
                if random.random() < ss.BOZO_DETECTION_SENSITIVITY[member.id]:
                    bozo_channel = self.get_channel(ss.VOICE_CHANNEL_IDS["Bozo's"])
                    await member.move_to(bozo_channel)
                    await general_channel.send(ss.BOZO_DETECTED_GIF)

    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if before == self.user:
            return

        # Updates quiet users, un-deafens when a member is in a voice channel and changes status
        if self._quiet_users_update(after) and after.voice is not None and after.voice.channel is not None:
            await after.edit(deafen=False)
        else:
            # This will cause a user to immediately be deafened if they change status to invis or dnd while in a vc
            await self.deafen_quiet_user(after, after.voice, self.get_channel(ss.TEXT_CHANNEL_IDS["general"]))

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

    @property
    def fridge(self):
        return self._fridge

    def _quiet_users_update(self, member: discord.Member):
        # Maintain a list of 'quiet users' who are in dnd or offline status
        if member.status in (discord.Status.do_not_disturb, discord.Status.offline):
            self._quiet_users.add(member.id)
        else:
            try:
                self._quiet_users.remove(member.id)
                return True
            except KeyError:
                pass

        return False


def main():
    # Fridge is the SQLite3 database backend for SalsaProvider
    with Fridge('salsa.db') as fridge:
        # Start the SalsaClient
        client = SalsaClient(fridge)

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
