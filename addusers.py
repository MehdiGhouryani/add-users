from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
import asyncio
from dotenv import load_dotenv
import os


load_dotenv()
token=os.getenv('Token')

# توکن ربات تلگرام


# ذخیره‌سازی موقتی اطلاعات کاربران
user_data = {}

# تابع برای دریافت API ID
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {'api_id': update.message.text}
    await update.message.reply_text("API Hash خود را ارسال کنید:")

# تابع برای دریافت API Hash
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data[user_id]['api_hash'] = update.message.text
        await update.message.reply_text("لطفاً دستور /addusers را با شناسه گروه منبع و هدف وارد کنید.")
    else:
        await update.message.reply_text("لطفاً ابتدا API ID خود را ارسال کنید.")

# تابع برای شروع تعامل با ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً API ID خود را ارسال کنید:")

# تابع برای اضافه کردن کاربران
async def add_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data or 'api_hash' not in user_data[user_id]:
        await update.message.reply_text("لطفاً ابتدا API ID و API Hash خود را ارسال کنید.")
        return

    api_id = int(user_data[user_id]['api_id'])
    api_hash = user_data[user_id]['api_hash']

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("لطفاً دستور را به صورت صحیح وارد کنید: /addusers source_group_id target_group_id")
            return

        source_group_id = args[0]
        target_group_id = args[1]

        async with TelegramClient('session_name', api_id, api_hash) as client:
            participants = await client.get_participants(source_group_id)
            users_with_username = [p for p in participants if p.username]

            # تقسیم کاربران به دسته‌ها
            batch_size = 50
            for i in range(0, len(users_with_username), batch_size):
                batch = users_with_username[i:i + batch_size]
                await client(InviteToChannelRequest(target_group_id, batch))
                await update.message.reply_text(f"کاربران {i+1} تا {i+len(batch)} اضافه شدند.")
                await asyncio.sleep(10)  # تاخیر 10 ثانیه‌ای بین دسته‌ها

            await update.message.reply_text("تمام کاربران با موفقیت اضافه شدند!")
    except Exception as e:
        await update.message.reply_text(f"خطایی رخ داد: {e}")

# تابع اصلی برای راه‌اندازی ربات
def main():
    app = Application.builder().token(token).build()

    # اضافه کردن handlerها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addusers", add_users))
    app.add_handler(MessageHandler(filters.Regex(r'^\d+$'), get_api_id))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), get_api_hash))

    # شروع سرویس‌دهی ربات
    app.run_polling()

if __name__ == '__main__':
    main()