import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telethon import TelegramClient
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.functions.auth import SendCodeRequest, SignInRequest
from telethon.tl.types import User

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(name)

# Create a dictionary to store sessions and client objects for each user
user_sessions = {}

async def add_users_to_contacts(client, group_link):
    try:
        entity = await client.get_entity(group_link)
        usernames_added = 0

        async for user in client.iter_participants(entity):
            if usernames_added >= 100:
                break
            if isinstance(user, User) and user.username:
                username = user.username
                logger.info(f'Adding username: {username}')
                try:
                    await client(AddContactRequest(phone=username, first_name=username, last_name=''))
                    usernames_added += 1
                except Exception as e:
                    logger.error(f'Failed to add {username}: {e}')
        return usernames_added
    except Exception as e:
        logger.error(f'Error in add_users_to_contacts: {e}')
        return 0

async def handle_request(api_id, api_hash, phone_number, code, group_link, chat_id):
    # Ensure the directory exists
    session_dir = 'sessions'
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    session_file = f'{session_dir}/{phone_number}.session'
    async with TelegramClient(session_file, api_id, api_hash) as client:
        await client.connect()
        
        if not await client.is_user_authorized():
            try:
                await client(SendCodeRequest(phone_number))
                if code:
                    await client(SignInRequest(phone_number, code))
                else:
                    await client.send_message(chat_id, "Please provide the verification code sent to your phone.")
                    logger.info('Verification code request sent. Awaiting user input.')
                    return
            except Exception as e:
                await client.send_message(chat_id, f"Error during authentication: {e}")
                logger.error(f'Error during authentication: {e}')
                return
        
        logger.info('Authentication successful, processing request...')
        await client.send_message(chat_id, "Operation in progress...")
        added_count = await add_users_to_contacts(client, group_link)
        await client.send_message(chat_id, f'{added_count} usernames have been added to contacts.')
        logger.info(f'{added_count} usernames added to contacts.')

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Send /setup to configure the bot.')
    logger.info(f'Start command received from user {update.message.from_user.id}')

async def setup(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': 'awaiting_data'}
    await update.message.reply_text('Please provide your API ID:')
    logger.info(f'Setup command received from user {user_id}')

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data = user_sessions.get(user_id, {})
    
    if user_data.get('state') == 'awaiting_data':
        text = update.message.text
        if 'api_id' not in user_data:
            user_data['api_id'] = text
            await update.message.reply_text('Please provide your API Hash:')        

            logger.info(f'Received API ID from user {user_id}')
        elif 'api_hash' not in user_data:
            user_data['api_hash'] = text
            await update.message.reply_text('Please provide your Phone Number:')
            logger.info(f'Received API Hash from user {user_id}')
        elif 'phone_number' not in user_data:
            user_data['phone_number'] = text
            await update.message.reply_text('Please provide your Verification Code (if applicable):')
            logger.info(f'Received Phone Number from user {user_id}')
        elif 'verification_code' not in user_data:
            user_data['verification_code'] = text
            await update.message.reply_text('Please provide the group link:')
            logger.info(f'Received Verification Code from user {user_id}')
        else:
            user_data['group_link'] = text
            await update.message.reply_text('Processing your request...')
            logger.info(f'Received group link from user {user_id}, starting processing.')
            await handle_request(
                api_id=user_data['api_id'],
                api_hash=user_data['api_hash'],
                phone_number=user_data['phone_number'],
                code=user_data.get('verification_code', ''),
                group_link=user_data['group_link'],
                chat_id=update.message.chat_id
            )
            user_data['state'] = 'completed'
    else:
        await update.message.reply_text('Please start the setup process by sending /setup.')
        logger.info(f'User {user_id} attempted to interact outside of setup process.')

def main():
    # Replace 'YOUR_BOT_API_TOKEN' with your actual Telegram Bot API token
    application = Application.builder().token('7130037834:AAGDXIFEJlIv-MpF9rLehhAjTjPALsGNzYc').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('setup', setup))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info('Bot is starting...')
    application.run_polling()
    logger.info('Bot is running.')

    main()
if __name__ == '__main__':
    main()