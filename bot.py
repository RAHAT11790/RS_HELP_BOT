import os
import telebot
import sqlite3
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ===== Bot Token =====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Environment variable preferred
bot = telebot.TeleBot(BOT_TOKEN)

# ===== Database setup =====
conn = sqlite3.connect("keywords.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE,
    response TEXT,
    file_id TEXT,
    button_text TEXT,
    button_url TEXT
)""")
conn.commit()

ADMINS = {6621572366, 8350605421}  # Admin IDs

# ===== /add command =====
@bot.message_handler(commands=["add"])
def add_keyword(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ শুধু অ্যাডমিন ব্যবহার করতে পারবে।")
        return
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "⚠️ উদাহরণ:\n/add (rr) HELLO {mention} TAP BUTTON\nButton: WATCH AND DOWNLOAD | https://t.me/cartoonfunny03")
        return
    blocks = re.split(r'(?=/add\s*\()', text)
    added_keywords = []
    for block in blocks:
        if not block.strip():
            continue
        keywords = re.findall(r"\((.*?)\)", block)
        if not keywords:
            continue
        kw = keywords[0].strip()
        button_text, button_url = None, None
        button_match = re.search(r'Button:\s*(.*?)\s*\|\s*(https?://\S+)', block, re.IGNORECASE)
        if button_match:
            button_text = button_match.group(1).strip()
            button_url = button_match.group(2).strip()
        response = re.sub(r"\(.*?\)", "", block)
        response = re.sub(r'Button:.*\|.*', '', response).replace("/add", "").strip()
        file_id = None
        if message.reply_to_message:
            if message.reply_to_message.photo:
                file_id = message.reply_to_message.photo[-1].file_id
            elif message.reply_to_message.document:
                file_id = message.reply_to_message.document.file_id
        cur.execute("DELETE FROM keywords WHERE keyword = ?", (kw,))
        cur.execute("INSERT INTO keywords (keyword, response, file_id, button_text, button_url) VALUES (?, ?, ?, ?, ?)",
                    (kw, response, file_id, button_text, button_url))
        conn.commit()
        added_keywords.append(kw)
    if added_keywords:
        reply_text = "✅ নিচের keyword(s) সেভ হয়েছে:\n"
        for k in added_keywords:
            reply_text += f"• {k}\n"
        bot.reply_to(message, reply_text)
    else:
        bot.reply_to(message, "⚠️ কোনো keyword সেভ করা হয়নি।")

# ===== /list =====
@bot.message_handler(commands=["list"])
def list_keywords(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ শুধু অ্যাডমিন ব্যবহার করতে পারবে।")
        return
    cur.execute("SELECT keyword FROM keywords ORDER BY id DESC")
    rows = cur.fetchall()
    if not rows:
        bot.reply_to(message, "📂 কোনো keyword নেই।")
        return
    msg = "📑 Saved Keywords:\n\n"
    for i, (kw,) in enumerate(rows, start=1):
        msg += f"{i}. {kw}\n"
    bot.reply_to(message, msg)

# ===== /del =====
@bot.message_handler(commands=["del"])
def delete_keyword(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ শুধু অ্যাডমিন ব্যবহার করতে পারবে।")
        return
    keyword = message.text.replace("/del", "").strip()
    if not keyword:
        bot.reply_to(message, "⚠️ ব্যবহার: /del <keyword>")
        return
    cur.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
    conn.commit()
    bot.reply_to(message, f"🗑️ Keyword মুছে দেওয়া হলো: {keyword}")

# ===== Group message check =====
@bot.message_handler(func=lambda m: True)
def check_keyword(message):
    if not message.text:
        return
    text = message.text
    cur.execute("SELECT keyword, response, file_id, button_text, button_url FROM keywords")
    rows = cur.fetchall()
    for kw, res, f_id, btn_text, btn_url in rows:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            reply_text = res.replace("{mention}", user_mention)
            markup = None
            if btn_text and btn_url:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(btn_text, url=btn_url))
            if f_id:
                bot.send_photo(message.chat.id, f_id, caption=reply_text, reply_markup=markup, parse_mode="HTML")
            else:
                bot.reply_to(message, reply_text, parse_mode="HTML", reply_markup=markup)
            break

# ===== Flask keep-alive server =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 🤖"

# ===== Run Bot and Keep-alive server =====
import threading

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

threading.Thread(target=run_flask).start()
bot.infinity_polling()
