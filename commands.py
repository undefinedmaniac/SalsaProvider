import re
import random

import asyncio
import discord
import salsa_settings as ss
from functools import partial

# Stores the last command issued by each user
last_command = {}


BOT_COMMAND_PATTERN = re.compile(r"^!(?i)salsa(.*)$")


async def handle(client, message):
    # See if the message starts with !salsa
    match = BOT_COMMAND_PATTERN.fullmatch(message.content)
    if not match:
        return False

    # Fetch the arguments to the command
    command_args = match.group(1).strip()
    lowercase_args = command_args.lower()

    # Try to match the command to one of our command functions
    commands = [_help, _redo, _have_salsa_instead, _flip_a_coin, _pick_a_number, _choose_from, _magic_8_ball,
                _unlibrary, _nick, _clear_nick,
                partial(_move_everyone_to_channel, "general", "General"),
                partial(_move_everyone_to_channel, "second", "second"),
                partial(_move_everyone_to_channel, "afk", "ahhpppfffkk"),
                partial(_move_everyone_to_channel, "library", "Library"), _thanks, _insults]

    matching_command = False
    for command in commands:
        if await command(client, message, command_args, lowercase_args):
            matching_command = True

            # Remember the last successful command from each user, but only if it's not the redo command
            if command != _redo:
                last_command[message.author.id] = message

            break

    # No dice, tell the user they did it wrong
    if not matching_command:
        # Unknown command
        await message.channel.send(f'Unknown command: `{command_args}`. Try `!salsa` for help!')

    return True


# Verifies that a user is a Member and that they have the 'big boss role'
def _has_boss_role(member):
    if not isinstance(member, discord.Member):
        return False

    for role in member.roles:
        if role.id == ss.BIG_BOSS_ROLE_ID:
            return True

    return False


async def _help(client, message, args, args_lower):
    if args_lower and args_lower != "help":
        return False

    # Print the help page
    await message.channel.send("```SalsaProvider Commands:\n"
                               "!salsa help - Display help information\n"
                               "!salsa redo - Execute your previous command again\n"
                               "!salsa flip a coin - Perform a coin flip\n"
                               "!salsa pick a number <first#> - <second#> - Pick a number from a range\n"
                               "!salsa m8b [question] - Magic 8 Ball, the question is optional\n"
                               "!salsa choose [count] from <comma separated list of options> - "
                               "Choose one or more options from a list\n"
                               "Requires 'Big Boss Role':\n"
                               "!salsa general - Move all users to the General channel\n"
                               "!salsa second - Move all users to the second channel\n"
                               "!salsa afk - Move all users to the ahhpppfffkk channel\n"
                               "!salsa library - Move all users to the Library channel\n"
                               "!salsa unlibrary - Remove all users from the Library\n"
                               "!salsa nick <Username> <Nickname> - Nickname a user\n"
                               "!salsa clear nick [Username] - Clear the nickname for a user```\n")

    return True


async def _redo(client, message, args, args_lower):
    if args_lower != 'redo':
        return False

    command_message = last_command.get(message.author.id)
    if command_message is None:
        await message.channel.send('If you\'ve used a command previously, I can\'t remember what it was. Sorry :(')
    else:
        await handle(client, command_message)

    return True


async def _have_salsa_instead(client, message, args, args_lower):
    # Random chance to sabotage other commands and deliver salsa instead
    if random.random() >= ss.HAVE_SALSA_INSTEAD_PROBABILITY:
        return False

    await message.channel.send("Instead of that, have some salsa! :)")
    if random.random() < ss.MESS_UP_AND_GIVE_SHRIMP_PROBABILITY:
        # Mess up and give them shrimp first
        await message.channel.send(random.choice(ss.SHRIMP_IMAGES), delete_after=8)
        await asyncio.sleep(5)
        await message.channel.send("OOPS! Wrong one!! :sweat_smile:", delete_after=4)
        await asyncio.sleep(5)

    await message.channel.send(random.choice(ss.SALSA_IMAGES))

    return True


async def _flip_a_coin(client, message, args, args_lower):
    if args_lower.replace(" ", "") != "flipacoin":
        return False

    # Flip a coin
    await message.channel.send(f'The result is: `{random.choice(["Heads", "Tails"])}`')
    return True


async def _unlibrary(client, message, args, args_lower):
    if args_lower != "unlibrary":
        return False

    if _has_boss_role(message.author):
        general_channel = client.get_channel(ss.VOICE_CHANNEL_IDS["General"])
        library_channel = client.get_channel(ss.VOICE_CHANNEL_IDS["Library"])

        for member in library_channel.members:
            await member.move_to(general_channel)
    else:
        await message.channel.send("You can't use this command here!")

    return True


NICKNAME_PATTERN = re.compile(r"[nN][iI][cC][kK]\s+(.+?)\s(.*)")


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


async def _nick(client, message, args, args_lower):
    match = NICKNAME_PATTERN.fullmatch(args)
    if not match:
        return False

    if not _has_boss_role(message.author):
        await message.channel.send("You can't use this command here!")
        return True

    user = get_member_by_username(client, match.group(1))

    if user is None:
        await message.channel.send(f"I don't know who `{match.group(1)}` is. Please try again")
    elif user == client.user:
        # Protect SalsaProvider from being nicknamed
        await message.channel.send("Hahaha nice try 😎")
    else:
        await user.edit(nick=match.group(2))

    return True


