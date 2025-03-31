import telebot
from telebot import types
from geopy.distance import geodesic
import sqlite3
import os

TOKEN = '7724168947:AAFzRrJxS6MqZeGFiDgbGylarYgFP2s4v3M'
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    language TEXT,
    locations TEXT
)''')
conn.commit()

locations = {
    "Несвижский замок": (53.2225, 26.6917),
    "Мирский замок": (53.4513, 26.4727),
    "Далянь-бомжань": (39.084631,122.028821),
    "Далянь-бомжань 2": (38.885634,121.546385)
}

def get_title(count):
    if count >= 31:
        return "👑 Великий Путешественник"
    elif count >= 16:
        return "⚔️ Рыцарь Беларуси"
    elif count >= 6:
        return "📺 Искатель Приключений"
    elif count >= 1:
        return "🌱 Юный Путешественник"
    return "🙈 Без титула"

def get_lang(user_id):
    with sqlite3.connect('users.db') as temp_conn:
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        row = temp_cursor.fetchone()
        return row[0] if row and row[0] else 'ru'

def get_main_markup(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == 'ru':
        markup.row('🧭 Отметиться', '🏅 Мои достижения')
        markup.row('👤 Аккаунт', 'ℹ️ О проекте')
        markup.row('📜 Карта', '❤️ Поддержать')
    elif lang == 'be':
        markup.row('🧭 Адзначыцца', '🏅 Мае дасягненні')
        markup.row('👤 Акаўнт', 'ℹ️ Аб праекце')
        markup.row('📜 Карта', '❤️ Падтрымаць')
    else:
        markup.row('🧭 Mark Location', '🏅 Achievements')
        markup.row('👤 Account', 'ℹ️ About')
        markup.row('📜 Map', '❤️ Support')
    return markup

def process_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, language, locations) VALUES (?, ?, ?, ?)",
                   (user_id, name, 'ru', ''))
    conn.commit()
    lang = get_lang(user_id)
    bot.send_message(user_id, f"Приятно познакомиться, {name}!", reply_markup=get_main_markup(lang))

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        bot.send_message(user_id, "Добро пожаловать! Введите ваше имя для начала:")
        bot.register_next_step_handler(message, process_name)
    else:
        name = row[0]
        bot.send_message(user_id, f"Приятно снова видеть тебя, {name}!", reply_markup=get_main_markup(lang))

@bot.message_handler(func=lambda m: 'Аккаунт' in m.text or 'Акаўнт' in m.text or 'Account' in m.text)
def account(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    cursor.execute("SELECT username, locations FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        name, locs = row
        visited = locs.split(',') if locs else []
        count = len(visited)
        title = get_title(count)
        bot.send_message(user_id, f"👤 Имя: {name}\n🏰 Посещено: {count}\n🛡 Титул: {title}", reply_markup=get_main_markup(lang))

@bot.message_handler(func=lambda m: 'Карта' in m.text or 'Map' in m.text)
def show_map(message):
    user_id = message.from_user.id
    map_path = os.path.join(os.path.dirname(__file__), 'map.jpg')
    with open(map_path, "rb") as img:
        bot.send_photo(user_id, img, caption="📜 Все достопримечательности нашего квеста собраны на этой карте.")

@bot.message_handler(func=lambda m: 'Отметиться' in m.text or 'Адзначыцца' in m.text or 'Mark Location' in m.text)
def mark_location(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Отправить местоположение", request_location=True))
    bot.send_message(user_id, "Отправьте своё местоположение:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def location_handler(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    user_coords = (message.location.latitude, message.location.longitude)
    matched = None
    for name, coord in locations.items():
        if geodesic(user_coords, coord).meters <= 1000:
            matched = name
            break

    cursor.execute("SELECT locations FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    visited = row[0].split(',') if row and row[0] else []

    if matched:
        if matched not in visited:
            visited.append(matched)
            cursor.execute("UPDATE users SET locations=? WHERE user_id=?", (','.join(visited), user_id))
            conn.commit()
            bot.send_message(user_id, f"🏰 Вы успешно отметились: {matched}!\nВсего посещено: {len(visited)}", reply_markup=get_main_markup(lang))
        else:
            bot.send_message(user_id, f"📍 Вы уже были в: {matched}.", reply_markup=get_main_markup(lang))
    else:
        bot.send_message(user_id, "❌ Вы не находитесь рядом с известной точкой квеста.", reply_markup=get_main_markup(lang))

@bot.message_handler(func=lambda m: 'Мои достижения' in m.text or 'Achievements' in m.text)
def achievements(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    cursor.execute("SELECT username, locations FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        name, loc_str = row
        visited = loc_str.split(',') if loc_str else []
        count = len(visited)
        title = get_title(count)
        bot.send_message(user_id, f"🧭 Уже многое пройдено, {name}, но самое интересное только впереди!\n\n🏰 Посещено: {count}\n🛡 Титул: {title}", reply_markup=get_main_markup(lang))

@bot.message_handler(func=lambda m: 'О проекте' in m.text or 'About' in m.text)
def about(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    bot.send_message(user_id, "VANDER- это туристический Квест по Беларуси. Отправляйся в приключение по замкам, костелам и природным чудесам страны.\n\n🌐 Сайт проекта: https://vandrounik.by\n🛒 Купить Пашпарт вандроўнік па Беларусі: https://wildberries.by/item", reply_markup=get_main_markup(lang))

@bot.message_handler(func=lambda m: 'Поддержать' in m.text or 'Support' in m.text)
def support(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    bot.send_message(user_id, "Вы можете поддержать проект здесь: https://boosty.to/vander", reply_markup=get_main_markup(lang))

bot.polling(none_stop=True)
