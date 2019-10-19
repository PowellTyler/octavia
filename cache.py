from db import Session

class Cache():

    def __init__(self):
        self.reminder_cache = {}
        self.message_cache = {}

    def update_reminder_cache(self):
        with Session() as session:
            self.reminder_cache.clear()
            reminders = session.get_all_reminders()
            for id, message, time, channel, last_reminder_sent in reminders:
                self.reminder_cache.setdefault(id, {}).update({
                    'message': message,
                    'time': time,
                    'channel': channel,
                    'last_reminder_sent': last_reminder_sent
                })
