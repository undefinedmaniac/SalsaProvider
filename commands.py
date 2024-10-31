import datetime
import re
import random
import inspect
import asyncio
from typing import Union, List, Optional, Callable, Awaitable, Any, Type, Iterable

import discord
from discord import app_commands

import fridge
import salsa_settings as ss
from functools import partial

import utilities
from fridge import UserStatus, VoiceStatus
from main import SalsaClient

# Stores the last command issued by each user
last_command = {}

BOT_COMMAND_PATTERN = re.compile(r"(?i)^!salsa\s*(.*?)\s*$")
COMMAND_CHANNEL_NAME = 'spam'


def get_command_channel(bot: SalsaClient) -> discord.TextChannel:
    for channel in bot.get_the_tunnel().channels:
        if isinstance(channel, discord.TextChannel) and channel.name == COMMAND_CHANNEL_NAME:
            return channel


def args_to_text(args: Iterable[Any]) -> str:
    text_args = []
    for arg in args:
        if isinstance(arg, (str, int)):
            text_args.append(str(arg))
        elif isinstance(arg, (discord.User, discord.Member)):
            text_args.append(arg.display_name)
        elif isinstance(arg, discord.VoiceChannel):
            text_args.append(arg.name)

    return " ".join(f'"{arg}"' for arg in text_args)


def _error(message: str):
    embed = discord.Embed(title=':warning: Command Error', description=message,
                          color=discord.Color.dark_red())
    return embed


class CommandContext:
    def __init__(self, bot: SalsaClient, context: Union[discord.Message, discord.Interaction]):
        self.context = context
        self.bot = bot
        self._responded = False

        # Setup send() function to use the correct underlying f() call
        if self.is_message():
            self._send = self.context.channel.send
            self.author = self.context.author
        else:
            self._send = self.context.response.send_message
            self.author = self.context.user

    async def prepare(self, command_name: str, *args, **kwargs):
        if self.is_context_menu():
            await self.context.response.send_message(f'Redirecting to command channel!', ephemeral=True, delete_after=3)
            command_channel = get_command_channel(self.bot)
            self._send = command_channel.send
            text_args = args_to_text(args + tuple(kwargs.values()))
            if text_args:
                text_args = ' ' + text_args
            await command_channel.send(f'{self.author.display_name} executed `/{command_name}{text_args}`')

    async def finish(self):
        if not self._responded:
            if self.is_slash_command():
                await self.send('Done!')
            elif self.is_message():
                await self.context.add_reaction('👍')

    async def send(self, *args, **kwargs):
        self._responded = True
        await self._send(*args, **kwargs)
        if self.is_slash_command():
            self._send = self.context.followup.send

    async def defer(self, *args, **kwargs):
        if self.is_slash_command() and not self._responded:
            await self.context.response.defer(*args, **kwargs)
            self._send = self.context.followup.send

    def is_message(self):
        return isinstance(self.context, discord.Message)

    def is_interaction(self):
        return isinstance(self.context, discord.Interaction)

    def is_slash_command(self):
        return self.is_interaction() and isinstance(self.context.command, app_commands.Command)

    def is_context_menu(self):
        return self.is_interaction() and isinstance(self.context.command, app_commands.ContextMenu)


async def _default_match(command_name: str, command_text: str) -> Optional[List[str]]:
    text_parts = utilities.split_respect_quotes(command_text)

    length = 0
    for index, part in enumerate(text_parts):
        length += len(part)
        if length > len(command_name):
            return None
        elif length == len(command_name):
            if ''.join(text_parts[:index + 1]).lower() != command_name.lower():
                return None

            return text_parts[index + 1:]

    return None


# Verifies that a user is a Member and that they have the 'big boss role'
def _has_boss_role(member):
    # Override for me
    if member.id == ss.NAME_TO_ID['Ian']:
        return True

    if not isinstance(member, discord.Member):
        return False

    for role in member.roles:
        if role.id == ss.BIG_BOSS_ROLE_ID:
            return True

    return False


