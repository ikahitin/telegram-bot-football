import html
import json
import logging
import traceback

from telegram import Update, InlineKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, ParseMode
from telegram.ext import CallbackContext, ConversationHandler, PicklePersistence, Updater, CallbackQueryHandler, \
    CommandHandler, MessageHandler, Filters

from app.service import schedule_request, send_bd_message
from config import TOKEN, DEVELOPER_CHAT_ID, DEVELOPER_USER_ID
from database import save_user, save_timezone
from utils import build_keyboard, get_summary_text, yield_list

LOCATION, LEAGUES, TIME, BROADCAST = range(4)

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
    """Send a message when the command /help is issued."""
    text = 'The bot sends schedule of matches every day at specified time.\n\nYou can choose by yourself from what ' \
           'leagues you want to get notifications. To do that - use /config command\n\nIf you want to ' \
           'cancel some operation - you can apply /cancel '
    update.message.reply_text(text)


def stats(update: Update, context: CallbackContext):
    """Send a message when the command /stats is issued."""
    if str(update.message.from_user.id) == DEVELOPER_USER_ID:
        total_users = len(context.bot_data['users'])
        active_jobs = len(context.job_queue.jobs())
        calls_remaining = context.bot_data['calls_remaining']
        text = 'Total number of users - {}\n' \
               'Scheduled jobs - {}\n' \
               'Request left - {}'.format(total_users, active_jobs, calls_remaining)
        update.message.reply_text(text)


def config(update: Update, context: CallbackContext, offset=None) -> None:
    """Shows config for choosing leagues."""
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

    return LEAGUES


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

    config(update, context, offset=offset)


def ask_location(update: Update, context: CallbackContext) -> int:
    """Asks user to send location."""
    text = 'Please, send me your location I need it to determine your timezone\n'
    keyboard = [
        [InlineKeyboardButton("Continue with UTC timezone", callback_data='utc')]
    ]
    if 'timezone' in context.user_data:
        ik_btn = [InlineKeyboardButton("Keep my current location", callback_data='skip')]
        keyboard.append(ik_btn)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.edit_text(text, reply_markup=reply_markup)

    return LOCATION


def location(update: Update, context: CallbackContext) -> int:
    """Saves timezone from location and asks for time."""
    if not update.message.location:
        update.message.reply_text("You would you have to send me location to find out the timezone")
        return 0
    else:
        user_location = update.message.location
        save_timezone(user_location, context)

    text = 'Send me time (in format HH:MM, for example 10:00) when you want to receive match fixtures.\n'
    reply_markup = None
    if 'notify_time' in context.user_data:
        user_time = context.user_data['notify_time']
        text += f'\nFor now your time is set to {user_time}'
        keyboard = [
            [InlineKeyboardButton("Skip", callback_data='skip')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)

    return TIME


def skip_location(update: Update, context: CallbackContext) -> int:
    """Skips location and asks for time."""
    text = 'Send me time (in format HH:MM, for example 10:00) when you want to receive match fixtures.\n'
    reply_markup = None
    message = update.callback_query.message
    message.edit_text(message.text, reply_markup=None)
    if update.callback_query.data == 'utc':
        context.user_data['timezone'] = "Etc/UTC"
    if 'notify_time' in context.user_data:
        user_time = context.user_data['notify_time']
        text += f'\nFor now your time is set to {user_time}'
        keyboard = [
            [InlineKeyboardButton("Skip", callback_data='skip_time')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    message.reply_text(text, reply_markup=reply_markup)

    return TIME


def time(update: Update, context: CallbackContext) -> int:
    """Stores time info about the user and ends the conversation."""
    message = update.message
    chat_id = message.chat_id
    context.user_data['notify_time'] = message.text
    text = get_summary_text(context)
    message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    schedule_request(context, chat_id)
    return ConversationHandler.END


def skip_time(update: Update, context: CallbackContext) -> int:
    """Skips the time and ends the conversation."""
    message = update.callback_query.message
    chat_id = message.chat_id
    message.edit_text(message.text, reply_markup=None)

    text = get_summary_text(context)
    message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    schedule_request(context, chat_id)
    return ConversationHandler.END


def broadcast(update: Update, context: CallbackContext) -> None:
    """Ask for a message for broadcasting."""
    user_id = update.message.from_user.id
    if str(user_id) == DEVELOPER_USER_ID:
        text = 'Send text that will be broadcasted to users'
        update.message.reply_text(text)
        return BROADCAST


def broadcast_to_all(update: Update, context: CallbackContext) -> None:
    """Schedules jobs for broadcasting."""
    bd_message = update.message.text
    users_generator = yield_list(context.bot_data['users'])
    context.job_queue.run_repeating(send_bd_message, context=(users_generator, bd_message, context), interval=1,
                                    name='broadcast')
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels operations and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Alright, if you want to modify something, send /config.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def unknown(update: Update, context: CallbackContext) -> None:
    """Replies if user sends unknown command or text."""
    update.message.reply_text(
        "Sorry, I didn't understand that command. Try using /help",
    )


def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Send message to specific chat
    context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)


def main() -> None:
    """Start the bot."""
    persistence = PicklePersistence(filename='persistence')
    updater = Updater(TOKEN, persistence=persistence)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("stats", stats))
    dispatcher.add_handler(CallbackQueryHandler(config, pattern='^edit_config'))
    dispatcher.add_handler(CallbackQueryHandler(save_or_delete_league, pattern='^league'))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('config', config)],
        states={
            LEAGUES: [CallbackQueryHandler(ask_location, pattern='^set_leagues')],
            LOCATION: [
                MessageHandler(((~Filters.command & Filters.text) | Filters.location), location),
                CallbackQueryHandler(skip_location, pattern='^skip$|^utc$')
            ],
            TIME: [
                MessageHandler(Filters.regex('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'), time),
                CallbackQueryHandler(skip_time, pattern='skip')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler('broadcast', broadcast)],
        states={
            BROADCAST: [MessageHandler((~Filters.command & Filters.text), broadcast_to_all)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(broadcast_conv)
    dispatcher.add_handler(MessageHandler(Filters.all, unknown))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()
