from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_menu_keyboard(menu_buttons) -> ReplyKeyboardMarkup:

    buttons = []

    for menu_button in menu_buttons:
        button = KeyboardButton(text=menu_button)
        buttons.append(button)

    grouped_buttons = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    keyboard = ReplyKeyboardMarkup(keyboard=grouped_buttons, resize_keyboard=True, input_field_placeholder='Выбрать команду')

    return keyboard


def generate_often_exchanges_keyboard(often_exchanges) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for exchange in often_exchanges:
        builder.add(InlineKeyboardButton(text=exchange, callback_data=exchange))

    builder.adjust(2)

    return builder.as_markup()