async def _have_salsa_instead(context: CommandContext):
    # Random chance to sabotage other commands and deliver salsa instead
    if random.random() >= ss.HAVE_SALSA_INSTEAD_PROBABILITY:
        return False

    await context.send("Instead of that, have some salsa! :)")
    if random.random() < ss.MESS_UP_AND_GIVE_SHRIMP_PROBABILITY and context.is_message():
        # Mess up and give them shrimp first
        await context.send(random.choice(ss.SHRIMP_IMAGES), delete_after=8)
        await asyncio.sleep(5)
        await context.send("OOPS! Wrong one!! :sweat_smile:", delete_after=4)
        await asyncio.sleep(5)

    await context.send(random.choice(ss.SALSA_IMAGES))
    return True


class SalsaCommand:
    def __init__(self, name: str, description: str,
                 invoke_func: Callable[[CommandContext, ...], Awaitable[None]],
                 match_func: Callable[[str], Awaitable[Optional[List[str]]]] = None, *, display_name: str = None):
        self.name = name
        self.description = description
        self._invoke = invoke_func
        self.match = partial(_default_match, name) if match_func is None else match_func
        self.display_name = name if display_name is None else display_name

    # Returns the parameters to the command. When calling self.invoke(), the inputs should be
    # 1. A CommandContext object and 2. a list of parameters corresponding to the ones returned by this method
    def get_parameters(self) -> List[inspect.Parameter]:
        return [parameter for i, parameter in enumerate(inspect.signature(self._invoke).parameters.values()) if i != 0]

    def get_docs(self) -> str:
        return self._invoke.__doc__

    # Invokes the command with the provided parameters
    async def invoke(self, context: CommandContext, *args, **kwargs) -> None:
        # Store this command + args so that the user can use the redo command later if they wish
        last_command[context.author.id] = (self, args, kwargs)

        # If we do not decide to give the user salsa instead, invoke the requested command
        if not await _have_salsa_instead(context):
            await self._invoke(context, *args, **kwargs)


# This is a special command. It will act like a normal command with no parameters, however, when invoked it will look up
# the previously run command for the user and then invoke that command instead, reusing the previous parameters
class RedoCommand(SalsaCommand):
    def __init__(self):
        super().__init__(name='redo', description='Execute your previous command again', invoke_func=None)

    def get_parameters(self) -> List[inspect.Parameter]:
        return []

    def get_docs(self) -> str:
        return ""

    async def invoke(self, context: CommandContext, *args, **kwargs) -> None:
        command_info = last_command.get(context.author.id)
        if command_info is None:
            await context.send(embed=_error('If you\'ve used a command previously, '
                                            'I can\'t remember what it was. Sorry :('))
        else:
            command = command_info[0]
            args = command_info[1]
            kwargs = command_info[2]
            text_args = args_to_text(args + tuple(kwargs.values()))
            if text_args:
                text_args = ' ' + text_args
            await context.send(f'Executing `/{command.display_name}{text_args}`')
            await command.invoke(context, *args, **kwargs)


