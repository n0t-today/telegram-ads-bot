import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import database
from free_ads import router as free_ads_router
from paid_ads import router as paid_ads_router
from support import router as support_router
from moderation import router as moderation_router

# ——————————————————————————————————————————————————————————————
# ЛОГИРОВАНИЕ
# ——————————————————————————————————————————————————————————————

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————————————
# ИНИЦИАЛИЗАЦИЯ БОТА
# ——————————————————————————————————————————————————————————————

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ——————————————————————————————————————————————————————————————
# КЛАВИАТУРЫ
# ——————————————————————————————————————————————————————————————

def get_main_menu():
    """Создание главного меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Разместить объявление бесплатно")],
            [KeyboardButton(text="💎 Разместить объявление платно")],
            [KeyboardButton(text="📣 Рекламный канал")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


# ——————————————————————————————————————————————————————————————
# ОБРАБОТЧИКИ КОМАНД
# ——————————————————————————————————————————————————————————————

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    
    # Добавляем пользователя в БД
    await database.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Формируем приветственное сообщение
    welcome_text = f"""<b>👋 Добро пожаловать, {user.first_name}!</b>

Этот бот поможет вам разместить объявления быстро и удобно.

<b>📌 Рекомендуем подписаться на наши каналы:</b>
"""
    
    # Добавляем ссылки на рекомендуемые каналы
    for channel in config.RECOMMENDED_CHANNELS:
        welcome_text += f"• <a href='{channel['link']}'>{channel['name']}</a>\n"
    
    welcome_text += "\n<b>Выберите действие из меню ниже:</b>"
    
    await message.answer(welcome_text, reply_markup=get_main_menu())


@dp.message(F.text == "📣 Рекламный канал")
async def show_ad_channel(message: Message, state: FSMContext):
    """Показать ссылку на рекламный канал"""
    await state.clear()  # Сбрасываем состояние FSM
    await message.answer(
        f"<b>📣 Канал с новыми коллекциями:</b>\n\n{config.AD_CHANNEL_LINK}",
        reply_markup=get_main_menu()
    )


# ——————————————————————————————————————————————————————————————
# ЗАПУСК БОТА
# ——————————————————————————————————————————————————————————————

async def main():
    """Главная функция для запуска бота"""
    # Инициализация базы данных
    await database.init_db()
    logger.info("База данных инициализирована")
    
    # Подключение роутеров
    dp.include_router(free_ads_router)
    dp.include_router(paid_ads_router)
    dp.include_router(support_router)
    dp.include_router(moderation_router)
    
    # Запуск polling
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")

