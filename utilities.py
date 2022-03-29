import heapq
import fridge
import asyncio
import discord
import salsa_settings as ss
from datetime import datetime


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


def get_next_birthday(user_id):
    month, day = ss.BIRTHDAYS.get(user_id)
    current_datetime = datetime.now()

    birthday_this_year = current_datetime.replace(day=day, month=month, hour=0, minute=0, second=0, microsecond=0)
    # If this year's birthday has not passed yet
    if birthday_this_year > current_datetime:
        return birthday_this_year

    # Return next year's birthday instead
    return birthday_this_year.replace(year=current_datetime.year + 1)


def convert_user_status(status: discord.Status) -> fridge.UserStatus:
    if status == discord.Status.online:
        return fridge.UserStatus.Online
    elif status == discord.Status.idle:
        return fridge.UserStatus.Idle
    elif status == discord.Status.do_not_disturb:
        return fridge.UserStatus.DoNotDisturb

    return fridge.UserStatus.Offline


class LongTermTask:
    def __init__(self, scheduler, coroutine, when):
        self._scheduler = scheduler
        self._coroutine = coroutine
        self._when = when
        self._task = None
        self._cancelled = False

    def __lt__(self, other):
        return self._when < other.scheduled_time()

    def __le__(self, other):
        return self._when <= other.scheduled_time()

    def __gt__(self, other):
        return self._when > other.scheduled_time()

    def __ge__(self, other):
        return self._when >= other.scheduled_time()

    def _run(self):
        # Run the task in the background
        self._task = asyncio.create_task(self._coroutine)
        self._coroutine = None

    # Check if the task is currently running
    def _check_running(self):
        # Gather the results of the task if it's done
        if self._task.done():
            result = self._task.result()
            self._task = None

            if result is None or self._cancelled:
                # The task is finished, do not reschedule
                self._coroutine = None
                self._when = None
            else:
                # Reschedule this task to run again
                self._coroutine, self._when = result

            return True

        return False

    async def _wait_until_stopped_running(self):
        if self._task is None:
            return

        await self._task

    def _cleanup(self):
        if self._coroutine is None:
            return

        self._coroutine.close()

    # Get the next scheduled time for this task, or None if the task won't run again
    def scheduled_time(self):
        return self._when

    # Check if the task is currently running
    def is_running(self):
        return self._task is not None

    # Check if the task is complete, meaning that it won't run again
    def is_complete(self):
        return self.scheduled_time() is None and not self.is_running()

    # Check if the task was cancelled, meaning that it cannot be scheduled again
    def cancelled(self):
        return self._cancelled

    # Cancel the task, preventing it from being scheduled and run again
    def cancel(self):
        self._cancelled = True

        # If this task is in the heap, force it to the top, so it gets discarded
        if not self.is_running():
            self._when = datetime.min
            self._scheduler.force_update()

    # Reschedule the task to run at a different time. Does not work on cancelled tasks.
    # Returns True if the task was successfully rescheduled, False if the task could not be rescheduled (because it is
    # already running or completed)
    def reschedule(self, when):
        if self.cancelled():
            raise RuntimeError('Cannot reschedule a cancelled task!')

        # Cannot reschedule if we are already running or complete
        if self.is_running() or self.is_complete():
            return False

        # Update the scheduled time and force update
        self._when = when
        self._scheduler.force_update()
        return True

    # Reschedule the task so that it runs As Soon As Possible
    def reschedule_asap(self):
        return self.reschedule(datetime.min)


class LongTermScheduler:
    def __init__(self):
        self._heap = []
        self._running_tasks = []

    def force_update(self):
        heapq.heapify(self._heap)

    async def run(self):
        try:
            while True:
                # Dispatch the soonest task if it is ready to be executed
                while len(self._heap) > 0 and self._heap[0].scheduled_time() <= datetime.now():
                    # Remove the task from the heap
                    heap_task = heapq.heappop(self._heap)

                    # Execute the task
                    if not heap_task.cancelled():
                        heap_task._run()
                        self._running_tasks.append(heap_task)

                # Reschedule or remove completed tasks
                for i, heap_task in enumerate(self._running_tasks):
                    if heap_task._check_running():
                        if not heap_task.is_complete():
                            heapq.heappush(self._heap, heap_task)

                        # The task is done running
                        del self._running_tasks[i]

                # Sleep so that other tasks may run
                await asyncio.sleep(0.1)
        finally:
            # Ensure that all tasks are awaited before exiting
            await asyncio.gather(*(task._wait_until_stopped_running() for task in self._running_tasks),
                                 return_exceptions=True)

            # Cleanup unused coroutines
            tuple(task._cleanup() for task in self._heap)

    def schedule(self, coroutine, when):
        task = LongTermTask(self, coroutine, when)
        heapq.heappush(self._heap, task)
        return task
