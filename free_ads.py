from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from collections import defaultdict

import config
import database

# ——————————————————————————————————————————————————————————————
# РОУТЕР
# ——————————————————————————————————————————————————————————————

router = Router()

# ——————————————————————————————————————————————————————————————
# СОСТОЯНИЯ FSM
# ——————————————————————————————————————————————————————————————

class FreeAdStates(StatesGroup):
    waiting_for_ad = State()


# Временное хранилище для медиагрупп
media_groups = defaultdict(list)


# ——————————————————————————————————————————————————————————————
# ОБРАБОТЧИКИ БЕСПЛАТНЫХ ОБЪЯВЛЕНИЙ
# ——————————————————————————————————————————————————————————————

@router.message(F.text == "📢 Разместить объявление бесплатно")
async def start_free_ad(message: Message, state: FSMContext):
    """Начало создания бесплатного объявления"""
    template_text = f"""<b>📢 Бесплатное объявление</b>

Отправьте ваше объявление в том виде, в котором оно должно быть опубликовано:

<b>Варианты:</b>
• Просто текст (до {config.FREE_AD_LIMIT} символов)
• Несколько фото (до {config.MAX_IMAGES}) с подписью


Объявление пройдет модерацию и будет опубликовано после одобрения."""
    
    await message.answer(template_text)
    await state.set_state(FreeAdStates.waiting_for_ad)


@router.message(FreeAdStates.waiting_for_ad, F.text)
async def receive_free_ad_text(message: Message, state: FSMContext, bot: Bot):
    """Получение текстового объявления"""
    ad_text = message.text
    
    # Проверка лимита символов
    if len(ad_text) > config.FREE_AD_LIMIT:
        await message.answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Ваше объявление содержит {len(ad_text)} символов, "
            f"но лимит для бесплатных объявлений — {config.FREE_AD_LIMIT} символов.\n\n"
            f"Пожалуйста, сократите текст и отправьте снова."
        )
        return
    
    # Отправляем на модерацию
    await process_free_ad(message, state, bot, ad_text, None)


@router.message(FreeAdStates.waiting_for_ad, F.photo)
async def receive_free_ad_photo(message: Message, state: FSMContext, bot: Bot):
    """Получение объявления с фото"""
    
    # Проверяем, это медиагруппа или одиночное фото
    if message.media_group_id:
        # Это часть медиагруппы
        media_groups[message.media_group_id].append(message)
        
        # Ждем немного, чтобы собрать все фото из группы
        import asyncio
        await asyncio.sleep(0.5)
        
        # Проверяем, все ли фото собраны (если больше не приходят)
        group = media_groups[message.media_group_id]
        
        # Берем последнее сообщение из группы для обработки
        if message == group[-1]:
            # Это последнее фото в группе
            await process_media_group_free_ad(group, state, bot)
            del media_groups[message.media_group_id]
    else:
        # Одиночное фото
        ad_text = message.caption or ""
        
        # Проверка лимита символов
        if len(ad_text) > config.FREE_AD_LIMIT:
            await message.answer(
                f"<b>❌ Ошибка!</b>\n\n"
                f"Подпись содержит {len(ad_text)} символов, "
                f"но лимит — {config.FREE_AD_LIMIT} символов.\n\n"
                f"Пожалуйста, сократите текст и отправьте снова."
            )
            return
        
        # Получаем file_id
        photo_file_id = message.photo[-1].file_id
        
        # Отправляем на модерацию
        await process_free_ad(message, state, bot, ad_text, [photo_file_id])


async def process_media_group_free_ad(messages: list, state: FSMContext, bot: Bot):
    """Обработка медиагруппы для бесплатного объявления"""
    # Берем подпись из первого сообщения
    ad_text = messages[0].caption or ""
    
    # Проверка лимита символов
    if len(ad_text) > config.FREE_AD_LIMIT:
        await messages[-1].answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Подпись содержит {len(ad_text)} символов, "
            f"но лимит — {config.FREE_AD_LIMIT} символов.\n\n"
            f"Пожалуйста, сократите текст и отправьте снова."
        )
        return
    
    # Проверка количества фото
    if len(messages) > config.MAX_IMAGES:
        await messages[-1].answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Вы отправили {len(messages)} изображений, "
            f"но максимум — {config.MAX_IMAGES}.\n\n"
            f"Пожалуйста, отправьте меньше изображений."
        )
        return
    
    # Собираем file_id всех фото
    images = [msg.photo[-1].file_id for msg in messages]
    
    # Отправляем на модерацию
    await process_free_ad(messages[-1], state, bot, ad_text, images)


async def process_free_ad(message: Message, state: FSMContext, bot: Bot, ad_text: str, images: list = None):
    """Обработка и отправка объявления на модерацию"""
    
    # Показываем превью
    preview_text = "<b>📋 Превью вашего объявления:</b>\n\n" + (ad_text if ad_text else "<i>Без текста</i>")
    
    if images:
        # Отправляем медиагруппу как превью
        media_group = [InputMediaPhoto(media=images[0], caption=preview_text)]
        for img in images[1:]:
            media_group.append(InputMediaPhoto(media=img))
        
        await message.answer_media_group(media=media_group)
    else:
        await message.answer(preview_text)
    
    # Сохранение объявления в БД
    ad_id = await database.create_ad(
        user_id=message.from_user.id,
        ad_type="free",
        content=ad_text,
        images=images if images else None
    )
    
    # Отправка объявления на модерацию
    await send_to_moderation(bot, ad_id, message.from_user, ad_text, "бесплатное", images)
    
    # Уведомление пользователя со смайликом загрузки
    notification_msg = await message.answer(
        "⏳ <b>Объявление отправлено на модерацию...</b>\n\n"
        "Ожидайте результатов проверки."
    )
    
    # Сохраняем ID уведомления для последующего удаления
    await database.save_user_notification_message_id(ad_id, notification_msg.message_id)
    
    await state.clear()


# ——————————————————————————————————————————————————————————————
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ——————————————————————————————————————————————————————————————

async def send_to_moderation(bot: Bot, ad_id: int, user, ad_text: str, ad_type_name: str, images: list = None):
    """Отправка объявления в группу модерации"""
    moderation_text = f"""<b>📢 Новое {ad_type_name} объявление #{ad_id}</b>

<b>От:</b> {user.first_name}
<b>Username:</b> @{user.username if user.username else 'не указан'}
<b>User ID:</b> <code>{user.id}</code>

<b>Текст объявления:</b>
{ad_text if ad_text else '<i>Без текста</i>'}

<b>Символов:</b> {len(ad_text)}
<b>Изображений:</b> {len(images) if images else 0}"""
    
    # Клавиатура для модерации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
        ]
    ])
    
    # Отправляем с изображениями или без
    if images:
        media_group = [InputMediaPhoto(media=images[0], caption=moderation_text)]
        for img in images[1:]:
            media_group.append(InputMediaPhoto(media=img))
        
        messages = await bot.send_media_group(
            chat_id=config.MODERATION_GROUP_ID,
            media=media_group
        )
        
        # Отправляем кнопки отдельным сообщением
        sent_message = await bot.send_message(
            chat_id=config.MODERATION_GROUP_ID,
            text=f"Объявление #{ad_id} - действия:",
            reply_markup=keyboard
        )
    else:
        sent_message = await bot.send_message(
            chat_id=config.MODERATION_GROUP_ID,
            text=moderation_text,
            reply_markup=keyboard
        )
    
    # Сохраняем ID сообщения для возможности редактирования
    await database.save_ad_message_id(ad_id, sent_message.message_id)
