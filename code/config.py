import os
from dotenv import load_dotenv

load_dotenv()

def get_db_config():
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST')
    }
    return db_config

def get_telegram_token():
    return os.getenv('TELEGRAM_TOKEN')
