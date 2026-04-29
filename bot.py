import os
import sys
import asyncio
import logging
import shutil
import psutil
from flask import Flask
from threading import Thread
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

# --- [ CONFIGURATION ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
ACTIVE_FLEET = {}  # {user_id: process_object}

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# States
AUTH, DASHBOARD, UPLOAD_CODE, UPLOAD_REQ = range(4)

# --- [ WEB SERVER FOR RENDER ] ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "<b>MR BOT MANAGER IS ONLINE 🚀</b>", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ UI HELPERS ] ---
def get_main_kb(user_id):
    btns = [
        [KeyboardButton("🚀 Deploy Bot"), KeyboardButton("🛰️ My Fleet")],
        [KeyboardButton("📊 Stats"), KeyboardButton("🛠️ Support")]
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ CORE HANDLERS ] ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"<b>🤖 MR BOT MANAGER V5</b>\n\n"
        f"স্বাগতম <b>{user.first_name}</b>!\n"
        f"আপনার নিজস্ব বট হোস্টিং করার জন্য নিচের বাটনটি চাপুন।"
    )
    btn = [[KeyboardButton("🔐 Verify Account", request_contact=True)]]
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ জালিয়াতি ধরা পড়েছে!")
        return AUTH
    
    await update.message.reply_text("✅ ভেরিফিকেশন সফল! আপনার ড্যাশবোর্ড ওপেন হচ্ছে...", reply_markup=get_main_kb(update.effective_user.id))
    return DASHBOARD

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🚀 Deploy Bot":
        await update.message.reply_text("📂 আপনার মেইন ফাইলটি (যেমন: <code>bot.py</code>) ডকুমেন্ট হিসেবে পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOAD_CODE
    
    elif text == "🛰️ My Fleet":
        return await show_fleet(update, context)
    
    elif text == "📊 Stats":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        active = len(ACTIVE_FLEET)
        msg = (
            f"<b>📊 SERVER STATUS</b>\n\n"
            f"🖥️ CPU Usage: {cpu}%\n"
            f"🧠 RAM Usage: {ram}%\n"
            f"🛰️ Active Bots: {active}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    return DASHBOARD

# --- [ BOT MANAGEMENT SYSTEM ] ---
async def show_fleet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}/bot.py"
    
    if not os.path.exists(path):
        await update.message.reply_text("❌ আপনার কোনো বট আপলোড করা নেই।")
        return DASHBOARD
    
    status = "🟢 Online" if user_id in ACTIVE_FLEET else "🔴 Offline"
    btns = [
        [InlineKeyboardButton("⚡ Start", callback_query_data="run"),
         InlineKeyboardButton("🛑 Stop", callback_query_data="stop")],
        [InlineKeyboardButton("📜 View Logs", callback_query_data="logs"),
         InlineKeyboardButton("🗑️ Wipe Bot", callback_query_data="wipe")]
    ]
    await update.message.reply_text(
        f"<b>🤖 BOT MANAGER</b>\n\nStatus: <code>{status}</code>\nPath: <code>/fleet/{user_id}/</code>",
        reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML
    )
    return DASHBOARD

async def fleet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    path = f"fleet/{user_id}"
    await query.answer()

    if query.data == "run":
        if user_id in ACTIVE_FLEET:
            await query.edit_message_text("⚠️ বট অলরেডি রানিং আছে।")
            return
        
        # Start Non-blocking Subprocess
        log_file = open(f"{path}/terminal.log", "w")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, f"{path}/bot.py",
                stdout=log_file, stderr=log_file
            )
            ACTIVE_FLEET[user_id] = proc
            await query.edit_message_text("🚀 বট সফলভাবে লাইভ করা হয়েছে!")
        except Exception as e:
            await query.edit_message_text(f"❌ এরর: {str(e)}")

    elif query.data == "stop":
        if user_id in ACTIVE_FLEET:
            proc = ACTIVE_FLEET[user_id]
            proc.terminate()
            del ACTIVE_FLEET[user_id]
            await query.edit_message_text("🛑 বট বন্ধ করা হয়েছে।")
        else:
            await query.edit_message_text("❌ বটটি বর্তমানে চালু নেই।")

    elif query.data == "logs":
        log_path = f"{path}/terminal.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = f.read()[-1000:] # শেষ ১০০০ অক্ষর
            await query.message.reply_text(f"<b>📜 Last Logs:</b>\n<code>{logs or 'No logs yet.'}</code>", parse_mode=ParseMode.HTML)
        else:
            await query.answer("কোনো লগ ফাইল পাওয়া যায়নি।")

    elif query.data == "wipe":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ আপনার বটের সব ফাইল ডিলিট করা হয়েছে।")

# --- [ FILE RECEIVERS ] ---
async def bot_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    
    if not doc.file_name.endswith('.py'):
        await update.message.reply_text("❌ শুধুমাত্র .py ফাইল পাঠান।")
        return UPLOAD_CODE

    os.makedirs(f"fleet/{user_id}", exist_ok=True)
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(f"fleet/{user_id}/bot.py")
    
    await update.message.reply_text("✅ Code Saved! এখন <code>requirements.txt</code> পাঠান অথবা <b>/skip</b> লিখুন।", parse_mode=ParseMode.HTML)
    return UPLOAD_REQ

async def req_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(f"fleet/{user_id}/requirements.txt")
        
        # স্বয়ংক্রিয়ভাবে লাইব্রেরি ইন্সটল করার চেষ্টা
        await update.message.reply_text("📦 Installing dependencies... please wait.")
        os.system(f"pip install -r fleet/{user_id}/requirements.txt")
    
    await update.message.reply_text("✅ সেটআপ সম্পন্ন! /start দিয়ে ড্যাশবোর্ডে যান।")
    return await show_dash_minimal(update, context)

async def show_dash_minimal(update, context):
    await update.message.reply_text("🎮 Dashboard Ready!", reply_markup=get_main_kb(update.effective_user.id))
    return DASHBOARD

# --- [ MAIN EXECUTION ] ---
def main():
    # Flask Web Server in Thread
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    # Telegram Bot
    application = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_handler)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu),
                CallbackQueryHandler(fleet_callback)
            ],
            UPLOAD_CODE: [MessageHandler(filters.Document.ALL, bot_rec)],
            UPLOAD_REQ: [
                MessageHandler(filters.Document.ALL, req_rec),
                CommandHandler("skip", req_rec)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv)
    
    print("🚀 MR BOT MANAGER is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
