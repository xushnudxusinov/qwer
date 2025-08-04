#!/usr/bin/env python3
"""
Sodda Telegram Media Yuklovchi Bot
"""

import os
import logging
import asyncio
import yt_dlp
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
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

# URL ni vaqtincha saqlash uchun
pending_downloads = {}

def is_valid_url(url):
    """URL ni tekshirish"""
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
    """Matndan URLlarni ajratib olish"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return [url for url in urls if is_valid_url(url)]

class SimpleMediaBot:
    def __init__(self):
        self.application = None
        self.downloads_dir = 'downloads'
        os.makedirs(self.downloads_dir, exist_ok=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start komandasi"""
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

  Buyruqlar:
/start - Botni boshlash
/help - Yordam

Boshlash uchun havola yuboring! 🚀
Muommo bo'lsa guruhga yozing: https://t.me/droptunee
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yordam komandasi"""
        help_text = """
🆘 Yordam - Botdan qanday foydalanish

  Asosiy foydalanish:
1. Qo'llab-quvvatlanadigan platformalardan havola yuboring
2. Video yoki audio formatini tanlang
3. Yuklab olish tugashini kuting
4. Faylingizni oling!

  Qo'llab-quvvatlanadigan platformalar:  
• YouTube (youtube.com, youtu.be)
• Instagram (instagram.com)
• TikTok (tiktok.com)
• Snapchat (snapchat.com)
• Twitter/X (twitter.com, x.com)
• Facebook (facebook.com)
• Vimeo (vimeo.com)

  Cheklovlar:
• Maksimal fayl hajmi: 50MB
• Maksimal video davomiyligi: 10 daqiqa
• Audio format: MP3 (192kbps)
• Video format: MP4

  Maslahatlar:
• Havolalar ochiq va mavjud bo'lishi kerak
• Shaxsiy kontent yuklab olinmaydi
• Ba'zi platformalarda cheklovlar bo'lishi mumkin

