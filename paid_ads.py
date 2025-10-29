from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
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

class PaidAdStates(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_ad = State()


# Временное хранилище для медиагрупп (photo/video)
media_groups_paid = defaultdict(list)

# Команды верхнего уровня (кнопки меню), которые должны иметь приоритет над вводом в состояниях
MENU_TEXTS = {
    "📢 Разместить объявление бесплатно",
    "💎 Разместить объявление платно",
    "📣 Рекламный канал",
    "❓ Помощь",
}


# ——————————————————————————————————————————————————————————————
# ОБРАБОТЧИКИ ПЛАТНЫХ ОБЪЯВЛЕНИЙ
# ——————————————————————————————————————————————————————————————

@router.message(F.text == "💎 Разместить объявление платно")
async def start_paid_ad(message: Message, state: FSMContext):
    """Начало создания платного объявления"""
    await state.clear()  # Сбрасываем предыдущее состояние
    # Показываем условия
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен, продолжить", callback_data="agree_paid_ad")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_paid_ad")]
    ])
    
    await message.answer(config.PAID_AD_CONDITIONS, reply_markup=keyboard)
    await state.set_state(PaidAdStates.waiting_for_agreement)


@router.callback_query(F.data == "agree_paid_ad", PaidAdStates.waiting_for_agreement)
async def agree_paid_ad(callback: CallbackQuery, state: FSMContext):
    """Пользователь согласился с условиями"""
    await callback.message.edit_reply_markup(reply_markup=None)
    
    user_name = callback.from_user.first_name or ("@" + callback.from_user.username if callback.from_user.username else "Пользователь")
    template_text = f"""<b>💎 Платное объявление</b>

{user_name}, если вам есть, что продать, то просто пришлите мне ваше объявление по образцу, а я размещу его 🙌

1️⃣ <b>Пришлите Фото/Видео</b>
До 6 фото или 5 фото и 1 видео. 

2️⃣ <b>Заголовок</b>
Пример : Продам платье синее Imperial размер S (заголовок до 5 слов❗️)

3️⃣ <b>Описание (100 символов)</b>
Пример:
• Платье в хорошем состоянии, практически без следов носки, гуляло 1 раз. Небольшой торг.

4️⃣ <b>Цена | Расположение | Контакты</b>
💰 17.500 рублей
📍 Королёв , Пр-т Космонавтов 4 В, магазин YOY_store 
👗 доступна примерка и самовывоз с 12.00 до 20.00
☎️ +79781111111

После одобрения администратор свяжется с вами для организации оплаты и транспортировки в магазин."""

@router.callback_query(F.data == "cancel_paid_ad", PaidAdStates.waiting_for_agreement)
async def cancel_paid_ad(callback: CallbackQuery, state: FSMContext):
    """Отмена создания платного объявления"""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Создание платного объявления отменено.")
    await state.clear()
    await callback.answer()


@router.message(PaidAdStates.waiting_for_ad, F.text & ~F.text.in_(MENU_TEXTS))
async def receive_paid_ad_text(message: Message, state: FSMContext, bot: Bot):
    """Получение текстового объявления"""
    ad_text = message.text
    
    # Проверка лимита символов
    if len(ad_text) > config.PAID_AD_LIMIT:
        await message.answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Ваше объявление содержит {len(ad_text)} символов, "
            f"но лимит для платных объявлений — {config.PAID_AD_LIMIT} символов.\n\n"
            f"Пожалуйста, сократите текст и отправьте снова."
        )
        return
    
    # Отправляем на модерацию
    await process_paid_ad(message, state, bot, ad_text, None)


@router.message(PaidAdStates.waiting_for_ad, F.photo | F.video)
async def receive_paid_ad_photo(message: Message, state: FSMContext, bot: Bot):
    """Получение объявления с фото"""
    
    # Проверяем, это медиагруппа или одиночное фото
    if message.media_group_id:
        # Это часть медиагруппы
        media_groups_paid[message.media_group_id].append(message)
        
        # Ждем немного, чтобы собрать все фото из группы
        import asyncio
        await asyncio.sleep(0.5)
        
        # Проверяем, все ли фото собраны
        group = media_groups_paid[message.media_group_id]
        
        # Берем последнее сообщение из группы для обработки
        if message == group[-1]:
            # Это последнее фото в группе
            await process_media_group_paid_ad(group, state, bot)
            del media_groups_paid[message.media_group_id]
    else:
        # Одиночное медиа (фото/видео)
        ad_text = message.caption or ""
        
        # Проверка лимита символов
        if len(ad_text) > config.PAID_AD_LIMIT:
            await message.answer(
                f"<b>❌ Ошибка!</b>\n\n"
                f"Подпись содержит {len(ad_text)} символов, "
                f"но лимит — {config.PAID_AD_LIMIT} символов.\n\n"
                f"Пожалуйста, сократите текст и отправьте снова."
            )
            return
        
        # Получаем file_id
        media_ids = []
        if message.photo:
            media_ids.append(("photo", message.photo[-1].file_id))
        if getattr(message, "video", None):
            media_ids.append(("video", message.video.file_id))

        # Отправляем на модерацию
        await process_paid_ad(message, state, bot, ad_text, media_ids)


