import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from openai import AsyncOpenAI

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация клиентов
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

#контекст
# Формат: {user_id: [{"role": "user/assistant", "content": "text"}, ...]}
user_contexts = {}

# Системный промпт с базой знаний и защитой
SYSTEM_PROMPT = """
Ты — вежливый AI-ассистент компании «Центр Красок #1» (Казахстан). 
Твоя задача — консультировать клиентов ТОЛЬКО на основе предоставленной информации. 
Если пользователь спрашивает о чем-то, чего нет в тексте ниже, отвечай: "К сожалению, я не владею этой информацией. Пожалуйста, обратитесь по телефону +7 778 061 5000."
Не придумывай цены, не выдумывай услуги и вакансии, если они не указаны.

ИНФОРМАЦИЯ О КОМПАНИИ:
- Название: Центр Красок #1 (ТОО «SAMRUk Trade»). Основана в 2016 году.
- Деятельность: Продажа лакокрасочной продукции (краски, лаки, пропитки, грунтовки, декоративные штукатурки).
- Бренды: Более 20 мировых брендов (Dulux, Marshall, Hammerite, Pinotex, Orac Decor и др.).
- Услуги: Профессиональная колеровка (45 000+ оттенков), доставка, мастер-классы по нанесению штукатурки.
- Клиенты: Строительные компании, ремонтные бригады, дизайнеры, частные клиенты.
- Контакты и адреса: 
  1. г. Алматы, ул. Кабдолова 1/8. 
  2. г. Астана, ул. Мангилик Ел, 29/2. 
  График: Пн-Вс 10:00 - 20:00.
  Телефон: +7 778 061 5000. Email: info@centr-krasok.kz.

Отвечай кратко, доброжелательно, без сложного форматирования.
"""

def get_user_context(user_id: int) -> list:
    """Получает или создает контекст пользователя (сохраняем последние 10 сообщений)."""
    if user_id not in user_contexts:
        user_contexts[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return user_contexts[user_id]

def update_user_context(user_id: int, role: str, content: str):
    """Обновляет историю диалога, не давая ей бесконечно расти."""
    context = get_user_context(user_id)
    context.append({"role": role, "content": content})
    # Оставляем только системный промпт (индекс 0) и последние 10 сообщений
    if len(context) > 11:
        user_contexts[user_id] = [context[0]] + context[-10:]

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Скрытая обработка команды старт для начала диалога."""
    greeting = "Здравствуйте! Я AI-ассистент «Центр Красок #1». Чем могу вам помочь? Задайте любой вопрос о нашей компании."
    update_user_context(message.from_user.id, "assistant", greeting)
    await message.answer(greeting)

@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обработка всех текстовых сообщений (общение без команд)."""
    user_id = message.from_user.id
    user_text = message.text

    # Добавляем вопрос пользователя в контекст
    update_user_context(user_id, "user", user_text)
    
    # Отправляем статус "печатает..."
    await bot.send_chat_action(chat_id=user_id, action="typing")
    
    try:
        # Запрос к OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # Идеально для простых ответов
            messages=get_user_context(user_id),
            temperature=0.3,     # Низкая температура снижает риск галлюцинаций
            max_tokens=300
        )
        
        ai_reply = response.choices[0].message.content
        
        # Сохраняем ответ бота в контекст
        update_user_context(user_id, "assistant", ai_reply)
        
        # Отправляем ответ пользователю
        await message.answer(ai_reply)

    except Exception as e:
        await message.answer("Извините, произошла техническая ошибка при обработке запроса. Попробуйте чуть позже.")
        print(f"Error: {e}")

async def main():
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())