Ko'proq yordam kerakmi? Havola yuborib sinab ko'ring! 😊
        """
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Matnli xabarlarni qayta ishlash"""
        text = update.message.text
        urls = extract_urls_from_text(text)
        
        if not urls:
            await update.message.reply_text(
                "Iltimos, qo'llab-quvvatlanadigan platformalardan havola yuboring.\n\n"
                "Qo'llab-quvvatlanadigan: YouTube, Instagram, TikTok, Snapchat, Twitter/X, Facebook, Vimeo\n\n"
                "Qo'shimcha ma'lumot uchun /help yozing."
            )
            return
        
        url = urls[0]
        await self.show_format_selection(update, url)
    
    async def show_format_selection(self, update, url):
        """Format tanlash uchun tugmalarni ko'rsatish"""
        # URL ni global dictionary da saqlash
        user_id = update.effective_user.id
        pending_downloads[user_id] = url
        
        keyboard = [
            [
                InlineKeyboardButton("🎥 Video", callback_data="download_video"),
                InlineKeyboardButton("🎵 Audio/Qo'shiq", callback_data="download_audio")
            ],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📱 Havola aniqlandi!\n\n"
            "Qaysi formatda yuklab olishni xohlaysiz?",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update, context):
        """Inline tugmalar bosganida ishlaydigan funksiya"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        if data == "cancel":
            # URL ni tozalash
            if user_id in pending_downloads:
                del pending_downloads[user_id]
            await query.edit_message_text("❌ Yuklab olish bekor qilindi.")
            return
        
        if data in ["download_video", "download_audio"]:
            # Saqlangan URL ni olish
            if user_id not in pending_downloads:
                await query.edit_message_text("❌ URL topilmadi. Qaytadan urinib ko'ring.")
                return
            
            url = pending_downloads[user_id]
            is_audio = data == "download_audio"
            
            format_name = "Audio/Qo'shiq" if is_audio else "Video"
            format_emoji = "🎵" if is_audio else "🎥"
            
            await query.edit_message_text(
                f"{format_emoji} **{format_name} yuklanmoqda...**\n\n"
                f"Iltimos kuting, bu bir necha daqiqa vaqt olishi mumkin."
            )
            
            await self.download_media_with_format(query, url, is_audio)
            
            # URL ni tozalash
            if user_id in pending_downloads:
                del pending_downloads[user_id]
    
    async def download_media_with_format(self, query, url, is_audio=False):
        """Belgilangan formatda media yuklab olish"""
        try:
            # Audio uchun yt-dlp sozlamalari
            if is_audio:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': f'{self.downloads_dir}/%(title)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'ignoreerrors': True,
                    'no_warnings': True,
                }
            else:
                # Video uchun sozlamalar - fayl hajmi cheklovsiz
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': f'{self.downloads_dir}/%(title)s.%(ext)s',
                    'ignoreerrors': True,
                    'no_warnings': True,
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Video ma'lumotlarini olish
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    await query.edit_message_text("❌ Media ma'lumotlarini olishda xatolik. Havolani tekshiring.")
                    return
                
                title = info.get('title', 'Noma\'lum')
                duration = info.get('duration', 0)
                
                # Davomiylik cheklovini olib tashlaymiz
                
                # Yuklash
                format_name = "Audio/Qo'shiq" if is_audio else "Video"
                await query.edit_message_text(f"📥 '{title}' {format_name.lower()} sifatida yuklanmoqda...")
                ydl.download([url])
                
                # Yuklangan faylni topish
                filepath = self.find_downloaded_file(info, is_audio)
                
                if filepath and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    
                    # Fayl hajmi cheklovini olib tashlaymiz - Telegram 2GB gacha qabul qiladi
                    
                    # Faylni yuborish
                    await query.edit_message_text("📤 Fayl yuborilmoqda...")
                    
                    with open(filepath, 'rb') as media_file:
                        caption = f"✅ **{format_name} muvaffaqiyatli yuklandi!\n\n📁 Nom: {title}\n📊 Hajm: {file_size / 1024 / 1024:.1f}MB"
                        
                        if is_audio or filepath.endswith(('.mp3', '.m4a', '.wav', '.ogg')):
                            await query.message.reply_audio(
                                media_file,
                                caption=caption,
                                title=title
                            )
                        elif filepath.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                            await query.message.reply_video(
                                media_file,
                                caption=caption
                            )
                        else:
                            await query.message.reply_document(
                                media_file,
                                caption=caption
                            )
                    
                    await query.edit_message_text(f"✅ {format_name} muvaffaqiyatli yuborildi!")
                    
                    # Faylni o'chirish
                    os.remove(filepath)
                else:
                    await query.edit_message_text("❌ Yuklangan fayl topilmadi.")
                    
        except Exception as e:
            logger.error(f"Yuklab olishda xatolik: {e}")
            await query.edit_message_text("❌ Yuklab olishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
    
    async def download_media(self, update, url):
        """Media yuklab olish"""
        try:
            # Yuklanish xabarini yuborish
            status_msg = await update.message.reply_text("📥 Video yuklanmoqda... Iltimos kuting...")
            
            # yt-dlp sozlamalari - fayl hajmi cheklovsiz
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{self.downloads_dir}/%(title)s.%(ext)s',
                'ignoreerrors': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Video ma'lumotlarini olish
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    await status_msg.edit_text("❌ Video ma'lumotlarini olishda xatolik. Havolani tekshiring.")
                    return
                
                title = info.get('title', 'Noma\'lum')
                duration = info.get('duration', 0)
                
                # Davomiylik cheklovini olib tashlaymiz
                
                # Yuklash
                await status_msg.edit_text(f"📥 '{title}' yuklanmoqda...")
                ydl.download([url])
                
                # Yuklangan faylni topish
                filepath = self.find_downloaded_file(info)
                
                if filepath and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    
                    # Fayl hajmi cheklovini olib tashlaymiz - Telegram 2GB gacha qabul qiladi
                    
                    # Faylni yuborish
                    await status_msg.edit_text("📤 Fayl yuborilmoqda...")
                    
                    with open(filepath, 'rb') as video_file:
                        caption = f"✅ Muvaffaqiyatli yuklandi!\n\n📁 Nom: {title}\n📊 Hajm: {file_size / 1024 / 1024:.1f}MB"
                        
                        if filepath.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                            await update.message.reply_video(
                                video_file,
                                caption=caption
                            )
                        else:
                            await update.message.reply_document(
                                video_file,
                                caption=caption
                            )
                    
                    await status_msg.edit_text("✅ Fayl muvaffaqiyatli yuborildi!")
                    
                    # Faylni o'chirish
                    os.remove(filepath)
                else:
                    await status_msg.edit_text("❌ Yuklab olingan fayl topilmadi.")
                    
        except Exception as e:
            logger.error(f"Yuklab olishda xatolik: {e}")
            await update.message.reply_text("❌ Yuklab olishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
    
    def find_downloaded_file(self, info, is_audio=False):
        """Yuklangan faylni topish"""
        try:
            title = info.get('title', 'download')
            # Xavfsiz nom yaratish
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            
            # Audio yoki video kengaytmalari
            if is_audio:
                extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.aac']
            else:
                extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v']
            
            for ext in extensions:
                filepath = os.path.join(self.downloads_dir, f"{safe_title}{ext}")
                if os.path.exists(filepath):
                    return filepath
            
            # Agar topilmasa, eng oxirgi yuklangan faylni olish
            if os.path.exists(self.downloads_dir):
                files = [f for f in os.listdir(self.downloads_dir) 
                        if any(f.endswith(ext) for ext in extensions)]
                if files:
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(self.downloads_dir, x)), reverse=True)
                    return os.path.join(self.downloads_dir, files[0])
            
            return None
        except Exception as e:
            logger.error(f"Fayl topishda xatolik: {e}")
            return None
    
    async def start_bot(self):
        """Botni ishga tushirish"""
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlerlarni qo'shish
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("Bot ishga tushmoqda...")
        # Initialize va start
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        try:
            # Bot ishlashi uchun kutish
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Bot to'xtatilmoqda...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

async def main():
    """Asosiy funksiya"""
    bot = SimpleMediaBot()
    await bot.start_bot()

if __name__ == '__main__':
    try:
        # Event loop muammosini hal qilish
        import platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Bot ishlamay qoldi: {e}")
    finally:
        if 'loop' in locals():
            loop.close()
