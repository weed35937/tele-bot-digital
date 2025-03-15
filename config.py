import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Payment API Keys
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
COINBASE_API_KEY = os.getenv('COINBASE_API_KEY')

# Admin Configuration
ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id]

# Database Configuration
DATABASE_URL = "sqlite:///digital_store.db" 