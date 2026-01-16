from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymemcache.client.base import Client
import logging
import coloredlogs
import warnings
import os

# Supprimer les warnings flask_limiter
warnings.filterwarnings("ignore", category=UserWarning, module="flask_limiter.extension")

def check_memcached_connection(host='memcached', port=11211):
    try:
        client = Client((host, port))
        client.set('test_key', 'test_value')
        if client.get('test_key') == b'test_value':
            client.delete('test_key')
            return True
        return False
    except:
        return False

def create_app():
    app = Flask(__name__)
    
    # Logger
    logger = logging.getLogger("1min-relay")
    coloredlogs.install(level='DEBUG', logger=logger)
    
    # Logo ASCII
    logger.info(r'''
    _ __  __ _      ___     _           
 / |  \/  (_)_ _ | _ \___| |__ _ _  _ 
 | | |\/| | | ' \|   / -_) / _` | || |
 |_|_|  |_|_|_||_|_|_\___|_\__,_|\_, |
                                 |__/ ''')

    # Limiter
    if check_memcached_connection():
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri="memcached://memcached:11211",
        )
    else:
        limiter = Limiter(
            get_remote_address,
            app=app,
        )
        logger.warning("Memcached is not available. Using in-memory storage for rate limiting. Not-Recommended")
        
    return app, logger, limiter