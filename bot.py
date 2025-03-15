import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import stripe
import paypalrestsdk
from coinbase_commerce.client import Client
import json
from decimal import Decimal

from config import (
    TELEGRAM_TOKEN, DATABASE_URL, STRIPE_API_KEY,
    PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, COINBASE_API_KEY,
    ADMIN_USER_IDS
)
from models import Base, Customer, Product, Order, PaymentMethod, PaymentStatus

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup database
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Setup payment providers
stripe.api_key = STRIPE_API_KEY
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" in production
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})
coinbase_client = Client(api_key=COINBASE_API_KEY)

# Conversation states
PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_URL = range(4)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USER_IDS

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the product addition process"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Sorry, this command is only available to administrators.")
        return ConversationHandler.END
    
    await update.message.reply_text("Let's add a new product! First, what's the product name?")
    return PRODUCT_NAME

async def product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save product name and ask for description"""
    context.user_data['product_name'] = update.message.text
    await update.message.reply_text("Great! Now, please provide a description for the product:")
    return PRODUCT_DESCRIPTION

async def product_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save product description and ask for price"""
    context.user_data['product_description'] = update.message.text
    await update.message.reply_text("Please enter the price in USD (e.g., 9.99):")
    return PRODUCT_PRICE

async def product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save product price and ask for digital content URL"""
    try:
        price = float(update.message.text)
        context.user_data['product_price'] = price
        await update.message.reply_text("Please provide the URL where the digital content can be accessed:")
        return PRODUCT_URL
    except ValueError:
        await update.message.reply_text("Please enter a valid price (e.g., 9.99)")
        return PRODUCT_PRICE

async def product_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save product URL and finish product creation"""
    context.user_data['product_url'] = update.message.text
    
    session = SessionLocal()
    new_product = Product(
        name=context.user_data['product_name'],
        description=context.user_data['product_description'],
        price=context.user_data['product_price'],
        digital_content_url=context.user_data['product_url']
    )
    session.add(new_product)
    session.commit()
    session.close()
    
    await update.message.reply_text("Product added successfully! ✅")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Product addition cancelled.")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    session = SessionLocal()
    
    # Register customer if not exists
    customer = session.query(Customer).filter_by(telegram_id=user.id).first()
    if not customer:
        customer = Customer(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        session.add(customer)
        session.commit()
    
    keyboard = [
        [InlineKeyboardButton("View Products 🛍", callback_data="view_products")],
        [InlineKeyboardButton("My Orders 📦", callback_data="my_orders")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Welcome to the Digital Products Store, {user.first_name}! 🎉\n"
        "What would you like to do?",
        reply_markup=reply_markup
    )
    session.close()

async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for viewing products"""
    query = update.callback_query
    session = SessionLocal()
    
    products = session.query(Product).all()
    keyboard = []
    
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"{product.name} - ${product.price:.2f}",
                callback_data=f"product_{product.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("Back to Menu 🔙", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Here are our available products:",
        reply_markup=reply_markup
    )
    session.close()

async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for product selection"""
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    session = SessionLocal()
    
    product = session.query(Product).filter_by(id=product_id).first()
    
    keyboard = [
        [
            InlineKeyboardButton("Credit Card 💳", callback_data=f"pay_cc_{product_id}"),
            InlineKeyboardButton("PayPal 📱", callback_data=f"pay_pp_{product_id}")
        ],
        [InlineKeyboardButton("Cryptocurrency 🪙", callback_data=f"pay_crypto_{product_id}")],
        [InlineKeyboardButton("Back to Products 🔙", callback_data="view_products")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Product: {product.name}\n"
        f"Price: ${product.price:.2f}\n"
        f"Description: {product.description}\n\n"
        "Choose your payment method:",
        reply_markup=reply_markup
    )
    session.close()

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for viewing order history"""
    query = update.callback_query
    user_id = update.effective_user.id
    session = SessionLocal()
    
    customer = session.query(Customer).filter_by(telegram_id=user_id).first()
    if not customer:
        await query.edit_message_text("No orders found.")
        session.close()
        return
    
    orders = session.query(Order).filter_by(customer_id=customer.id).all()
    if not orders:
        await query.edit_message_text(
            "You haven't placed any orders yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu 🔙", callback_data="start")]])
        )
        session.close()
        return
    
    order_text = "Your Orders:\n\n"
    for order in orders:
        product = order.product
        order_text += f"Order #{order.id}\n"
        order_text += f"Product: {product.name}\n"
        order_text += f"Amount: ${order.amount:.2f}\n"
        order_text += f"Status: {order.payment_status.value}\n"
        order_text += f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    keyboard = [[InlineKeyboardButton("Back to Menu 🔙", callback_data="start")]]
    await query.edit_message_text(
        order_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    session.close()

async def process_stripe_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Stripe payment"""
    query = update.callback_query
    product_id = int(query.data.split('_')[2])
    session = SessionLocal()
    
    product = session.query(Product).filter_by(id=product_id).first()
    customer = session.query(Customer).filter_by(telegram_id=update.effective_user.id).first()
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                        'description': product.description,
                    },
                    'unit_amount': int(product.price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://t.me/your_bot_username',
            cancel_url='https://t.me/your_bot_username',
        )
        
        # Create pending order
        order = Order(
            customer_id=customer.id,
            product_id=product.id,
            payment_method=PaymentMethod.CREDIT_CARD,
            payment_status=PaymentStatus.PENDING,
            amount=product.price,
            transaction_id=checkout_session.id
        )
        session.add(order)
        session.commit()
        
        # Send payment link
        await query.edit_message_text(
            f"Please complete your payment using this link:\n{checkout_session.url}\n\n"
            "After payment, you'll receive your digital product.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Stripe payment error: {str(e)}")
        await query.edit_message_text(
            "Sorry, there was an error processing your payment. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
            ]])
        )
    finally:
        session.close()

