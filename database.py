import aiosqlite
from datetime import datetime

# ——————————————————————————————————————————————————————————————
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ——————————————————————————————————————————————————————————————

DB_NAME = "bot_database.db"


async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица объявлений
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ad_type TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                moderated_at TIMESTAMP,
                moderator_id INTEGER,
                reject_reason TEXT,
                message_id INTEGER,
                user_notification_message_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Таблица медиа для объявлений (нормализованное хранение)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ad_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id INTEGER NOT NULL,
                media_type TEXT NOT NULL CHECK(media_type IN ('photo','video')),
                file_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (ad_id) REFERENCES ads (id) ON DELETE CASCADE
            )
        """)
        
        # Таблица обращений в поддержку
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await db.commit()


# ——————————————————————————————————————————————————————————————
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ——————————————————————————————————————————————————————————————

async def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавление пользователя в базу данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
               VALUES (?, ?, ?, ?)""",
            (user_id, username, first_name, last_name)
        )
        await db.commit()


async def get_user(user_id: int):
    """Получение данных пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


# ——————————————————————————————————————————————————————————————
# ФУНКЦИИ ДЛЯ РАБОТЫ С ОБЪЯВЛЕНИЯМИ
# ——————————————————————————————————————————————————————————————

async def create_ad(user_id: int, ad_type: str, content: str, media_items: list | None = None):
    """Создание нового объявления и сохранение медиа.

    media_items: список кортежей вида (media_type, file_id), где media_type в {'photo','video'}
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO ads (user_id, ad_type, content, status) 
               VALUES (?, ?, ?, 'pending')""",
            (user_id, ad_type, content)
        )
        ad_id = cursor.lastrowid

        if media_items:
            for idx, (media_type, file_id) in enumerate(media_items):
                await db.execute(
                    """INSERT INTO ad_media (ad_id, media_type, file_id, position)
                           VALUES (?, ?, ?, ?)""",
                    (ad_id, media_type, file_id, idx)
                )

        await db.commit()
        return ad_id


async def get_ad(ad_id: int):
    """Получение объявления по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
            return await cursor.fetchone()


async def get_ad_media(ad_id: int):
    """Получение списка медиа для объявления, упорядоченных по позиции"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT media_type, file_id FROM ad_media WHERE ad_id = ? ORDER BY position ASC",
            (ad_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row["media_type"], row["file_id"]) for row in rows]


async def update_ad_status(ad_id: int, status: str, moderator_id: int = None, reject_reason: str = None):
    """Обновление статуса объявления"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """UPDATE ads 
               SET status = ?, moderated_at = CURRENT_TIMESTAMP, moderator_id = ?, reject_reason = ?
               WHERE id = ?""",
            (status, moderator_id, reject_reason, ad_id)
        )
        await db.commit()


async def save_ad_message_id(ad_id: int, message_id: int):
    """Сохранение ID сообщения с объявлением"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE ads SET message_id = ? WHERE id = ?",
            (message_id, ad_id)
        )
        await db.commit()


async def save_user_notification_message_id(ad_id: int, message_id: int):
    """Сохранение ID уведомления пользователя о модерации"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE ads SET user_notification_message_id = ? WHERE id = ?",
            (message_id, ad_id)
        )
        await db.commit()


# ——————————————————————————————————————————————————————————————
# ФУНКЦИИ ДЛЯ РАБОТЫ С ОБРАЩЕНИЯМИ В ПОДДЕРЖКУ
# ——————————————————————————————————————————————————————————————

async def create_support_request(user_id: int, message: str):
    """Создание обращения в поддержку"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """INSERT INTO support_requests (user_id, message) 
               VALUES (?, ?)""",
            (user_id, message)
        )
        await db.commit()
        return cursor.lastrowid


async def get_support_request(request_id: int):
    """Получение обращения по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)) as cursor:
            return await cursor.fetchone()

