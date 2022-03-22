import sys
import discord
import utilities
import salsa_settings as ss


# Insults people who are taking the time to write a thought provoking message
class TypingInsulter:
    def __init__(self):
        self._candidates = {}

    async def user_started_typing(self, user, channel):
        if not ss.check_enabled(ss.TYPING_INSULTS_ENABLED, ss.TYPING_INSULTS_WHITELIST, user.id):
            return

        # Create a new timer
        timer = utilities.Timer()
        self._candidates[user] = [channel, timer, []]

        messages = [f"Hmm... You've been typing that message for quite a while {user.mention}. Everything okay?",

                    f"{user.mention} Still typing? Remember to use all your fingers. It goes a lot faster that way "
                    f":grin:",

                    f"I'm starting to get concerned... {user.mention} has been typing for an unhealthy amount of "
                    f"time...",

                    f"ARE YOU GONNA SEND THE MESSAGE SOMETIME TODAY?? I'll wait patiently :smiling_face_with_tear:"]

        for timeout, message in (tuple(zip(ss.TYPING_INSULTS_TIMEOUTS, messages)) + ((sys.maxsize, ""),)):
            timer_result = await timer.wait(timeout)
            if timer_result:
                self._candidates[user][2].append(await channel.send(message))
            else:
                break

        # Delete our messages and cleanup
        if isinstance(channel, discord.TextChannel):
            await channel.delete_messages(self._candidates[user][2])
        else:
            for message in self._candidates[user][2]:
                await message.delete()

        del self._candidates[user]

    def user_stopped_typing(self, user):
        if not ss.check_enabled(ss.TYPING_INSULTS_ENABLED, ss.TYPING_INSULTS_WHITELIST, user.id):
            return

        candidate = self._candidates.get(user)
        if candidate is not None:
            candidate[1].cancel()