async def _clear_nick(client, message, args, args_lower):
    args_parts = args.split()
    if len(args_parts) < 2 or args_parts[0].lower() != 'clear' or args_parts[1].lower() != 'nick':
        return False

    if not _has_boss_role(message.author):
        await message.channel.send("You can't use this command here!")
        return True

    if len(args_parts) == 2:
        user = message.author
    else:
        user = get_member_by_username(client, args_parts[2])

    if user is None:
        await message.channel.send(f"I don't know who `{args_parts[2]}` is. Please try again")
    elif user == client.user:
        # Protect SalsaProvider from being nicknamed
        await message.channel.send("This doesn't apply to me 😎")
    else:
        await user.edit(nick=None)

    return True


async def _move_everyone_to_channel(command_name, target_channel_name, client, message, args, args_lower):
    if args_lower != command_name:
        return False

    if _has_boss_role(message.author):
        target_channel = client.get_channel(ss.VOICE_CHANNEL_IDS[target_channel_name])
        other_channels = [client.get_channel(ss.VOICE_CHANNEL_IDS[name]) for name in
                          ss.VOICE_CHANNEL_IDS if name != target_channel_name]

        move_operations = []
        for channel in other_channels:
            for member in channel.members:
                move_operations.append(member.move_to(target_channel))

        await asyncio.gather(*move_operations)
    else:
        await message.channel.send("You can't use this command here!")

    return True


PICK_A_NUMBER_PATTERN = re.compile(r"pick\s*a\s*number\s+(-?\d+)\s*-\s*(-?\d+)")


async def _pick_a_number(client, message, args, args_lower):
    match = PICK_A_NUMBER_PATTERN.fullmatch(args_lower)
    if not match:
        return False

    try:
        numbers = [int(match.group(1)), int(match.group(2))]
        if numbers[0] > numbers[1]:
            numbers.reverse()

        await message.channel.send(f'I picked the number {random.randint(*numbers)}')
    except ValueError:
        await message.channel.send('Your numbers are garbage!! (Try again, with formatting like this: `1-10`)')

    return True


CHOOSE_FROM_PATTERN = re.compile(r"(?i)choose\s*(\d*)\s*from\s*(.+)")


async def _choose_from(client, message, args, args_lower):
    match = CHOOSE_FROM_PATTERN.fullmatch(args)
    if not match:
        return False

    # Extract the info we need from the command
    count_text, options_list_text = match.group(1, 2)

    try:
        # If a count was not provided, default to 1
        count = 1 if count_text == "" else int(count_text)

        # Remove starting and ending brackets if present
        if options_list_text[0] == '[' and options_list_text[-1] == ']':
            options_list_text = options_list_text[1:-1]

        # Convert the list of options into an actual python list and remove padding from each option
        options_list = [option.strip() for option in options_list_text.split(',')]

        if count == 0:
            # Special message for choose 0
            await message.channel.send('Hmm... choose 0 you say? I think my work here is already done')
        elif count > len(options_list):
            # Message for asking to choose too many options
            await message.channel.send(f'How do you expect me to choose {count} given only {len(options_list)} '
                                       f'option{"s" if len(options_list) > 1 else ""}?!?! Try again please')
        elif len(options_list) == 1:
            # Special message for only one option
            await message.channel.send('You only gave me one option :( That\'s no fun')
        elif count == len(options_list):
            await message.channel.send('You want ALL the options? You can have them ;)')
        else:
            # Make the choice(s)
            choices = random.sample(options_list, count)

            if len(choices) == 1:
                await message.channel.send(f'I chose `{choices[0]}`')
            elif len(choices) == 2:
                await message.channel.send(f'I chose `{choices[0]}` and `{choices[1]}`')
            else:
                await message.channel.send(f'I chose {", ".join(f"`{choice}`" for choice in choices[:-1])}, '
                                           f'and `{choices[-1]}`')

    except ValueError:
        await message.channel.send('Your numbers are garbage!! '
                                   '(Not sure how you broke this, but you probably know what\'s wrong already)')

    return True


MAGIC_8_BALL_RESPONSES = ["It is certain", "It is decidedly so", "Without a doubt", "Yes - definitely",
                          "You may rely on it", "As I see it, yes", "Most likely", "Outlook good", "Yes",
                          "Signs point to yes", "Reply hazy, try again", "Ask again later", "Better not tell you now",
                          "Cannot predict now", "Concentrate and ask again", "Don't count on it", "My reply is no",
                          "My sources say no", "Outlook not so good", "Very doubtful"]
MAGIC_8_BALL_RESPONSE_COUNT = len(MAGIC_8_BALL_RESPONSES)


async def _magic_8_ball(client, message, args, args_lower):
    if not args_lower.startswith("m8b"):
        return False

    # Use the current random generator to pick a response
    response_index = random.randint(0, MAGIC_8_BALL_RESPONSE_COUNT - 1)

    # Allow the question to influence our result
    question = args[3:].strip()
    if question:
        response_index += hash(question)
        response_index %= MAGIC_8_BALL_RESPONSE_COUNT

    await message.channel.send(f'The Magic 8 Ball says: `{MAGIC_8_BALL_RESPONSES[response_index]}`')
    return True


async def _thanks(client, message, args, args_lower):
    if args_lower.replace(" ", "") not in ("thankyou", "thanks", "thank", "ty", "thx"):
        return False

    await message.channel.send(ss.get_thank_you_reply(message.author))
    await message.add_reaction("👍")
    return True


async def _insults(client, message, args, args_lower):
    return False
    # if args_lower != "test":
    #     return False
    #
    # await message.channel.send("This is a test!")
    # await message.channel.send(ss.SALSA_IMAGES[0])
    #
    # return True