def _seen():
    async def invoke(context: CommandContext, member: discord.Member) -> None:
        """
        Args:
            member: The Discord member whose last seen info should be displayed
        """
        # Permission check
        if not _has_boss_role(context.author):
            await context.send(embed=_error("You don't have permission to use this command!"))
            return

        if member == context.bot.user:
            # Protect SalsaProvider from being nicknamed
            await context.send("I am always here. I see you. Not the other way around :grinning:")
            return

        def get_color_circle(status: UserStatus):
            is_mobile = fridge.user_status_check_mobile(status)
            status = fridge.user_status_adjust_mobile(status, False)

            text = ''
            if status == UserStatus.Online:
                text = ':green_circle:'
            elif status == UserStatus.Idle:
                text = ':yellow_circle:'
            elif status == UserStatus.DoNotDisturb:
                text = ':red_circle:'

            return text + (':mobile_phone:' if is_mobile else '')

        current_timestamp = datetime.datetime.now()
        last_activity = context.bot.fridge.get_last_user_activity(member.id)
        if last_activity is None:
            description = f'There is no activity history for {member.name}. This could be my fault, or, it may have ' \
                          f'been a very long time since their last activity'
            last_known_status = 'No History'
        elif last_activity[2] is None:
            # Currently online/idle/dnd
            description = f'{member.name} is currently active and has been active since ' \
                          f'{last_activity[1].strftime("%I:%M %p (%H:%M)")}'
            duration = round((current_timestamp - last_activity[1]) / datetime.timedelta(minutes=1))
            last_known_status = f'{get_color_circle(last_activity[0])} {last_activity[0]} for {duration} minutes'
        else:
            last_active_timestamp = last_activity[1] + last_activity[2]
            description = last_active_timestamp.strftime(
                f'{member.name} was last seen on %A, %B %d, %Y (%m/%d/%y) at %I:%M %p (%H:%M). They have been Offline '
                f'for {round((current_timestamp - last_active_timestamp) / datetime.timedelta(minutes=1))} minutes')
            last_known_status = f'{get_color_circle(last_activity[0])} {last_activity[0]} for ' \
                                f'{last_activity[2].days * 24 * 60 + round(last_activity[2].seconds / 60)} minutes'

        title_insert = member.name if member.name == member.display_name else f'{member.name} ({member.display_name})'
        embed = discord.Embed(title=f'When Was {title_insert} Last Seen?',
                              description=description,
                              color=discord.Color.dark_red(), timestamp=current_timestamp)
        embed.set_footer(text='Information is not Garon-teed to be accurate. '
                              'Based on SalsaProvider™️ observations')

        embed.add_field(name='Last Known Status', value=last_known_status, inline=False)

        last_vc_activity = context.bot.fridge.get_last_voice_activity(member.id)
        if last_vc_activity is None:
            value = f'There is no VC history for {member.name}. This could be my fault, or, it may have been a very ' \
                    f'long time since their last VC'
            last_vc_status = 'No History'
        elif last_vc_activity[2] is None:
            # Currently online/idle/dnd
            value = f'{member.name} is currently in VC and has been active since ' \
                    f'{last_vc_activity[1].strftime("%I:%M %p (%H:%M)")}'
            duration = round((current_timestamp - last_vc_activity[1]) / datetime.timedelta(minutes=1))
            last_vc_status = f'{last_vc_activity[0]} for {duration} minutes'
        else:
            last_active_timestamp = last_vc_activity[1] + last_vc_activity[2]
            value = last_active_timestamp.strftime(
                f'{member.name} was last seen in VC on %A, %B %d, %Y (%m/%d/%y) at %I:%M %p (%H:%M). They have been '
                f'Disconnected for '
                f'{round((current_timestamp - last_active_timestamp) / datetime.timedelta(minutes=1))} minutes')
            last_vc_status = f'{last_vc_activity[0]} for ' \
                             f'{last_vc_activity[2].days * 24 * 60 + round(last_vc_activity[2].seconds / 60)} minutes'

        embed.add_field(name='Last VC Activity', value=value, inline=False)
        embed.add_field(name='Last VC Status', value=last_vc_status, inline=False)

        await context.send(embed=embed)

    return SalsaCommand(name='seen', description='Display information about when a member was last seen',
                        invoke_func=invoke)


def _juggle():
    async def invoke(context: CommandContext, member: discord.Member) -> None:
        """
        Args:
            member: The Discord member who should be juggled
        """
        # Permission check
        if not _has_boss_role(context.author):
            await context.send(embed=_error("You don't have permission to use this command!"))
            return

        if member == context.bot.user:
            await context.send(f'Doesn\'t work on me :sunglasses:')
            return

        if member.voice is not None and isinstance(member.voice.channel, discord.VoiceChannel):
            current_channel = member.voice.channel
            if current_channel.guild != context.bot.get_the_tunnel():
                await context.send(embed=_error(f'I can only juggle people who are '
                                                f'in {context.bot.get_the_tunnel().name}!'))
                return

            voice_channels = [channel for channel in context.bot.get_the_tunnel().channels if
                              isinstance(channel, discord.VoiceChannel)]

            # This next part will take a bit of time
            await context.defer()

            # Let the juggling commence
            count = 0
            target_count = random.randint(3, 5)
            while count < target_count or member.voice.channel == current_channel:
                while True:
                    new_channel = random.choice(voice_channels)
                    if new_channel != member.voice.channel:
                        break
                try:
                    await member.move_to(new_channel)
                except Exception:
                    pass

                count += 1
                await asyncio.sleep(0.4)

            # Finally, put the victim back where they started
            try:
                await member.move_to(current_channel)
            except Exception:
                pass
        else:
            await context.send(embed=_error(f'{member.name} is not connected to a voice channel!'))

    return SalsaCommand(name='juggle', description='Move someone around a bit', invoke_func=invoke)


