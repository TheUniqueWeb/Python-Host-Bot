import asyncio
import logging
import os
import subprocess
import sys
import shutil
from flask import Flask
from threading import Thread
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- [ KEEP ALIVE SYSTEM ] ---
app = Flask('')
@app.route('/')
def home(): return "Hosting Server is Active!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ CONFIGURATION ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY" 
ADMIN_ID = 7136887795
USER_BOTS = {} # সচল বটগুলো ট্র্যাক করার জন্য {user_id: subprocess_object}

# States
AUTH, DASHBOARD, UPLOAD_BOT, UPLOAD_REQ = range(4)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- [ HELPER FUNCTIONS ] ---

async def save_file(update, context, file_type):
    user_id = update.effective_user.id
    user_dir = f"users/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    file = await context.bot.get_file(update.message.document.file_id)
    file_path = os.path.join(user_dir, "bot.py" if file_type == "bot" else "requirements.txt")
    await file.download_to_drive(file_path)
    
    context.user_data[f'{file_type}_ready'] = True
    return file_path

def get_keyboard(user_id, context):
    b_ok = "✅" if context.user_data.get('bot_ready') else "❌"
    r_ok = "✅" if context.user_data.get('req_ready') else "❌"
    btns = [
        [KeyboardButton(f"📤 Bot.py {b_ok}"), KeyboardButton(f"📜 Req.txt {r_ok}")],
        [KeyboardButton("🚀 Connect & Run Bot")],
        [KeyboardButton("🛑 Stop My Bot"), KeyboardButton("📊 Status")]
    ]
    if user_id == ADMIN_ID: btns.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"<b>💠 ━━━━━ [ HOSTING PRO ] ━━━━━ 💠</b>\n👋 স্বাগতম <b>{user.first_name}</b>\nআপনার বট হোস্ট করতে ভেরিফাই করুন।"
    btn = [[KeyboardButton("🔐 Verify Account", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact.user_id != update.message.from_user.id:
        return AUTH
    await update.message.reply_text("✅ ভেরিফিকেশন সফল!", reply_markup=ReplyKeyboardRemove())
    return await show_dash(update, context)

async def show_dash(update, context):
    user = update.effective_user
    text = f"<b>💎 USER DASHBOARD</b>\n👤 User: <code>{user.first_name}</code>\n📂 ফাইল আপলোড করে কানেক্ট করুন।"
    await update.message.reply_text(text, reply_markup=get_keyboard(user.id, context), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if "Bot.py" in msg:
        await update.message.reply_text("📤 আপনার <code>bot.py</code> ফাইলটি পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOAD_BOT
    elif "Req.txt" in msg:
        await update.message.reply_text("📤 আপনার <code>requirements.txt</code> ফাইলটি পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOAD_REQ
    elif "Connect" in msg:
        return await deploy_bot(update, context)
    elif "Stop" in msg:
        return await stop_bot(update, context)
    return DASHBOARD

async def deploy_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get('bot_ready') or not context.user_data.get('req_ready'):
        await update.message.reply_text("⚠️ আগে দুটি ফাইলই আপলোড করুন!")
        return DASHBOARD

    # যদি আগে থেকে কোনো বট চলে তবে সেটি বন্ধ করা
    if user_id in USER_BOTS:
        USER_BOTS[user_id].terminate()

    status_msg = await update.message.reply_text("🚀 <b>Deployment Started...</b>", parse_mode=ParseMode.HTML)
    user_dir = f"users/{user_id}"

    try:
        # ১. লাইব্রেরি ইন্সটল করা
        await status_msg.edit_text("📦 <b>Installing Requirements...</b>", parse_mode=ParseMode.HTML)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", f"{user_dir}/requirements.txt"])

        # ২. বট রান করা (Subprocess হিসেবে)
        await status_msg.edit_text("⚙️ <b>Starting Bot Process...</b>", parse_mode=ParseMode.HTML)
        process = subprocess.Popen([sys.executable, f"{user_dir}/bot.py"])
        USER_BOTS[user_id] = process

        await asyncio.sleep(2)
        await status_msg.edit_text("✅ <b>Your Bot is now Online!</b>\nএটি এখন ব্যাকগ্রাউন্ডে চলছে।", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)

    return DASHBOARD

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in USER_BOTS:
        USER_BOTS[user_id].terminate()
        del USER_BOTS[user_id]
        await update.message.reply_text("🛑 আপনার বটটি বন্ধ করা হয়েছে।")
    else:
        await update.message.reply_text("ℹ️ আপনার কোনো বট বর্তমানে চলছে না।")
    return DASHBOARD

# --- [ FILE SAVERS ] ---
async def bot_uploader(update, context):
    await save_file(update, context, "bot")
    await update.message.reply_text("✅ bot.py সফলভাবে সেভ হয়েছে।")
    return await show_dash(update, context)

async def req_uploader(update, context):
    await save_file(update, context, "req")
    await update.message.reply_text("✅ requirements.txt সফলভাবে সেভ হয়েছে।")
    return await show_dash(update, context)

# --- [ MAIN ] ---
def main():
    Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, verify)],
            DASHBOARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            UPLOAD_BOT: [MessageHandler(filters.Document.ALL, bot_uploader)],
            UPLOAD_REQ: [MessageHandler(filters.Document.ALL, req_uploader)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    app.add_handler(conv)
    print("Master Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
