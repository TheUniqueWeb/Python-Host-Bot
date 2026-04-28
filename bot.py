import os
import sys
import asyncio
import logging
import subprocess
import threading
from flask import Flask
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    ParseMode
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- [ কনফিগারেশন ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
USER_PROCESSES = {} 

# Flask Server
app = Flask('')
@app.route('/')
def home(): return "Hosting Server is Active! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# States
AUTH, MENU, UPLOADING_BOT, UPLOADING_REQ = range(4)

def main_menu(user_id, context):
    b_stat = "✅" if context.user_data.get('bot_path') else "❌"
    r_stat = "✅" if context.user_data.get('req_path') else "❌"
    buttons = [
        [KeyboardButton(f"📂 Bot.py {b_stat}"), KeyboardButton(f"📜 Req.txt {r_stat}")],
        [KeyboardButton("🚀 Connect & Host (Terminal)")],
        [KeyboardButton("🛑 Stop My Bot"), KeyboardButton("📊 Server Info")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- [ HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"<b>💎 REAL VPS TERMINAL</b>\n\nস্বাগতম {user.first_name}! ভেরিফাই করতে কন্টাক্ট শেয়ার করুন।"
    btn = [[KeyboardButton("🔐 Verify", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact.user_id != update.message.from_user.id:
        return AUTH
    await update.message.reply_text("✅ ভেরিফিকেশন সফল!", reply_markup=main_menu(update.effective_user.id, context))
    return MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Bot.py" in text:
        await update.message.reply_text("📥 <b>bot.py</b> ফাইলটি পাঠান।")
        return UPLOADING_BOT
    elif "Req.txt" in text:
        await update.message.reply_text("📥 <b>requirements.txt</b> ফাইলটি পাঠান।")
        return UPLOADING_REQ
    elif "Connect" in text:
        return await start_terminal(update, context)
    elif "Stop" in text:
        return await stop_bot(update, context)
    return MENU

async def save_file(update, context, f_type):
    user_id = update.effective_user.id
    path = f"users/{user_id}"
    os.makedirs(path, exist_ok=True)
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    f_name = "bot.py" if f_type == "bot" else "requirements.txt"
    dest = f"{path}/{f_name}"
    
    await file.download_to_drive(dest)
    context.user_data[f'{f_type}_path'] = dest
    await update.message.reply_text(f"✅ {f_name} সেভ হয়েছে।")
    return MENU

# --- [ REAL TERMINAL ENGINE ] ---

async def start_terminal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_path = context.user_data.get('bot_path')
    req_path = context.user_data.get('req_path')

    if not bot_path:
        await update.message.reply_text("❌ ফাইল পাওয়া যায়নি!")
        return MENU

    if user_id in USER_PROCESSES:
        await update.message.reply_text("⚠️ একটি বট অলরেডি চলছে।")
        return MENU

    status = await update.message.reply_text("🛰️ <b>টার্মিনাল বুট হচ্ছে...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # ১. লাইব্রেরি ইন্সটলেশন (যদি requirements.txt থাকে)
        if req_path:
            await status.edit_text("📦 <b>Pip Installing...</b> (টার্মিনাল আউটপুট চেক হচ্ছে)")
            # Render-এর সীমাবদ্ধতা কাটাতে --no-cache-dir এবং --user ট্রাই করা হচ্ছে
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_path, "--no-cache-dir"],
                capture_output=True, text=True
            )
            if proc.returncode != 0:
                # এরর মেসেজ বড় করে দেখানো হচ্ছে
                await status.edit_text(f"❌ <b>Pip Error:</b>\n<code>{proc.stderr[:300]}</code>", parse_mode=ParseMode.HTML)
                # এখানে আমরা পুরোপুরি স্টপ করব না, কারণ কিছু লাইব্রেরি হয়তো আগে থেকেই ইন্সটল আছে
                await update.message.reply_text("⚠️ কিছু লাইব্রেরি ইন্সটল হয়নি, তবে বট রান করার চেষ্টা করছি...")

        # ২. বট রান করা
        await status.edit_text("🚀 <b>বট স্ক্রিপ্ট এক্সিকিউট হচ্ছে...</b>")
        
        # আউটপুট এবং এরর ধরার জন্য লগ ফাইল তৈরি
        log_file = f"users/{user_id}/logs.txt"
        with open(log_file, "w") as f:
            p = subprocess.Popen(
                [sys.executable, bot_path],
                stdout=f, stderr=f, start_new_session=True
            )
        
        USER_PROCESSES[user_id] = p
        await asyncio.sleep(3)
        
        # লগের প্রথম কয়েক লাইন ইউজারকে দেখানো
        with open(log_file, "r") as f: logs = f.read()
        
        await status.edit_text(
            f"✅ <b>বট এখন লাইভ!</b>\n\n"
            f"🎯 PID: <code>{p.pid}</code>\n"
            f"📄 <b>Terminal Logs:</b>\n<code>{logs[:200] if logs else 'No output yet...'}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await status.edit_text(f"💥 <b>Terminal Crash:</b>\n<code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    return MENU

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in USER_PROCESSES:
        USER_PROCESSES[user_id].terminate()
        del USER_PROCESSES[user_id]
        await update.message.reply_text("🛑 বট সফলভাবে বন্ধ হয়েছে।")
    else:
        await update.message.reply_text("ℹ️ কোনো সচল বট নেই।")
    return MENU

# --- [ MAIN ] ---
def main():
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
    print("Master Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
