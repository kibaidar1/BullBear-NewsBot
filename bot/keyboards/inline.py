"""Inline клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить компанию", callback_data="add_subscription")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои подписки", callback_data="list_subscriptions")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить новости", callback_data="check_news")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
    )
    return builder.as_markup()


def get_subscriptions_keyboard(subscriptions: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура со списком подписок"""
    builder = InlineKeyboardBuilder()

    for company in subscriptions:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {company}",
                callback_data=f"unsub:{company}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def get_back_button() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()
