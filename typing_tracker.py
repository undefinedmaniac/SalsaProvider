import asyncio
import utilities


class TypingTracker:
    def __init__(self, client, timeout_time=12):
        self._typing_users = {}
        self._client = client
        self._timeout_time = timeout_time

    async def on_typing(self, user, channel):
        # Retrieve the timer for this user
        if self.is_typing(user):
            timer = self._typing_users[user]
        else:
            # Create a timer for this user if this is the beginning of their typing
            timer = utilities.Timer()
            self._typing_users[user] = timer

        # Either restart an existing timer, or start the timer for the first time
        if timer.is_running():
            timer.restart(self._timeout_time)
        else:
            # Just started typing, run the started typing handler and start the timer
            task = asyncio.create_task(self._client.user_started_typing(user, channel))

            await timer.wait(self._timeout_time)
            del self._typing_users[user]

            # No longer typing
            await asyncio.gather(task, self._client.user_stopped_typing(user, channel))

    def on_message(self, user):
        timer = self._typing_users.get(user)
        if timer is not None:
            timer.cancel()

    def is_typing(self, user):
        return user in self._typing_users

    async def wait_until_stopped_typing(self, user):
        while self.is_typing(user):
            await asyncio.sleep(0.1)
