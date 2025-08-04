#!/usr/bin/env python3
"""
Sodda Telegram Media Yuklovchi Bot (yangilangan)
"""

import os
import logging
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from urllib.parse import urlparse
import re

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konfiguratsiya
BOT_TOKEN = os.getenv('BOT_TOKEN', '8125750878:AAEeyftrcKyw7sNRq_tmTZL6Kj8QjODSNsw')
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com',
    'snapchat.com', 'twitter.com', 'x.com', 'facebook.com', 'vimeo.com'
]

pending_downloads = {}

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        return any(platform in domain for platform in SUPPORTED_PLATFORMS)
    except:
        return False

def extract_urls_from_text(text):
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return [url for url in urls if is_valid_url(url)]

class SimpleMediaBot:
    def __init__(self):
        self.application = None
        self.downloads_dir = 'downloads'
        os.makedirs(self.downloads_dir, exist_ok=True)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """
🎉 Assalomu alaykum! Media Yuklovchi Botga xush kelibsiz! 🎉

Men sizga turli ijtimoiy tarmoqlardan video va musiqani 'hd' sifatida yuklashda yordam beraman!

Qo'llab-quvvatlanadigan platformalar:
• YouTube
• Instagram
• TikTok
• Snapchat
• Twitter/X
• Facebook
• Vimeo

Foydalanish:
1. Menga havola yuboring
2. Video yoki audio formatini tanlang
3. Yuklab olish natijasini kuting!

/start - Botni boshlash
/help - Yordam

Boshlash uchun havola yuboring! 🚀
"""
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🆘 Yordam

1. Havola yuboring
2. Format tanlang
3. Yuklab olish tugashini kuting

Qo'llab-quvvatlanadigan platformalar:
• YouTube, Instagram, TikTok, Snapchat, Twitter/X, Facebook, Vimeo
"""
        await update.message.reply_text(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        urls = extract_urls_from_text(text)

        if not urls:
            await update.message.reply_text(
                "Iltimos, qo'llab-quvvatlanadigan platformalardan havola yuboring.\n"
                "Masalan: YouTube, Instagram, TikTok va boshqalar."
            )
            return

        url = urls[0]
        await self.show_format_selection(update, url)

    async def show_format_selection(self, update, url):
        user_id = update.effective_user.id
        pending_downloads[user_id] = url

        keyboard = [
            [
                InlineKeyboardButton("🎥 Video", callback_data="download_video"),
                InlineKeyboardButton("🎵 Audio", callback_data="download_audio")
            ],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📱 Havola aniqlandi! Qaysi formatda yuklashni xohlaysiz?",
            reply_markup=reply_markup
        )

    async def handle_callback(self, update, context):
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        if data == "cancel":
            if user_id in pending_downloads:
                del pending_downloads[user_id]
            await query.edit_message_text("❌ Yuklash bekor qilindi.")
            return

        if data in ["download_video", "download_audio"]:
            if user_id not in pending_downloads:
                await query.edit_message_text("❌ URL topilmadi. Qaytadan urinib ko'ring.")
                return

            url = pending_downloads[user_id]
            is_audio = data == "download_audio"

            format_name = "Audio" if is_audio else "Video"
            format_emoji = "🎵" if is_audio else "🎥"

            await query.edit_message_text(
                f"{format_emoji} **{format_name} yuklanmoqda...**\nIltimos kuting."
            )

            await self.download_media_with_format(query, url, is_audio)

            if user_id in pending_downloads:
                del pending_downloads[user_id]

    async def download_media_with_format(self, query, url, is_audio=False):
        try:
            ydl_opts = {
                'format': 'bestaudio/best' if is_audio else 'best',
                'outtmpl': f'{self.downloads_dir}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }] if is_audio else [],
                'ignoreerrors': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    await query.edit_message_text("❌ Media ma'lumotlarini olishda xatolik.")
                    return

                title = info.get('title', 'Noma\'lum')
                await query.edit_message_text(f"📥 '{title}' yuklanmoqda...")

                ydl.download([url])
                filepath = self.find_downloaded_file(info, is_audio)

                if filepath and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)

                    await query.edit_message_text("📤 Fayl yuborilmoqda...")

                    with open(filepath, 'rb') as media_file:
                        caption = f"✅ Yuklandi!\n📁: {title}\n📊: {file_size / 1024 / 1024:.1f}MB"

                        if is_audio:
                            await query.message.reply_audio(media_file, caption=caption, title=title)
                        else:
                            await query.message.reply_video(media_file, caption=caption)

                    await query.edit_message_text("✅ Tugadi!")

                    os.remove(filepath)
                else:
                    await query.edit_message_text("❌ Yuklangan fayl topilmadi.")
        except Exception as e:
            logger.error(f"Xatolik: {e}")
            await query.edit_message_text("❌ Yuklashda xatolik yuz berdi.")

    def find_downloaded_file(self, info, is_audio=False):
        try:
            title = info.get('title', 'download')
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)

            extensions = ['.mp3'] if is_audio else ['.mp4', '.mkv', '.webm']
            for ext in extensions:
                filepath = os.path.join(self.downloads_dir, f"{safe_title}{ext}")
                if os.path.exists(filepath):
                    return filepath
            return None
        except Exception as e:
            logger.error(f"Fayl topishda xato: {e}")
            return None

    async def start_bot(self):
        self.application = Application.builder().token(BOT_TOKEN).build()

        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        logger.info("Bot ishga tushmoqda...")
        await self.application.run_polling()

async def main():
    bot = SimpleMediaBot()
    await bot.start_bot()

if __name__ == '__main__':
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
