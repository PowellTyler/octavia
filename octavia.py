import discord
from asyncio import sleep, get_event_loop
from datetime import time, datetime
from discord.member import Member
from db import Session
from version import version
from math import ceil
from helpmessage import help_message
import logger as log
import re as regex
import youtube_dl
from __init__ import config

REMINDER_TIME = time(hour=config['reminder_hour'])


client = discord.Client()
compiled_pattern = regex.compile('octavia.*([^wW])\s*[wW]\s*([^wW])')
mention_pattern = regex.compile('<@!(\d+)>')
# stores the last message sent in a given channel
message_cache = {}
reminder_sent = True
reminder_channel = None

# youtube configuration
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '192.168.1.156'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@client.event
async def on_message(message):
    """
    Makes the bot execute specified commands when a member types a message in discord chat.
    """
    author_name = message.author.name
    if isinstance(message.author, Member) and message.author.nick:
        author_name = message.author.nick
    server = message.guild.id
    channel = message.channel
    user = message.author.id
    match = compiled_pattern.match(message.content)
    if message.author.voice:
        voice_channel = message.author.voice.channel
    voice_client = message.guild.voice_client

    # TODO move if statements into their own functions

    # history command
    if message.content.startswith("octavia.history") and len(message.mentions) > 0:
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
        return

    # cookie display command
    elif message.content.startswith("octavia.cookies") and len(message.mentions) > 0:
        mention = message.mentions[0]
        with Session() as session:
            if user and server:
                points = session.get_money(mention.id, server)
                if points == 0:
                    additional_message = 'You may not have any but it\'s never too late to start getting some!'
                elif points <= 50:
                    additional_message = 'that\'s a nice midnight snack! (:'
                elif points <= 150:
                    additional_message = 'well now you\'re just showing off'
                elif points <= 300:
                    additional_message = 'sharing is caring, ya know...'
                elif points <= 1000:
                    additional_message = '...So you\'re gonna share those, right?'
                else:
                    additional_message = 'Be sure to share with the rest of us please! (:'

                await bot_print(channel, '{} currently has {} cookies!  {}'.format(mention.name, points, additional_message))
        return

    # version command
    elif message.content.startswith("octavia.version"):
        await bot_print(channel, 'This is a version {} Octavia Bot'.format(version))
    
    # help command
    elif message.content.startswith('octavia.help'):
        await channel.send(help_message)

    # owo command
    elif message.content.startswith("octavia.owo"):
        if server in message_cache and channel.id in message_cache[server]:
            matches = mention_pattern.match(message_cache[server][channel.id])
            if matches:
                for m in matches.groups():
                    user = client.get_user(int(m))
                    if user:
                        message_cache[server][channel.id] = mention_pattern.sub(user.name, message_cache[server][channel.id], 1)

            owo_text = (message_cache[server][channel.id]
            .replace('l', 'w')
            .replace('r', 'w')
            .replace('L', 'W')
            .replace('R', 'W')
            .replace('ou', 'uw')
            .replace('OU', 'UW')
            .replace('octavia.owo', '')) + ' uwu'
            await bot_print(channel, owo_text)
        else:
            message = "I'm sorry but either there are no messages to translate in this channel or sometimes I have short term memory loss, try typing something in this channel first so I know what to translate next time!"
            await bot_print(channel, message)
    
    # luis is gay command
    elif message.content.startswith('octavia.remind'):
        global reminder_channel
        reminder_channel = channel
        await bot_print(channel, "This channel has been set to receive reminders at {} everyday.".format(time(hour=config['reminder_hour'])))
    
    # play youtube audio command
    # elif message.content.startswith('octavia.play') and voice_channel:
    #     search_content = message.content.replace('octavia.play', '').strip()
    #     log.info('command=play search_content="{}" user={}'.format(search_content, user))
    #     # await voice_channel.connect()
    #     player = await YTDLSource.from_url(search_content)
    #     voice_channel.play(player, after=lambda e: log.error('command=play search_content="{}" status=failed'.format(search_content)))

        # bot_print(channel, 'Now playing: {}'.format(player.title))

    # hidden command
    elif match:
        if match.group(1) == match.group(2):
            await bot_print(channel, 'OwO what\'s this?')

    # cache the last sent message in a channel
    elif message.author.id != int(config['bot_id']):
        if not server in message_cache:
            message_cache[server] = {}
        
        message_cache[server][channel.id] = message.content

    # add new nick name and increment points
    with Session() as session:
        session.add_nick(user, server, author_name)
        points = int(config['points_per_message']) if not message.author.premium_since else int(config['points_per_premium_message'])
        session.add_money(user, server, points)


async def bot_print(channel, text=''):
    """
    Makes the bot print out a message with usual text formatting
    """
    await channel.send("```{}```".format(text))


async def print_reminder():
    global reminder_sent
    while True:
        now = datetime.now().time()
        if now < REMINDER_TIME:
            reminder_sent = False
        elif not reminder_sent and reminder_channel is not None:
            reminder_sent = True
            log.info('event=print_reminder')
            await reminder_channel.send("This is a reminder that <@{}> is gay.".format(config['gay_id']))

        await sleep(60)

client.loop.create_task(print_reminder())
client.run(config['bot_token'])
