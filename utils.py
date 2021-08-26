from datetime import datetime

from telegram import InlineKeyboardButton
from telegram.ext import CallbackContext

from config import BOT_LEAGUES


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_today_date():
    date_now = datetime.now().date()
    return date_now


def build_keyboard(context: CallbackContext, offset: int):
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
        [InlineKeyboardButton("Next", callback_data='set_time')],
    ]

    return keyboard