def _move_all():
    async def invoke(context: CommandContext, channel: discord.VoiceChannel = None) -> None:
        """
        Args:
            channel: The voice channel to which all server members should be moved. Uses General if not specified
        """
        # Permission check
        if not _has_boss_role(context.author):
            await context.send(embed=_error("You don't have permission to use this command!"))
            return

        # Fetch the list of voice channels so that we can move users who are in these channels to the target channel
        other_channels = []
        for guild_channel in context.bot.get_the_tunnel().channels:
            if isinstance(guild_channel, discord.VoiceChannel):
                # No channel was given, attempt to find a channel named 'General'
                if channel is None and guild_channel.name.lower() == 'general':
                    channel = guild_channel
                elif channel != guild_channel:
                    other_channels.append(guild_channel)

        # There is a possibility that we could not find the default 'general' channel
        if channel is None:
            await context.send(embed=_error("I couldn't find a voice channel named `general`! "
                                            "Please try again and specify an existing voice channel"))
            return

        # It will take a little time to move the users
        await context.defer()

        # Move all the users
        for guild_channel in other_channels:
            for member in guild_channel.members:
                await member.move_to(channel)

    return SalsaCommand(name='moveall', description='Move everyone to the specified voice channel', invoke_func=invoke)


NICK_SET_PATTERN = re.compile(r"[nN][iI][cC][kK]\s+[sS][eE][tT]\s+(.+?)\s(.*)")


def _nick_set():
    async def invoke(context: CommandContext, member: discord.Member, nickname: str) -> None:
        """
        Args:
            member: The Discord server member whose nickname should be updated
            nickname: The new nickname
        """
        # Permission check
        if not _has_boss_role(context.author):
            await context.send(embed=_error("You don't have permission to use this command!"))
            return

        if member == context.bot.user:
            # Protect SalsaProvider from being nicknamed
            await context.send("Hahaha nice try 😎")
        else:
            await member.edit(nick=nickname)
            await context.send(f"I updated the nickname for {member.name} to {nickname}!")

    async def match(command_text: str) -> Optional[List[str]]:
        match = NICK_SET_PATTERN.fullmatch(command_text)
        if not match:
            return None

        return [match.group(1), match.group(2)]

    return SalsaCommand(name='set', description='Nickname a server member',
                        invoke_func=invoke, match_func=match)


def _nick_clear():
    async def invoke(context: CommandContext, member: discord.Member = None) -> None:
        """
        Args:
            member: The Discord server member whose nickname should be cleared
        """
        # Permission check
        if not _has_boss_role(context.author):
            await context.send(embed=_error("You don't have permission to use this command!"))
            return

        # If no member is specified, we shall use the member who is invoking the command
        if member is None:
            member = context.author

        if member == context.bot.user:
            # Protect SalsaProvider from being nicknamed
            await context.send("This doesn't apply to me 😎")
        else:
            await member.edit(nick=None)

    async def match(command_text: str) -> Optional[List[str]]:
        return await _default_match('nickclear', command_text)

    return SalsaCommand(name='clear', description='Clear the nickname for a server member',
                        display_name='nick clear', invoke_func=invoke, match_func=match)


def _flip_a_coin():
    async def invoke(context: CommandContext) -> None:
        await context.send(f'The result is: `{random.choice(["Heads", "Tails"])}`')

    return SalsaCommand(name='flipacoin', description='Perform a coin flip', invoke_func=invoke)


PICK_A_NUMBER_PATTERN = re.compile(r"pick\s*a\s*number\s+(-?\d+)\s*-\s*(-?\d+)")


