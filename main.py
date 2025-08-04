#!/usr/bin/env python3
"""
Sodda Telegram Media Yuklovchi Bot
"""

import os
import logging
import re
import asyncio
from urllib.parse import urlparse

import requests
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationBuilder,
    CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# 🔐 Token (tokenni istasangiz .env dan oling, bu yerda bevosita yozilgan)
BOT_TOKEN = "8125750878:AAEeyftrcKyw7sNRq_tmTZL6Kj8QjODSNsw"

# 📝 Log sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

# ✅ Qo‘llab-quvvatlanadigan platformalar
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com',
    'snapchat.com', 'twitter.com', 'x.com', 'facebook.com', 'vimeo.com'
]

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return any(p in domain for p in SUPPORTED_PLATFORMS)
    except:
        return False

def extract_urls(text):
    pattern = r'https?://[^\s]+'
    return [u for u in re.findall(pattern, text) if is_valid_url(u)]

class SimpleMediaBot:
    def init(self):
        self.downloads_dir = "downloads"
        os.makedirs(self.downloads_dir, exist_ok=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎉 Salom! Media yuklash uchun link yuboring (YouTube, TikTok, Instagram, va boshqalar)."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Havola yuboring — men media faylni yuklab beraman.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        urls = extract_urls(text)

        if not urls:
            await update.message.reply_text("⚠️ To‘g‘ri havola yuboring.")
            return

        url = urls[0]
        await update.message.reply_text("🔄 Yuklanmoqda...")

        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{self.downloads_dir}/%(title)s.%(ext)s',
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            with open(file_path, 'rb') as f:
                await update.message.reply_document(f)
        except Exception as e:
            logger.error(f"Yuklab olishda xatolik: {e}")
            await update.message.reply_text("❌ Yuklab bo‘lmadi. Iltimos, boshqa havola yuboring.")

async def main():
    bot = SimpleMediaBot()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print("🤖 Bot ishga tushdi...")
    await app.run_polling()

if name == "main":
    asyncio.run(main())
