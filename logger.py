from os.path import exists, isdir, dirname, join, abspath
from os import mkdir
from datetime import datetime
from __init__ import config

def info(message):
    _log(message, 'INFO')
    

def warning(message):
    _log(message, 'WARNING')


def error(message):
    _log(message, 'ERROR')


def _log(message, log_type):
    _create_file()
    now = datetime.now().strftime("%H:%M:%S %Y-%d-%m")
    log = '[{}][{}][{}]'.format(log_type, now, message)
    with open(config['log_file_path'], 'ab') as file:
        file.write(log.encode('utf8'))
    print(log)


def _create_file():
    file_path = config['log_file_path']
    if exists(file_path):
        return

    if not isdir(join('.', dirname(file_path))):
        mkdir(join('.', dirname(file_path)))

    with open(file_path, 'wb') as _:
        pass
