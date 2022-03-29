import os.path
import sqlite3
from enum import IntEnum
from datetime import datetime
from datetime import timedelta


class SalsaStatus(IntEnum):
    Up = 0
    Down = 1
    Disconnected = 2
    Connected = 3


def _calc_status_value(number: int, is_mobile: bool):
    return (number << 1) | int(is_mobile)


class UserStatus(IntEnum):
    # Normal status values
    Idle = _calc_status_value(0, False)
    Online = _calc_status_value(1, False)
    DoNotDisturb = _calc_status_value(2, False)

    # Status values when the user is on a mobile device
    MobileIdle = _calc_status_value(0, True)
    MobileOnline = _calc_status_value(1, True)
    MobileDoNotDisturb = _calc_status_value(2, True)

    Offline = -1  # Not actually used in the db. Listed for completion and internal comparisons


# Check if a given UserStatus is a mobile status (e.g. the user is on their phone)
def user_status_check_mobile(status: UserStatus) -> bool:
    if status == UserStatus.Offline:
        return False

    return bool(status & 1)


# Adjust the mobile component of a given status. Can be used to convert between mobile/non-mobile versions of statuses
def user_status_adjust_mobile(status: UserStatus, is_mobile: bool = True) -> UserStatus:
    if status == UserStatus.Offline:
        return UserStatus.Offline

    return UserStatus(status | 1) if is_mobile else UserStatus(status & ~1)


class VoiceStatus(IntEnum):
    Talking = 0
    AFK = 1

    Disconnected = -1  # Not actually used in the db. Listed for completion and internal comparisons


ACCEPTABLE_DOWNTIME = timedelta(minutes=10)


class Fridge:
    def __init__(self, db_file):
        self._db_file = db_file

    def salsa_activity_update_connected(self):
        with self._connection:
            # Update connected timestamp to say we are currently connected!
            result = self._connection.execute('UPDATE SalsaActivity SET timestamp=? WHERE status=?',
                                              (datetime.now(), SalsaStatus.Connected))

            # If there is no entry with status=Connected, then the result rowcount will be zero. In this case we should
            # insert the first entry
            if result.rowcount == 0:
                self._connection.execute('INSERT INTO SalsaActivity VALUES(?,?)',
                                         (SalsaStatus.Connected, datetime.now()))

    # Initialize logging of user activity (e.g. discord status - Online, Idle, Do Not Disturb)
    # active_users must be an up-to-date list of the {user_id,status} of non-offline users
    def user_activity_init(self, active_users):
        current_timestamp = datetime.now()
        last_connected_timestamp = self._connection.execute(
            'SELECT timestamp FROM SalsaActivity WHERE status=? ORDER BY timestamp DESC LIMIT 1',
            (SalsaStatus.Connected,)).fetchone()

        if last_connected_timestamp is None:
            # If there is no connected timestamp, this must be a new db and the UserActivity table must also be empty
            table_has_content = self._connection.execute('SELECT EXISTS(SELECT 1 FROM UserActivity)').fetchone()[0]
            if table_has_content:
                raise Exception('Database corruption!')
        elif current_timestamp - last_connected_timestamp[0] > ACCEPTABLE_DOWNTIME:
            # If we have been disconnected for longer than the acceptable downtime, we must finish old activity entries
            # in the db and assume that those users went offline when we were disconnected
            with self._connection:
                self._connection.execute(
                    'UPDATE UserActivity SET duration=MAX(?-start,0) WHERE duration IS NULL',
                    (last_connected_timestamp[0],))
        else:
            # If we have been disconnected for less than the acceptable downtime, then we may assume that any users who
            # were previously online and are STILL online have been online during our period of downtime
            change_timestamp = last_connected_timestamp[0] + (current_timestamp - last_connected_timestamp[0]) / 2
            for user_id, db_status in self._connection.execute(
                    'SELECT id, status FROM UserActivityView WHERE duration IS NULL'):
                current_status = active_users.pop(user_id, UserStatus.Offline)
                if db_status != current_status:
                    self.user_activity_update(user_id, current_status, change_timestamp)

        # For any users who are currently online and not present in the database, open entries for them
        for user_id, current_status in active_users.items():
            self.user_activity_update(user_id, current_status, current_timestamp)

    def user_activity_update(self, user_id: int, status: UserStatus, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()

        # Close any open entry for this user and then open a new entry with the updated status
        alias_id = self.get_alias_id(user_id)
        with self._connection:
            self._connection.execute(
                'UPDATE UserActivity SET duration=MAX(?-start,0) WHERE '
                'duration IS NULL AND id=?', (timestamp, alias_id))

            if status != UserStatus.Offline:
                self._connection.execute('INSERT INTO UserActivity VALUES(?,?,?,NULL)', (alias_id, status, timestamp))

    # Get the alias ID for a given discord user_id. The alias ID is the rowid of the discord user_id inside the UserIDs
    # table. We are using alias IDs in place of discord IDs in order to make our db size as small as possible
    def get_alias_id(self, user_id: int):
        with self._connection:
            while True:
                alias_id = self._connection.execute('SELECT rowid FROM UserIDs WHERE id=?', (user_id,)).fetchone()
                if alias_id is None:
                    self._connection.execute('INSERT INTO UserIDs VALUES (?)', (user_id,))
                else:
                    # Remove the tuple
                    return alias_id[0]

    def init_db(self):
        sql_tables = [
            'CREATE TABLE IF NOT EXISTS SalsaActivity (status SalsaStatus, timestamp Timestamp)',

            'CREATE TABLE IF NOT EXISTS UserIDs (id Integer NOT NULL UNIQUE)',

            'CREATE TABLE IF NOT EXISTS UserActivity '
            '(id Integer, status UserStatus, start Timestamp, duration Duration)',

            'CREATE TABLE IF NOT EXISTS VoiceActivity '
            '(id Integer, status VoiceStatus, start Timestamp, duration Duration)',

            'CREATE VIEW IF NOT EXISTS UserActivityView AS '
            'SELECT UserIDs.id, UserActivity.status, UserActivity.start, UserActivity.duration '
            'FROM UserActivity LEFT JOIN UserIDs ON UserActivity.id=UserIDs.rowid'
        ]
        with self._connection:
            for sql in sql_tables:
                self._connection.execute(sql)

    def __enter__(self):
        # Open database file and initialize
        self._connection = sqlite3.connect(self._db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.init_db()

        # Register custom timestamp converter/adapter. We are using Unix epoch timestamps instead of ISO because they
        # are also supported by sqlite3 and use significantly less storage space inside the db
        def adapt_timestamp(timestamp: datetime):
            return round(timestamp.timestamp())

        def convert_timestamp(timestamp: bytes):
            return datetime.fromtimestamp(int(timestamp))

        sqlite3.register_adapter(datetime, adapt_timestamp)
        sqlite3.register_converter('timestamp', convert_timestamp)

        # Also register adapter/converter for duration -> Python timedelta to make things easier :)
        def adapt_duration(duration: timedelta):
            return duration.total_seconds()

        def convert_duration(duration: bytes):
            return timedelta(seconds=int(duration))

        sqlite3.register_adapter(timedelta, adapt_duration)
        sqlite3.register_converter('duration', convert_duration)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connection.close()


if __name__ == '__main__':
    # with Fridge('test.db') as fridge:
    #     fridge.salsa_activity_update_connected()
    #     fridge.user_activity_init({})
    print([user_status_adjust_mobile(x, True) for x in UserStatus])