async def process_paypal_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PayPal payment"""
    query = update.callback_query
    product_id = int(query.data.split('_')[2])
    session = SessionLocal()
    
    product = session.query(Product).filter_by(id=product_id).first()
    customer = session.query(Customer).filter_by(telegram_id=update.effective_user.id).first()
    
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {
                    "total": f"{product.price:.2f}",
                    "currency": "USD"
                },
                "description": f"Purchase of {product.name}"
            }],
            "redirect_urls": {
                "return_url": "https://t.me/your_bot_username",
                "cancel_url": "https://t.me/your_bot_username"
            }
        })
        
        if payment.create():
            # Create pending order
            order = Order(
                customer_id=customer.id,
                product_id=product.id,
                payment_method=PaymentMethod.PAYPAL,
                payment_status=PaymentStatus.PENDING,
                amount=product.price,
                transaction_id=payment.id
            )
            session.add(order)
            session.commit()
            
            # Get approval URL
            approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
            
            await query.edit_message_text(
                f"Please complete your payment using this link:\n{approval_url}\n\n"
                "After payment, you'll receive your digital product.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
                ]])
            )
        else:
            raise Exception(payment.error)
            
    except Exception as e:
        logger.error(f"PayPal payment error: {str(e)}")
        await query.edit_message_text(
            "Sorry, there was an error processing your payment. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
            ]])
        )
    finally:
        session.close()

async def process_crypto_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Cryptocurrency payment"""
    query = update.callback_query
    product_id = int(query.data.split('_')[2])
    session = SessionLocal()
    
    product = session.query(Product).filter_by(id=product_id).first()
    customer = session.query(Customer).filter_by(telegram_id=update.effective_user.id).first()
    
    try:
        # Create Coinbase Commerce charge
        charge = coinbase_client.charge.create(
            name=product.name,
            description=product.description,
            pricing_type="fixed_price",
            local_price={
                "amount": str(product.price),
                "currency": "USD"
            }
        )
        
        # Create pending order
        order = Order(
            customer_id=customer.id,
            product_id=product.id,
            payment_method=PaymentMethod.CRYPTOCURRENCY,
            payment_status=PaymentStatus.PENDING,
            amount=product.price,
            transaction_id=charge.id
        )
        session.add(order)
        session.commit()
        
        await query.edit_message_text(
            f"Please complete your crypto payment using this link:\n{charge.hosted_url}\n\n"
            "After payment, you'll receive your digital product.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Crypto payment error: {str(e)}")
        await query.edit_message_text(
            "Sorry, there was an error processing your payment. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Menu 🔙", callback_data="start")
            ]])
        )
    finally:
        session.close()

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment webhook"""
    session = SessionLocal()
    data = json.loads(update.webhook_data)
    
    try:
        # Find the order based on transaction ID
        order = session.query(Order).filter_by(transaction_id=data['id']).first()
        if order:
            order.payment_status = PaymentStatus.COMPLETED
            session.commit()
            
            # Send digital product to customer
            await context.bot.send_message(
                chat_id=order.customer.telegram_id,
                text=f"Thank you for your purchase! Here's your digital product:\n{order.product.digital_content_url}"
            )
    except Exception as e:
        logger.error(f"Payment webhook error: {str(e)}")
    finally:
        session.close()

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add conversation handler for product management
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_product', add_product)],
        states={
            PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_name)],
            PRODUCT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_description)],
            PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_price)],
            PRODUCT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_url)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(view_products, pattern="^view_products$"))
    application.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    application.add_handler(CallbackQueryHandler(handle_product_selection, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(process_stripe_payment, pattern="^pay_cc_"))
    application.add_handler(CallbackQueryHandler(process_paypal_payment, pattern="^pay_pp_"))
    application.add_handler(CallbackQueryHandler(process_crypto_payment, pattern="^pay_crypto_"))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 