import json
from collections import defaultdict
from datetime import datetime

from requests import Response
from telegram.ext import CallbackContext
from telegram.error import Unauthorized
import requests

from config import HEADERS, URL, BOT_LEAGUES, DEVELOPER_CHAT_ID
from database import get_user_leagues
from utils import get_today_date, convert_time


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def schedule_request(context: CallbackContext, chat_id: int) -> None:
    """Scheduler request by user time."""
    user_time = context.user_data['notify_time']
    user_timezone = context.user_data['timezone']
    time_in_utc = convert_time(user_time, user_timezone)
    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_daily(send_fixtures, time_in_utc, context=(chat_id, context), name=str(chat_id))


def make_request(context: CallbackContext) -> str:
    """Send HTTP request to API."""
    user_leagues = get_user_leagues(context)
    today_date = get_today_date()
    user_timezone = context.user_data['timezone']
    querystring = {"date": today_date, "season": "2021", "timezone": user_timezone}

    try:
        resp = requests.request("GET", URL, headers=HEADERS, params=querystring)
    except requests.ConnectionError:
        resp = Response()
        resp._content = '{ "Error" : "Connection Error" }'
        return resp.text
    limit_control(context, resp.headers)
    msg = prepare_text_for_message(resp.text, user_leagues)
    return msg


def send_fixtures(context: CallbackContext) -> None:
    """Send results to user"""
    chat_id, context = context.job.context
    text = make_request(context)
    if not text:
        text = 'Oh no, failed to send matches'
    try:
        context.bot.send_message(chat_id, text=text)
    except Unauthorized:
        message = 'Job was removed, user blocked the bot'
        context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message)
        remove_job_if_exists(str(chat_id), context)


def prepare_text_for_message(response: str, user_leagues: list) -> str:
    """Creates a message from API response"""
    fixtures = json.loads(response)['response']
    leagues_by_user = defaultdict(list)

    for f in fixtures:
        if f['league']['id'] in user_leagues:
            match = {'league': f['league'],
                     'home_team': f['teams']['home']['name'],
                     'away_team': f['teams']['away']['name'],
                     'f_time': f['fixture']['date']}
            leagues_by_user[f['league']['id']].append(match)

    if not leagues_by_user:
        return 'Seems like no matches for today 😕'

    msg = 'Schedule of matches for today:\n\n'
    for league, matches in leagues_by_user.items():
        msg += BOT_LEAGUES[league] + '\n'
        for m in matches:
            event_time = datetime.strptime(m['f_time'], "%Y-%m-%dT%H:%M:%S%z")
            current_time = event_time.strftime("%H:%M")
            even_time = '🕐 ' + current_time + ' '
            msg += even_time + m['home_team'] + ' - ' + m['away_team'] + '\n'
        msg += '\n'
    return msg


def limit_control(context: CallbackContext, headers) -> None:
    """Checks api limits and informs if it has been."""
    calls = int(headers['X-RateLimit-requests-Remaining'])
    context.bot_data['calls_remaining'] = calls
    if calls < 10:
        message = 'API calls left - {}'.format(calls)
        context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message)


def send_bd_message(context: CallbackContext) -> None:
    """Sends message to all possible users"""
    users_generator, bd_message, context = context.job.context
    try:
        context.bot.send_message(chat_id=next(users_generator), text=bd_message)
    except Unauthorized:
        pass
    except StopIteration:
        remove_job_if_exists('broadcast', context)
