from telegram import Location
from telegram.ext import CallbackContext
import timezonefinder


def get_user_leagues(context: CallbackContext) -> list:
    if context.user_data.get('leagues', None):
        return context.user_data['leagues']


def save_user(user_id: int, context: CallbackContext) -> None:
    if 'users' not in context.bot_data:
        context.bot_data['users'] = []
    if user_id not in context.bot_data['users']:
        context.bot_data['users'].append(user_id)


def save_timezone(user_location: Location, context: CallbackContext) -> None:
    tf = timezonefinder.TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    context.user_data['timezone'] = timezone_str
