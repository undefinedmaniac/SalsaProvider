import heapq
from typing import List, Optional, Tuple

import fridge
import asyncio
import discord
import requests
import salsa_settings as ss
from datetime import datetime
from bs4 import BeautifulSoup
from bs4 import Tag

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


def next_annual_event(datetime_this_year):
    if datetime.now() <= datetime_this_year:
        return datetime_this_year

    return datetime_this_year.replace(year=datetime_this_year.year + 1)


def get_next_birthday(user_id):
    month, day = ss.BIRTHDAYS.get(user_id)
    current_datetime = datetime.now()

    birthday_this_year = current_datetime.replace(day=day, month=month, hour=0, minute=0, second=0, microsecond=0)
    return next_annual_event(birthday_this_year)


# Check the wizard101 news feed for anything good going on today
async def check_w101_news():
    loop = asyncio.get_event_loop()
    r = await loop.run_in_executor(None, requests.get, ss.W101_NEWS_WEBPAGE)
    if (r.status_code != 200):
        return

    soup_c = BeautifulSoup(r.content, features="html.parser")
    t = soup_c.find("table", {"id": "renderRegionDiv", "class": "renderRegionDiv", "cellspacing": "0", 
                              "cellpadding": "0", "border": "0", "width": "100%"})

    if not isinstance(t, Tag):
        return

    r = t.find_all("tr", recursive=False)

    # Generate today's month/day string
    now = datetime.now()
    today_str = "{d:%B} {d.day}".format(d=now)

    for row in r:
        td = row.td
        if td is None:
            continue

        div = td.div
        if div is None:
            continue

        tables = div.find_all("table")
        if len(tables) != 2:
            continue

        top, bottom = tables
        
        center = top.center
        if center is None:
            continue

        if center.contents and center.contents[0].startswith(today_str):
            # Found today's news post
            p = bottom.p
            if p is None:
                continue

            contents = p.find_all(string=True)
            if len(contents) < 2:
                continue

            header, content = [s.strip() for s in contents][:2]

            key = " ".join([header, content]).lower()
            has = lambda *s: all(x in key for x in s)
            matches = any(( \
                has("free", "wizard city"), \
                has("free", "krokotopia"), \
                has("new", "member", "save", "50%"), \
                has("elixir", "sale"), \
                has("mastery", "amulet", "sale"), \
                has("five", "b.o.x.e.s"), \
                has("free", "crowns"), \
                has("mystery", "discount"), \
                has("free", "pack"), \
                has("free", "membership"), \
            ))
                
            if matches:
                yield header, content


def convert_user_status(status: discord.Status) -> fridge.UserStatus:
    if status == discord.Status.online:
        return fridge.UserStatus.Online
    elif status == discord.Status.idle:
        return fridge.UserStatus.Idle
    elif status == discord.Status.do_not_disturb:
        return fridge.UserStatus.DoNotDisturb

    return fridge.UserStatus.Offline


split_respect_quotes_cache: Optional[Tuple[str, List[str]]] = None


def split_respect_quotes(text: str) -> List[str]:
    # Caching because this function is often called repeatedly with the same value
    global split_respect_quotes_cache
    if split_respect_quotes_cache is not None and split_respect_quotes_cache[0] == text:
        return split_respect_quotes_cache[1]

    quote_indexes = []
    skipped_sections = []

    # Start by finding the locations of all escaped characters, whitespace, and potential grouping quotes
    start = 0
    backslash = False
    whitespace = False
    for stop, character in enumerate(text):
        if backslash:
            if character in ('\\', '"', '\''):
                skipped_sections.append((stop-1, stop, False))
            backslash = False
        elif character == '\\':
            backslash = True
        elif character in ('"', '\''):
            quote_indexes.append(stop)

        if whitespace ^ (character in (' ', '\t')):
            if whitespace:
                skipped_sections.append((start, stop, True))
            else:
                start = stop
            whitespace = not whitespace

    if whitespace:
        skipped_sections.append((start, len(text), True))

    # Figure out which grouping quotes are 'real' and which ones should be interpreted as literal quotes
    grouping_quotes = []
    quote = 0
    while quote < len(quote_indexes):
        found = False
        for search in range(quote+1, len(quote_indexes)):
            if text[quote_indexes[quote]] == text[quote_indexes[search]]:
                grouping_quotes.append((quote_indexes[quote], quote_indexes[search]))
                quote = search + 1
                found = True
                break

        if not found:
            quote += 1

    # Insert the grouping quotes into the skipped_sections, as we do not want grouping quotes included in output
    index = 0
    for quote in (quote for quote_pair in grouping_quotes for quote in quote_pair):
        while index < len(skipped_sections) and skipped_sections[index][0] < quote:
            index += 1

        skipped_sections.insert(index, (quote, quote+1, False))

    # Checks if we are inside grouping quotes and the skip should not be applied if it is whitespace
    def inside_grouping_quotes(_skip_start):
        while grouping_quotes:
            quote_start, quote_stop = grouping_quotes[0]
            if quote_stop < _skip_start:
                del grouping_quotes[0]
            else:
                return quote_start < _skip_start < quote_stop

    result = []
    parts = []
    start = 0

    # Chop up the original string using slicing and piece together the parts we need to form the result strings
    for skip_start, skip_stop, whitespace in skipped_sections:
        if whitespace and inside_grouping_quotes(skip_start):
            continue

        parts.append(text[start:skip_start])

        if whitespace:
            result.append(''.join(parts))
            parts = []

        start = skip_stop

    parts.append(text[start:])
    result.append(''.join(parts))

    # Filter out empty strings from the results and return finally
    split_respect_quotes_cache = (text, [split_text for split_text in result if split_text])
    return split_respect_quotes_cache[1]


def cvt_escaped_str_to_literal(text: str) -> str:
    temp = []

    start = 0
    backslash = False
    for stop, character in enumerate(text):
        if backslash:
            if character in ('\\', '"', '\''):
                temp.append(text[start:stop-1])
                start = stop

            backslash = False
        elif character == '\\':
            backslash = True

    return ''.join(temp + [text[start:]])


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
