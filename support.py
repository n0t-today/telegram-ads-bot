from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import database

# ——————————————————————————————————————————————————————————————
# РОУТЕР
# ——————————————————————————————————————————————————————————————

router = Router()

# ——————————————————————————————————————————————————————————————
# СОСТОЯНИЯ FSM
# ——————————————————————————————————————————————————————————————

class SupportStates(StatesGroup):
    waiting_for_question = State()


# ——————————————————————————————————————————————————————————————
# ОБРАБОТЧИКИ ПОДДЕРЖКИ
# ——————————————————————————————————————————————————————————————

@router.message(F.text == "❓ Помощь")
async def start_support(message: Message, state: FSMContext):
    """Начало обращения в поддержку"""
    await state.clear()  # Сбрасываем предыдущее состояние
    support_text = """<b>❓ Помощь и поддержка</b>

Если у вас возникли вопросы или проблемы, опишите их в следующем сообщении.

Администратор рассмотрит ваше обращение и свяжется с вами в ближайшее время.

<b>Примеры обращений:</b>
• Вопросы по размещению объявлений
• Технические проблемы
• Предложения по улучшению сервиса
• Жалобы и претензии"""
    
    await message.answer(support_text)
    await state.set_state(SupportStates.waiting_for_question)


@router.message(SupportStates.waiting_for_question)
async def receive_support_question(message: Message, state: FSMContext, bot: Bot):
    """Получение вопроса/обращения от пользователя"""
    question_text = message.text
    user = message.from_user
    
    # Сохранение обращения в БД
    request_id = await database.create_support_request(
        user_id=user.id,
        message=question_text
    )
    
    # Отправка обращения администраторам
    admin_text = f"""<b>❓ Новое обращение в поддержку #{request_id}</b>

<b>От:</b> {user.first_name}
<b>Username:</b> @{user.username if user.username else 'не указан'}
<b>User ID:</b> <code>{user.id}</code>

<b>Сообщение:</b>
{question_text}

<b>Для ответа:</b> Напишите пользователю напрямую через @{user.username if user.username else f'tg://user?id={user.id}'}"""
    
    # Отправляем сообщение каждому администратору
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception as e:
            # Если не удалось отправить админу, логируем ошибку
            print(f"Не удалось отправить сообщение админу {admin_id}: {e}")
    
    # Также отправляем в группу модерации, если она настроена
    if config.MODERATION_GROUP_ID:
        try:
            await bot.send_message(chat_id=config.MODERATION_GROUP_ID, text=admin_text)
        except Exception as e:
            print(f"Не удалось отправить в группу модерации: {e}")
    
    # Уведомление пользователя
    await message.answer(
        "<b>✅ Ваше обращение принято!</b>\n\n"
        "Администратор рассмотрит его и свяжется с вами в ближайшее время.\n"
        "Спасибо за обращение!"
    )
    
    await state.clear()

