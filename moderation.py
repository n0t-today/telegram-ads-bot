from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json

import config
import database

# ——————————————————————————————————————————————————————————————
# РОУТЕР
# ——————————————————————————————————————————————————————————————

router = Router()

# ——————————————————————————————————————————————————————————————
# СОСТОЯНИЯ FSM
# ——————————————————————————————————————————————————————————————

class ModerationStates(StatesGroup):
    waiting_for_reject_reason = State()


# ——————————————————————————————————————————————————————————————
# ОБРАБОТЧИКИ МОДЕРАЦИИ
# ——————————————————————————————————————————————————————————————

@router.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: CallbackQuery, bot: Bot):
    """Одобрение объявления"""
    # Проверка прав администратора
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для модерации!", show_alert=True)
        return
    
    # Получаем ID объявления
    ad_id = int(callback.data.split("_")[1])
    
    # Получаем объявление из БД
    ad = await database.get_ad(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено!", show_alert=True)
        return
    
    # Проверяем, не было ли уже обработано
    if ad["status"] != "pending":
        await callback.answer("❌ Объявление уже обработано!", show_alert=True)
        return
    
    # Обновляем статус объявления
    await database.update_ad_status(ad_id, "approved", callback.from_user.id)
    
    # Публикуем объявление в канал
    try:
        ad_type_emoji = "📢" if ad["ad_type"] == "free" else "💎"
        published_text = f"{ad_type_emoji} <b>Объявление</b>\n\n{ad['content']}"
        
        # Получаем изображения если есть
        images = json.loads(ad["images"]) if ad["images"] else None
        
        if images:
            # Публикуем как медиагруппу
            media_group = [InputMediaPhoto(media=images[0], caption=published_text)]
            for img in images[1:]:
                media_group.append(InputMediaPhoto(media=img))
            
            await bot.send_media_group(
                chat_id=config.PUBLISH_CHANNEL_ID,
                media=media_group
            )
        else:
            # Публикуем как обычное сообщение
            await bot.send_message(
                chat_id=config.PUBLISH_CHANNEL_ID,
                text=published_text
            )
        
        # Удаляем сообщение с загрузкой у пользователя
        if ad["user_notification_message_id"]:
            try:
                await bot.delete_message(
                    chat_id=ad["user_id"],
                    message_id=ad["user_notification_message_id"]
                )
            except Exception as e:
                print(f"Не удалось удалить уведомление: {e}")
        
        # Уведомляем пользователя об одобрении
        notification_text = (
            "✅ <b>Ваше объявление одобрено и опубликовано!</b>\n\n"
        )
        
        if ad["ad_type"] == "paid":
            notification_text += (
                "Администратор скоро свяжется с вами для организации оплаты.\n"
                "Спасибо за использование нашего сервиса!"
            )
        else:
            notification_text += "Спасибо за использование нашего сервиса!"
        
        await bot.send_message(
            chat_id=ad["user_id"],
            text=notification_text
        )
        
        # Обновляем сообщение в группе модерации
        await callback.message.edit_text(
            callback.message.text + 
            f"\n\n<b>✅ ОДОБРЕНО</b>\nМодератор: {callback.from_user.first_name} (ID: {callback.from_user.id})",
            reply_markup=None
        )
        
        await callback.answer("✅ Объявление одобрено и опубликовано!")
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при публикации: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject_ad_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отклонения объявления"""
    # Проверка прав администратора
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для модерации!", show_alert=True)
        return
    
    # Получаем ID объявления
    ad_id = int(callback.data.split("_")[1])
    
    # Получаем объявление из БД
    ad = await database.get_ad(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено!", show_alert=True)
        return
    
    # Проверяем, не было ли уже обработано
    if ad["status"] != "pending":
        await callback.answer("❌ Объявление уже обработано!", show_alert=True)
        return
    
    # Сохраняем ID объявления и ID сообщения в состояние
    await state.update_data(
        ad_id=ad_id,
        moderation_message_id=callback.message.message_id,
        moderation_chat_id=callback.message.chat.id
    )
    await state.set_state(ModerationStates.waiting_for_reject_reason)
    
    # Просим ввести причину отклонения
    await callback.message.answer(
        f"<b>Отклонение объявления #{ad_id}</b>\n\n"
        "Пожалуйста, напишите причину отклонения.\n"
        "Она будет отправлена пользователю."
    )
    
    await callback.answer()


@router.message(ModerationStates.waiting_for_reject_reason)
async def reject_ad_finish(message: Message, state: FSMContext, bot: Bot):
    """Завершение процесса отклонения объявления"""
    # Проверка прав администратора
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет прав для модерации!")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    ad_id = data.get("ad_id")
    moderation_message_id = data.get("moderation_message_id")
    moderation_chat_id = data.get("moderation_chat_id")
    reject_reason = message.text
    
    # Получаем объявление из БД
    ad = await database.get_ad(ad_id)
    if not ad:
        await message.answer("❌ Объявление не найдено!")
        await state.clear()
        return
    
    # Обновляем статус объявления
    await database.update_ad_status(ad_id, "rejected", message.from_user.id, reject_reason)
    
    # Удаляем сообщение с загрузкой у пользователя
    if ad["user_notification_message_id"]:
        try:
            await bot.delete_message(
                chat_id=ad["user_id"],
                message_id=ad["user_notification_message_id"]
            )
        except Exception as e:
            print(f"Не удалось удалить уведомление: {e}")
    
    # Уведомляем пользователя об отклонении
    try:
        notification_text = (
            "❌ <b>Ваше объявление отклонено</b>\n\n"
            f"<b>Причина:</b>\n{reject_reason}\n\n"
            "Вы можете исправить объявление и отправить его снова."
        )
        
        await bot.send_message(
            chat_id=ad["user_id"],
            text=notification_text
        )
        
        # Обновляем сообщение в группе модерации
        try:
            await bot.edit_message_text(
                text=f"<b>❌ Объявление #{ad_id} ОТКЛОНЕНО</b>\n"
                     f"Модератор: {message.from_user.first_name} (ID: {message.from_user.id})\n"
                     f"Причина: {reject_reason}",
                chat_id=moderation_chat_id,
                message_id=moderation_message_id,
                reply_markup=None
            )
        except:
            # Если не удалось отредактировать, просто отправляем новое сообщение
            await bot.send_message(
                chat_id=moderation_chat_id,
                text=f"<b>❌ Объявление #{ad_id} ОТКЛОНЕНО</b>\n"
                     f"Модератор: {message.from_user.first_name} (ID: {message.from_user.id})\n"
                     f"Причина: {reject_reason}"
            )
        
        await message.answer(f"✅ Объявление #{ad_id} отклонено. Пользователь уведомлен.")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отклонении: {str(e)}")
    
    await state.clear()
