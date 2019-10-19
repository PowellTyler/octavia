import configparser
import discord
from discord.ext import commands

class Config():
    def __init__(self, config_file=''):
        self.config = configparser.ConfigParser()
        with open(config_file, 'r') as file:
            self.config.readfp(file)
    
    def __getitem__(self, key):
        try:
            return self.config.getint('elvy', key)
        except Exception:
            pass
        try:
            return self.config.get('elvy', key)
        except Exception:
            pass

config = Config('config.ini')
client = commands.Bot(command_prefix=config['bot_prefix'])
