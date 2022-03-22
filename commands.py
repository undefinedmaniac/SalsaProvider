import re
import random

import asyncio
import discord
import salsa_settings as ss
from functools import partial

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
    commands = [_help, _flip_a_coin, _pick_a_number, _magic_8_ball, _unlibrary,
                partial(_move_everyone_to_channel, "general", "General"),
                partial(_move_everyone_to_channel, "second", "second"),
                partial(_move_everyone_to_channel, "afk", "ahhpppfffkk"),
                partial(_move_everyone_to_channel, "library", "Library"), _thanks]

    matching_command = False
    for command in commands:
        if await command(client, message, command_args, lowercase_args):
            matching_command = True
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
                               "!salsa flip a coin - Perform a coin flip\n"
                               "!salsa pick a number <first#> - <second#> - Pick a number from a range\n"
                               "!salsa m8b [question] - Magic 8 Ball, the question is optional\n"
                               "Requires 'Big Boss Role':\n"
                               "!salsa general - Move all users to the General channel\n"
                               "!salsa second - Move all users to the second channel\n"
                               "!salsa afk - Move all users to the ahhpppfffkk channel\n"
                               "!salsa library - Move all users to the Library channel\n"
                               "!salsa unlibrary - Remove all users from the Library```\n")

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
    if args_lower.replace(" ", "") not in ("thankyou", "thanks"):
        return False

    await message.channel.send(ss.get_thank_you_reply(message.author))
    await message.add_reaction("👍")
    return True
