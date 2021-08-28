import logging

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, \
    ReplyKeyboardRemove, InlineKeyboardButton
from telegram.ext import CallbackContext, ConversationHandler, PicklePersistence, Updater, CallbackQueryHandler, \
    CommandHandler, MessageHandler, Filters

from app.service import remove_job_if_exists, schedule_request
from config import BOT_LEAGUES, TOKEN
from database import save_user
from utils import build_keyboard

LEAGUES, TIME, SUMMARY = range(3)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.message.from_user.id
    save_user(user_id, context)
    text = 'Hi, I can help reminding about matches in your favorite leagues. But first you will need to choose and ' \
           'specify time for it.\n\nUse command /config to do that. '
    update.message.reply_text(text)


def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    text = 'The bot sends schedule of matches every day at specified time.\n\nYou can choose by yourself from what ' \
           'leagues you want to get notifications and time. To do that - use /config command\n\nIf you want to ' \
           'cancel some operation - you can apply /cancel '
    update.message.reply_text(text)


def config(update: Update, context: CallbackContext) -> int:
    """Initiates conversation to change setting of the bot."""
    reply_keyboard = [['Continue', '/cancel']]
    update.message.reply_text(
        'This is the place where you can choose you want to get notifications and also when do you want to get them. '
        'You can choose cancel to stop this.\n\n'
        'Should we go on?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),
    )
    return LEAGUES


def config_leagues(update: Update, context: CallbackContext, offset=None) -> None:
    not_first_call = update.callback_query is not None
    if not_first_call and offset is None:
        offset = int(update.callback_query.data.split("#")[-1])
    elif offset is None:
        offset = 0
    query = update.callback_query
    keyboard = build_keyboard(context, offset)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if not_first_call:
        if offset != -1:
            query.edit_message_text('Please choose your favourite leagues:', reply_markup=reply_markup)
    else:
        update.message.reply_text('Please choose your favourite leagues:', reply_markup=reply_markup)
    return TIME


def save_or_delete_league(update: Update, context: CallbackContext) -> None:
    """Deletes or adds league id to user data"""
    offset = int(update.callback_query.data.split("#")[-2])
    league_id = int(update.callback_query.data.split("#")[-1])

    if 'leagues' not in context.user_data:
        context.user_data['leagues'] = []
    if league_id in context.user_data['leagues']:
        context.user_data['leagues'].remove(league_id)
    else:
        context.user_data['leagues'].append(league_id)

    config_leagues(update, context, offset=offset)


def set_notify_time(update: Update, context: CallbackContext) -> int:
    text = 'Send me time (in format HH:MM) when you want to receive match fixtures. Note that you should be sent me ' \
           'in UTC timezone!\n'
    reply_markup = None
    if 'notify_time' in context.user_data:
        user_time = context.user_data['notify_time']
        text += f'\nFor now your time is set to {user_time}'
        keyboard = [
            [InlineKeyboardButton("Skip", callback_data='skip')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    return SUMMARY


def summary(update: Update, context: CallbackContext) -> int:
    """Stores the info about the user and ends the conversation."""
    if update.message:
        message = update.message
        chat_id = message.chat_id
        context.user_data['notify_time'] = message.text
    else:
        message = update.callback_query.message
        chat_id = message.chat_id
        message.edit_text(message.text, reply_markup=None)
    user_leagues = context.user_data['leagues']
    leagues_to_show = []
    for i in user_leagues:
        leagues_to_show.append(BOT_LEAGUES[i])
    user_time = context.user_data['notify_time']
    leagues_to_show = ', '.join(map(str, leagues_to_show))
    message.reply_text(f'Great! I will notify you about those leagues - {leagues_to_show} at {user_time}.',
                       reply_markup=ReplyKeyboardRemove())

    remove_job_if_exists(str(chat_id), context)
    schedule_request(context, chat_id)
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Alright, if you want to modify something, send /config.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def unknown(update: Update, context: CallbackContext):
    """Replies if user sends unknown command or text."""
    update.message.reply_text(
        "Sorry, I didn't understand that command. Try using /help",
    )


def main() -> None:
    """Start the bot."""
    persistence = PicklePersistence(filename='persistence')
    updater = Updater(TOKEN, persistence=persistence)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CallbackQueryHandler(config_leagues, pattern='^edit_config'))
    dispatcher.add_handler(CallbackQueryHandler(save_or_delete_league, pattern='^league'))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('config', config)],
        states={
            LEAGUES: [MessageHandler(Filters.regex('^(Continue)$'), config_leagues)],
            TIME: [CallbackQueryHandler(set_notify_time, pattern='^set_time')],
            SUMMARY: [MessageHandler(Filters.regex('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'), summary),
                      CallbackQueryHandler(summary, pattern='^skip')]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(MessageHandler(~(Filters.command |
                                            Filters.regex('^Continue') |
                                            Filters.regex('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')), unknown))
    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()
