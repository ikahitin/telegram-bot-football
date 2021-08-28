from datetime import datetime
from typing import Iterator

from telegram import InlineKeyboardButton
from telegram.ext import CallbackContext

from config import BOT_LEAGUES


def chunks(lst, n) -> Iterator[list]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_today_date() -> datetime.date:
    date_now = datetime.now().date()

    return date_now


def build_keyboard(context: CallbackContext, offset: int) -> list:
    kb_leagues = []

    for i in BOT_LEAGUES:
        name = BOT_LEAGUES[i]
        if context.user_data.get('leagues', None):
            if i in context.user_data['leagues']:
                name = '✅ ' + BOT_LEAGUES[i]

        row = [InlineKeyboardButton(name, callback_data=f'league#{offset}#{i}')]
        kb_leagues.append(row)

    leagues = list(chunks(kb_leagues, 5))
    keyboard = [
        *leagues[offset],
        [
            InlineKeyboardButton("<-",
                                 callback_data=f'edit_config#{offset - 1}' if offset > 0 else 'edit_config#-1'),
            InlineKeyboardButton("->",
                                 callback_data=f'edit_config#{offset + 1}' if offset < len(
                                     leagues) - 1 else 'edit_config#-1'),
        ],
        [InlineKeyboardButton("Next", callback_data='set_leagues')],
    ]

    return keyboard


def get_summary_text(context: CallbackContext) -> str:
    user_leagues = context.user_data['leagues']
    leagues_to_show = []

    for i in user_leagues:
        leagues_to_show.append(BOT_LEAGUES[i])

    user_time = context.user_data['notify_time']
    leagues_to_show = ', '.join(map(str, leagues_to_show))
    text = f'Great! I will notify you about those leagues - {leagues_to_show} at {user_time}.'

    return text
