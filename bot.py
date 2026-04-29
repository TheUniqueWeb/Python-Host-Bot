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
ACTIVE_FLEET = {}
USER_LIST = set() # ইউজারের ডাটা রাখার জন্য (বট রিস্টার্ট দিলে এটি খালি হয়ে যাবে, তবে কাজ করবে)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States
AUTH, DASHBOARD, UPLOAD_CODE, UPLOAD_REQ, ADMIN_STATE = range(5)

# --- [ WEB SERVER FOR RENDER ] ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "MR BOT MANAGER IS LIVE 🚀", 200

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

def get_admin_kb():
    btns = [
        [InlineKeyboardButton("📢 Broadcast", callback_query_data="admin_bc")],
        [InlineKeyboardButton("👥 User Stats", callback_query_data="admin_users")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_query_data="back_to_dash")]
    ]
    return InlineKeyboardMarkup(btns)

# --- [ HANDLERS ] ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_LIST.add(user_id)
    
    text = (
        f"<b>🤖 MR BOT MANAGER V5</b>\n\n"
        f"স্বাগতম <b>{update.effective_user.first_name}</b>!\n"
        f"নিচের বাটন চেপে একাউন্ট ভেরিফাই করুন।"
    )
    btn = [[KeyboardButton("🔐 Verify Account", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ জালিয়াতি করবেন না!")
        return AUTH
    
    await update.message.reply_text("✅ ভেরিফিকেশন সফল!", reply_markup=get_main_kb(update.effective_user.id))
    return DASHBOARD

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🚀 Deploy Bot":
        await update.message.reply_text("📂 আপনার <b>bot.py</b> ফাইলটি ডকুমেন্ট হিসেবে পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOAD_CODE
    
    elif text == "🛰️ My Fleet":
        return await show_fleet(update, context)
    
    elif text == "📊 Stats":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        await update.message.reply_text(f"📊 <b>SERVER STATS</b>\n\nCPU: {cpu}%\nRAM: {ram}%", parse_mode=ParseMode.HTML)
        return DASHBOARD

    elif text == "👑 Admin Panel":
        if user_id == ADMIN_ID:
            await update.message.reply_text("👑 <b>WELCOME ADMIN</b>\nকন্ট্রোল প্যানেল সিলেক্ট করুন:", 
                                           reply_markup=get_admin_kb(), parse_mode=ParseMode.HTML)
            return DASHBOARD # Keep in dashboard to handle callbacks
        else:
            await update.message.reply_text("🚫 আপনার এই পারমিশন নেই।")
            return DASHBOARD
    
    return DASHBOARD

# --- [ BOT MANAGEMENT LOGIC ] ---
async def show_fleet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}/bot.py"
    
    if not os.path.exists(path):
        await update.message.reply_text("❌ আপনার কোনো বট নেই। আগে Deploy করুন।")
        return DASHBOARD
    
    status = "🟢 Online" if user_id in ACTIVE_FLEET else "🔴 Offline"
    btns = [
        [InlineKeyboardButton("⚡ Start", callback_query_data="run"),
         InlineKeyboardButton("🛑 Stop", callback_query_data="stop")],
        [InlineKeyboardButton("📜 Logs", callback_query_data="logs"),
         InlineKeyboardButton("🗑️ Wipe", callback_query_data="wipe")]
    ]
    await update.message.reply_text(f"🤖 <b>Bot Manager</b>\nStatus: {status}", 
                                   reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    # Admin Callbacks
    if data == "admin_users":
        await query.message.reply_text(f"👥 <b>Total Users:</b> {len(USER_LIST)}", parse_mode=ParseMode.HTML)
    
    elif data == "admin_bc":
        await query.message.reply_text("📝 ব্রডকাস্ট মেসেজটি লিখুন:")
        # এখানে ব্রডকাস্ট লজিক যোগ করা যায়

    # Fleet Callbacks
    path = f"fleet/{user_id}"
    if data == "run":
        if user_id in ACTIVE_FLEET:
            await query.edit_message_text("⚠️ অলরেডি রানিং!")
        else:
            log_file = open(f"{path}/terminal.log", "w")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, f"{path}/bot.py", stdout=log_file, stderr=log_file
            )
            ACTIVE_FLEET[user_id] = proc
            await query.edit_message_text("🚀 বট লাইভ হয়েছে!")

    elif data == "stop":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
            await query.edit_message_text("🛑 বট বন্ধ করা হয়েছে।")
        else:
            await query.edit_message_text("❌ কোনো বট চালু নেই।")

    elif data == "logs":
        log_p = f"{path}/terminal.log"
        if os.path.exists(log_p):
            with open(log_p, "r") as f: logs = f.read()[-500:]
            await query.message.reply_text(f"📜 <b>Logs:</b>\n<code>{logs}</code>", parse_mode=ParseMode.HTML)
    
    elif data == "wipe":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ ফাইল ডিলিট করা হয়েছে।")

# --- [ FILE UPLOAD SYSTEM ] ---
async def bot_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.document: return UPLOAD_CODE
    
    os.makedirs(f"fleet/{user_id}", exist_ok=True)
    f = await context.bot.get_file(update.message.document.file_id)
    await f.download_to_drive(f"fleet/{user_id}/bot.py")
    await update.message.reply_text("✅ Code Saved! এখন <b>requirements.txt</b> দিন (অথবা /skip লিখুন)।", parse_mode=ParseMode.HTML)
    return UPLOAD_REQ

async def req_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        f = await context.bot.get_file(update.message.document.file_id)
        await f.download_to_drive(f"fleet/{user_id}/requirements.txt")
        os.system(f"pip install -r fleet/{user_id}/requirements.txt")
    
    await update.message.reply_text("✅ সব সেট! ড্যাশবোর্ড থেকে স্টার্ট করুন।", reply_markup=get_main_kb(user_id))
    return DASHBOARD

# --- [ MAIN ] ---
def main():
    Thread(target=run_web, daemon=True).start()

    app_bot = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_handler)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu),
                CallbackQueryHandler(callback_handler)
            ],
            UPLOAD_CODE: [MessageHandler(filters.Document.ALL, bot_rec)],
            UPLOAD_REQ: [
                MessageHandler(filters.Document.ALL, req_rec),
                CommandHandler("skip", req_rec)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    app_bot.add_handler(conv)
    print("🚀 MR BOT MANAGER V5 STARTED")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
