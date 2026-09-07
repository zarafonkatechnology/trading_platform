# src/telegram/trading_bot.py
"""
Telegram bot for trading commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

class TradingBot:
    def __init__(self, token):
        self.token = token
        
    async def start(self, update, context):
        keyboard = [
            [InlineKeyboardButton("📊 Prices", callback_data='prices')],
            [InlineKeyboardButton("📈 Execute Trade", callback_data='trade')],
            [InlineKeyboardButton("📋 Positions", callback_data='positions')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 Trading Bot Active!\nChoose an option:",
            reply_markup=reply_markup
        )