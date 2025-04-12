import os
import logging
import json
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates
from datetime import datetime

# --- Настройка логгера ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Константы ---
DEFAULT_MODEL = "openchat/openchat-3.5-0106"  # Бесплатная модель по умолчанию

# --- Инициализация БД ---
def init_db():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                         (user_id INTEGER PRIMARY KEY,
                          data TEXT,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
    finally:
        if conn:
            conn.close()

init_db()

# --- Работа с пользователями ---
def get_user(user_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования данных для user_id={user_id}")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def save_user(user_id, data):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO users (user_id, data) VALUES (?, ?)",
            (user_id, json.dumps(data))
        )
        conn.commit()
        logger.debug(f"Данные пользователя {user_id} сохранены")
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
    finally:
        if conn:
            conn.close()

# --- Токены и конфигурация ---
API_TOKEN = os.getenv("API_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

if not API_TOKEN:
    logger.critical("Не указан API_TOKEN")
    raise ValueError("❌ Токен бота не найден. Получите у @BotFather")

if not OPENROUTER_API_KEY:
    logger.critical("Не указан OPENROUTER_API_KEY")
    raise ValueError("❌ Ключ OpenRouter не найден. Зарегистрируйтесь на openrouter.ai")

# --- Инициализация бота ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- Клавиатуры ---
def start_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Начать"))

def confirm_keyboard():
    return InlineKeyboardMarkup().add(InlineKeyboardButton("Принять и продолжить", callback_data="accept_terms"))

def option_keyboard(options):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for opt in options:
        kb.add(KeyboardButton(opt))
    return kb

# --- Обработчики сообщений ---
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    try:
        await message.answer(
            "🚭 NoSmoke Coach — ваш помощник в отказе от курения\n\n"
            "✅ Принимая условия, вы соглашаетесь с [пользовательским соглашением](https://example.com).",
            reply_markup=start_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info(f"Пользователь {message.from_user.id} начал работу")
    except Exception as e:
        logger.error(f"Ошибка в send_welcome: {e}")

@dp.message_handler(lambda m: m.text == "Начать")
async def ask_terms(message: types.Message):
    try:
        await message.answer(
            "📄 Пожалуйста, ознакомьтесь с условиями:",
            reply_markup=confirm_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка в ask_terms: {e}")

@dp.callback_query_handler(lambda c: c.data == 'accept_terms')
async def accepted_terms(c: types.CallbackQuery):
    try:
        user_id = c.from_user.id
        user_data = {
            "день": 0,
            "дата_старта": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "статус": "начал опрос"
        }
        save_user(user_id, user_data)
        
        await bot.answer_callback_query(c.id)
        await bot.send_message(
            user_id, 
            "1️⃣ Как давно вы курите?", 
            reply_markup=option_keyboard(["Меньше года", "1–5 лет", "6–10 лет", "Больше 10 лет"])
        )
    except Exception as e:
        logger.error(f"Ошибка в accepted_terms: {e}")

@dp.message_handler(lambda m: m.text in ["Меньше года", "1–5 лет", "6–10 лет", "Больше 10 лет"])
async def ask_cigs(message: types.Message):
    try:
        user_id = message.from_user.id
        user_data = get_user(user_id) or {}
        user_data["стаж"] = message.text
        save_user(user_id, user_data)
        
        await message.answer(
            "2️⃣ Сколько сигарет в день вы курите?",
            reply_markup=option_keyboard(["1–9", "10–14", "15–19", "20 и больше"])
        )
    except Exception as e:
        logger.error(f"Ошибка в ask_cigs: {e}")

@dp.message_handler(lambda m: m.text in ["1–9", "10–14", "15–19", "20 и больше"])
async def ask_type(message: types.Message):
    try:
        user_id = message.from_user.id
        user_data = get_user(user_id) or {}
        
        if "и больше" in message.text:
            user_data["сигарет_в_день"] = 20
        else:
            user_data["сигарет_в_день"] = int(message.text.split("–")[0])
            
        save_user(user_id, user_data)
        await message.answer(
            "3️⃣ Что именно вы курите чаще всего?",
            reply_markup=option_keyboard(["Сигареты", "Вейп", "Айкос/стики", "Всё понемногу"])
        )
    except Exception as e:
        logger.error(f"Ошибка в ask_type: {e}")

@dp.message_handler(lambda m: m.text in ["Сигареты", "Вейп", "Айкос/стики", "Всё понемногу"])
async def ask_attempts(message: types.Message):
    try:
        user_id = message.from_user.id
        user_data = get_user(user_id) or {}
        user_data["тип"] = message.text
        save_user(user_id, user_data)
        
        await message.answer(
            "4️⃣ Сколько раз вы уже пытались бросить?",
            reply_markup=option_keyboard(["Ни разу", "1–2", "3–5", "Больше 5", "Бросал(а), но сорвался(ась)"])
        )
    except Exception as e:
        logger.error(f"Ошибка в ask_attempts: {e}")

@dp.message_handler(lambda m: m.text in ["Ни разу", "1–2", "3–5", "Больше 5", "Бросал(а), но сорвался(ась)"])
async def start_day_one(message: types.Message):
    try:
        user_id = message.from_user.id
        user_data = get_user(user_id) or {}
        user_data.update({
            "день": 1,
            "старт": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "не_выкурено": 0,
            "экономия": 0,
            "попытки": message.text
        })
        save_user(user_id, user_data)
        
        await message.answer("✅ Отлично! Первый день начинается!")
        await message.answer(
            "📅 День 1: Определение мотивации\n\n"
            "✍️ Запишите причины, по которым вы решили бросить курить.\n"
            "📘 Подсказка: нажмите SOS, если тяжело.",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
                KeyboardButton("🚨 SOS"),
                KeyboardButton("👥 Запись к психологу")
            )
    except Exception as e:
        logger.error(f"Ошибка в start_day_one: {e}")

@dp.message_handler(lambda m: m.text == "🚨 SOS")
async def sos_help(message: types.Message):
    try:
        await message.answer("🧠 Думаю над ответом...")
        logger.info(f"Запрос к OpenRouter от {message.from_user.id}, модель: {OPENROUTER_MODEL}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты психолог, помогающий бросить курить."},
                    {"role": "user", "content": "Мне хочется курить, что делать?"}
                ]
            }
            
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"OpenRouter error: {error}")
                    await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
                    return
                
                data = await resp.json()
                answer = data['choices'][0]['message']['content']
                await message.answer(f"👏 Ответ:\n{answer}")
                
    except Exception as e:
        logger.error(f"Ошибка в sos_help: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

# --- Запуск ---
if __name__ == '__main__':
    try:
        logger.info("Бот запускается...")
        executor.start_polling(dp, skip_updates=True)
    except TerminatedByOtherGetUpdates:
        logger.error("Ошибка: уже запущен другой экземпляр бота!")
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {e}")
