# ═══════════════════════════════════════════════════════════
# 🤖 GOMER BOT - Главный файл
# ═══════════════════════════════════════════════════════════

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS, CATEGORIES, WELCOME_MESSAGE, ADMIN_PANEL_MESSAGE
from database import (
    init_db, add_user, get_all_users, get_all_user_ids,
    get_users_by_category, get_user_count, get_category_stats,
    deactivate_user
)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ═══════════════════════════════════════════════════════════
# 📝 СОСТОЯНИЯ FSM (для рассылки)
# ═══════════════════════════════════════════════════════════

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_category_message = State()
    selected_category = State()


# ═══════════════════════════════════════════════════════════
# 🎛️ КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📥 Выгрузить всю базу ID", callback_data="admin_export_all")],
        [
            InlineKeyboardButton(text="🟢 Новички", callback_data="admin_export_1"),
            InlineKeyboardButton(text="🟡 Средние", callback_data="admin_export_2"),
            InlineKeyboardButton(text="🔴 Высокие", callback_data="admin_export_3"),
        ],
        [InlineKeyboardButton(text="📨 Рассылка всем", callback_data="admin_broadcast_all")],
        [
            InlineKeyboardButton(text="📨 Новичкам", callback_data="admin_broadcast_1"),
            InlineKeyboardButton(text="📨 Средним", callback_data="admin_broadcast_2"),
            InlineKeyboardButton(text="📨 Высоким", callback_data="admin_broadcast_3"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_back")]
    ])


# ═══════════════════════════════════════════════════════════
# 🚪 АВТОМАТИЧЕСКОЕ ОДОБРЕНИЕ ЗАЯВОК НА ВСТУПЛЕНИЕ
# ═══════════════════════════════════════════════════════════

@dp.chat_join_request()
async def handle_join_request(update: types.ChatJoinRequest):
    """Автоматически одобряем заявку и пишем приветствие"""
    user = update.from_user
    
    try:
        # Одобряем заявку на вступление
        await update.approve()
        logger.info(f"✅ Одобрена заявка: {user.id} (@{user.username})")
        
        # Сохраняем пользователя в базу
        add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Отправляем приветственное сообщение в личку
        await bot.send_message(user.id, WELCOME_MESSAGE)
        logger.info(f"📨 Приветствие отправлено: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке заявки {user.id}: {e}")


# ═══════════════════════════════════════════════════════════
# 👤 КОМАНДЫ ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    user = message.from_user
    
    # Сохраняем пользователя в базу
    add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    logger.info(f"Новый пользователь: {user.id} (@{user.username})")
    
    # Отправляем приветствие
    await message.answer(WELCOME_MESSAGE)


# ═══════════════════════════════════════════════════════════
# 🔐 АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════════════════════

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Открыть админ-панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У тебя нет доступа к админ-панели.")
        return
    
    await message.answer(ADMIN_PANEL_MESSAGE, reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в админ-панель"""
    await state.clear()
    await callback.message.edit_text(ADMIN_PANEL_MESSAGE, reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отменить действие"""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=get_back_keyboard())


# ═══════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА
# ═══════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    """Показать статистику"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    total = get_user_count()
    stats = get_category_stats()
    
    text = f"""
📊 <b>Статистика бота</b>

👥 Всего пользователей: <b>{total}</b>

📁 По категориям:
├ ⚪ Не определена: <b>{stats.get(0, 0)}</b>
├ 🟢 Новичок: <b>{stats.get(1, 0)}</b>
├ 🟡 Средний: <b>{stats.get(2, 0)}</b>
└ 🔴 Высокий: <b>{stats.get(3, 0)}</b>
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())


# ═══════════════════════════════════════════════════════════
# 📥 ВЫГРУЗКА БАЗЫ
# ═══════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_export_all")
async def admin_export_all(callback: types.CallbackQuery):
    """Выгрузить все ID"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    user_ids = get_all_user_ids()
    
    if not user_ids:
        await callback.message.edit_text("📭 База пользователей пуста.", reply_markup=get_back_keyboard())
        return
    
    # Создаём файл
    content = "\n".join(map(str, user_ids))
    file = BufferedInputFile(content.encode(), filename="all_users.txt")
    
    await callback.message.answer_document(
        file,
        caption=f"📥 Все пользователи: <b>{len(user_ids)}</b> ID"
    )
    await callback.message.edit_text("✅ Файл отправлен!", reply_markup=get_back_keyboard())


