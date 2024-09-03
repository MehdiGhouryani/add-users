import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telethon import TelegramClient
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import User

# Create a dictionary to store sessions and client objects for each user
user_sessions = {}

async def add_users_to_contacts(client, group_link):
    entity = await client.get_entity(group_link)
    usernames_added = 0

    async for user in client.iter_participants(entity):
        if usernames_added >= 100:
            break
        if isinstance(user, User) and user.username:
            username = user.username
            print(f'Adding username: {username}')
            try:
                await client(AddContactRequest(phone=username, first_name=username, last_name=''))
                usernames_added += 1
            except Exception as e:
                print(f'Failed to add {username}: {e}')
    return usernames_added

async def handle_request(api_id, api_hash, phone_number, code, group_link, chat_id):
    async with TelegramClient(f'sessions/{phone_number}', api_id, api_hash) as client:
        await client.start(phone_number, code)
        await client.send_message(chat_id, "Operation in progress...")
        added_count = await add_users_to_contacts(client, group_link)
        await client.send_message(chat_id, f'{added_count} usernames have been added to contacts.')

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Send /setup to configure the bot.')

async def setup(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': 'awaiting_data'}
    await update.message.reply_text('Please provide your API ID:')

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data = user_sessions.get(user_id, {})
    
    if user_data.get('state') == 'awaiting_data':
        text = update.message.text
        if 'api_id' not in user_data:
            user_data['api_id'] = text
            await update.message.reply_text('Please provide your API Hash:')
        elif 'api_hash' not in user_data:
            user_data['api_hash'] = text
            await update.message.reply_text('Please provide your Phone Number:')
        elif 'phone_number' not in user_data:
            user_data['phone_number'] = text
            await update.message.reply_text('Please provide your Verification Code (if applicable):')
        elif 'verification_code' not in user_data:
            user_data['verification_code'] = text
            await update.message.reply_text('Please provide the group link:')
        else:
            user_data['group_link'] = text
            await update.message.reply_text('Processing your request...')
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

def main():
    # Replace 'YOUR_BOT_API_TOKEN' with your actual Telegram Bot API token
    application = Application.builder().token('7130037834:AAGDXIFEJlIv-MpF9rLehhAjTjPALsGNzYc').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('setup', setup))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()