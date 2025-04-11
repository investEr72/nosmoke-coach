import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime

# --- Logging ---
logging.basicConfig(level=logging.INFO)

# --- Tokens ---
API_TOKEN = os.getenv("API_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Не указаны переменные окружения API_TOKEN или OPENROUTER_API_KEY")

# --- Bot ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
user_data = {}

# --- Keyboards ---
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Начать"))
    return kb

def confirm_keyboard():
    ikb = InlineKeyboardMarkup()
    ikb.add(InlineKeyboardButton("Принять и продолжить", callback_data="accept_terms"))
    return ikb

def option_keyboard(options):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for opt in options:
        kb.add(KeyboardButton(opt))
    return kb

# --- Handlers ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer(
        "Что умеет этот бот?\n"
        "NoSmoke Coach — умный помощник на пути к свободе от курения.\n\n"
        "🧠 Научный подход (CBT, мотивация, дыхание)\n"
        "🧩 Программа 45 дней с заданиями\n"
        "🤖 ИИ-помощник 24/7\n"
        "🚨 Кнопка SOS\n"
        "🪞 Рефлексия и осознанность\n"
        "📊 Учёт прогресса\n"
        "⏱️ Всего 10–15 мин в день (меньше, чем на сигареты)\n"
        "🎁 Бонус: запись к психологу 20 мин (1000₽ / $10)\n\n"
        "💬 После нажатия /start\n"
        "📅 Первые 7 дней — бесплатно, затем 1790₽ или 17,9 USDT (разово)\n\n"
        "✅ Отвечая на вопросы и начиная первый день, вы принимаете условия [пользовательского соглашения](https://drive.google.com/file/d/1BNAdSPYoec5faELaqt5gNYVdCoUy93k7/view?usp=sharing).",
        reply_markup=start_keyboard(),
        parse_mode="Markdown"
    )

@dp.message_handler(lambda m: m.text == "Начать")
async def ask_terms(message: types.Message):
    await message.answer(
        "📄 Прежде чем начать, ознакомьтесь с условиями.\n\n"
        "Вы соглашаетесь с [пользовательским соглашением](https://drive.google.com/file/d/1BNAdSPYoec5faELaqt5gNYVdCoUy93k7/view?usp=sharing).",
        reply_markup=confirm_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == 'accept_terms')
async def accepted_terms(c: types.CallbackQuery):
    user_id = c.from_user.id
    user_data[user_id] = {"день": 0, "дата_старта": datetime.now()}
    await bot.answer_callback_query(c.id)
    await bot.send_message(user_id, "1️⃣ Как давно вы курите?", reply_markup=option_keyboard([
        "Меньше года", "1–5 лет", "6–10 лет", "Больше 10 лет"
    ]))

@dp.message_handler(lambda m: m.text in ["Меньше года", "1–5 лет", "6–10 лет", "Больше 10 лет"])
async def ask_cigs(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['стаж'] = message.text
    await message.answer("2️⃣ Сколько сигарет в день вы курите?", reply_markup=option_keyboard([
        "1–9", "10–14", "15–19", "20 и больше"
    ]))

@dp.message_handler(lambda m: m.text in ["1–9", "10–14", "15–19", "20 и больше"])
async def ask_type(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['кол-во'] = message.text
    try:
        user_data[user_id]['сигарет_в_день'] = int(message.text.split("–")[0])
    except Exception:
        user_data[user_id]['сигарет_в_день'] = 20
    await message.answer("3️⃣ Что именно вы курите чаще всего?", reply_markup=option_keyboard([
        "Сигареты", "Вейп", "Айкос / стики", "Всё понемногу"
    ]))

@dp.message_handler(lambda m: m.text in ["Сигареты", "Вейп", "Айкос / стики", "Всё понемногу"])
async def ask_attempts(message: types.Message):
    user_data[message.from_user.id]['тип'] = message.text
    await message.answer("4️⃣ Сколько раз вы уже пытались бросить?", reply_markup=option_keyboard([
        "Ни разу", "1–2", "3–5", "Больше 5", "Бросал(а), но сорвался(ась)"
    ]))

@dp.message_handler(lambda m: m.text in ["Ни разу", "1–2", "3–5", "Больше 5", "Бросал(а), но сорвался(ась)"])
async def start_day_one(message: types.Message):
    user_data[message.from_user.id]['попытки'] = message.text
    user_data[message.from_user.id].update({
        'день': 1, 'старт': datetime.now(), 'не_выкурено': 0, 'экономия': 0
    })
    await message.answer("✅ Отлично! Первый день начинается!")
    await message.answer(
        "📅 День 1: Определение мотивации\n\n"
        "✍️ Запишите причины, по которым вы решили бросить курить.\n"
        "Это активирует внутреннюю мотивацию и помогает выдержать первые дни.\n\n"
        "📘 Подсказка: нажмите SOS, если тяжело.",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("🚨 SOS"),
            KeyboardButton("👥 Записаться к психологу")
        )
    )

import aiohttp  # добавь в начало файла, если ещё не добавил

@dp.message_handler(lambda m: m.text == "🚨 SOS")
async def sos_help(message: types.Message):
    await message.answer("🧠 Думаю над ответом...")
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openchat/openchat-3.5",  # ✅ бесплатная модель
                "messages": [
                    {"role": "system", "content": "Ты доброжелательный психолог, помогающий бросить курить."},
                    {"role": "user", "content": "Мне хочется курить, что делать?"}
                ]
            }
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as resp:
                data = await resp.json()

                if 'choices' in data and len(data['choices']) > 0:
                    answer = data['choices'][0]['message']['content']
                    await message.answer(f"👏 Ответ:\n{answer}")
                else:
                    await message.answer(f"⚠️ Ошибка OpenRouter:\n{data.get('error', 'Ответ пустой или не содержит поля choices')}")

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")

if __name__ == '__main__':
    logging.info("Бот запускается...")
    executor.start_polling(dp, skip_updates=True)

