from datetime import datetime, time
from typing import Iterator

import pytz
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
    ]
    if context.user_data['leagues']:
        ik_btn = [InlineKeyboardButton("Next", callback_data='set_leagues')]
        keyboard.append(ik_btn)
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


def time_to_tz_naive(t, tz_in, tz_out):
    return tz_in.localize(datetime.combine(datetime.today(), t)).astimezone(tz_out).time()


def convert_time(user_str_time: str, user_timezone: str) -> time:
    user_time = datetime.strptime(user_str_time, '%H:%M').time()
    utc_user_time = time_to_tz_naive(user_time, pytz.timezone(user_timezone), pytz.timezone("Etc/UTC"))
    return utc_user_time
