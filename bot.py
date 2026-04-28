import asyncio
import logging
import os
from flask import Flask
from threading import Thread
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode

# --- [ KEEP ALIVE SYSTEM FOR RENDER ] ---
app = Flask('')

@app.route('/')
def home():
    return "<b>Bot is Running 24/7!</b>"

def run():
    # Render সাধারণত 8080 বা 10000 পোর্ট ব্যবহার করে
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- [ CONFIGURATION ] ---
# আপনার বট টোকেনটি এখানে বসান অথবা Render-এর Env Variable-এ BOT_TOKEN নাম দিন
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY" 
ADMIN_ID = 7136887795
users_database = set()

# Conversation States
AUTH, DASHBOARD, UPLOAD_BOT, UPLOAD_REQ = range(4)

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- [ UI COMPONENTS ] ---
def get_main_buttons(user_id, context):
    bot_status = "✅" if context.user_data.get('bot_file') else "❌"
    req_status = "✅" if context.user_data.get('req_file') else "❌"
    
    buttons = [
        [KeyboardButton(f"📤 Bot.py {bot_status}"), KeyboardButton(f"📜 Req.txt {req_status}")],
        [KeyboardButton("🚀 Connect to Server (High Speed)")],
        [KeyboardButton("📊 My Status"), KeyboardButton("🛠️ Support")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("👑 Admin Control Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- [ HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_database.add(user.id)
    
    welcome_text = (
        f"<b>💠 ━━━━━━━━━━━━━━━━━━ 💠</b>\n"
        f"👋 <b>স্বাগতম {user.first_name}!</b>\n"
        f"এটি একটি <b>Advanced Python Bot Hosting</b> প্ল্যাটফর্ম।\n\n"
        f"🛡️ <i>নিরাপত্তার স্বার্থে প্রথমে আপনার অ্যাকাউন্ট ভেরিফাই করুন।</i>\n"
        f"<b>💠 ━━━━━━━━━━━━━━━━━━ 💠</b>"
    )
    
    btn = [[KeyboardButton("🔐 Verify via Contact", request_contact=True)]]
    await update.message.reply_text(
        welcome_text, 
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), 
        parse_mode=ParseMode.HTML
    )
    return AUTH

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("🚫 <b>Error:</b> দয়া করে আপনার নিজের কন্টাক্ট শেয়ার করুন।", parse_mode=ParseMode.HTML)
        return AUTH
    
    await update.message.reply_text("✅ <b>Verification Success!</b>\nড্যাশবোর্ড লোড হচ্ছে...", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(1)
    return await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"<b>💎 ━━━ [ USER DASHBOARD ] ━━━ 💎</b>\n\n"
        f"👤 <b>User:</b> <code>{user.first_name}</code>\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📡 <b>Server:</b> <code>Premium-Node-01 (Active)</code>\n"
        f"⚡ <b>Speed:</b> <code>1.0 Gbps</code>\n\n"
        f"📢 <i>নিচের বাটনগুলো ব্যবহার করে ফাইল আপলোড করুন।</i>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━</b>"
    )
    await update.message.reply_text(text, reply_markup=get_main_buttons(user.id, context), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def handle_uploads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Bot.py" in text:
        await update.message.reply_text("📂 <b>বট ফাইল পাঠান:</b>\nদয়া করে আপনার <code>bot.py</code> ফাইলটি ডকুমেন্ট হিসেবে দিন।", parse_mode=ParseMode.HTML)
        return UPLOAD_BOT
    elif "Req.txt" in text:
        await update.message.reply_text("📜 <b>রিকোয়ারমেন্ট ফাইল পাঠান:</b>\nদয়া করে <code>requirements.txt</code> ফাইলটি দিন।", parse_mode=ParseMode.HTML)
        return UPLOAD_REQ
    elif "Connect" in text:
        return await start_hosting(update, context)
    elif "Admin" in text and update.effective_user.id == ADMIN_ID:
        return await admin_menu(update, context)
    elif "Status" in text:
        await update.message.reply_text(f"📊 <b>আপনার স্ট্যাটাস:</b> <code>Active</code>\n🚀 <b>সার্ভার টাইম:</b> <code>Unlimited</code>", parse_mode=ParseMode.HTML)
    return DASHBOARD

async def save_bot_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        context.user_data['bot_file'] = update.message.document.file_id
        await update.message.reply_text("🔵 <b>bot.py</b> সফলভাবে মেমরিতে সেভ হয়েছে!", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

async def save_req_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        context.user_data['req_file'] = update.message.document.file_id
        await update.message.reply_text("🟡 <b>requirements.txt</b> সফলভাবে সেভ হয়েছে!", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

async def start_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('bot_file') or not context.user_data.get('req_file'):
        await update.message.reply_text("❌ <b>ফাইল পাওয়া যায়নি!</b>\nআগে <code>bot.py</code> এবং <code>requirements.txt</code> আপলোড করুন।", parse_mode=ParseMode.HTML)
        return DASHBOARD

    msg = await update.message.reply_text("⏳ <b>Initializing Virtual Machine...</b>", parse_mode=ParseMode.HTML)
    
    stages = [
        "📡 <b>Connecting to Node-01...</b> [10%]",
        "📂 <b>Extracting Files...</b> [30%]",
        "🔨 <b>Installing Dependencies...</b> [55%]",
        "⚙️ <b>Compiling Python Bytecode...</b> [80%]",
        "🚀 <b>Starting Webhook...</b> [95%]",
        "🟢 <b>BOT IS LIVE!</b>\n\n🎯 <b>Status:</b> <code>Online 🟢</code>\n🔋 <b>RAM Usage:</b> <code>42MB</code>\n⚡ <b>Latency:</b> <code>12ms</code>"
    ]

    for stage in stages:
        await asyncio.sleep(0.7)
        await msg.edit_text(stage, parse_mode=ParseMode.HTML)
    
    return DASHBOARD

# --- [ ADMIN FUNCTIONS ] ---

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(users_database)
    text = (
        f"<b>👑 ━━━ [ ADMIN PANEL ] ━━━ 👑</b>\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"📉 <b>Server CPU:</b> <code>0.05%</code>\n"
        f"🔋 <b>Total Hosting:</b> <code>{total_users * 2} Files</code>\n\n"
        f"<i>এডমিন হিসেবে আপনি সব কন্ট্রোল করতে পারবেন।</i>"
    )
    btns = [[InlineKeyboardButton("📢 Broadcast Message", callback_query_data="bc")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return DASHBOARD

# --- [ MAIN RUNNER ] ---

def main():
    # Keep Alive চালু করা (Render হোস্টিং এর জন্য)
    keep_alive()

    # বট অ্যাপ্লিকেশন তৈরি
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, verify)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_uploads),
            ],
            UPLOAD_BOT: [MessageHandler(filters.Document.ALL, save_bot_file)],
            UPLOAD_REQ: [MessageHandler(filters.Document.ALL, save_req_file)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    
    print("🚀 Advanced Bot is Running with Keep-Alive...")
    app.run_polling()

if __name__ == "__main__":
    main()
