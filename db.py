import sqlite3
import logger as log
from os.path import isfile
import datetime
from __init__ import config


class Session():
    def __init__(self):
        """
        Connects to the database, creating a new one if one does not exist
        """
        if not isfile(config['database_path']):
            with open(config['database_path'], 'w') as file:
                pass

        self.connection = sqlite3.connect(config['database_path'])
        self.cursor = self.connection.cursor()

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS history (id int NOT NULL PRIMARY KEY,user,server,name nvarchar(255))""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS money (id NOT NULL PRIMARY KEY, user, server, money int)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS reminder (id NOT NULL PRIMARY KEY, message, time, channel, last_reminder_sent)""")
 
    def __enter__ (self):
        return self

    def __exit__ (self, exc_type, exc_value, traceback):
        self.connection.commit()
        self.connection.close()

    def add_nick(self, user, server, name):
        """
        Adds a new nick name for given server and user
        """
        if user == None or server == None or name == None:
            log.info('message="unable to create new table row as user_id, server_id, or name given is invald" user_id="{}" server_id="{}" name="{}"'.format(user, server, name))
            return

        clean_name = self._clean_name(name)

        try:
            self.cursor.execute("""
            SELECT id 
            FROM history 
            WHERE user = '{user}' 
                AND server = '{server}' 
                AND name = '{name}'
            """.format(user=user, server=server, name=clean_name))

            if not self.cursor.fetchone():
                self.cursor.execute("""SELECT MAX(id) FROM history""")
                result = self.cursor.fetchone()
                id = 0 if result[0] == None else int(result[0]) + 1

                self.cursor.execute("""INSERT INTO history VALUES({id},'{user}','{server}','{name}')""".format(id=id, user=user, server=server, name=clean_name))
                log.info('command=add_nick status=success user="{}" server="{}" name="{}"'.format(user, server, name))
        except:
            log.error('command=add_nick status=fail user={} server={} name="{}"'.format(user, server, name))

    def add_money(self, user, server, amount):
        """
        Adds money for a user on a given server.  This value is added to the current amount in the database
        """
        if user == None or server == None:
            log.info('command=add_money status=fail message=invalid_user_or_server user_id="{}" server_id="{}"'.format(user, server, name))
            return

        self.cursor.execute("""
        SELECT id
        FROM money
        WHERE user = '{user}'
            AND server = '{server}'
        """.format(user=user, server=server))

        if not self.cursor.fetchone():
            self.cursor.execute("""SELECT MAX(id) FROM money""")
            result = self.cursor.fetchone()
            id = 0 if result[0] is None else int(result[0]) + 1

            self.cursor.execute("""INSERT INTO money VALUES({id},'{user}','{server}',{money})""".format(id=id, user=user, server=server, money=amount))
            log.info('command=add_money status=success message=new_user user={} server={} money={}'.format(user, server, amount))

        else:
            self.cursor.execute("""
            UPDATE money
            SET money = money + {amount}
            WHERE user = '{user}'
                AND server = '{server}'
            """.format(amount=amount, user=user, server=server))

    def get_money(self, user, server):
        """
        Given user and server return the amount of money they currently have
        """
        if not user or not server:
            return 0
        
        self.cursor.execute("""
        SELECT money
        FROM money
        WHERE user = '{user}'
            AND server = '{server}'
        """.format(user=user, server=server))
        result = self.cursor.fetchone()
        if not result:
            return 0

        return result[0]

    def add_reminder(self, message, time, channel_id):
        """
        Adds a reminder to the database with given message daily time
        """
        self.cursor.execute("""SELECT MAX(id) FROM reminder""")
        result = self.cursor.fetchone()
        id = 0 if result[0] is None else int(result[0]) + 1

        last_reminder_sent = str(datetime.date.today())

        self.cursor.execute("""INSERT INTO reminder VALUES({id},'{message}','{time}','{channel}','{last_reminder_sent}')""".format(id=id, message=message, time=time, channel=channel_id, last_reminder_sent=last_reminder_sent))
        log.info('command=add_reminder status=success id={} channel={}'.format(id, channel_id))

        return id
    
    def edit_reminder(self, id, message=None, time=None, last_reminder_sent=None):
        """
        Edits an existing reminder
        """
        if last_reminder_sent:
            self.cursor.execute("""UPDATE reminder SET last_reminder_sent = '{last_reminder_sent}' WHERE id = {id}""".format(last_reminder_sent=last_reminder_sent, id=id))
        elif time:
            self.cursor.execute("""UPDATE reminder SET message = '{message}', time = '{time}' WHERE id = {id}""".format(message=message, time=time, id=id))
        else:
            self.cursor.execute("""UPDATE reminder SET message = '{message}' WHERE id = {id}""".format(message=message, id=id))

        log.info('command=edit_reminder status=success id={}'.format(id))

    def move_reminder(self, id, channel_id):
        """
        Moves an existing reminder
        """
        self.cursor.execute("""UPDATE reminder SET channel = '{channel}' WHERE id = {id}""".format(channel=channel_id, id=id))

    def delete_reminder(self, id):
        """
        deletes reminder from table given id
        """
        self.cursor.execute("""DELETE FROM reminder WHERE id = {id}""".format(id=id))
        log.info('command=delete_reminder status=success id={}'.format(id))

    def get_reminder(self, id):
        """
        Gets a single reminder with given id
        """
        self.cursor.execute("""SELECT * from reminder WHERE id = {id}""".format(id=id))
        return self.cursor.fetchone()

    def get_all_reminders(self):
        """
        Returns all currently active reminders
        """
        self.cursor.execute("""SELECT * from reminder""")
        return self.cursor.fetchall()

    def _clean_name(self, name):
        """
        Cleans the name for database insertion
        """
        return name.replace("'", "''")
