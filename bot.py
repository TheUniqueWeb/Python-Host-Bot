import os, sys, asyncio, logging, subprocess, threading, shutil, psutil, time
from flask import Flask
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

# --- [ CORE CONFIG ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
ACTIVE_FLEET = {} # {user_id: process_obj}

# Render Keep-Alive Server
app = Flask('')
@app.route('/')
def home(): return "<h1>Nexus Core: Online 🟢</h1>"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# Logging
logging.basicConfig(level=logging.ERROR)

# States
AUTH, DASHBOARD, UPLOAD_CODE, UPLOAD_REQ = range(4)

# --- [ BEAUTIFUL UI HELPERS ] ---

def get_dashboard_kb(user_id):
    btns = [
        [KeyboardButton("🚀 Deploy New Core"), KeyboardButton("🛰️ My Fleet (Manager)")],
        [KeyboardButton("📊 System Analytics"), KeyboardButton("🛠️ Support Center")]
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton("👑 Admin Master Terminal")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ CORE HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    banner = (
        f"<b>┏━━━━━━━ [ NEXUS CORE ] ━━━━━━━┓</b>\n"
        f"<b>   🚀 NEXT-GEN BOT HOSTING V4  </b>\n"
        f"<b>┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛</b>\n\n"
        f"👋 স্বাগতম <b>{user.first_name}</b>!\n"
        f"এটি একটি আল্ট্রা-ফাস্ট এবং সিকিউর হোস্টিং প্ল্যাটফর্ম।\n\n"
        f"🛡️ <i>ভেরিফাই করতে কন্টাক্ট শেয়ার করুন।</i>"
    )
    btn = [[KeyboardButton("🔐 𝙄𝙣𝙨𝙩𝙖𝙣𝙩 𝙑𝙚𝙧𝙞𝙛𝙮", request_contact=True)]]
    await update.message.reply_text(banner, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ <b>Error:</b> প্রতারণা শনাক্ত হয়েছে!")
        return AUTH
    return await show_dashboard(update, context)

async def show_dashboard(update, context):
    user = update.effective_user
    text = (
        f"<b>🖥️ ━━━━━━ [ DASHBOARD ] ━━━━━━ 🖥️</b>\n\n"
        f"👤 <b>Operator:</b> <code>{user.first_name}</code>\n"
        f"📡 <b>Node:</b> <code>Premium-US-East-1</code>\n"
        f"⚡ <b>Latency:</b> <code>7ms</code>\n"
        f"🔋 <b>Status:</b> <code>Connected 🟢</code>\n\n"
        f"📢 <i>প্যানেল ব্যবহার করে আপনার প্রজেক্ট শুরু করুন।</i>"
    )
    await update.message.reply_text(text, reply_markup=get_dashboard_kb(user.id), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🚀 Deploy New Core":
        await update.message.reply_text("📁 <b>Step 1:</b> আপনার <code>bot.py</code> ফাইলটি ড্রপ করুন।", parse_mode=ParseMode.HTML)
        return UPLOAD_CODE

    elif text == "🛰️ My Fleet (Manager)":
        return await my_fleet_manager(update, context)

    elif text == "📊 System Analytics":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        await update.message.reply_text(
            f"<b>📊 SERVER ANALYTICS</b>\n\n"
            f"💠 <b>CPU Load:</b> <code>{cpu}%</code>\n"
            f"💠 <b>RAM Usage:</b> <code>{ram}%</code>\n"
            f"💠 <b>Network:</b> <code>Stable 🟢</code>\n"
            f"💠 <b>Uptime:</b> <code>99.9%</code>", 
            parse_mode=ParseMode.HTML
        )
    
    elif text == "👑 Admin Master Terminal" and user_id == ADMIN_ID:
        active = len(ACTIVE_FLEET)
        await update.message.reply_text(f"👑 <b>MASTER ADMIN STATS</b>\n\n🚀 <b>Total Running Bots:</b> <code>{active}</code>\n🖥️ <b>Core Status:</b> <code>Optimized</code>", parse_mode=ParseMode.HTML)

    return DASHBOARD

# --- [ ADVANCED FLEET MANAGER ] ---

async def my_fleet_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    
    if not os.path.exists(f"{path}/bot.py"):
        await update.message.reply_text("❌ <b>No Bot Found!</b>\nআগে একটি বট ফাইল আপলোড করুন।", parse_mode=ParseMode.HTML)
        return DASHBOARD

    is_alive = "Online 🟢" if user_id in ACTIVE_FLEET else "Offline 🔴"
    text = (
        f"<b>🛰️ ━━━━ [ CORE MANAGER ] ━━━━ 🛰️</b>\n\n"
        f"📄 <b>File:</b> <code>bot.py</code>\n"
        f"🔌 <b>Power:</b> <code>{is_alive}</code>\n"
        f"📦 <b>Package:</b> <code>Premium-Tier</code>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━</b>"
    )
    
    btns = [
        [InlineKeyboardButton("⚡ Start / Restart", callback_query_data="op_run"),
         InlineKeyboardButton("🛑 Terminate", callback_query_data="op_stop")],
        [InlineKeyboardButton("📜 Live Logs", callback_query_data="op_logs"),
         InlineKeyboardButton("🗑️ Wipe Project", callback_query_data="op_wipe")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def fleet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    path = f"fleet/{user_id}"
    await query.answer()

    if data == "op_run":
        await query.edit_message_text("⚡ <b>Nexus Core Booting...</b>", parse_mode=ParseMode.HTML)
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate()
        
        # Fast Install
        req_file = f"{path}/requirements.txt"
        if os.path.exists(req_file):
            subprocess.Popen([sys.executable, "-m", "pip", "install", "-r", req_file, "--upgrade", "--no-cache-dir"])
            
        # Execute in Background
        log_file = f"{path}/terminal.log"
        with open(log_file, "w") as f:
            proc = subprocess.Popen([sys.executable, f"{path}/bot.py"], stdout=f, stderr=f)
            ACTIVE_FLEET[user_id] = proc
        
        await query.edit_message_text("🚀 <b>বট সফলভাবে লাইভ হয়েছে!</b>\nস্ট্যাটাস: <code>Active 🟢</code>", parse_mode=ParseMode.HTML)

    elif data == "op_stop":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
            await query.edit_message_text("🛑 <b>সার্ভার বন্ধ করা হয়েছে।</b>", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("ℹ️ বটটি অফলাইন আছে।", parse_mode=ParseMode.HTML)

    elif data == "op_logs":
        log_path = f"{path}/terminal.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f: logs = f.read()[-800:] 
            await query.message.reply_text(f"📜 <b>TERMINAL OUTPUT:</b>\n<code>{logs if logs else 'Waiting for data...'}</code>", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ লগ ডাটা নেই।")

    elif data == "op_wipe":
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate(); del ACTIVE_FLEET[user_id]
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ <b>প্রজেক্ট পুরোপুরি ক্লিন করা হয়েছে।</b>", parse_mode=ParseMode.HTML)

# --- [ FILE RECEIVERS ] ---

async def bot_file_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    os.makedirs(path, exist_ok=True)
    
    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive(f"{path}/bot.py")
    await update.message.reply_text("✅ <b>Binary Received!</b>\nএখন আপনার <code>requirements.txt</code> দিন। (না থাকলে 'skip' লিখুন)", parse_mode=ParseMode.HTML)
    return UPLOADING_REQ

async def req_file_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive(f"{path}/requirements.txt")
    
    await update.message.reply_text("✅ <b>System Configured!</b>\nআপনার প্রজেক্ট এখন রেডি।", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

# --- [ ENGINE START ] ---

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_check)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dashboard),
                CallbackQueryHandler(fleet_callback)
            ],
            UPLOADING_CODE: [MessageHandler(filters.Document.ALL, bot_file_rec)],
            UPLOADING_REQ: [MessageHandler(filters.Document.ALL | filters.Regex("(?i)skip"), req_file_rec)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    app.add_handler(conv_handler)
    print("💎 Nexus Core V4 is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