def _pick_a_number():
    async def invoke(context: CommandContext, begin: int, end: int) -> None:
        """
        Args:
            begin: The smallest possible number
            end: The largest possible number
        """
        numbers = [begin, end]
        if numbers[0] > numbers[1]:
            numbers.reverse()

        await context.send(f'I picked the number {random.randint(*numbers)}')

    async def match(command_text: str) -> Optional[List[str]]:
        match = PICK_A_NUMBER_PATTERN.fullmatch(command_text)
        if not match:
            return None

        return [match.group(1), match.group(2)]

    return SalsaCommand(name='pickanumber', description='Pick a number from a range',
                        invoke_func=invoke, match_func=match)


CHOOSE_FROM_PATTERN = re.compile(r"(?i)choose\s*(\d*)\s*from\s*(.+)")


def _choose_from():
    async def invoke(context: CommandContext, options: str, count: int = 1) -> None:
        """
        Args:
            options: A comma separated list of options to choose from. Ex. 'option 1, option 2, option 3'
            count: How many of the options to pick
        """
        # Remove starting and ending brackets if present
        if options[0] == '[' and options[-1] == ']':
            options = options[1:-1]

        # Convert the list of options into an actual python list and remove padding from each option
        options_list = [option.strip() for option in options.split(',')]

        if count == 0:
            # Special message for choose 0
            await context.send('Hmm... choose 0 you say? I think my work here is already done')
        elif count > len(options_list):
            # Message for asking to choose too many options
            await context.send(f'How do you expect me to choose {count} given only {len(options_list)} '
                               f'option{"s" if len(options_list) > 1 else ""}?!?! Try again please')
        elif len(options_list) == 1:
            # Special message for only one option
            await context.send('You only gave me one option :( That\'s no fun')
        elif count == len(options_list):
            await context.send('You want ALL the options? You can have them ;)')
        else:
            # Make the choice(s)
            choices = random.sample(options_list, count)

            if len(choices) == 1:
                await context.send(f'I chose `{choices[0]}`')
            elif len(choices) == 2:
                await context.send(f'I chose `{choices[0]}` and `{choices[1]}`')
            else:
                await context.send(f'I chose {", ".join(f"`{choice}`" for choice in choices[:-1])}, '
                                   f'and `{choices[-1]}`')

    async def match(command_text: str) -> Optional[List[str]]:
        match = CHOOSE_FROM_PATTERN.fullmatch(command_text)
        if not match:
            return None

        # Extract the info we need from the command
        count_text, options_list_text = match.group(1, 2)

        return [options_list_text] + ([count_text] if count_text else [])

    return SalsaCommand(name='choosefrom', description='Choose one or more options from a list',
                        invoke_func=invoke, match_func=match)


def _tea_me():
    async def invoke(context: CommandContext) -> None:
        c = random.choice(["a Green", "a White", "a black", "an oolong", "a yellow", 
                           "a raw puerh", "a ripe puerh"])
        await context.send(f'I think you should drink {c}')

    return SalsaCommand(name='teame', description="Chooses a category of tea for you :)",
                        invoke_func=invoke)


MAGIC_8_BALL_RESPONSES = ["It is certain", "It is decidedly so", "Without a doubt", "Yes - definitely",
                          "You may rely on it", "As I see it, yes", "Most likely", "Outlook good", "Yes",
                          "Signs point to yes", "Reply hazy, try again", "Ask again later", "Better not tell you now",
                          "Cannot predict now", "Concentrate and ask again", "Don't count on it", "My reply is no",
                          "My sources say no", "Outlook not so good", "Very doubtful"]
MAGIC_8_BALL_RESPONSE_COUNT = len(MAGIC_8_BALL_RESPONSES)


def _magic_8_ball():
    async def invoke(context: CommandContext, question: str = None) -> None:
        """
        Args:
            question: The question to ask the Magic 8 Ball
        """
        # Use the current random generator to pick a response
        response_index = random.randint(0, MAGIC_8_BALL_RESPONSE_COUNT - 1)

        # Allow the question to influence our result
        if question is not None:
            response_index += hash(question)
            response_index %= MAGIC_8_BALL_RESPONSE_COUNT

        await context.send(f'The Magic 8 Ball says: `{MAGIC_8_BALL_RESPONSES[response_index]}`')

    return SalsaCommand(name='m8b', description='Ask the Magic 8 Ball a question', invoke_func=invoke)


