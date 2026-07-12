import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== CONFIG ====================
BOT_TOKEN = "8841420440:AAGQ4fyG4JscIq7BTWpTMOxyRVeXsxUrqT4"
OWNER_ID = 8622816165
ADMIN_ID = 8341484113
ADMIN_USERNAME = "@viru_113"
BOT_USERNAME = "@Bhatmagic_bot"

# Force Channel Config
FORCE_CHANNEL = "@cardinghouss"
FORCE_CHANNEL_ID = -1001234567890  # Replace with your channel ID (get from @getidsbot)
FORCE_CHANNEL_LINK = "@cardinghouss"

# Admin list
ADMINS = [OWNER_ID, ADMIN_ID]

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
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT,
        joined_channel INTEGER DEFAULT 0,
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
    c.execute('''CREATE TABLE IF NOT EXISTS bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        banned_by INTEGER,
        reason TEXT,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    is_admin = 1 if user_id in ADMINS else 0
    c.execute("INSERT INTO users (user_id, username, credits, refer_code, is_admin) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, 10, refer_code, is_admin))
    conn.commit()
    conn.close()

def update_credits(user_id, credits):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits=? WHERE user_id=?", (credits, user_id))
    conn.commit()
    conn.close()

def update_channel_join(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET joined_channel=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def log_action(user_id, action):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id in ADMINS

def is_banned(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def ban_user(user_id, banned_by, reason="No reason"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, user_id))
    c.execute("INSERT INTO bans (user_id, banned_by, reason) VALUES (?, ?, ?)", (user_id, banned_by, reason))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ==================== CHECK JOIN ====================
async def check_join(user_id, context):
    """Check if user has joined the channel"""
    try:
        member = await context.bot.get_chat_member(FORCE_CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            update_channel_join(user_id)
            return True
        return False
    except:
        return False

async def force_join_message(update, context):
    """Send force join message"""
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"🔐 *Channel Required*\n\n"
        f"Please join our channel to use this bot!\n\n"
        f"👉 {FORCE_CHANNEL}\n\n"
        f"After joining, click the button below."
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== API ====================
async def fetch_api(url):
    try:
        timeout = aiohttp.ClientTimeout(total=8)
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

# ==================== MAIN MENU ====================
def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📱 Mobile", callback_data="mobile"),
         InlineKeyboardButton("📧 Email", callback_data="email")],
        [InlineKeyboardButton("🆔 Telegram", callback_data="telegram"),
         InlineKeyboardButton("🪪 Aadhaar", callback_data="aadhaar")],
        [InlineKeyboardButton("🏦 IFSC", callback_data="ifsc"),
         InlineKeyboardButton("📊 GST", callback_data="gst")],
        [InlineKeyboardButton("📍 Pincode", callback_data="pincode"),
         InlineKeyboardButton("🌐 IP", callback_data="ip")],
        [InlineKeyboardButton("🚗 Vehicle", callback_data="vehicle"),
         InlineKeyboardButton("📞 Truecaller", callback_data="truecaller")],
        [InlineKeyboardButton("🎮 FreeFire", callback_data="freefire")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("🔗 Refer", callback_data="refer")]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Check if user is banned
    if is_banned(user_id):
        user = get_user(user_id)
        reason = user[6] if user else "No reason"
        await update.message.reply_text(
            f"🚫 *You are Banned!*\n\n"
            f"Reason: {reason}\n"
            f"Contact: {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
        return
    
    # Check if user joined channel (skip for admins)
    if user_id not in ADMINS:
        user = get_user(user_id)
        if not user or user[7] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                await force_join_message(update, context)
                return
            else:
                update_channel_join(user_id)
    
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
        
        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, f"🆕 New User!\n👤 @{username}\n🆔 {user_id}")
            except:
                pass
    
    user = get_user(user_id)
    
    msg = f"🤖 *BHAT MEGICAL BOT* ⚡\n\n"
    msg += f"👋 Welcome @{username}!\n"
    msg += f"💳 Credits: `{user[2]}`\n"
    msg += f"🔗 Code: `{user[3]}`\n\n"
    msg += "📌 Select an option below:"
    
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user joined
    joined = await check_join(user_id, context)
    
    if joined:
        update_channel_join(user_id)
        user = get_user(user_id)
        username = query.from_user.username or "Unknown"
        
        msg = f"🤖 *BHAT MEGICAL BOT* ⚡\n\n"
        msg += f"👋 Welcome @{username}!\n"
        msg += f"💳 Credits: `{user[2]}`\n"
        msg += f"🔗 Code: `{user[3]}`\n\n"
        msg += "📌 Select an option below:"
        
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ You haven't joined yet!\n\n"
            f"Please join {FORCE_CHANNEL} first.",
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is banned
    if is_banned(user_id):
        await query.edit_message_text("🚫 You are banned! Contact admin.")
        return
    
    # Check channel join for non-admins
    if user_id not in ADMINS:
        user = get_user(user_id)
        if not user or user[7] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                keyboard = [
                    [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
                ]
                await query.edit_message_text(
                    f"🔐 *Channel Required*\n\nPlease join {FORCE_CHANNEL} first!",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            else:
                update_channel_join(user_id)
    
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ Please use /start first!")
        return
    
    data = query.data
    
    if data == "balance":
        await show_balance(query, user)
        return
    
    if data == "refer":
        await show_refer(query, user)
        return
    
    if data == "admin_panel":
        if is_admin(user_id):
            await show_admin_panel(query)
        return
    
    if data.startswith("admin_"):
        await admin_panel_handlers(query, context)
        return
    
    # Store lookup type
    context.user_data['lookup_type'] = data
    await query.edit_message_text(
        f"📝 *Enter value for {data.upper()} lookup*\n\n"
        f"Examples:\n"
        f"• Mobile: 9876543210\n"
        f"• Email: example@gmail.com\n"
        f"• Telegram: @username\n"
        f"• Aadhaar: 123456789012\n"
        f"• IFSC: SBIN0000001\n"
        f"• GST: 19BOKPS7056D1ZI\n"
        f"• Pincode: 110001\n"
        f"• IP: 192.168.1.1\n"
        f"• Vehicle: RJ18CF3690\n"
        f"• FreeFire: 1234567890",
        parse_mode='Markdown'
    )
    context.user_data['waiting_for_input'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user is banned
    if is_banned(user_id):
        await update.message.reply_text("🚫 You are banned! Contact admin.")
        return
    
    # Check channel join for non-admins
    if user_id not in ADMINS:
        user = get_user(user_id)
        if not user or user[7] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                await force_join_message(update, context)
                return
            else:
                update_channel_join(user_id)
    
    if not context.user_data.get('waiting_for_input'):
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    user = get_user(user_id)
    lookup_type = context.user_data.get('lookup_type')
    value = update.message.text.strip()
    
    if not lookup_type:
        await update.message.reply_text("❌ Something went wrong. Use /start again!")
        return
    
    # Check credits for non-admins
    if not is_admin(user_id):
        credits = user[2]
        plan_expiry = user[4]
        has_plan = plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry)
        
        if not has_plan and credits <= 0:
            await update.message.reply_text("❌ No credits left!\n🔗 Refer friends to earn more!")
            context.user_data['waiting_for_input'] = False
            return
        
        if not has_plan:
            update_credits(user_id, credits - 1)
    
    # Fetch API
    api_url = APIS[lookup_type](value)
    loading = await update.message.reply_text("⏳ Fetching...")
    
    response = await fetch_api(api_url)
    
    if "❌" in response:
        await loading.edit_text(response)
    else:
        result = f"🔍 *{lookup_type.upper()} Lookup*\n"
        result += f"📝 Value: `{value}`\n\n"
        result += f"```\n{response[:3000]}\n```"
        
        user = get_user(user_id)
        if user:
            if is_admin(user_id):
                result += "\n\n👑 *Admin Access*"
            elif user[4] and datetime.now() < datetime.fromisoformat(user[4]):
                result += "\n\n✅ *Plan Active*"
            else:
                result += f"\n\n💳 Remaining: `{user[2]}` credits"
        
        await loading.edit_text(result, parse_mode='Markdown')
        log_action(user_id, f"lookup_{lookup_type}")
    
    context.user_data['waiting_for_input'] = False

async def show_balance(query, user):
    msg = "💳 *Your Balance*\n\n"
    if user[4] and datetime.now() < datetime.fromisoformat(user[4]):
        msg += f"✅ Plan Active\n📅 Expires: `{user[4]}`"
    else:
        msg += f"💰 Credits: `{user[2]}`"
    msg += f"\n\n🔗 Code: `{user[3]}`"
    
    if is_admin(user[0]):
        msg += f"\n\n👑 *Admin Access*\n✅ Unlimited usage"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_refer(query, user):
    msg = f"🔗 *Your Referral Link*\n\n"
    msg += f"`https://t.me/{BOT_USERNAME}?start={user[3]}`\n\n"
    msg += "📌 *How it works:*\n"
    msg += "• Friend gets 10 free credits\n"
    msg += "• You get 2 credits each\n"
    msg += "• Unlimited referrals!"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    username = query.from_user.username or "Unknown"
    
    msg = f"🤖 *BHAT MEGICAL BOT* ⚡\n\n"
    msg += f"👋 Welcome @{username}!\n"
    msg += f"💳 Credits: `{user[2]}`\n"
    msg += f"🔗 Code: `{user[3]}`\n\n"
    msg += "📌 Select an option below:"
    
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

# ==================== ADMIN PANEL ====================
async def show_admin_panel(query):
    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
         InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 Grant Plan", callback_data="admin_grant"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
        [InlineKeyboardButton("📋 Banned List", callback_data="admin_banned"),
         InlineKeyboardButton("📋 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("💰 Credits", callback_data="admin_credits")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    
    msg = "⚙️ *Admin Panel*\n\n"
    msg += "👑 Welcome Admin!\n"
    msg += "✅ You have unlimited access\n\n"
    msg += "📌 Select an option:"
    
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel_handlers(query, context):
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin access required!")
        return
    
    data = query.data
    
    if data == "admin_users":
        await show_admin_users(query)
    elif data == "admin_stats":
        await show_admin_stats(query)
    elif data == "admin_grant":
        await query.edit_message_text(
            "📝 *Grant Plan*\n\n"
            "Send: /plan @username days\n"
            "Example: /plan @viru_113 30",
            parse_mode='Markdown'
        )
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 *Broadcast*\n\n"
            "Send: /broadcast message\n"
            "Example: /broadcast Hello everyone!",
            parse_mode='Markdown'
        )
    elif data == "admin_ban":
        await query.edit_message_text(
            "🚫 *Ban User*\n\n"
            "Send: /ban @username reason\n"
            "Example: /ban @viru_113 Spamming",
            parse_mode='Markdown'
        )
    elif data == "admin_unban":
        await query.edit_message_text(
            "✅ *Unban User*\n\n"
            "Send: /unban @username",
            parse_mode='Markdown'
        )
    elif data == "admin_banned":
        await show_banned_users(query)
    elif data == "admin_logs":
        await show_admin_logs(query)
    elif data == "admin_credits":
        await show_admin_credits(query)

async def show_admin_users(query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT user_id, username, credits, plan_expiry, is_banned, joined_channel FROM users ORDER BY created_at DESC LIMIT 10")
    users = c.fetchall()
    conn.close()
    
    msg = f"👥 *Recent Users* (10)\n\n"
    for user in users:
        uid, name, credits, plan, banned, joined = user
        plan_status = "✅ Plan" if plan and datetime.now() < datetime.fromisoformat(plan) else "💳 Free"
        status = "🚫 Banned" if banned else "✅ Active"
        channel = "📢 Joined" if joined else "❌ Not Joined"
        msg += f"• @{name or uid} | Credits: {credits} | {plan_status} | {status} | {channel}\n"
    
    msg += f"\n📊 Total Users: {total}"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_admin_stats(query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM referrals")
    refs = c.fetchone()[0]
    c.execute("SELECT SUM(credits) FROM users")
    credits = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM users WHERE plan_expiry IS NOT NULL AND plan_expiry > datetime('now')")
    plans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
    banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE joined_channel=1")
    joined = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM logs WHERE date(timestamp) = date('now')")
    today = c.fetchone()[0]
    conn.close()
    
    msg = f"📊 *Statistics*\n\n"
    msg += f"👥 Users: `{users}`\n"
    msg += f"🔗 Referrals: `{refs}`\n"
    msg += f"💳 Credits: `{credits}`\n"
    msg += f"✅ Plans: `{plans}`\n"
    msg += f"🚫 Banned: `{banned}`\n"
    msg += f"📢 Joined Channel: `{joined}`\n"
    msg += f"⚡ Today: `{today}` actions"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_banned_users(query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, ban_reason FROM users WHERE is_banned=1")
    banned = c.fetchall()
    conn.close()
    
    if not banned:
        msg = "✅ *No banned users*"
    else:
        msg = f"🚫 *Banned Users* ({len(banned)})\n\n"
        for user in banned:
            uid, name, reason = user
            msg += f"• @{name or uid} | {reason or 'No reason'}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_admin_logs(query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id, action, timestamp FROM logs ORDER BY timestamp DESC LIMIT 10")
    logs = c.fetchall()
    conn.close()
    
    msg = f"📋 *Recent Logs*\n\n"
    for log in logs:
        uid, action, time = log
        msg += f"• {uid} | {action} | {time[:16]}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_admin_credits(query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT SUM(credits) FROM users")
    total = c.fetchone()[0] or 0
    c.execute("SELECT AVG(credits) FROM users")
    avg = c.fetchone()[0] or 0
    c.execute("SELECT MAX(credits) FROM users")
    max_credits = c.fetchone()[0] or 0
    conn.close()
    
    msg = f"💰 *Credit Statistics*\n\n"
    msg += f"Total Credits: `{total}`\n"
    msg += f"Average: `{avg:.1f}`\n"
    msg += f"Max: `{max_credits}`"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== BAN COMMANDS ====================
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "🚫 *Ban User*\n\n"
            "Usage: /ban @username reason\n"
            "Example: /ban @viru_113 Spamming",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason"
    
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
        try:
            target_id = int(target)
        except:
            await update.message.reply_text("❌ Invalid user!")
            conn.close()
            return
    
    if target_id in ADMINS:
        await update.message.reply_text("❌ Cannot ban an admin!")
        conn.close()
        return
    
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (target_id,))
    result = c.fetchone()
    if result and result[0] == 1:
        await update.message.reply_text("❌ User is already banned!")
        conn.close()
        return
    
    ban_user(target_id, user_id, reason)
    conn.close()
    
    await update.message.reply_text(
        f"✅ *User Banned!*\n\n"
        f"👤 User: `{target_id}`\n"
        f"📝 Reason: {reason}",
        parse_mode='Markdown'
    )
    log_action(user_id, f"banned_{target_id}")
    
    try:
        await context.bot.send_message(
            target_id,
            f"🚫 *You have been Banned!*\n\n"
            f"Reason: {reason}\n"
            f"Contact: {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
    except:
        pass

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "✅ *Unban User*\n\n"
            "Usage: /unban @username",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    
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
        try:
            target_id = int(target)
        except:
            await update.message.reply_text("❌ Invalid user!")
            conn.close()
            return
    
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (target_id,))
    result = c.fetchone()
    if not result or result[0] == 0:
        await update.message.reply_text("❌ User is not banned!")
        conn.close()
        return
    
    unban_user(target_id)
    conn.close()
    
    await update.message.reply_text(
        f"✅ *User Unbanned!*\n\n"
        f"👤 User: `{target_id}`",
        parse_mode='Markdown'
    )
    log_action(user_id, f"unbanned_{target_id}")
    
    try:
        await context.bot.send_message(
            target_id,
            f"✅ *You have been Unbanned!*\n\n"
            f"You can now use the bot again.",
            parse_mode='Markdown'
        )
    except:
        pass

# ==================== ADMIN COMMANDS ====================
async def admin_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /plan <@username or user_id> <days>")
        return
    
    target = context.args[0]
    try:
        days = int(context.args[1])
    except:
        await update.message.reply_text("❌ Invalid days!")
        return
    
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
        try:
            target_id = int(target)
        except:
            await update.message.reply_text("❌ Invalid user!")
            conn.close()
            return
    
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET plan_expiry=? WHERE user_id=?", (expiry, target_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Plan granted to `{target_id}` for `{days}` days")
    log_action(user_id, f"grant_plan_{days}_to_{target_id}")
    
    try:
        await context.bot.send_message(target_id, f"🎉 *Plan Activated!*\n\n📅 {days} days\n📆 Expires: {expiry}", parse_mode='Markdown')
    except:
        pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
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
    c.execute("SELECT COUNT(*) FROM users WHERE plan_expiry IS NOT NULL AND plan_expiry > datetime('now')")
    plans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
    banned = c.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(
        f"📊 *Stats*\n\n"
        f"👥 Users: `{users}`\n"
        f"🔗 Referrals: `{refs}`\n"
        f"💳 Credits: `{credits}`\n"
        f"✅ Plans: `{plans}`\n"
        f"🚫 Banned: `{banned}`",
        parse_mode='Markdown'
    )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    msg = ' '.join(context.args)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned=0")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    status = await update.message.reply_text("📤 Sending broadcast...")
    
    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 {msg}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status.edit_text(f"✅ Sent to `{sent}` users\n❌ Failed: `{failed}`", parse_mode='Markdown')

# ==================== MAIN ====================
def main():
    print("🚀 Starting BHAT MEGICAL BOT...")
    init_db()
    print("✅ Database ready")
    
    app = Application.builder().token(BOT_TOKEN).build()
    print("✅ App built")
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plan", admin_plan))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(mobile|email|telegram|aadhaar|ifsc|gst|pincode|ip|vehicle|truecaller|freefire|balance|refer|admin_panel|back)$"))
    app.add_handler(CallbackQueryHandler(admin_panel_handlers, pattern="^admin_"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ All handlers added")
    print("🤖 Bot is running!")
    
    app.run_polling()

if __name__ == "__main__":
    main()
    
