# Digital Products Telegram Bot

A Telegram bot for selling digital products with multiple payment methods support (Credit Card, PayPal, and Cryptocurrency).

## Features

- 🛍️ Digital product catalog management
- 💳 Multiple payment methods:
  - Credit Card (via Stripe)
  - PayPal
  - Cryptocurrency (via Coinbase Commerce)
- 👤 Customer management
- 📦 Order tracking
- 🔐 Admin panel for product management

## Prerequisites

- Python 3.11 (recommended) or lower version
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Payment service accounts:
  - [Stripe](https://stripe.com)
  - [PayPal Developer](https://developer.paypal.com)
  - [Coinbase Commerce](https://commerce.coinbase.com)

## Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd telegram-bot
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your credentials:
# - TELEGRAM_TOKEN (from @BotFather)
# - STRIPE_API_KEY
# - PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET
# - COINBASE_API_KEY
# - ADMIN_USER_IDS (your Telegram user ID, get it from @userinfobot)
```

5. **Run the bot**
```bash
python bot.py
```

## Usage

### Admin Commands
- `/start` - Start the bot
- `/add_product` - Add a new digital product
- `/cancel` - Cancel current operation

### Customer Flow
1. Start chat with bot
2. Browse products using "View Products 🛍" button
3. Select a product
4. Choose payment method
5. Complete payment
6. Receive digital product

### Managing Products (Admin)
1. Use `/add_product` command
2. Follow the prompts to enter:
   - Product name
   - Description
   - Price
   - Digital content URL

### Viewing Orders
- Click "My Orders 📦" to view order history
- Orders show status, payment method, and delivery status

## Payment Methods

### Credit Card (Stripe)
- Secure checkout page
- Supports major credit cards
- Instant payment confirmation

### PayPal
- Redirect to PayPal login
- Secure payment processing
- Support for PayPal balance and linked accounts

### Cryptocurrency (Coinbase Commerce)
- Support for multiple cryptocurrencies
- Real-time exchange rates
- Secure blockchain transactions

## Troubleshooting

If you encounter any issues:

1. **Bot not responding**
   - Check if bot is running
   - Verify TELEGRAM_TOKEN in .env

2. **Payment errors**
   - Verify API keys in .env
   - Check payment service dashboard for errors

3. **Database issues**
   - Check if digital_store.db exists
   - Verify database permissions

## Security Notes

- Never share your .env file
- Keep API keys confidential
- Regularly update dependencies
- Monitor transactions for suspicious activity

## Support

For support, please:
1. Check troubleshooting guide
2. Review error logs
3. Contact administrator

## License

This project is licensed under the MIT License - see the LICENSE file for details. 