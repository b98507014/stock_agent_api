"""
Telegram Bot for Stock Trading API
Connects directly to /suggest endpoint for real-time trading suggestions
"""

import os
import logging
import requests
from typing import Optional
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ChatAction

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
STOCK_API_URL = os.getenv('STOCK_API_URL', 'https://stockagentapi-production.up.railway.app/suggest')
API_TIMEOUT = 120

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

logger.info(f"Stock API URL: {STOCK_API_URL}")


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split message into chunks of max_length characters."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
            current_chunk = line + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    return chunks


async def send_trading_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Call stock API and send response to Telegram."""
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Call stock API
        logger.info(f"Calling {STOCK_API_URL}")
        payload = {
            "mode": "paper",
            "execute": True
        }
        
        response = requests.post(
            STOCK_API_URL,
            json=payload,
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if telegram_text exists
            if 'telegram_text' in result and result['telegram_text']:
                message_text = result['telegram_text']
                logger.info(f"Received telegram_text: {len(message_text)} chars")
            else:
                # Fallback to error message with summary
                message_text = (
                    "⚠️ No telegram_text in response\n\n"
                    f"Mode: {result.get('mode', 'N/A')}\n"
                    f"Cash: {result.get('cash', 'N/A')}\n"
                    f"Executed: {result.get('executed', 'N/A')}\n"
                    f"Balance After: {result.get('balance_after', 'N/A')}\n"
                    f"Portfolio Value: {result.get('portfolio_value', 'N/A')}"
                )
        else:
            # API error
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', {}).get('message', str(response.text))
            message_text = (
                f"❌ API Error (Status {response.status_code})\n\n"
                f"Message: {error_msg}"
            )
            logger.error(f"API error: {response.status_code} - {error_msg}")
        
        # Split message and send
        chunks = split_message(message_text)
        logger.info(f"Sending {len(chunks)} chunk(s)")
        
        for i, chunk in enumerate(chunks):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode=None  # Plain text, no HTML/Markdown
                )
                if i < len(chunks) - 1:
                    # Small delay between chunks
                    import asyncio
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to send chunk {i+1}/{len(chunks)}: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Failed to send message chunk {i+1}/{len(chunks)}"
                )
    
    except requests.Timeout:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ API timeout (120s exceeded). Trading API is taking too long to respond."
        )
        logger.error(f"API timeout after {API_TIMEOUT}s")
    
    except requests.ConnectionError as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Connection error: Cannot reach stock API\n\nURL: {STOCK_API_URL}"
        )
        logger.error(f"Connection error: {e}")
    
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Error: {str(e)}"
        )
        logger.error(f"Unexpected error: {e}", exc_info=True)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /run command - get trading suggestions and execute."""
    logger.info(f"User {update.effective_user.id} called /run")
    await send_trading_response(update, context)


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stock command - same as /run."""
    logger.info(f"User {update.effective_user.id} called /stock")
    await send_trading_response(update, context)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health command - check API health."""
    try:
        logger.info(f"User {update.effective_user.id} called /health")
        
        response = requests.post(
            STOCK_API_URL.replace('/suggest', '/health'),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            status_text = (
                f"✅ Stock API is healthy\n\n"
                f"Status: {result.get('status', 'unknown')}\n"
                f"API URL: {STOCK_API_URL}"
            )
        else:
            status_text = (
                f"⚠️ Stock API returned {response.status_code}\n\n"
                f"API URL: {STOCK_API_URL}"
            )
    
    except requests.Timeout:
        status_text = (
            f"❌ Stock API timeout\n\n"
            f"API URL: {STOCK_API_URL}"
        )
    
    except requests.ConnectionError:
        status_text = (
            f"❌ Cannot reach stock API\n\n"
            f"API URL: {STOCK_API_URL}"
        )
    
    except Exception as e:
        status_text = f"❌ Health check error: {str(e)}"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=status_text
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_text = (
        "👋 Welcome to Stock Trading Telegram Bot!\n\n"
        "Available commands:\n"
        "/run - Get AI trading suggestions and execute trades\n"
        "/stock - Same as /run\n"
        "/health - Check API health\n"
        "/start - Show this message\n\n"
        "The bot will send trading analysis directly from the AI system."
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text
    )


async def setup_commands(application: Application) -> None:
    """Setup bot commands in Telegram."""
    commands = [
        BotCommand("run", "Get AI trading suggestions and execute"),
        BotCommand("stock", "Same as /run"),
        BotCommand("health", "Check API health"),
        BotCommand("start", "Show help message"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set up successfully")


def main() -> None:
    """Start the bot."""
    logger.info("Starting Stock Trading Telegram Bot")
    logger.info(f"Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"API URL: {STOCK_API_URL}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("run", cmd_run))
    application.add_handler(CommandHandler("stock", cmd_stock))
    application.add_handler(CommandHandler("health", cmd_health))
    
    # Setup commands
    application.post_init = setup_commands
    
    # Start the bot
    logger.info("Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
