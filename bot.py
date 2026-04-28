import os
import sys
import asyncio
import logging
import subprocess
import threading
from flask import Flask
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- [ CONFIGURATION ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
USER_PROCESSES = {} # ডাইনামিক প্রসেস ট্র্যাকিং

# Flask Server for Render (Keep Alive)
app = Flask('')
@app.route('/')
def home(): return "<b>System Status: Online 🟢</b>"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# States
AUTH, MENU, UPLOADING_BOT, UPLOADING_REQ = range(4)

# --- [ UI KEYBOARDS ] ---
def main_menu(user_id, context):
    b_stat = "✅" if context.user_data.get('bot_path') else "❌"
    r_stat = "✅" if context.user_data.get('req_path') else "❌"
    
    buttons = [
        [KeyboardButton(f"📂 Bot.py {b_stat}"), KeyboardButton(f"📜 Req.txt {r_stat}")],
        [KeyboardButton("🚀 Connect & Host Bot")],
        [KeyboardButton("🛑 Stop My Bot"), KeyboardButton("📊 Server Status")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- [ HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"<b>💎 ━━━ [ REAL VPS HOSTING ] ━━━ 💎</b>\n\n"
        f"👋 স্বাগতম <b>{user.first_name}</b>!\n"
        f"এটি একটি রিয়েল-টাইম পাইথন হোস্টিং টার্মিনাল।\n\n"
        f"🛡️ <i>নিরাপত্তার জন্য আপনার কন্টাক্ট শেয়ার করে ভেরিফাই করুন।</i>"
    )
    btn = [[KeyboardButton("🔐 Verify via Contact", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ <b>প্রতারণা শনাক্ত!</b> নিজের কন্টাক্ট দিন।", parse_mode=ParseMode.HTML)
        return AUTH
    
    await update.message.reply_text("✅ ভেরিফিকেশন সফল! ড্যাশবোর্ড লোড হচ্ছে...", reply_markup=ReplyKeyboardRemove())
    return await show_dashboard(update, context)

async def show_dashboard(update, context):
    user = update.effective_user
    text = (
        f"<b>🖥️ SYSTEM DASHBOARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: <code>{user.first_name}</code>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📡 Node: <code>Render-Premium-01</code>\n\n"
        f"📢 <i>নিচের বাটন থেকে ফাইল আপলোড করুন।</i>"
    )
    await update.message.reply_text(text, reply_markup=main_menu(user.id, context), parse_mode=ParseMode.HTML)
    return MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Bot.py" in text:
        await update.message.reply_text("📥 আপনার <code>bot.py</code> ফাইলটি ডকুমেন্ট হিসেবে পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOADING_BOT
    elif "Req.txt" in text:
        await update.message.reply_text("📥 আপনার <code>requirements.txt</code> ফাইলটি পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOADING_REQ
    elif "Connect" in text:
        return await start_real_hosting(update, context)
    elif "Stop" in text:
        return await stop_bot(update, context)
    elif "Admin Panel" in text and update.effective_user.id == ADMIN_ID:
        active = len(USER_PROCESSES)
        await update.message.reply_text(f"👑 <b>Admin Stats:</b>\n\n🚀 Active Bots: <code>{active}</code>\n🔋 Server: <code>Online</code>", parse_mode=ParseMode.HTML)
    return MENU

# --- [ FILE HANDLERS ] ---

async def save_file(update, context, type):
    user_id = update.effective_user.id
    user_dir = f"vps/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    
    if type == "bot":
        path = f"{user_dir}/bot.py"
        context.user_data['bot_path'] = path
    else:
        path = f"{user_dir}/requirements.txt"
        context.user_data['req_path'] = path
        
    await file.download_to_drive(path)
    await update.message.reply_text(f"✅ <b>{doc.file_name}</b> সেভ হয়েছে।", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

# --- [ REAL TERMINAL ENGINE ] ---

async def start_real_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_file = context.user_data.get('bot_path')
    req_file = context.user_data.get('req_path')

    if not bot_file or not req_file:
        await update.message.reply_text("❌ ফাইল পাওয়া যায়নি! আগে Bot.py এবং Req.txt আপলোড করুন।")
        return MENU

    if user_id in USER_PROCESSES:
        await update.message.reply_text("⚠️ একটি বট অলরেডি চলছে। সেটি আগে Stop করুন।")
        return MENU

    log = await update.message.reply_text("⚙️ <b>টার্মিনাল বুট হচ্ছে...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # ১. রিয়েল ডিপেন্ডেন্সি ইন্সটল
        await log.edit_text("📦 <b>Installing Dependencies...</b>", parse_mode=ParseMode.HTML)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file])

        # ২. ব্যাকগ্রাউন্ড প্রসেস লঞ্চ
        await log.edit_text("🚀 <b>Executing Script...</b>", parse_mode=ParseMode.HTML)
        p = subprocess.Popen([sys.executable, bot_file])
        USER_PROCESSES[user_id] = p
        
        await asyncio.sleep(2)
        await log.edit_text(
            f"✅ <b>বট এখন আপনার সার্ভারে লাইভ!</b>\n\n"
            f"📊 PID: <code>{p.pid}</code>\n"
            f"🟢 Status: <code>Running</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await log.edit_text(f"💥 <b>Terminal Error:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    return MENU

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in USER_PROCESSES:
        USER_PROCESSES[user_id].terminate()
        del USER_PROCESSES[user_id]
        await update.message.reply_text("🛑 <b>বট সফলভাবে বন্ধ করা হয়েছে।</b>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("ℹ️ কোনো সচল বট পাওয়া যায়নি।")
    return MENU

# --- [ MAIN RUNNER ] ---

def main():
    # Flask Start
    threading.Thread(target=run_web, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_handler)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            UPLOADING_BOT: [MessageHandler(filters.Document.ALL, lambda u, c: save_file(u, c, "bot"))],
            UPLOADING_REQ: [MessageHandler(filters.Document.ALL, lambda u, c: save_file(u, c, "req"))],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    print("💎 Master Hosting Bot is Live!")
    app.run_polling()

if __name__ == "__main__":
    main()
