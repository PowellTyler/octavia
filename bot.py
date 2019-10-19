import discord
from discord.ext import commands
from discord.member import Member
from db import Session
from datetime import datetime, date, time
from asyncio import sleep
import logger as log
import re as regex
from cache import Cache
from __init__ import config, client
from __version__ import version
from __help__ import remind_help_message

MENTION_PATTERN = regex.compile('<@!(\d+)>')
REMINDER_ADD_PATTERN = regex.compile(r'-n\s*"(.+)"\s*([0-9]{1,2}:[0-9]{1,2})\s*([aApP][mM])?')
REMINDER_EDIT_PATTERN = regex.compile(r'-e\s*([0-9]+)\s*"(.+)"\s*([0-9]{1,2}:[0-9]{1,2})\s*([aApP][mM])?')
REMINDER_DELETE_PATTERN = regex.compile(r'-d\s*([0-9]+)')
BOT_ID = 597587492228694036

app_cache = Cache()
reminder_sent = True
reminder_channel = None

audio_players = {}


@client.event
async def on_ready():
    app_cache.update_reminder_cache()
    log.info('message=bot_ready')


@client.event
async def on_message(message):
    """
    Store nickname/username of message author as well as increment the amount of points
    they have on the server and store message in cache if it is not a command.
    """

    user = message.author.id
    author_name = message.author.name
    server = message.guild.id
    channel = message.channel

    if message.author.id == BOT_ID:
        return

    with Session() as session:
        session.add_nick(user, server, author_name)
        points = int(config['points_per_message']) if not message.author.premium_since else int(config['points_per_premium_message'])
        session.add_money(user, server, points)
    
    if not message.content.startswith(config['bot_prefix']):
       app_cache.message_cache.setdefault(server, {}).update({
            channel.id: message.content
        })
    
    await client.process_commands(message)


@client.command(pass_context=True)
async def history(ctx):
    """
    Generates a list of known nickname/username for a mentioned user
    on the server and prints out the list to the text channel.
    """
    message = ctx.message
    channel = message.channel
    user = message.author.id
    author_name = message.author.name
    server = message.guild.id

    if len(message.mentions) == 0:
        await bot_print(channel, 'history <@mentioned user>:\n\nWhen I see this command I will display all\nthe names this user is known by on this server.')
        return

    mention = message.mentions[0]
    name = None
    previous_names = None
    with Session() as session:
        if user and server and author_name:
            session.add_nick(user, server, author_name)
        name_history = [n[0] for n in session.filter(mention.id, server)]
        name = mention.name
        if isinstance(mention, Member) and mention.nick:
            name = mention.nick
        previous_names = '\n'.join(name_history)

    if previous_names:
        await bot_print(channel, 'Here are all the names that {} is known by\n\n{}'.format(name, previous_names))
    else:
        await bot_print(channel, 'Hmm it appears I don\'t know who that is, have them type something in chat so I can remember them in the future! :)')
    
    log.info('command=history status=success user={} server={} text_channel={}'.format(user, server, channel.name))


@client.command(pass_context=True)
async def about(ctx):
    """
    Displays version info
    """
    message = ctx.message
    channel = message.channel
    user = message.author.id
    server = message.guild.id
    await bot_print(channel, 'This is a version {} Octavia Bot'.format(version))

    log.info('command=version status=success user={} server={} text_channel={}'.format(user, server, channel.name))


@client.command(pass_context=True)
async def remind(ctx):
    """
    Create, edit, or delete a daily reminder.

    New reminder - octavia.remind -n "message" <time HH:MM> <period am/pm>

    Edit reminder - octavia.remind -e <reminder_ticket_number> "message" <time HH:MM> <period am/pm>

    Delete reminder - octavia.remind -d <reminder_ticket_number>
    """
    message = ctx.message
    channel = message.channel
    user = message.author.id
    author_name = message.author.name
    server = message.guild.id

    match = REMINDER_ADD_PATTERN.search(ctx.message.content)
    if match:
        message, reminder_time, period = match.groups()
        hours, minutes = reminder_time.split(':')
        hours = int(hours)
        minutes = int(minutes)

        if hours > 23 or minutes > 59:
            await bot_print(channel, 'This time is not valid, please try a different time.')
            return 

        additional_hours = 12 if period and period.lower() == 'pm' and hours < 12 else 0
        hours += additional_hours

        time_str = time(hour=hours, minute=minutes).strftime('%H:%M')

        with Session() as session:
            ticket = session.add_reminder(message, time_str, channel.id)
        
        await bot_print(channel, 'I have setup a new reminder to be sent to this channel at {} everyday, the ticket number is {}.'.format(time_str, ticket))
        app_cache.update_reminder_cache()
        return

    match = REMINDER_EDIT_PATTERN.search(ctx.message.content)
    if match:
        ticket_id, message, reminder_time, period = match.groups()
        hours, minutes = reminder_time.split(':')
        hours = int(hours)
        minutes = int(minutes)

        if hours > 23 or minutes > 59:
            await bot_print(channel, 'This time is not valid, please try a different time.')
            return

        additional_hours = 12 if period and period.lower() == 'pm' and hours <= 12 else 0
        hours += additional_hours

        time_str = time(hour=hours, minute=minutes).strftime('%H:%M')

        with Session() as session:
            if not session.get_reminder(ticket_id):
                await bot_print(channel, 'This ticket number is not valid, please try a different one.')
                return
            session.edit_reminder(ticket_id, message, time_str)

        await bot_print(channel, 'Reminder has been updated!')
        app_cache.update_reminder_cache()
        return

    match = REMINDER_DELETE_PATTERN.search(ctx.message.content)
    if match:
        ticket_id = match.group(1)
        with Session() as session:
            if not session.get_reminder(ticket_id):
                await bot_print(channel, 'This ticket number is not valid, please try a different one.')
                return
            session.delete_reminder(ticket_id)
        await bot_print(channel, 'Reminder has been deleted!')
        app_cache.update_reminder_cache()
        return

    await bot_print(channel, remind_help_message)
    return


async def bot_print(channel, text=''):
    """
    Makes the bot print out a message with usual text formatting
    """
    await channel.send("```{}```".format(text))
    log.info('command=bot_print status=success')


async def leave(voice_client):
    await voice_client.disconnect()


async def loop_task():
    while True:
        for id in app_cache.reminder_cache.keys():
            reminder = app_cache.reminder_cache[id]
            today = date.today()
            now = datetime.now().time()
            last_reminder_sent = datetime.strptime(reminder['last_reminder_sent'], '%Y-%m-%d').date()
            reminder_time = datetime.strptime(reminder['time'], '%H:%M').time()

            if today > last_reminder_sent and now >= reminder_time:
                with Session() as session:
                    session.edit_reminder(id, last_reminder_sent=str(today))
                app_cache.reminder_cache[id].update({'last_reminder_sent': str(today)})
                channel = client.get_channel(int(reminder['channel']))
                await channel.send('[{}] {}'.format(id, reminder['message']))
        await sleep(60)

client.loop.create_task(loop_task())
client.run(config['bot_token'])
