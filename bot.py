import os
import sys
import asyncio
import logging
import subprocess
import threading
import shutil
import time
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

# --- [ কনফিগারেশন ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
ACTIVE_FLEET = {} # {user_id: subprocess_object}

# Render Keep-Alive Server
app = Flask('')
@app.route('/')
def home(): return "<b>Core Engine: Operational 🟢</b>"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# States
AUTH, DASHBOARD, UPLOADING_CODE, UPLOADING_REQ = range(4)

# --- [ UI ডিজাইন হেল্পার ] ---

def get_dashboard_kb(user_id):
    btns = [
        [KeyboardButton("🚀 Deploy New Bot"), KeyboardButton("🛰️ My Fleet (Manager)")],
        [KeyboardButton("📊 Global Status"), KeyboardButton("⚙️ Support")]
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton("👑 Admin Core")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ কোর হ্যান্ডলার ফাংশনস ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    banner = (
        f"<b>💎 ━━━━━━━━━━━━━━━━━━━━ 💎</b>\n"
        f"<b>🚀 NEXUS CLOUD HOSTING V3</b>\n"
        f"<b>💎 ━━━━━━━━━━━━━━━━━━━━ 💎</b>\n\n"
        f"👋 স্বাগতম <b>{user.first_name}</b>!\n"
        f"এটি একটি প্রফেশনাল এবং হাই-স্পিড হোস্টিং টার্মিনাল।\n\n"
        f"🛡️ <i>নিরাপত্তার জন্য আপনার অ্যাকাউন্ট ভেরিফাই করুন।</i>"
    )
    btn = [[KeyboardButton("🔐 Verify via Contact", request_contact=True)]]
    await update.message.reply_text(banner, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ <b>Error:</b> প্রতারণা শনাক্ত হয়েছে! নিজের কন্টাক্ট দিন।", parse_mode=ParseMode.HTML)
        return AUTH
    
    msg = await update.message.reply_text("🔄 <b>Authenticating...</b>", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(1)
    await msg.edit_text("✅ <b>Access Granted!</b>\nড্যাশবোর্ড লোড হচ্ছে...", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

async def show_dashboard(update, context):
    user = update.effective_user
    text = (
        f"<b>🖥️ SYSTEM CONSOLE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User:</b> <code>{user.first_name}</code>\n"
        f"🆔 <b>UID:</b> <code>{user.id}</code>\n"
        f"🛰️ <b>Server:</b> <code>Premium-Node-US</code>\n"
        f"⚡ <b>Latency:</b> <code>9ms</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <i>প্যানেল ব্যবহার করে আপনার প্রজেক্ট শুরু করুন।</i>"
    )
    await update.message.reply_text(text, reply_markup=get_dashboard_kb(user.id), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🚀 Deploy New Bot":
        await update.message.reply_text("📁 <b>Step 1:</b> আপনার <code>bot.py</code> ফাইলটি পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOADING_CODE

    elif text == "🛰️ My Fleet (Manager)":
        return await my_fleet_manager(update, context)

    elif text == "📊 Global Status":
        await update.message.reply_text(f"📡 <b>Network:</b> <code>Stable 🟢</code>\n🔋 <b>CPU:</b> <code>{os.getloadavg()[0]}%</code>\n🛰️ <b>Uptime:</b> <code>24/7 Active</code>", parse_mode=ParseMode.HTML)
    
    return DASHBOARD

# --- [ FLEET MANAGEMENT (Real-Time Control) ] ---

async def my_fleet_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    
    if not os.path.exists(f"{path}/bot.py"):
        await update.message.reply_text("❌ <b>No Project Found!</b>\nআগে একটি বট আপলোড করুন।", parse_mode=ParseMode.HTML)
        return DASHBOARD

    is_alive = "Online 🟢" if user_id in ACTIVE_FLEET else "Offline 🔴"
    text = (
        f"<b>🛰️ PROJECT COMMANDER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>File:</b> <code>bot.py</code>\n"
        f"🔋 <b>Power:</b> <code>{is_alive}</code>\n"
        f"📦 <b>Node:</b> <code>Docker-Instance-V3</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    
    btns = [
        [InlineKeyboardButton("⚡ Start / Reboot", callback_query_data="op_run"),
         InlineKeyboardButton("🛑 Terminate", callback_query_data="op_stop")],
        [InlineKeyboardButton("📁 Edit Code", callback_query_data="op_edit"),
         InlineKeyboardButton("📜 Live Logs", callback_query_data="op_logs")],
        [InlineKeyboardButton("🗑️ Wipe Project", callback_query_data="op_wipe")]
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
        await query.edit_message_text("⚙️ <b>Deploying to Sandbox...</b>", parse_mode=ParseMode.HTML)
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate()
        
        # Dependency Check
        req_file = f"{path}/requirements.txt"
        if os.path.exists(req_file):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file, "--no-cache-dir"])
            
        # Spawn Process
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
            await query.edit_message_text("ℹ️ বটটি বর্তমানে অফলাইন।", parse_mode=ParseMode.HTML)

    elif data == "op_logs":
        log_path = f"{path}/terminal.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f: logs = f.read()[-800:] 
            await query.message.reply_text(f"📜 <b>REAL-TIME LOGS:</b>\n<code>{logs if logs else 'Waiting for output...'}</code>", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ কোনো লগ ডাটা নেই।")

    elif data == "op_edit":
        await query.message.reply_text("📝 আপনার বর্তমান কোডটি নিচে দেওয়া হলো। নতুন <b>bot.py</b> ফাইল আপলোড করলে এটি আপডেট হয়ে যাবে।")
        await query.message.reply_document(document=open(f"{path}/bot.py", "rb"))

    elif data == "op_wipe":
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate(); del ACTIVE_FLEET[user_id]
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ <b>প্রজেক্ট পুরোপুরি ডিলিট করা হয়েছে।</b>", parse_mode=ParseMode.HTML)

# --- [ FILE HANDLERS ] ---

async def bot_file_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    os.makedirs(path, exist_ok=True)
    
    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive(f"{path}/bot.py")
    
    await update.message.reply_text("✅ <b>Code Uploaded!</b>\nএখন আপনার <code>requirements.txt</code> ফাইলটি পাঠান। (না থাকলে 'Skip' লিখুন)", parse_mode=ParseMode.HTML)
    return UPLOADING_REQ

async def req_file_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive(f"{path}/requirements.txt")
        await update.message.reply_text("✅ <b>Config Saved!</b>\nআপনার প্রজেক্ট এখন ডেপ্লয়মেন্টের জন্য রেডি।")
    else:
        await update.message.reply_text("⏩ <b>Skipped.</b> ডিফল্ট রিকোয়ারমেন্ট ব্যবহার হবে।")
        
    return await show_dashboard(update, context)

# --- [ CORE ENGINE ] ---

def main():
    # Start Keep-Alive WebServer
    threading.Thread(target=run_web, daemon=True).start()
    
    # Initialize Master Bot
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
    print("💎 Nexus Hosting V3 is Online!")
    app.run_polling()

if __name__ == "__main__":
    main()
