import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== CONFIG ====================
BOT_TOKEN = "8841420440:AAGQ4fyG4JscIq7BTWpTMOxyRVeXsxUrqT4"
OWNER_ID = 8622816165
ADMIN_ID = 8341484113
ADMIN_USERNAME = "@viru_113"
BOT_USERNAME = "BHAT_MEGICAL_BOT"

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 10,
        refer_code TEXT UNIQUE,
        plan_expiry TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username, refer_code):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, credits, refer_code) VALUES (?, ?, ?, ?)",
              (user_id, username, 10, refer_code))
    conn.commit()
    conn.close()

def update_credits(user_id, credits):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits=? WHERE user_id=?", (credits, user_id))
    conn.commit()
    conn.close()

def log_action(user_id, action):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()
    conn.close()

# ==================== API ====================
async def fetch_api(url):
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                return "❌ API Error"
    except:
        return "❌ Connection Error"

APIS = {
    'telegram': lambda x: f"https://tguserid-detils.ghddys32.workers.dev/?usernameid={x}",
    'mobile': lambda x: f"https://num-detils.hiteckgroup.workers.dev/?mobile={x}",
    'email': lambda x: f"https://email-detils.ghddys32.workers.dev/?email={x}",
    'aadhaar': lambda x: f"https://aadhar-detils.ghddys32.workers.dev/?adhaar={x}",
    'ifsc': lambda x: f"https://ifsc-account-detils.warmifans.workers.dev/?ifsc={x}",
    'gst': lambda x: f"https://gst-detils.warmifans.workers.dev/?gstNumber={x}",
    'pincode': lambda x: f"https://pincode-detils.warmifans.workers.dev/?pincode={x}",
    'ip': lambda x: f"https://ipwho.is/{x}",
    'vehicle': lambda x: f"https://vehicle-detils.ghddys32.workers.dev/?rc={x}",
    'truecaller': lambda x: f"https://curly-anteater-23.toul.deno.net/?q={x}",
    'freefire': lambda x: f"https://ff-detils.ghddys32.workers.dev/?uid={x}"
}

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    user = get_user(user_id)
    
    if context.args and not user:
        refer_code = context.args[0]
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE refer_code=?", (refer_code,))
        referrer = c.fetchone()
        if referrer and referrer[0] != user_id:
            c.execute("UPDATE users SET credits = credits + 10 WHERE user_id=?", (user_id,))
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (referrer[0],))
            c.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer[0], user_id))
            conn.commit()
            try:
                await context.bot.send_message(referrer[0], "🎉 Someone used your referral!\n💰 You earned 2 credits!")
            except:
                pass
        conn.close()
    
    if not user:
        refer_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        create_user(user_id, username, refer_code)
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 New User!\n👤 @{username}\n🆔 {user_id}")
        except:
            pass
    
    user = get_user(user_id)
    msg = f"🤖 **BHAT MEGICAL BOT** ⚡\n\n👋 Welcome @{username}!\n💳 Credits: `{user[2]}`\n\n📌 /lookup - Search\n/balance - Credits\n/refer - Referral link\n/help - Help\n\n🔗 Code: `{user[3]}`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ Use /start first!")
        return
    
    credits = user[2]
    plan_expiry = user[4]
    has_plan = plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry)
    
    if not has_plan and credits <= 0:
        await update.message.reply_text(f"❌ No credits!\n🔗 Refer friends to earn\n📞 {ADMIN_USERNAME}")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🔍 Usage: /lookup <type> <value>\n\nTypes: telegram, mobile, email, aadhaar, ifsc, gst, pincode, ip, vehicle, truecaller, freefire")
        return
    
    lookup_type = context.args[0].lower()
    lookup_value = ' '.join(context.args[1:])
    
    if lookup_type not in APIS:
        await update.message.reply_text("❌ Invalid type!")
        return
    
    if not has_plan:
        update_credits(user_id, credits - 1)
    
    api_url = APIS[lookup_type](lookup_value)
    loading = await update.message.reply_text("⏳ Fetching...")
    
    response = await fetch_api(api_url)
    
    if "❌" in response:
        await loading.edit_text(response)
    else:
        result = f"🔍 **{lookup_type.upper()}**\n📝 `{lookup_value}`\n\n```\n{response[:3000]}\n```"
        user = get_user(user_id)
        if user:
            if user[4] and datetime.now() < datetime.fromisoformat(user[4]):
                result += "\n\n✅ Plan Active"
            else:
                result += f"\n\n💳 Remaining: `{user[2]}`"
        await loading.edit_text(result, parse_mode='Markdown')
        log_action(user_id, f"lookup_{lookup_type}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Use /start first!")
        return
    
    msg = f"💳 **Balance**\n\n"
    if user[4] and datetime.now() < datetime.fromisoformat(user[4]):
        msg += f"✅ Plan Active\n📅 Expires: `{user[4]}`"
    else:
        msg += f"💰 Credits: `{user[2]}`"
    msg += f"\n\n🔗 Code: `{user[3]}`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Use /start first!")
        return
    
    msg = f"🔗 **Referral Link**\n\n`https://t.me/{BOT_USERNAME}?start={user[3]}`\n\n📌 Friend gets 10 credits\n💰 You get 2 credits each"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📚 **Commands**\n\n/lookup telegram <id>\n/lookup mobile <num>\n/lookup email <email>\n/lookup aadhaar <num>\n/lookup ifsc <code>\n/lookup gst <num>\n/lookup pincode <code>\n/lookup ip <addr>\n/lookup vehicle <num>\n/lookup truecaller <num>\n/lookup freefire <id>\n\n/balance - Credits\n/refer - Referral\n/start - Start\n\n📞 " + ADMIN_USERNAME
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== ADMIN ====================
async def admin_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /plan <user_id or @username> <days>")
        return
    
    target = context.args[0]
    days = int(context.args[1])
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    if target.startswith('@'):
        c.execute("SELECT user_id FROM users WHERE username=?", (target[1:],))
        result = c.fetchone()
        if not result:
            await update.message.reply_text("❌ User not found!")
            conn.close()
            return
        target_id = result[0]
    else:
        target_id = int(target)
    
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET plan_expiry=? WHERE user_id=?", (expiry, target_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Plan granted to `{target_id}` for `{days}` days")
    try:
        await context.bot.send_message(target_id, f"🎉 Plan Activated!\n📅 {days} days\n📆 Expires: {expiry}")
    except:
        pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only!")
        return
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM referrals")
    refs = c.fetchone()[0]
    c.execute("SELECT SUM(credits) FROM users")
    credits = c.fetchone()[0] or 0
    conn.close()
    
    await update.message.reply_text(f"📊 **Stats**\n\n👥 Users: `{users}`\n🔗 Referrals: `{refs}`\n💳 Credits: `{credits}`", parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    msg = ' '.join(context.args)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 {msg}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to `{sent}` users", parse_mode='Markdown')

# ==================== MAIN ====================
def main():
    print("🚀 Starting BHAT MEGICAL BOT...")
    init_db()
    print("✅ Database ready")
    
    app = Application.builder().token(BOT_TOKEN).build()
    print("✅ App built")
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lookup", lookup))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("plan", admin_plan))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    
    print("✅ All handlers added")
    print("🤖 Bot is running!")
    
    app.run_polling()

if __name__ == "__main__":
    main()
