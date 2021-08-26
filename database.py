from telegram.ext import CallbackContext


def get_user_leagues(context: CallbackContext) -> list:
    if context.user_data.get('leagues', None):
        return context.user_data['leagues']


def save_user(user_id: int, context: CallbackContext):
    if 'users' not in context.bot_data:
        context.bot_data['users'] = []
    if user_id not in context.bot_data['users']:
        context.bot_data['users'].append(user_id)


