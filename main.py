import asyncio
import json
import logging
import random
import aiohttp
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3

# Bot Configuration
BOT_TOKEN = "8841420440:AAGQ4fyG4JscIq7BTWpTMOxyRVeXsxUrqT4"
OWNER_ID = 8622816165
ADMIN_ID = 8341484113
ADMIN_USERNAME = "@viru_113"

# Initialize database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  credits INTEGER DEFAULT 10,
                  refer_code TEXT,
                  referred_by INTEGER,
                  plan_expiry TEXT,
                  is_admin BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  referrer_id INTEGER,
                  referred_id INTEGER,
                  credits_earned INTEGER DEFAULT 2,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# API Functions with fallback
async def fetch_api(url, fallback=None):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                return fallback
    except:
        return fallback

# API endpoints
APIS = {
    'telegram': lambda uid: f"https://tguserid-detils.ghddys32.workers.dev/?usernameid={uid}",
    'mobile': lambda num: f"https://num-detils.hiteckgroup.workers.dev/?mobile={num}",
    'email': lambda email: f"https://email-detils.ghddys32.workers.dev/?email={email}",
    'aadhaar': lambda aadhaar: f"https://aadhar-detils.ghddys32.workers.dev/?adhaar={aadhaar}",
    'ifsc': lambda ifsc: f"https://ifsc-account-detils.warmifans.workers.dev/?ifsc={ifsc}",
    'gst': lambda gst: f"https://gst-detils.warmifans.workers.dev/?gstNumber={gst}",
    'pincode': lambda pin: f"https://pincode-detils.warmifans.workers.dev/?pincode={pin}",
    'ip': lambda ip: f"https://ipwho.is/{ip}",
    'vehicle': lambda rc: f"https://vehicle-detils.ghddys32.workers.dev/?rc={rc}",
    'truecaller': lambda num: f"https://curly-anteater-23.toul.deno.net/?q={num}",
    'freefire': lambda uid: f"https://ff-detils.ghddys32.workers.dev/?uid={uid}"
}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Check if user exists
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    
    # Check if this is a referral
    refer_code = None
    if context.args:
        refer_code = context.args[0]
        # Validate referral code
        c.execute("SELECT user_id FROM users WHERE refer_code=?", (refer_code,))
        referrer = c.fetchone()
        if referrer and user_id != referrer[0]:
            # Add referral bonus
            c.execute("UPDATE users SET credits = credits + 10 WHERE user_id=?", (user_id,))
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (referrer[0],))
            c.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer[0], user_id))
            conn.commit()
    
    if not user:
        # Create new user with 10 credits
        refer_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        c.execute("INSERT INTO users (user_id, username, credits, refer_code) VALUES (?, ?, ?, ?)",
                 (user_id, username, 10, refer_code))
        conn.commit()
        
        # Notify admin
        await context.bot.send_message(
            ADMIN_ID, 
            f"🆕 New User Alert!\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: `{user_id}`\n"
            f"🔗 Refer Code: `{refer_code}`"
        )
    
    conn.close()
    
    welcome_msg = (
        "🤖 **BHAT MEGICAL BOT** ⚡\n\n"
        f"👋 Welcome @{username}!\n"
        f"💳 Your Credits: `{10 if not user else user[2]}`\n\n"
        "📌 **Available Commands:**\n"
        "/lookup - Search information\n"
        "/balance - Check your credits\n"
        "/refer - Get your referral link\n"
        "/help - Show all commands\n\n"
        "⚡ Refer friends and earn 2 credits each!\n"
        "🔗 Your Refer Code: `" + (refer_code or user[4]) + "`"
    )
    
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check credits
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT credits, plan_expiry FROM users WHERE user_id=?", (user_id,))
    user_data = c.fetchone()
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first!")
        conn.close()
        return
    
    credits, plan_expiry = user_data
    
    # Check if user has plan or credits
    has_plan = plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry)
    
    if not has_plan and credits <= 0:
        await update.message.reply_text(
            "❌ **Insufficient Credits!**\n\n"
            "💳 You have 0 credits.\n"
            "🔗 Refer friends to earn 2 credits each!\n"
            "📞 Contact admin: " + ADMIN_USERNAME
        )
        conn.close()
        return
    
    # Get query
    if not context.args:
        await update.message.reply_text(
            "🔍 **Usage:**\n"
            "/lookup <type> <value>\n\n"
            "📌 **Types:**\n"
            "`telegram` - Telegram ID\n"
            "`mobile` - Phone number\n"
            "`email` - Email address\n"
            "`aadhaar` - Aadhaar number\n"
            "`ifsc` - IFSC code\n"
            "`gst` - GST number\n"
            "`pincode` - PIN code\n"
            "`ip` - IP address\n"
            "`vehicle` - Vehicle number\n"
            "`truecaller` - Phone number\n"
            "`freefire` - Free Fire ID"
        )
        conn.close()
        return
    
    lookup_type = context.args[0].lower()
    lookup_value = ' '.join(context.args[1:]) if len(context.args) > 1 else None
    
    if not lookup_value:
        await update.message.reply_text("❌ Please provide a value to lookup!")
        conn.close()
        return
    
    if lookup_type not in APIS:
        await update.message.reply_text("❌ Invalid lookup type! Use /lookup to see all types.")
        conn.close()
        return
    
    # Deduct credit if no plan
    if not has_plan:
        c.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
        conn.commit()
    
    # Get API response
    api_url = APIS[lookup_type](lookup_value)
    
    # Send loading message
    loading_msg = await update.message.reply_text("⏳ Fetching information...")
    
    try:
        response = await fetch_api(api_url, "❌ API Error: Unable to fetch data")
        
        if "❌" in response:
            await loading_msg.edit_text(response)
        else:
            # Format response
            result = f"🔍 **{lookup_type.upper()} Lookup Result**\n\n"
            result += f"📝 **Value:** `{lookup_value}`\n\n"
            result += f"```\n{response[:3500]}\n```"
            
            # Check remaining credits
            c.execute("SELECT credits, plan_expiry FROM users WHERE user_id=?", (user_id,))
            new_data = c.fetchone()
            
            if new_data:
                remaining = new_data[0]
                plan = new_data[1]
                if plan and datetime.now() < datetime.fromisoformat(plan):
                    result += f"\n\n✅ **Plan Active**: Unlimited checks"
                else:
                    result += f"\n\n💳 **Remaining Credits**: `{remaining}`"
            
            await loading_msg.edit_text(result, parse_mode='Markdown')
            
            # Log action
            c.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", 
                     (user_id, f"lookup_{lookup_type}"))
            conn.commit()
            
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
    
    conn.close()

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT credits, plan_expiry, refer_code FROM users WHERE user_id=?", (user_id,))
    user_data = c.fetchone()
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first!")
        conn.close()
        return
    
    credits, plan_expiry, refer_code = user_data
    
    msg = "💳 **Your Balance**\n\n"
    
    if plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry):
        msg += f"✅ **Plan Active**\n"
        msg += f"📅 Expires: `{plan_expiry}`\n"
    else:
        msg += f"💰 **Credits**: `{credits}`\n"
    
    msg += f"\n🔗 **Refer Code**: `{refer_code}`\n"
    msg += f"👥 Earn 2 credits per referral!"
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    conn.close()

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT refer_code FROM users WHERE user_id=?", (user_id,))
    user_data = c.fetchone()
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first!")
        conn.close()
        return
    
    refer_code = user_data[0]
    
    msg = (
        "🔗 **Your Referral Link**\n\n"
        f"🤖 Bot: @{"your_bot_username"}\n"
        f"🔗 Link: `https://t.me/{"your_bot_username"}?start={refer_code}`\n\n"
        "📌 **How it works:**\n"
        "1️⃣ Share your link with friends\n"
        "2️⃣ When they join, you get 2 credits\n"
        "3️⃣ They also get 10 free credits!\n\n"
        "⚡ Start referring now!"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    conn.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📚 **BHAT MEGICAL BOT Help** ⚡\n\n"
        "🔍 **Lookup Commands:**\n"
        "/lookup telegram <id>\n"
        "/lookup mobile <number>\n"
        "/lookup email <email>\n"
        "/lookup aadhaar <number>\n"
        "/lookup ifsc <code>\n"
        "/lookup gst <number>\n"
        "/lookup pincode <code>\n"
        "/lookup ip <address>\n"
        "/lookup vehicle <number>\n"
        "/lookup truecaller <number>\n"
        "/lookup freefire <id>\n\n"
        "💳 **Account:**\n"
        "/balance - Check credits\n"
        "/refer - Get referral link\n"
        "/start - Start the bot\n\n"
        "📞 **Support:** " + ADMIN_USERNAME + "\n"
        "👑 **Owner:** @your_owner_username"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if admin or owner
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "📌 **Usage:**\n"
            "/plan <@username or user_id> <days>\n\n"
            "Example: `/plan @viru_113 30`"
        )
        return
    
    # Parse target user
    target = context.args[0]
    days = int(context.args[1])
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Get user by username or id
    if target.startswith('@'):
        username = target[1:]
        c.execute("SELECT user_id FROM users WHERE username=?", (username,))
        user = c.fetchone()
        if not user:
            await update.message.reply_text(f"❌ User @{username} not found!")
            conn.close()
            return
        target_id = user[0]
    else:
        target_id = int(target)
    
    # Set plan
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET plan_expiry=? WHERE user_id=?", (expiry, target_id))
    c.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", 
             (user_id, f"plan_granted_{days}_days_to_{target_id}"))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **Plan Granted!**\n\n"
        f"👤 User: `{target_id}`\n"
        f"📅 Duration: `{days}` days\n"
        f"📆 Expires: `{expiry}`"
    )
    
    # Notify user
    try:
        await context.bot.send_message(
            target_id,
            f"🎉 **Plan Activated!**\n\n"
            f"📅 Duration: `{days}` days\n"
            f"📆 Expires: `{expiry}`\n\n"
            f"Enjoy unlimited access! 🔥"
        )
    except:
        pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM referrals")
    total_refs = c.fetchone()[0]
    
    c.execute("SELECT SUM(credits) FROM users")
    total_credits = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM logs WHERE date(timestamp) = date('now')")
    today_actions = c.fetchone()[0]
    
    conn.close()
    
    msg = (
        "📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"🔗 Total Referrals: `{total_refs}`\n"
        f"💳 Total Credits: `{total_credits}`\n"
        f"⚡ Today's Actions: `{today_actions}`"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text("❌ Admin only command!")
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
            await context.bot.send_message(user[0], f"📢 **Broadcast Message**\n\n{msg}")
            sent += 1
            await asyncio.sleep(0.1)  # Avoid rate limiting
        except:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users")

# Main function
def main():
    init_db()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lookup", lookup))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("refer", refer))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("plan", admin_plan))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    
    # Start bot
    print("🤖 BHAT MEGICAL BOT is running!")
    application.run_polling()

if __name__ == "__main__":
    main()
