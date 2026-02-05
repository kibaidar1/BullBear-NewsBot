"""Обработчики подписок с фильтрами"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.database import Database
from services.news_filter import NewsFilter
from bot.keyboards.inline import get_main_menu_keyboard, get_back_button

router = Router()


class SubscriptionStates(StatesGroup):
    """Состояния для добавления подписки"""
    waiting_for_company = State()
    waiting_for_exclusions = State()


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