def _thanks():
    async def invoke(context: CommandContext) -> None:
        await context.send(ss.get_thank_you_reply(context.author))

        if context.is_message():
            await context.context.add_reaction("👍")

    async def match(command_text: str) -> Optional[List[str]]:
        command_text_no_whitespace = command_text.replace(" ", "")
        if any(text in command_text_no_whitespace for text in ("thankyou", "thanks", "thank", "ty", "thx")):
            return []

        return None

    return SalsaCommand(name='thanksalsa', description='You will make me happy :)', invoke_func=invoke,
                        match_func=match)


def _help():
    async def invoke(context: CommandContext) -> None:
        await context.send("```SalsaProvider Commands:\n"
                           "!salsa help - Display help information\n"
                           "!salsa redo - Execute your previous command again\n"
                           "!salsa flip a coin - Perform a coin flip\n"
                           "!salsa pick a number <first#> - <second#> - Pick a number from a range\n"
                           "!salsa m8b [question] - Magic 8 Ball, the question is optional\n"
                           "!salsa choose [count] from <comma separated list of options> - "
                           "Choose one or more options from a list\n"
                           "Requires 'Big Boss Role':\n"
                           "!salsa moveall <voice_channel> - Move everyone to the specified voice channel \n"
                           "!salsa nick set <Username> <Nickname> - Nickname a user\n"
                           "!salsa nick clear [Username] - Clear the nickname for a user```\n")

    async def match(command_text: str) -> Optional[List[str]]:
        if not command_text:
            return []

        return await _default_match('help', command_text)

    return SalsaCommand(name='help', description='Display text command help information', invoke_func=invoke,
                        match_func=match)


def _sync():
    async def invoke(context: CommandContext) -> None:
        if await context.bot.is_owner(context.author):
            print('Syncing commands!')
            await context.bot.tree.sync(guild=None)  # context.bot.get_the_tunnel())
            await context.bot.tree.sync(guild=context.bot.get_the_tunnel())
            await context.send('Sync successful!')
        else:
            await context.send(embed=_error('Only the bot owner is allowed to run this command!'))

    return SalsaCommand(name='sync', description='Sync the bot commands to Discord', invoke_func=invoke)


# Constants containing the command objects in the correct processing order
JUGGLE_COMMAND = _juggle()
SLASH_COMMANDS = (RedoCommand(), _choose_from(), _tea_me(), _flip_a_coin(), _magic_8_ball(), 
                  _pick_a_number(), _move_all(), JUGGLE_COMMAND, _seen(), _thanks(), _help())
NICK_COMMANDS = (_nick_set(), _nick_clear())
TEXT_COMMANDS = (_sync(),) + SLASH_COMMANDS + NICK_COMMANDS


def load_app_commands(bot: SalsaClient):
    def create_cb(_command):
        async def new_cb(interaction: discord.Interaction, *args, **kwargs) -> None:
            context = CommandContext(bot, interaction)
            await context.prepare(_command.display_name, *args, **kwargs)
            await _command.invoke(context, *args, **kwargs)
            await context.finish()

        # Copy over the function signature so that parameters are registered correctly
        cb_signature = [inspect.Parameter('interaction', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                          annotation=discord.Interaction)] + _command.get_parameters()
        new_cb.__signature__ = inspect.Signature(cb_signature)

        # Copy over the doc string so that parameter descriptions are registered correctly
        new_cb.__doc__ = _command.get_docs()

        return new_cb

    for command in SLASH_COMMANDS:
        bot.tree.add_command(app_commands.Command(name=command.name, description=command.description,
                                                  callback=create_cb(command)))

    # These commands are special and need to be put in a group together
    nick_group = app_commands.Group(name='nick', description='Manage nicknames for server members')
    for command in NICK_COMMANDS:
        nick_group.add_command(app_commands.Command(name=command.name, description=command.description,
                                                    callback=create_cb(command)))
    bot.tree.add_command(nick_group)

    # Also add nick clear and juggle as context menu commands for bonus points
    nick_clear = NICK_COMMANDS[1]
    bot.tree.add_command(app_commands.ContextMenu(name='Clear Nickname', callback=create_cb(nick_clear)))
    bot.tree.add_command(app_commands.ContextMenu(name='Juggle', callback=create_cb(JUGGLE_COMMAND)))


