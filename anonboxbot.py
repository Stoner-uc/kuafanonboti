import telebot
from telebot import types
import sqlite3
import logging
import os
from datetime import datetime
import csv
import io
from dotenv import load_dotenv  # Yangi qo'shilgan qator

# Environment faylidan ma'lumotlarni yuklash
load_dotenv()

# Token va Admin ID environment variables dan olish
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(id_str.strip()) for id_str in os.getenv("ADMIN_ID", "").split(",") if id_str.strip()]

# Guruh ID(lar)i: bir nechta bo'lsa vergul bilan ajrating, masalan: -10012345,-10067890
GROUP_IDS = [int(id_str.strip()) for id_str in os.getenv("TELEGRAM_GROUP_ID", "").split(",") if id_str.strip()]

# Token mavjudligini tekshirish
if not API_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable topilmadi!")
    exit(1)
    
if not ADMIN_IDS:
    logging.error("ADMIN_ID environment variable topilmadi!")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Foydalanuvchi ma'lumotlari saqlanadigan lug'at
user_data = {}

# Loglashni yoqish
logging.basicConfig(level=logging.INFO)

# SQLite bazasini o'rnatish
def init_db():
    conn = sqlite3.connect("user_reports.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        name TEXT,
                        location TEXT,
                        details TEXT,
                        identity TEXT,
                        media_type TEXT,
                        media TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Til matnlari lug'ati
TEXTS = {
    "uz": {
        "help": "Botdan foydalanish uchun /start bosing.\nMa'lumotlaringiz sir saqlanadi.\nSavollar bo'lsa adminlarga murojaat qiling.",
        "welcome": "🛡 KUAF ichki nazorat botiga xush kelibsiz!\n\nESLATIB O'TAMIZ BU YERDAGI HAR QANDAY MA'LUMOT SIR SAQLANADI!\n\nBatafsil ma'lumot olishimiz uchun ISM VA FAMILIYANGIZNI kiriting!",
        "name_received": "📍 Xolat qayerda ro'y berdi! Batafsil (Bino bo'lsa xona raqami ham!):",
        "location_received": "📝 Xodisani to'liq yozib bering har bir detal yoki ishtirokchilargacha (Nima boldi?)",
        "identity_request": "🧾 KUAF uchun kim bo'lasiz! Pastdagi tugmalardan birini tanlang👇:",
        "media_request": "📷 Agar rasm yoki fayl yuklamoqchi bo'lsangiz yuboring:",
        "media_cancel": "❌ Bekor qilish",
        "success": "✅ Ma'lumotlaringiz adminlarga yuborildi!\n\nJarayon tugadi! ✅ Xabar yuborilgan!  /start",
        "wait": "Iltimos, biroz kuting...",
        "cancelled": "❌ Media yuklash bekor qilindi. Ma'lumotlaringiz saqlandi.",
        "identity_options": ["🎓 KUAF Talabasi", "👨‍🏫 KUAF Xodimi(asi)", "👤 Begona / talaba ota onasi"],
        "admin_welcome": "👨‍💻 Admin panelga xush kelibsiz!",
        "no_stats": "📭 Hali hech qanday hisobot yo'q",
        "db_cleared": "✅ Baza muvaffaqiyatli tozalandi!",
        "db_clean_cancelled": "❌ Baza tozalash bekor qilindi.",
        "cleanup_confirm": "⚠️ Bazani tozalashni xohlaysizmi?\nBarcha hisobotlar o'chib ketadi!",
        "back_to_main": "🏠 Asosiy menyu",
        "export_success": "📊 Barcha hisobotlar Excel fayliga yuklandi!",
        "export_empty": "📭 Eksport qilish uchun ma'lumot yo'q"
    },
    "ru": {
        "help": "Для использования бота нажмите /start.\nВаша информация конфиденциальна.\nЕсли есть вопросы, обратитесь к администраторам.",
        "welcome": "🛡 Добро пожаловать в бот внутреннего контроля KUAF!\n\nВАЖНО: ВСЯ ВАША ИНФОРМАЦИЯ БУДЕТ СТРОГО КОНФИДЕНЦИАЛЬНОЙ!\n\nПожалуйста, введите свое ИМЯ и ФАМИЛИЮ.",
        "name_received": "📍 Где произошло происшествие? Укажите подробно (если здание – номер комнаты):",
        "location_received": "📝 Опишите происшествие подробно, включая все детали и участников (Что произошло?)",
        "identity_request": "🧾 Кем вы являетесь для KUAF? Выберите вариант ниже👇:",
        "media_request": "📷 Если хотите загрузить фото или файл, отправьте:",
        "media_cancel": "❌ Отмена",
        "success": "✅ Ваша информация отправлена администраторам!\n\nПроцесс завершен! ✅ Сообщение отправлено! /start",
        "wait": "Пожалуйста, подождите немного...",
        "cancelled": "❌ Загрузка медиа отменена. Ваша информация сохранена.",
        "identity_options": ["🎓 Студент KUAF", "👨‍🏫 Сотрудник KUAF", "👤 Родитель студента / посторонний"],
        "admin_welcome": "👨‍💻 Добро пожаловать в админ-панель!",
        "no_stats": "📭 Пока нет отчетов",
        "db_cleared": "✅ База данных успешно очищена!",
        "db_clean_cancelled": "❌ Очистка базы данных отменена.",
        "cleanup_confirm": "⚠️ Вы уверены, что хотите очистить базу данных?\nВсе отчеты будут удалены!",
        "back_to_main": "🏠 Главное меню",
        "export_success": "📊 Все отчеты загружены в Excel файл!",
        "export_empty": "📭 Нет данных для экспорта"
    },
    "en": {
        "help": "Press /start to use the bot.\nYour information is confidential.\nIf you have questions, contact the administrators.",
        "welcome": "🛡 Welcome to the KUAF internal control bot!\n\nIMPORTANT: ALL YOUR INFORMATION WILL BE STRICTLY CONFIDENTIAL!\n\nPlease enter your FIRST and LAST NAME.",
        "name_received": "📍 Where did the incident happen? Please specify in detail (if building – room number):",
        "location_received": "📝 Describe the incident in detail, including all details and participants (What happened?)",
        "identity_request": "🧾 Who are you for KUAF? Choose one option below👇:",
        "media_request": "📷 If you want to upload a photo or file, send it:",
        "media_cancel": "❌ Cancel",
        "success": "✅ Your information has been sent to administrators!\n\nProcess completed! ✅ Message sent!  /start",
        "wait": "Please wait a bit...",
        "cancelled": "❌ Media upload cancelled. Your information has been saved.",
        "identity_options": ["🎓 KUAF Student", "👨‍🏫 KUAF Staff", "👤 Parent / outsider"],
        "admin_welcome": "👨‍💻 Welcome to admin panel!",
        "no_stats": "📭 No reports yet",
        "db_cleared": "✅ Database cleared successfully!",
        "db_clean_cancelled": "❌ Database cleanup cancelled.",
        "cleanup_confirm": "⚠️ Are you sure you want to clear the database?\nAll reports will be deleted!",
        "back_to_main": "🏠 Main menu",
        "export_success": "📊 All reports loaded to Excel file!",
        "export_empty": "📭 No data for export"
    }
}

# -------------------- ADMIN PANEL --------------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Sizda ruxsat yo'q")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📊 Statistika"),
        types.KeyboardButton("👥 Foydalanuvchilar"),
        types.KeyboardButton("📋 Oxirgi hisobotlar"),
        types.KeyboardButton("📤 Excelga yuklash"),
        types.KeyboardButton("🗑️ Bazani tozalash"),
        types.KeyboardButton("🔙 Orqaga")
    )
    bot.send_message(message.chat.id, "👨‍💻 Admin panelga xush kelibsiz!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📊 Statistika")
