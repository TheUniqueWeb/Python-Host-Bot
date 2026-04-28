import os
import sys
import asyncio
import logging
import subprocess
import threading
from flask import Flask
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)

# --- [ কনফিগারেশন ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
USER_PROCESSES = {} 

# Render-এর জন্য Flask সার্ভার (Keep Alive)
app = Flask('')
@app.route('/')
def home(): return "<b>System Status: Running 24/7 🚀</b>"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Conversation States
AUTH, MENU, UPLOADING_BOT, UPLOADING_REQ = range(4)

# --- [ কীবোর্ড বাটন ] ---
def main_menu_keyboard(user_id, context):
    b_stat = "✅" if context.user_data.get('bot_path') else "❌"
    r_stat = "✅" if context.user_data.get('req_path') else "❌"
    
    buttons = [
        [KeyboardButton(f"📤 Bot.py {b_stat}"), KeyboardButton(f"📜 Req.txt {r_stat}")],
        [KeyboardButton("🚀 Connect & Host Bot")],
        [KeyboardButton("🛑 Stop My Bot"), KeyboardButton("📊 Server Status")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("👑 Admin Control Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- [ হ্যান্ডলার ফাংশনসমূহ ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"<b>💠 ━━━━━ [ VPS HOSTING ] ━━━━━ 💠</b>\n\n"
        f"👋 স্বাগতম <b>{user.first_name}</b>!\n"
        f"এটি একটি প্রফেশনাল রিয়েল-টাইম হোস্টিং টার্মিনাল।\n\n"
        f"🛡️ <i>ভেরিফাই করতে নিচের বাটনে ক্লিক করে কন্টাক্ট শেয়ার করুন।</i>"
    )
    btn = [[KeyboardButton("🔐 Verify Account", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ <b>Error:</b> নিজের কন্টাক্ট শেয়ার করুন!", parse_mode=ParseMode.HTML)
        return AUTH
    
    await update.message.reply_text("✅ ভেরিফিকেশন সফল! ড্যাশবোর্ড ওপেন হচ্ছে...", reply_markup=ReplyKeyboardRemove())
    return await show_dashboard(update, context)

async def show_dashboard(update, context):
    user = update.effective_user
    text = (
        f"<b>🖥️ SYSTEM DASHBOARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: <code>{user.first_name}</code>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📡 Node: <code>Render-Cloud-01</code>\n\n"
        f"📢 <i>প্রথমে ফাইল দুটি আপলোড করুন, তারপর Connect দিন।</i>"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user.id, context), parse_mode=ParseMode.HTML)
    return MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Bot.py" in text:
        await update.message.reply_text("📥 আপনার <b>bot.py</b> ফাইলটি ডকুমেন্ট হিসেবে পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOADING_BOT
    elif "Req.txt" in text:
        await update.message.reply_text("📥 আপনার <b>requirements.txt</b> ফাইলটি পাঠান।\n(ফাইলে শুধু লাইব্রেরির নাম লিখবেন)", parse_mode=ParseMode.HTML)
        return UPLOADING_REQ
    elif "Connect" in text:
        return await start_hosting_engine(update, context)
    elif "Stop" in text:
        return await stop_user_bot(update, context)
    elif "Admin" in text and update.effective_user.id == ADMIN_ID:
        active_bots = len(USER_PROCESSES)
        await update.message.reply_text(f"👑 <b>Admin Stats:</b>\n\n🚀 Active Bots: <code>{active_bots}</code>\n🔋 Server: <code>Online</code>", parse_mode=ParseMode.HTML)
    return MENU

# --- [ ফাইল সেভার ] ---

async def save_user_file(update, context, file_type):
    user_id = update.effective_user.id
    user_dir = f"users/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    doc = update.message.document
    if not doc:
        await update.message.reply_text("❌ ফাইল হিসেবে পাঠান!")
        return MENU

    file = await context.bot.get_file(doc.file_id)
    f_name = "bot.py" if file_type == "bot" else "requirements.txt"
    dest = f"{user_dir}/{f_name}"
    
    await file.download_to_drive(dest)
    context.user_data[f'{file_type}_path'] = dest
    await update.message.reply_text(f"✅ <b>{f_name}</b> সফলভাবে সেভ হয়েছে।", parse_mode=ParseMode.HTML)
    return await show_dashboard(update, context)

# --- [ রিয়েল হোস্টিং ইঞ্জিন ] ---

async def start_hosting_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_path = context.user_data.get('bot_path')
    req_path = context.user_data.get('req_path')

    if not bot_path:
        await update.message.reply_text("❌ <b>Error:</b> আগে Bot.py ফাইল আপলোড করুন।", parse_mode=ParseMode.HTML)
        return MENU

    if user_id in USER_PROCESSES:
        await update.message.reply_text("⚠️ আপনার একটি বট অলরেডি চলছে। সেটি Stop করুন।")
        return MENU

    status_msg = await update.message.reply_text("⚙️ <b>টার্মিনাল বুট হচ্ছে...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # ১. রিয়েল ডিপেন্ডেন্সি ইন্সটল (যদি থাকে)
        if req_path:
            await status_msg.edit_text("📦 <b>Pip Installing...</b>", parse_mode=ParseMode.HTML)
            # --no-cache-dir দিয়ে রেন্ডারে পারমিশন সমস্যা কমানো হয়েছে
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path, "--no-cache-dir"], capture_output=True)

        # ২. ব্যাকগ্রাউন্ডে বট রান করা
        await status_msg.edit_text("🚀 <b>বট স্ক্রিপ্ট লঞ্চ হচ্ছে...</b>", parse_mode=ParseMode.HTML)
        
        log_file = f"users/{user_id}/terminal.log"
        with open(log_file, "w") as f:
            p = subprocess.Popen([sys.executable, bot_path], stdout=f, stderr=f)
        
        USER_PROCESSES[user_id] = p
        await asyncio.sleep(3) # ৩ সেকেন্ড ওয়েট করে স্ট্যাটাস দেখা
        
        await status_msg.edit_text(
            f"✅ <b>বট এখন সার্ভারে লাইভ!</b>\n\n"
            f"📊 PID: <code>{p.pid}</code>\n"
            f"📡 Status: <code>Running 🟢</code>\n"
            f"🕒 Uptime: <code>Unlimited</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await status_msg.edit_text(f"💥 <b>Terminal Crash:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    return MENU

async def stop_user_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in USER_PROCESSES:
        USER_PROCESSES[user_id].terminate()
        del USER_PROCESSES[user_id]
        await update.message.reply_text("🛑 <b>বট সফলভাবে বন্ধ করা হয়েছে।</b>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("ℹ️ আপনার কোনো সচল বট নেই।")
    return MENU

# --- [ মেইন রানার ] ---

def main():
    # Flask ওয়েব সার্ভার চালু (Render-এর জন্য)
    threading.Thread(target=run_web, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_handler)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            UPLOADING_BOT: [MessageHandler(filters.Document.ALL, lambda u, c: save_user_file(u, c, "bot"))],
            UPLOADING_REQ: [MessageHandler(filters.Document.ALL, lambda u, c: save_user_file(u, c, "req"))],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    print("💎 Master Hosting Bot is Online & Ready!")
    app.run_polling()

if __name__ == "__main__":
    main()