async def process_media_group_paid_ad(messages: list, state: FSMContext, bot: Bot):
    """Обработка медиагруппы для платного объявления"""
    # Берем подпись из первого сообщения
    ad_text = messages[0].caption or ""
    
    # Проверка лимита символов
    if len(ad_text) > config.PAID_AD_LIMIT:
        await messages[-1].answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Подпись содержит {len(ad_text)} символов, "
            f"но лимит — {config.PAID_AD_LIMIT} символов.\n\n"
            f"Пожалуйста, сократите текст и отправьте снова."
        )
        return
    
    # Подсчет фото/видео и проверка лимитов
    num_photos = sum(1 for m in messages if m.photo)
    num_videos = sum(1 for m in messages if getattr(m, "video", None))
    total_media = num_photos + num_videos

    if total_media > config.PAID_MAX_MEDIA or num_videos > config.PAID_MAX_VIDEOS:
        await messages[-1].answer(
            f"<b>❌ Ошибка!</b>\n\n"
            f"Ограничения платного объявления:\n"
            f"• До {config.PAID_MAX_MEDIA} медиа всего\n"
            f"• До {config.PAID_MAX_VIDEOS} видео\n\n"
            f"У вас: фото {num_photos}, видео {num_videos}."
        )
        return
    
    # Собираем media (тип, id)
    media_ids = []
    for msg in messages:
        if msg.photo:
            media_ids.append(("photo", msg.photo[-1].file_id))
        if getattr(msg, "video", None):
            media_ids.append(("video", msg.video.file_id))
    
    # Отправляем на модерацию
    await process_paid_ad(messages[-1], state, bot, ad_text, media_ids)


async def process_paid_ad(message: Message, state: FSMContext, bot: Bot, ad_text: str, media_ids: list = None):
    """Обработка и отправка объявления на модерацию"""
    
    # Показываем превью
    preview_text = "<b>📋 Превью вашего объявления:</b>\n\n" + (ad_text if ad_text else "<i>Без текста</i>")
    
    if media_ids:
        # Отправляем медиагруппу как превью
        first_type, first_id = media_ids[0]
        media_group = [
            InputMediaPhoto(media=first_id, caption=preview_text)
            if first_type == "photo" else
            InputMediaVideo(media=first_id, caption=preview_text)
        ]
        for typ, mid in media_ids[1:]:
            media_group.append(InputMediaPhoto(media=mid) if typ == "photo" else InputMediaVideo(media=mid))
        
        await message.answer_media_group(media=media_group)
    else:
        await message.answer(preview_text)
    
    # Сохранение объявления в БД
    ad_id = await database.create_ad(
        user_id=message.from_user.id,
        ad_type="paid",
        content=ad_text,
        media_items=media_ids if media_ids else None
    )
    
    # Отправка объявления на модерацию
    await send_to_moderation(bot, ad_id, message.from_user, ad_text, "платное", media_ids)
    
    # Уведомление пользователя со смайликом загрузки
    notification_msg = await message.answer(
        "⏳ <b>Объявление отправлено на модерацию...</b>\n\n"
        "После проверки администратор свяжется с вами для организации оплаты."
    )
    
    # Сохраняем ID уведомления для последующего удаления
    await database.save_user_notification_message_id(ad_id, notification_msg.message_id)
    
    await state.clear()


# ——————————————————————————————————————————————————————————————
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ——————————————————————————————————————————————————————————————

async def send_to_moderation(bot: Bot, ad_id: int, user, ad_text: str, ad_type_name: str, media_ids: list = None):
    """Отправка объявления в группу модерации"""
    moderation_text = f"""<b>💎 Новое {ad_type_name} объявление #{ad_id}</b>

<b>От:</b> {user.first_name}
<b>Username:</b> @{user.username if user.username else 'не указан'}
<b>User ID:</b> <code>{user.id}</code>

<b>Текст объявления:</b>
{ad_text if ad_text else '<i>Без текста</i>'}

<b>Символов:</b> {len(ad_text)}
<b>Медиа:</b> {len(media_ids) if media_ids else 0}"""
    
    # Клавиатура для модерации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
        ]
    ])
    
    # Отправляем с изображениями или без
    if media_ids:
        first_type, first_id = media_ids[0]
        media_group = [
            InputMediaPhoto(media=first_id, caption=moderation_text)
            if first_type == "photo" else
            InputMediaVideo(media=first_id, caption=moderation_text)
        ]
        for typ, mid in media_ids[1:]:
            media_group.append(InputMediaPhoto(media=mid) if typ == "photo" else InputMediaVideo(media=mid))
        
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
