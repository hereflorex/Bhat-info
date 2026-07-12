import asyncio
import json
import logging
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8841420440:AAGQ4fyG4JscIq7BTWpTMOxyRVeXsxUrqT4"
OWNER_ID = 8622816165
ADMIN_ID = 8341484113
ADMIN_USERNAME = "@viru_113"
BOT_USERNAME = "BHAT_MEGICAL_BOT"  # Change this to your bot's username

# ==================== DATABASE ====================
def init_db():
    """Initialize database with all tables"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 10,
        refer_code TEXT UNIQUE,
        referred_by INTEGER,
        plan_expiry TEXT,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Referrals table
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        credits_earned INTEGER DEFAULT 2,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Logs table
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def get_user(user_id):
    """Get user from database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def update_user_credits(user_id, credits):
    """Update user credits"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits=? WHERE user_id=?", (credits, user_id))
    conn.commit()
    conn.close()

def create_user(user_id, username, refer_code):
    """Create new user"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, credits, refer_code) VALUES (?, ?, ?, ?)",
        (user_id, username, 10, refer_code)
    )
    conn.commit()
    conn.close()

def log_action(user_id, action):
    """Log user action"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()
    conn.close()

# ==================== API FUNCTIONS ====================
async def fetch_api(url, fallback=None):
    """Fetch API with timeout and error handling"""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.text()
                    return data[:4000]  # Limit response size
                return fallback or f"❌ API Error: Status {response.status}"
    except asyncio.TimeoutError:
        return "❌ Timeout: API took too long to respond"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"

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

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Check if user exists
    user = get_user(user_id)
    
    # Handle referral
    if context.args and not user:
        refer_code = context.args[0]
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE refer_code=?", (refer_code,))
        referrer = c.fetchone()
        
        if referrer and referrer[0] != user_id:
            # Give bonus to new user and referrer
            c.execute("UPDATE users SET credits = credits + 10 WHERE user_id=?", (user_id,))
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (referrer[0],))
            c.execute(
                "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                (referrer[0], user_id)
            )
            conn.commit()
            # Notify referrer
            try:
                await context.bot.send_message(
                    referrer[0],
                    f"🎉 Someone used your referral link!\n"
                    f"💰 You earned 2 credits! 🎊"
                )
            except:
                pass
        conn.close()
    
    if not user:
        # Create new user
        refer_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        create_user(user_id, username, refer_code)
        
        # Notify admin
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 **New User Alert!**\n\n"
                f"👤 User: @{username}\n"
                f"🆔 ID: `{user_id}`\n"
                f"🔗 Code: `{refer_code}`\n"
                f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        except:
            pass
    
    user = get_user(user_id)
    
    welcome = (
        f"🤖 **BHAT MEGICAL BOT** ⚡\n\n"
        f"👋 Welcome @{username}!\n"
        f"💳 Credits: `{user[2]}`\n\n"
        f"📌 **Commands:**\n"
        f"/lookup - Search information\n"
        f"/balance - Check credits\n"
        f"/refer - Get referral link\n"
        f"/help - Show all commands\n\n"
        f"🔗 Your Code: `{user[4]}`\n"
        f"👥 Refer friends & earn 2 credits each!"
    )
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lookup command - search information"""
    user_id = update.effective_user.id
    
    # Check user
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    credits = user[2]
    plan_expiry = user[5]
    
    # Check if user has plan or credits
    has_plan = plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry)
    
    if not has_plan and credits <= 0:
        await update.message.reply_text(
            f"❌ **Insufficient Credits!**\n\n"
            f"💳 Credits: 0\n"
            f"🔗 Refer friends to earn 2 credits each!\n"
            f"📞 Contact: {ADMIN_USERNAME}"
        )
        return
    
    # Parse command
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            f"🔍 **Usage:**\n"
            f"/lookup <type> <value>\n\n"
            f"📌 **Types:**\n"
            f"`telegram` - Telegram ID\n"
            f"`mobile` - Phone number\n"
            f"`email` - Email address\n"
            f"`aadhaar` - Aadhaar number\n"
            f"`ifsc` - IFSC code\n"
            f"`gst` - GST number\n"
            f"`pincode` - PIN code\n"
            f"`ip` - IP address\n"
            f"`vehicle` - Vehicle number\n"
            f"`truecaller` - Phone number\n"
            f"`freefire` - Free Fire ID"
        )
        return
    
    lookup_type = context.args[0].lower()
    lookup_value = ' '.join(context.args[1:])
    
    if lookup_type not in APIS:
        await update.message.reply_text("❌ Invalid type! Use /lookup to see all types.")
        return
    
    # Deduct credit if no plan
    if not has_plan:
        update_user_credits(user_id, credits - 1)
    
    # Get API response
    api_url = APIS[lookup_type](lookup_value)
    
    # Send loading
    loading = await update.message.reply_text("⏳ Fetching information...")
    
    try:
        response = await fetch_api(api_url)
        
        if "❌" in response or "Error" in response:
            await loading.edit_text(response)
        else:
            result = f"🔍 **{lookup_type.upper()} Result**\n\n"
            result += f"📝 **Input:** `{lookup_value}`\n\n"
            result += f"```\n{response[:3500]}\n```"
            
            # Show remaining credits
            user = get_user(user_id)
            if user:
                remaining = user[2]
                plan = user[5]
                if plan and datetime.now() < datetime.fromisoformat(plan):
                    result += f"\n\n✅ **Plan Active**: Unlimited"
                else:
                    result += f"\n\n💳 **Remaining**: `{remaining}` credits"
            
            await loading.edit_text(result, parse_mode='Markdown')
            
            # Log
            log_action(user_id, f"lookup_{lookup_type}")
            
    except Exception as e:
        await loading.edit_text(f"❌ Error: {str(e)}")
    
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check balance"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    credits = user[2]
    plan_expiry = user[5]
    refer_code = user[4]
    
    msg = "💳 **Your Balance**\n\n"
    
    if plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry):
        msg += f"✅ **Plan Active**\n"
        msg += f"📅 Expires: `{plan_expiry}`\n"
    else:
        msg += f"💰 **Credits**: `{credits}`\n"
    
    msg += f"\n🔗 **Refer Code**: `{refer_code}`\n"
    msg += f"👥 Earn 2 credits per referral!"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get referral link"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    refer_code = user[4]
    bot_username = BOT_USERNAME
    
    msg = (
        f"🔗 **Your Referral Link**\n\n"
        f"🤖 Bot: @{bot_username}\n"
        f"🔗 Link: `https://t.me/{bot_username}?start={refer_code}`\n\n"
        f"📌 **How it works:**\n"
        f"1️⃣ Share your link with friends\n"
        f"2️⃣ They get 10 free credits\n"
        f"3️⃣ You get 2 credits each\n\n"
        f"⚡ Start referring now!"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    msg = (
        f"📚 **BHAT MEGICAL BOT Help** ⚡\n\n"
        f"🔍 **Lookup Commands:**\n"
        f"/lookup telegram <id>\n"
        f"/lookup mobile <number>\n"
        f"/lookup email <email>\n"
        f"/lookup aadhaar <number>\n"
        f"/lookup ifsc <code>\n"
        f"/lookup gst <number>\n"
        f"/lookup pincode <code>\n"
        f"/lookup ip <address>\n"
        f"/lookup vehicle <number>\n"
        f"/lookup truecaller <number>\n"
        f"/lookup freefire <id>\n\n"
        f"💳 **Account:**\n"
        f"/balance - Check credits\n"
        f"/refer - Get referral link\n"
        f"/start - Start the bot\n\n"
        f"📞 **Support:** {ADMIN_USERNAME}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== ADMIN COMMANDS ====================
async def is_admin(user_id):
    """Check if user is admin or owner"""
    return user_id in [OWNER_ID, ADMIN_ID]

async def admin_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant plan to user"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            f"📌 **Usage:**\n"
            f"/plan <user_id or @username> <days>\n\n"
            f"Example: `/plan 123456789 30`"
        )
        return
    
    target = context.args[0]
    try:
        days = int(context.args[1])
    except:
        await update.message.reply_text("❌ Invalid days!")
        return
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Find user
    if target.startswith('@'):
        username = target[1:]
        c.execute("SELECT user_id FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if not result:
            await update.message.reply_text(f"❌ User @{username} not found!")
            conn.close()
            return
        target_id = result[0]
    else:
        target_id = int(target)
        c.execute("SELECT user_id FROM users WHERE user_id=?", (target_id,))
        if not c.fetchone():
            await update.message.reply_text(f"❌ User {target_id} not found!")
            conn.close()
            return
    
    # Set plan
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET plan_expiry=? WHERE user_id=?", (expiry, target_id))
    log_action(user_id, f"plan_{days}_days_to_{target_id}")
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
            f"✅ Unlimited access granted!"
        )
    except:
        pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
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
    
    c.execute("SELECT COUNT(*) FROM users WHERE plan_expiry IS NOT NULL AND plan_expiry > datetime('now')")
    active_plans = c.fetchone()[0]
    
    conn.close()
    
    msg = (
        f"📊 **Bot Statistics**\n\n"
        f"👥 Users: `{total_users}`\n"
        f"🔗 Referrals: `{total_refs}`\n"
        f"💳 Credits: `{total_credits}`\n"
        f"✅ Active Plans: `{active_plans}`\n"
        f"⚡ Today: `{today_actions}` actions"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
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
    failed = 0
    
    status = await update.message.reply_text("📤 Sending broadcast...")
    
    for user in users:
        try:
            await context.bot.send_message(
                user[0],
                f"📢 **Broadcast**\n\n{msg}"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"📤 Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`"
    )

# ==================== MAIN ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Error handler"""
    print(f"❌ Error: {context.error}")
    try:
        await update.message.reply_text("❌ An error occurred. Please try again later.")
    except:
        pass

def main():
    """Start the bot"""
    try:
        print("🚀 Starting BHAT MEGICAL BOT...")
        print(f"🐍 Python version: {sys.version}")
        
        # Initialize database
        init_db()
        
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        print("✅ Application built")
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("lookup", lookup))
        app.add_handler(CommandHandler("balance", balance))
        app.add_handler(CommandHandler("refer", refer))
        app.add_handler(CommandHandler("help", help_command))
        
        # Admin commands
        app.add_handler(CommandHandler("plan", admin_plan))
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CommandHandler("broadcast", admin_broadcast))
        
        # Error handler
        app.add_error_handler(error_handler)
        
        print("✅ All handlers registered")
        print("🤖 BHAT MEGICAL BOT is running!")
        print("=" * 50)
        
        # Start polling
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
