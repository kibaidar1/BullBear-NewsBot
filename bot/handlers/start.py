"""Обработчики команды start"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from database.database import Database
from bot.keyboards.inline import get_main_menu_keyboard, get_back_button

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    await db.add_user(user_id, username)

    welcome_text = """
🤖 <b>Добро пожаловать в Бот мониторинга новостей!</b>

Я помогу вам отслеживать новости по интересующим компаниям и акциям.

Выберите действие из меню ниже:
    """

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    await message.answer(
        "📱 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.edit_text(
        "📱 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать помощь"""
    help_text = """
📋 <b>Помощь</b>

<b>Доступные команды:</b>
/start - Запустить бота
/menu - Главное меню
/add &lt;название&gt; - Добавить компанию
/remove &lt;название&gt; - Удалить компанию
/list - Список подписок
/check - Проверить новости

<b>Примеры использования:</b>
• /add Apple
• /add Газпром
• /remove Tesla

Бот автоматически проверяет новости каждый час и отправляет их вам.
    """

    await callback.message.edit_text(
        help_text,
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()
