"""Обработчики подписок"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.database import Database
from bot.keyboards.inline import (
    get_subscriptions_keyboard,
    get_back_button,
    get_main_menu_keyboard
)
from services.news_filter import NewsFilter

router = Router()


class SubscriptionStates(StatesGroup):
    """Состояния для добавления подписки"""
    waiting_for_company = State()
    waiting_for_exclusions = State()


@router.message(Command("add"))
async def cmd_add_subscription(message: Message, db: Database):
    """Команда для добавления подписки"""
    try:
        company_name = message.text.split(maxsplit=1)[1].strip()
        user_id = message.from_user.id

        if await db.add_subscription(user_id, company_name):
            await message.answer(
                f"✅ Вы подписались на новости: <b>{company_name}</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"⚠️ Вы уже подписаны на: <b>{company_name}</b>",
                parse_mode="HTML"
            )
    except IndexError:
        await message.answer(
            "❌ Использование: /add <название компании>\n"
            "Пример: /add Tesla",
            parse_mode="HTML"
        )


@router.message(SubscriptionStates.waiting_for_exclusions)
async def process_exclusions(message: Message, state: FSMContext, db: Database):
    """Обработка слов-исключений"""
    user_id = message.from_user.id
    data = await state.get_data()
    company_name = data.get('company_name')

    # Обработка исключений
    exclude_keywords = []
    if message.text.strip().lower() not in ['нет', 'no', 'skip', '-']:
        exclude_keywords = [
            kw.strip()
            for kw in message.text.split(',')
            if kw.strip()
        ]

    # Добавляем подписку с фильтрами
    if await db.add_subscription(user_id, company_name, exclude_keywords):
        exclude_text = ""
        if exclude_keywords:
            exclude_text = f"\n🚫 Исключения: {', '.join(exclude_keywords)}"

        await message.answer(
            f"✅ Подписка создана!\n\n"
            f"📊 <b>{company_name}</b>"
            f"{exclude_text}\n\n"
            f"Вы можете изменить фильтры командой:\n"
            f"/filter {company_name}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⚠️ Вы уже подписаны на: <b>{company_name}</b>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

    await state.clear()


@router.message(Command("filter"))
async def cmd_filter_subscription(message: Message, db: Database):
    """Настроить фильтры для подписки"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "❌ Использование: /filter <компания>\n"
                "Пример: /filter Яндекс"
            )
            return

        company_name = parts[1].strip()
        user_id = message.from_user.id

        # Проверяем существование подписки
        subscriptions = await db.get_user_subscriptions(user_id)
        if company_name not in subscriptions:
            await message.answer(
                f"❌ Подписка на '<b>{company_name}</b>' не найдена",
                parse_mode="HTML"
            )
            return

        # Получаем текущие фильтры
        filters = await db.get_subscription_filters(user_id, company_name)

        current = ""
        if filters['exclude']:
            current = f"\n\n<b>Текущие исключения:</b>\n{', '.join(filters['exclude'])}"

        await message.answer(
            f"⚙️ <b>Настройка фильтров</b>\n\n"
            f"Компания: <b>{company_name}</b>"
            f"{current}\n\n"
            f"Введите новые слова-исключения через запятую:",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "add_subscription")
async def callback_add_subscription(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления подписки"""
    await callback.message.edit_text(
        "✍️ <b>Шаг 1/2: Название компании</b>\n\n"
        "Введите название компании или акции:\n\n"
        "<i>Например: Яндекс, Apple, Tesla, Сбербанк</i>",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_company)
    await callback.answer()


@router.message(SubscriptionStates.waiting_for_company)
async def process_company_name(message: Message, state: FSMContext):
    """Обработка названия компании"""
    company_name = message.text.strip()

    if len(company_name) < 2:
        await message.answer("❌ Название слишком короткое. Попробуйте еще раз:")
        return

    # Сохраняем название компании
    await state.update_data(company_name=company_name)

    # Получаем рекомендуемые исключения
    filter_service = NewsFilter()
    suggested_exclusions = filter_service.get_common_exclusions(company_name)

    suggestion_text = ""
    if suggested_exclusions:
        suggestion_text = f"\n\n💡 <b>Рекомендуемые исключения:</b>\n{', '.join(suggested_exclusions)}"

    await message.answer(
        f"✍️ <b>Шаг 2/2: Фильтрация новостей</b>\n\n"
        f"Компания: <b>{company_name}</b>\n\n"
        f"Хотите исключить нерелевантные новости?\n"
        f"Введите слова через запятую или отправьте <b>нет</b> чтобы пропустить.\n"
        f"{suggestion_text}\n\n"
        f"<i>Например: карты, такси, браузер</i>",
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_exclusions)


@router.message(Command("remove"))
async def cmd_remove_subscription(message: Message, db: Database):
    """Команда для удаления подписки"""
    try:
        company_name = message.text.split(maxsplit=1)[1].strip()
        user_id = message.from_user.id

        if await db.remove_subscription(user_id, company_name):
            await message.answer(
                f"✅ Вы отписались от новостей: <b>{company_name}</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ Подписка на '<b>{company_name}</b>' не найдена",
                parse_mode="HTML"
            )
    except IndexError:
        await message.answer(
            "❌ Использование: /remove <название компании>\n"
            "Пример: /remove Tesla"
        )


@router.message(Command("list"))
async def cmd_list_subscriptions(message: Message, db: Database):
    """Список подписок"""
    user_id = message.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)

    if subscriptions:
        text = "📊 <b>Ваши подписки:</b>\n\n"
        for idx, company in enumerate(subscriptions, 1):
            text += f"{idx}. {company}\n"

        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(
            "📭 У вас пока нет подписок.\n"
            "Используйте /add <название компании>"
        )


@router.callback_query(F.data == "list_subscriptions")
async def callback_list_subscriptions(callback: CallbackQuery, db: Database):
    """Показать список подписок через callback"""
    user_id = callback.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)

    if subscriptions:
        text = "📊 <b>Ваши подписки:</b>\n\nНажмите на компанию, чтобы отписаться:"
        keyboard = get_subscriptions_keyboard(subscriptions)
    else:
        text = "📭 У вас пока нет подписок.\n\nИспользуйте кнопку «Добавить компанию»"
        keyboard = get_back_button()

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("unsub:"))
async def callback_unsubscribe(callback: CallbackQuery, db: Database):
    """Отписаться от компании"""
    company_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    if await db.remove_subscription(user_id, company_name):
        await callback.answer(f"✅ Отписка от {company_name}", show_alert=True)

        # Обновляем список
        subscriptions = await db.get_user_subscriptions(user_id)
        if subscriptions:
            text = "📊 <b>Ваши подписки:</b>\n\nНажмите на компанию, чтобы отписаться:"
            keyboard = get_subscriptions_keyboard(subscriptions)
        else:
            text = "📭 У вас больше нет подписок."
            keyboard = get_back_button()

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отписке", show_alert=True)
