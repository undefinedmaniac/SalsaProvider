import asyncio


class Timer:
    def __init__(self):
        self._task = None
        self._delay = None
        self._restart = False

    async def wait(self, delay):
        if self.is_running():
            return False

        self._delay = delay
        while True:
            # Create a new task
            self._task = asyncio.create_task(self._timer(self._delay))

            # Wait for it to finish
            try:
                await self._task
                timer_expired = True
            except asyncio.CancelledError:
                timer_expired = False

            # Restart the task, if needed
            if self._restart:
                self._restart = False
            else:
                break

        # Delete the task
        self._task = None
        return timer_expired

    # Check if the timer is already running
    def is_running(self):
        return self._task is not None

    # Restart the timer
    def restart(self, new_delay):
        if self.is_running():
            self._delay = new_delay
            self._restart = True
            self._task.cancel()

    # Cancel the timer
    def cancel(self):
        if self.is_running():
            self._restart = False
            self._task.cancel()

    async def _timer(self, delay):
        await asyncio.sleep(delay)


ASCII_TO_REGIONAL_INDICATOR_OFFSET = 0x1F1E6 - ord('A')


# Converts as many letters as possible in the given message into regional indicator symbols
def convert_to_regional_indicators(message):
    def cvt_ascii_to_regional_indicators(character):
        character_value = ord(character)
        if ord('A') <= character_value <= ord('Z'):
            return chr(character_value + ASCII_TO_REGIONAL_INDICATOR_OFFSET)
        elif character == 'i':
            return "ℹ"

        return character

    return ''.join(cvt_ascii_to_regional_indicators(character) for character in message)
