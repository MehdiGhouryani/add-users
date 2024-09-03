from telegram import Update
from telethon.tl.functions.messages import AddChatUserRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telethon import TelegramClient
import os
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import InviteToChannelRequest
import asyncio

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s',level=logging.INFO)

# Define stages of the conversation
API_ID, API_HASH, PHONE_NUMBER, AUTH_CODE, SOURCE_GROUP, TARGET_GROUP = range(6)

# Function to start the conversation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Please enter your API ID:")
    return API_ID

# Function to capture the API ID
async def api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_id'] = update.message.text
    await update.message.reply_text("Now, please enter your API Hash:")
    return API_HASH

# Function to capture the API Hash
async def api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_hash'] = update.message.text
    await update.message.reply_text("Please enter your phone number:")
    return PHONE_NUMBER

# Function to capture the phone number
async def phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone_number'] = update.message.text
    
    # Start the Telethon client for the user session
    client = TelegramClient(f'session_{update.message.from_user.id}', context.user_data['api_id'], context.user_data['api_hash'])
    context.user_data['client'] = client

    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(context.user_data['phone_number'])
        await update.message.reply_text("Enter the code sent to your phone:")
        return AUTH_CODE
    else:
        await update.message.reply_text("You are already authorized. Please enter the source group link:")
        return SOURCE_GROUP

# Function to capture the auth code and finalize authentication
async def auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    client = context.user_data['client']
    
    try:
        await client.sign_in(context.user_data['phone_number'], code)
        await update.message.reply_text("Authentication successful! Now, please enter the source group link:")
        return SOURCE_GROUP
    except Exception as e:
        await update.message.reply_text(f"Authentication failed: {e}")
        return ConversationHandler.END

# Function to capture the source group link
async def source_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['source_group'] = update.message.text
    await update.message.reply_text("Now, please enter the target group link:")
    return TARGET_GROUP

# Function to capture the target group link
async def target_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_group'] = update.message.text
    await update.message.reply_text("Adding members...")

    # Start the process of adding members
    await add_members(update, context)
    return ConversationHandler.END




async def add_members(update, context):
    client = context.user_data['client']
    await client.connect()

    source_group = context.user_data['source_group']
    target_group = context.user_data['target_group']

    try:
        # دریافت اعضای گروه مبدأ
        participants = await client.get_participants(source_group)

        # افزودن اعضا به گروه مقصد
        for user in participants:
            if user.id is not None:
                try:
                    await client(InviteToChannelRequest(target_group, [user.id]))
                    await update.message.reply_text(f"Added {user.username or user.id} to {target_group}")

                    # منتظر ماندن برای 10 ثانیه قبل از افزودن نفر بعدی
                    await asyncio.sleep(10)

                except FloodWaitError as e:
                    await update.message.reply_text(f"Flood wait error: {e}. Waiting for {e.seconds} seconds.")
                    await asyncio.sleep(e.seconds)
                except RPCError as e:
                    await update.message.reply_text(f"RPC error: {e}.")
                except Exception as e:
                    await update.message.reply_text(f"Failed to add {user.username or user.id}: {e}")

        await update.message.reply_text("Finished adding members!")
    
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        await client.disconnect()




async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END

# Main function to set up the bot
if __name__ == '__main__':
    application = ApplicationBuilder().token("7130037834:AAGDXIFEJlIv-MpF9rLehhAjTjPALsGNzYc").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, api_id)],
            API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, api_hash)],
            PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number)],
            AUTH_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_code)],
            SOURCE_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_group)],
            TARGET_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_group)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.run_polling()