@dp.callback_query(F.data.startswith("admin_export_"))
async def admin_export_category(callback: types.CallbackQuery):
    """Выгрузить ID по категории"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    category = int(callback.data.split("_")[-1])
    user_ids = get_users_by_category(category)
    category_name = CATEGORIES.get(category, "Неизвестно")
    
    if not user_ids:
        await callback.message.edit_text(
            f"📭 Нет пользователей в категории «{category_name}».",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Создаём файл
    content = "\n".join(map(str, user_ids))
    file = BufferedInputFile(content.encode(), filename=f"category_{category}.txt")
    
    await callback.message.answer_document(
        file,
        caption=f"📥 Категория «{category_name}»: <b>{len(user_ids)}</b> ID"
    )
    await callback.message.edit_text("✅ Файл отправлен!", reply_markup=get_back_keyboard())


# ═══════════════════════════════════════════════════════════
# 📨 РАССЫЛКА
# ═══════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_broadcast_all")
async def admin_broadcast_all(callback: types.CallbackQuery, state: FSMContext):
    """Начать рассылку всем"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await state.update_data(category=None)  # None = всем
    
    await callback.message.edit_text(
        "📨 <b>Рассылка всем пользователям</b>\n\n"
        "Отправь сообщение, которое нужно разослать.\n"
        "Поддерживается: текст, фото, видео, документы.",
        reply_markup=get_cancel_keyboard()
    )


@dp.callback_query(F.data.startswith("admin_broadcast_"))
async def admin_broadcast_category(callback: types.CallbackQuery, state: FSMContext):
    """Начать рассылку по категории"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    category = int(callback.data.split("_")[-1])
    category_name = CATEGORIES.get(category, "Неизвестно")
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await state.update_data(category=category)
    
    await callback.message.edit_text(
        f"📨 <b>Рассылка категории «{category_name}»</b>\n\n"
        "Отправь сообщение, которое нужно разослать.\n"
        "Поддерживается: текст, фото, видео, документы.",
        reply_markup=get_cancel_keyboard()
    )


@dp.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    data = await state.get_data()
    category = data.get("category")
    
    # Получаем список пользователей
    if category is None:
        user_ids = get_all_user_ids()
        target = "всем пользователям"
    else:
        user_ids = get_users_by_category(category)
        target = f"категории «{CATEGORIES.get(category)}»"
    
    if not user_ids:
        await message.answer(f"📭 Нет пользователей для рассылки.", reply_markup=get_back_keyboard())
        await state.clear()
        return
    
    await message.answer(f"⏳ Начинаю рассылку {target}...\nВсего: {len(user_ids)} пользователей")
    
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            # Копируем сообщение пользователю
            await message.copy_to(chat_id=user_id)
            success += 1
        except Exception as e:
            failed += 1
            # Если пользователь заблокировал бота
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                deactivate_user(user_id)
            logger.warning(f"Не удалось отправить {user_id}: {e}")
        
        # Небольшая пауза чтобы не превысить лимиты
        await asyncio.sleep(0.05)
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Успешно: <b>{success}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>",
        reply_markup=get_back_keyboard()
    )


# ═══════════════════════════════════════════════════════════
# ⏰ АВТОМАТИЧЕСКАЯ ВЫГРУЗКА БАЗЫ КАЖДЫЕ 24 ЧАСА
# ═══════════════════════════════════════════════════════════

async def daily_backup_task():
    """Отправляет выгрузку базы ID админам каждые 24 часа"""
    while True:
        # Ждём 24 часа (86400 секунд)
        await asyncio.sleep(86400)
        
        try:
            user_ids = get_all_user_ids()
            stats = get_category_stats()
            total = get_user_count()
            
            if not user_ids:
                logger.info("📭 Автовыгрузка: база пуста")
                continue
            
            # Создаём файл
            content = "\n".join(map(str, user_ids))
            file = BufferedInputFile(content.encode(), filename="daily_backup.txt")
            
            # Формируем сообщение
            caption = (
                f"📊 <b>Ежедневная выгрузка базы</b>\n\n"
                f"👥 Всего: <b>{total}</b> пользователей\n\n"
                f"📁 По категориям:\n"
                f"├ ⚪ Не определена: <b>{stats.get(0, 0)}</b>\n"
                f"├ 🟢 Новичок: <b>{stats.get(1, 0)}</b>\n"
                f"├ 🟡 Средний: <b>{stats.get(2, 0)}</b>\n"
                f"└ 🔴 Высокий: <b>{stats.get(3, 0)}</b>"
            )
            
            # Отправляем всем админам
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_document(admin_id, file, caption=caption)
                    logger.info(f"📨 Автовыгрузка отправлена админу {admin_id}")
                except Exception as e:
                    logger.warning(f"❌ Не удалось отправить автовыгрузку админу {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка автовыгрузки: {e}")


# ═══════════════════════════════════════════════════════════
# 🚀 ЗАПУСК БОТА
# ═══════════════════════════════════════════════════════════

async def main():
    """Главная функция запуска"""
    # Инициализация базы данных
    init_db()
    logger.info("✅ База данных инициализирована")
    
    # Запускаем фоновую задачу автовыгрузки
    asyncio.create_task(daily_backup_task())
    logger.info("⏰ Автовыгрузка каждые 24ч запущена")
    
    # Запуск бота
    logger.info("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