def show_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect("user_reports.db")
    cursor = conn.cursor()
    
    # Umumiy statistika
    cursor.execute("SELECT COUNT(*) FROM reports")
    total_reports = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reports WHERE date(timestamp) = date('now')")
    today_reports = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT chat_id) FROM reports")
    total_users = cursor.fetchone()[0]
    
    # Haftalik statistika
    cursor.execute("SELECT COUNT(*) FROM reports WHERE timestamp >= date('now', '-7 days')")
    weekly_reports = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (f"📊 Bot statistikasi:\n\n"
                 f"🔢 Jami hisobotlar: {total_reports}\n"
                 f"📅 Bugungi hisobotlar: {today_reports}\n"
                 f"📈 Haftalik hisobotlar: {weekly_reports}\n"
                 f"👥 Jami foydalanuvchilar: {total_users}\n"
                 f"🕐 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(func=lambda message: message.text == "👥 Foydalanuvchilar")
def show_users(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect("user_reports.db")
    cursor = conn.cursor()
    
    cursor.execute('''SELECT chat_id, COUNT(*) as report_count 
                      FROM reports GROUP BY chat_id ORDER BY report_count DESC LIMIT 20''')
    top_users = cursor.fetchall()
    
    conn.close()
    
    if not top_users:
        bot.send_message(message.chat.id, "📭 Hali hech qanday foydalanuvchi yo'q")
        return
    
    users_text = "👥 Eng faol foydalanuvchilar:\n\n"
    for i, (chat_id, count) in enumerate(top_users, 1):
        users_text += f"{i}. ID: {chat_id} - {count} hisobot\n"
    
    bot.send_message(message.chat.id, users_text)

@bot.message_handler(func=lambda message: message.text == "📋 Oxirgi hisobotlar")
def show_recent_reports(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect("user_reports.db")
    cursor = conn.cursor()
    
    cursor.execute('''SELECT name, location, details, identity, timestamp 
                      FROM reports ORDER BY timestamp DESC LIMIT 10''')
    recent_reports = cursor.fetchall()
    
    conn.close()
    
    if not recent_reports:
        bot.send_message(message.chat.id, "📭 Hali hech qanday hisobot yo'q")
        return
    
    reports_text = "📋 Oxirgi 10 ta hisobot:\n\n"
    for i, (name, location, details, identity, timestamp) in enumerate(recent_reports, 1):
        try:
            time_str = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        except Exception:
            time_str = timestamp
        reports_text += f"{i}. 👤 {name} - {identity}\n📍 {location}\n📝 {details[:50]}...\n🕐 {time_str}\n\n"
    
    bot.send_message(message.chat.id, reports_text)

@bot.message_handler(func=lambda message: message.text == "📤 Excelga yuklash")
def export_to_excel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect("user_reports.db")
    cursor = conn.cursor()
    
    cursor.execute('''SELECT name, location, details, identity, timestamp 
                      FROM reports ORDER BY timestamp DESC''')
    all_reports = cursor.fetchall()
    
    conn.close()
    
    if not all_reports:
        bot.send_message(message.chat.id, "📭 Eksport qilish uchun ma'lumot yo'q")
        return
    
    # CSV fayl yaratish
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Sarlavha qatorini yozish
    writer.writerow(['Ism', 'Manzil', 'Tafsilotlar', 'Kimlik', 'Vaqt'])
    
    # Ma'lumotlarni yozish
    for report in all_reports:
        writer.writerow(report)
    
    # CSV ma'lumotini olish va faylga yuborish
    csv_data = output.getvalue().encode('utf-8')
    output.close()
    
    # Foydalanuvchiga fayl yuborish
    bot.send_document(message.chat.id, 
                     ('hisobotlar.csv', io.BytesIO(csv_data)),
                     caption="📊 Barcha hisobotlar")

@bot.message_handler(func=lambda message: message.text == "🗑️ Bazani tozalash")
def cleanup_database(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Ha", callback_data="cleanup_confirm"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data="cleanup_cancel")
    )
    
    bot.send_message(message.chat.id, "⚠️ Bazani tozalashni xohlaysizmi?\nBarcha hisobotlar o'chib ketadi!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cleanup_"))
def handle_cleanup(call):
    if call.data == "cleanup_confirm":
        conn = sqlite3.connect("user_reports.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reports")
        conn.commit()
        conn.close()
        
        bot.send_message(call.message.chat.id, "✅ Baza muvaffaqiyatli tozalandi!")
    else:
        bot.send_message(call.message.chat.id, "❌ Baza tozalash bekor qilindi.")
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.text == "🔙 Orqaga")
def back_to_main(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    remove_markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "🏠 Asosiy menyu", reply_markup=remove_markup)

# -------------------- HELP --------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    chat_id = message.chat.id
    lang = user_data.get(chat_id, {}).get('lang', 'uz')
    bot.send_message(chat_id, TEXTS[lang]["help"])

# -------------------- TIL TANLASH --------------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    bot.clear_step_handler_by_chat_id(chat_id)
    user_data[chat_id] = {}
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz"),
        types.InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    bot.send_message(chat_id, "🌐 Tilni tanlang / Выберите язык / Choose language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_language(call):
    chat_id = call.message.chat.id
    lang = call.data.split("_")[1]
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['lang'] = lang
    bot.send_message(chat_id, TEXTS[lang]["welcome"])
    bot.register_next_step_handler(call.message, get_name)

# -------------------- ISM / ФИО / NAME --------------------
def get_name(message):
    chat_id = message.chat.id
    if message.text == "/start":
        return start(message)
    if chat_id not in user_data:
        return start(message)
    user_data[chat_id]['name'] = message.text
    lang = user_data[chat_id]['lang']
    bot.send_message(chat_id, TEXTS[lang]["name_received"])
    bot.register_next_step_handler(message, get_location)

# -------------------- JOY / МЕСТО / LOCATION --------------------
def get_location(message):
    chat_id = message.chat.id
    if message.text == "/start":
        return start(message)
    if chat_id not in user_data:
        return start(message)
    user_data[chat_id]['location'] = message.text
    lang = user_data[chat_id]['lang']
    bot.send_message(chat_id, TEXTS[lang]["location_received"])
    bot.register_next_step_handler(message, get_event_details)

# -------------------- VOQEA / ПРОИСШЕСТВИЕ / EVENT --------------------
def get_event_details(message):
    chat_id = message.chat.id
    if message.text == "/start":
        return start(message)
    if chat_id not in user_data:
        return start(message)
    user_data[chat_id]['details'] = message.text
    lang = user_data[chat_id]['lang']
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for option in TEXTS[lang]["identity_options"]:
        markup.add(types.KeyboardButton(option))
        
    bot.send_message(chat_id, TEXTS[lang]["identity_request"], reply_markup=markup)
    bot.register_next_step_handler(message, process_identity)

# -------------------- KIMLIKNI QAYTA ISHLOV --------------------
def process_identity(message):
    chat_id = message.chat.id
    if message.text == "/start":
        return start(message)
    if chat_id not in user_data:
        return start(message)
    
    user_data[chat_id]['identity'] = message.text
    lang = user_data[chat_id]['lang']
    
    # Media so'rash va Bekor qilish tugmasi
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(TEXTS[lang]["media_cancel"], callback_data="media_cancel"))
    
    bot.send_message(chat_id, TEXTS[lang]["media_request"], reply_markup=markup)
    bot.register_next_step_handler(message, get_media)

# -------------------- MEDIA BEKOR QILISH --------------------
@bot.callback_query_handler(func=lambda call: call.data == "media_cancel")
def cancel_media(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        return
    
    lang = user_data[chat_id]['lang']
    
    user_data[chat_id]['media_type'] = 'none'
    user_data[chat_id]['media'] = 'none'
    
    bot.send_message(chat_id, TEXTS[lang]["cancelled"])
    save_to_db(chat_id)

# -------------------- MEDIA QABUL QILISH --------------------
def get_media(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return start(message)
    
    lang = user_data[chat_id]['lang']
    
    # Media mavjudligini tekshirish
    if message.content_type == 'photo':
        user_data[chat_id]['media_type'] = 'photo'
        user_data[chat_id]['media'] = message.photo[-1].file_id
    elif message.content_type == 'document':
        user_data[chat_id]['media_type'] = 'document'
        user_data[chat_id]['media'] = message.document.file_id
    elif message.content_type == 'audio':
        user_data[chat_id]['media_type'] = 'audio'
        user_data[chat_id]['media'] = message.audio.file_id
    elif message.content_type == 'video':
        user_data[chat_id]['media_type'] = 'video'
        user_data[chat_id]['media'] = message.video.file_id
    else:
        user_data[chat_id]['media_type'] = 'text'
        user_data[chat_id]['media'] = message.text if message.text else 'none'
    
    save_to_db(chat_id)

def save_to_db(chat_id):
    if chat_id not in user_data:
        return
    
    # Ma'lumotlarni bazaga qo'shish
    conn = sqlite3.connect("user_reports.db", check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''INSERT INTO reports (chat_id, name, location, details, identity, media_type, media)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (chat_id, 
                       user_data[chat_id].get('name', ''),
                       user_data[chat_id].get('location', ''),
                       user_data[chat_id].get('details', ''),
                       user_data[chat_id].get('identity', ''),
                       user_data[chat_id].get('media_type', 'none'),
                       user_data[chat_id].get('media', 'none')))
        
        conn.commit()
        
        # Adminlarga xabar yuborish
        lang = user_data[chat_id].get('lang', 'uz')
        report_text = f"🆕 Yangi hisobot:\n\n👤 Ism: {user_data[chat_id].get('name', '')}\n"
        report_text += f"🧾 Kim: {user_data[chat_id].get('identity', '')}\n"
        report_text += f"📍 Manzil: {user_data[chat_id].get('location', '')}\n"
        report_text += f"📝 Tafsilot: {user_data[chat_id].get('details', '')}\n"
        report_text += f"🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        media_type = user_data[chat_id].get('media_type', 'none')
        media_id = user_data[chat_id].get('media', 'none')
        
        for admin_id in ADMIN_IDS:
            try:
                if media_type == 'photo':
                    bot.send_photo(admin_id, media_id, caption=report_text)
                elif media_type == 'document':
                    bot.send_document(admin_id, media_id, caption=report_text)
                elif media_type == 'audio':
                    bot.send_audio(admin_id, media_id, caption=report_text)
                elif media_type == 'video':
                    bot.send_video(admin_id, media_id, caption=report_text)
                else:
                    bot.send_message(admin_id, report_text)
            except Exception as e:
                logging.error(f"Adminga yuborishda xatolik ({admin_id}): {e}")
        
        # Guruhlarga yuborish (agar .env ga TELEGRAM_GROUP_ID qo'shilgan bo'lsa)
        if GROUP_IDS:
            for group_id in GROUP_IDS:
                try:
                    if media_type == 'photo':
                        bot.send_photo(group_id, media_id, caption=report_text)
                    elif media_type == 'document':
                        bot.send_document(group_id, media_id, caption=report_text)
                    elif media_type == 'audio':
                        bot.send_audio(group_id, media_id, caption=report_text)
                    elif media_type == 'video':
                        bot.send_video(group_id, media_id, caption=report_text)
                    else:
                        bot.send_message(group_id, report_text)
                except Exception as e:
                    logging.error(f"Guruhga yuborishda xatolik ({group_id}): {e}")
        
        # Foydalanuvchiga tasdiqlash xabari
        bot.send_message(chat_id, TEXTS[lang]["success"])
        
    except Exception as e:
        logging.error(f"Database error: {e}")
        bot.send_message(chat_id, "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    finally:
        conn.close()
        # Foydalanuvchi ma'lumotlarini tozalash
        user_data.pop(chat_id, None)

# Botni ishga tushurish
if __name__ == "__main__":
    logging.info("Bot started...")
    bot.infinity_polling()