def get_member_by_username(client, username):
    # First, try to look up the user as a username
    user = client.get_the_tunnel().get_member_named(username)
    if user is None:
        try:
            # It's possible that the given value is a user ID instead. So try that too
            user = client.get_the_tunnel().get_member(int(re.sub('[^0-9]', '', username)))
        except ValueError:
            user = None

    return user


def _get_voice_channel_helper(bot: 'SalsaClient', name_or_id: str) -> Optional[discord.VoiceChannel]:
    # Grab the last part of the channel link, where the channel ID is
    count = 0
    all_numbers = True
    for count, character in enumerate(reversed(name_or_id)):
        if not ord('0') <= ord(character) <= ord('9'):
            all_numbers = False
            break

    id_text = name_or_id if all_numbers else name_or_id[-count:]
    try:
        # We will first try to parse this text as a channel ID or channel link
        channel_id = int(id_text)
        for channel in bot.get_the_tunnel().channels:
            if isinstance(channel, discord.VoiceChannel) and channel.id == channel_id:
                return channel
    except ValueError:
        pass

    # If we make it here, we could not parse the text as a channel ID or link. Try searching by name
    for channel in bot.get_the_tunnel().channels:
        if isinstance(channel, discord.VoiceChannel) and channel.name == name_or_id:
            return channel

    # Could not find the channel
    return None


class ConversionError(ValueError):
    pass


# TODO Add an insult instead of sorry when conversion fails
def convert_args(bot: SalsaClient, args: List[str], types: List[Type]) -> List[Any]:
    converted_args = []
    for index, (arg, arg_type) in enumerate(zip(args, types), 1):
        if arg_type == str:
            # Hahaha, that was easy!
            converted_args.append(arg)
        elif arg_type == int:
            try:
                converted_args.append(int(arg))
            except ValueError:
                raise ConversionError(f'I was expecting a number, but you gave me `{arg}` at position {index}. '
                                      f'Sorry, please try again :smiling_face_with_tear:')
        elif arg_type == discord.Member:
            member = get_member_by_username(bot, arg)
            if member is None:
                raise ConversionError(f"I can't find a Discord member with nickname, username, or ID matching "
                                      f'`{arg}`, as you gave me at position {index}. '
                                      f'Sorry, please try again :smiling_face_with_tear:')

            converted_args.append(member)
        elif arg_type == discord.VoiceChannel:
            channel = _get_voice_channel_helper(bot, arg)
            if channel is None:
                raise ConversionError(f"I can't find a voice channel with ID, link, or name matching "
                                      f'`{arg}`, as you gave me at position {index}. '
                                      f'Sorry, please try again :smiling_face_with_tear:')
            converted_args.append(channel)
        else:
            raise ConversionError(f'The bozo who developed this bot did not implement this command correctly! '
                                  f'Please yell at them! Info: index=`{index}`, arg=`{arg}`, arg_type=`{arg_type}`')

    return converted_args


async def handle(bot: SalsaClient, message: discord.Message):
    # See if the message starts with !salsa
    match = BOT_COMMAND_PATTERN.fullmatch(message.content)
    if not match:
        return False

    # Attempt to match the command text and then invoke the correct command
    command_text = match.group(1)
    for command in TEXT_COMMANDS:
        args = await command.match(command_text)
        if args is not None:
            types = [parameter.annotation for parameter in command.get_parameters()]
            context = CommandContext(bot, message)

            # Attempt to convert the str args of the command to the appropriate types and then invoke the command.
            # If there is a conversion error we will print the message to the user and then gracefully exit
            try:
                converted_args = convert_args(bot, args, types)
                await context.prepare(command.name, *converted_args)
                await command.invoke(context, *converted_args)
            except ConversionError as error:
                await context.send(embed=_error(str(error)))
            except TypeError:
                await context.send(embed=_error("You didn't provide enough information! "
                                                "This command requires more parameters"))
            finally:
                await context.finish()

            return True

    # Unknown command
    await message.channel.send(f'Unknown command: `{command_text}`. Try `!salsa` for help!')
    return True
