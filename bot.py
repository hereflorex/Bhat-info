import asyncio
import random
import aiosqlite
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

# Force Channel Configuration
FORCE_CHANNEL = "@cardinghouss"
FORCE_CHANNEL_ID = ---1003552161874
FORCE_CHANNEL_LINK = "https://t.me/cardinghouss"

# Admins list
ADMINS = [OWNER_ID, ADMIN_ID]
DB_NAME = 'users.db'

# ==================== DATABASE INITIALIZATION ====================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
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
        
        await conn.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        await conn.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        await conn.execute('''CREATE TABLE IF NOT EXISTS bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            banned_by INTEGER,
            reason TEXT,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await conn.commit()

# ==================== DATABASE METHODS ====================
async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT user_id, username, credits, refer_code, plan_expiry, is_admin, is_banned, ban_reason, joined_channel FROM users WHERE user_id=?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, username, refer_code):
    async with aiosqlite.connect(DB_NAME) as conn:
        is_admin_flag = 1 if user_id in ADMINS else 0
        await conn.execute("INSERT OR IGNORE INTO users (user_id, username, credits, refer_code, is_admin) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, 10, refer_code, is_admin_flag))
        await conn.commit()

async def update_credits(user_id, credits):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE users SET credits=? WHERE user_id=?", (credits, user_id))
        await conn.commit()

async def update_channel_join(user_id):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE users SET joined_channel=1 WHERE user_id=?", (user_id,))
        await conn.commit()

async def log_action(user_id, action):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, action))
        await conn.commit()

def is_admin(user_id):
    return user_id in ADMINS

async def is_banned(user_id):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result and result[0] == 1

async def ban_user(user_id, banned_by, reason="No reason"):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, user_id))
        await conn.execute("INSERT INTO bans (user_id, banned_by, reason) VALUES (?, ?, ?)", (user_id, banned_by, reason))
        await conn.commit()

async def unban_user(user_id):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (user_id,))
        await conn.commit()

# ==================== JOIN CHECK CONTROLLER ====================
async def check_join(user_id, context):
    try:
        member = await context.bot.get_chat_member(FORCE_CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await update_channel_join(user_id)
            return True
        return False
    except Exception:
        return False

async def force_join_message(update, context):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = (
        "┌───────────────────┐\n"
        "🔒  *ACCESS RESTRICTED* 🔒\n"
        "└───────────────────┘\n\n"
        "Our official update channel subscription is required to authorize usage.\n\n"
        f"🔗 *Channel:* {FORCE_CHANNEL}\n\n"
        "» _Join the channel and click 'I've Joined' button below._"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== SUPER FAST PERSISTENT API FETCH ====================
async def fetch_api(url, session):
    try:
        async with session.get(url, timeout=6) as response:
            if response.status == 200:
                return await response.text()
            return "❌ [API Error: Bad HTTP response code]"
    except Exception:
        return "❌ [Connection Timeout / Offline Host API]"

# Cloud APIs mappings
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

# ==================== KEYBOARDS ====================
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

# ==================== SYSTEM CORE HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if await is_banned(user_id):
        user = await get_user(user_id)
        reason = user[7] if user and user[7] else "Violating terms of system."
        await update.message.reply_text(
            "┌───────────────────┐\n"
            "🚫      *ACCESS BLACKLISTED* 🚫\n"
            "└───────────────────┘\n\n"
            f"⚡ *Reason:* `{reason}`\n"
            f"✉️ *Support Admin Node:* {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
        return
    
    if user_id not in ADMINS:
        user = await get_user(user_id)
        if not user or user[8] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                await force_join_message(update, context)
                return

    user = await get_user(user_id)
    
    if context.args and not user:
        refer_code = context.args[0]
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("SELECT user_id FROM users WHERE refer_code=?", (refer_code,)) as cursor:
                referrer = await cursor.fetchone()
            if referrer and referrer[0] != user_id:
                await conn.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (referrer[0],))
                await conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer[0], user_id))
                await conn.commit()
                try:
                    await context.bot.send_message(referrer[0], "🎉 *Referral Success!*\n\n🤝 Someone joined using your link.\n💰 `+2 Credits` added instantly!", parse_mode='Markdown')
                except Exception:
                    pass
    
    if not user:
        refer_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        await create_user(user_id, username, refer_code)
        user = await get_user(user_id)
        
        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, f"🆕 *New User Alert!*\n👤 @{username}\n🆔 `{user_id}`", parse_mode='Markdown')
            except Exception:
                pass
    
    msg = (
        "⚡ *BHAT MAGIC OS v2.0* ⚡\n"
        "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
        f"👋 Welcome @{username}!\n\n"
        f"💳 Balance: `{user[2]}` Credits\n"
        f"🔑 Ref Code: `{user[3]}`\n\n"
        "⚡ *Select a module from dashboard:* "
    )
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    joined = await check_join(user_id, context)
    if joined:
        user = await get_user(user_id)
        if not user:
            refer_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            await create_user(user_id, query.from_user.username or "Unknown", refer_code)
            user = await get_user(user_id)
            
        msg = (
            "⚡ *BHAT MAGIC OS v2.0* ⚡\n"
            "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
            f"👋 Verified! Welcome @{query.from_user.username or 'User'}!\n\n"
            f"💳 Balance: `{user[2]}` Credits\n"
            f"🔑 Ref Code: `{user[3]}`\n\n"
            "⚡ *Select a module from dashboard:*"
        )
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
        ]
        await query.edit_message_text(
            "❌ *Verification Failed!*\n\n"
            f"Please join updates channel {FORCE_CHANNEL} first to use.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== MAIN CALLBACK ROUTER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if await is_banned(user_id):
        await query.edit_message_text("🚫 System locked! Blacklisted nodes cannot interact.")
        return
    
    if user_id not in ADMINS:
        user = await get_user(user_id)
        if not user or user[8] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                await force_join_message(update, context)
                return

    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ System expired session. Send /start")
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
    if data == "back":
        await back_handler(update, context)
        return
    
    context.user_data['lookup_type'] = data
    context.user_data['waiting_for_input'] = True
    
    examples = {
        'mobile': '9876543210', 'email': 'example@gmail.com', 'telegram': '@username / ID',
        'aadhaar': '123456789012', 'ifsc': 'SBIN0000001', 'gst': '19BOKPS7056D1ZI',
        'pincode': '110001', 'ip': '8.8.8.8', 'vehicle': 'DL3CAM1234',
        'truecaller': '9876543210', 'freefire': '123456789'
    }
    
    msg = (
        f"📥 *INPUT REQUIRED* 📥\n"
        f"‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
        f"Selected Module: *{data.upper()}* Lookup.\n\n"
        f"👉 *Send the target search query now.*\n"
        f"💡 _Example format: `{examples.get(data, 'Format')}`_\n\n"
        "📎 _Awaiting standard response packet..._"
    )
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]))

# ==================== TRANSACTION MESSAGE ENGINE ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_banned(user_id): return
    
    if user_id not in ADMINS:
        user = await get_user(user_id)
        if not user or user[8] == 0:
            joined = await check_join(user_id, context)
            if not joined:
                await force_join_message(update, context)
                return

    if not context.user_data.get('waiting_for_input'):
        return
    
    user = await get_user(user_id)
    lookup_type = context.user_data.get('lookup_type')
    value = update.message.text.strip()
    
    if not lookup_type:
        await update.message.reply_text("❌ Connection broke. Restart with /start")
        return
    
    if not is_admin(user_id):
        credits = user[2]
        plan_expiry = user[4]
        has_plan = plan_expiry and datetime.now() < datetime.fromisoformat(plan_expiry)
        
        if not has_plan and credits <= 0:
            msg = (
                "⚠️ *INSUFFICIENT BALANCE* ⚠️\n"
                "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
                "Your account balance has dropped to `0 Credits`.\n\n"
                "💼 *To Purchase Premium Plans or Add Credits:*\n"
                f"» Contact Admin/Owner: {ADMIN_USERNAME}\n\n"
                "ℹ️ _Alternatively, click 'Invite & Earn' from the dashboard to earn free credits._"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
            context.user_data['waiting_for_input'] = False
            return
        
        if not has_plan:
            await update_credits(user_id, credits - 1)
            
    loading = await update.message.reply_text("🛸 `PROCESSING REQ... FETCHING SECURE API RECORDS`", parse_mode='Markdown')
    
    session = context.bot_data.get('http_session')
    api_url = APIS[lookup_type](value)
    response = await fetch_api(api_url, session)
    
    if "❌" in response:
        await loading.edit_text(response)
    else:
        user = await get_user(user_id)
        status_footer = "👑 Admin Premium Access" if is_admin(user_id) else (f"📅 Active Premium Plan" if user[4] and datetime.now() < datetime.fromisoformat(user[4]) else f"💳 Balance Remaining: `{user[2]}` Credits")
        
        result = (
            "🟢 *LOOKUP REPORT GENERATED* 🟢\n"
            "┌────────────────────────────┐\n"
            f" 💎  *Type:* `{lookup_type.upper()}`\n"
            f" 🔍  *Query:* `{value}`\n"
            "└────────────────────────────┘\n\n"
            f"📋 *Data Logs:*\n"
            f"⚡ _{status_footer}_"
        )
        await loading.edit_text(result, parse_mode='Markdown')
        await log_action(user_id, f"lookup_{lookup_type}")
        
    context.user_data['waiting_for_input'] = False

# ==================== MENU VIEW BLOCKS ====================
async def show_balance(query, user):
    user_id = user[0]
    has_plan = user[4] and datetime.now() < datetime.fromisoformat(user[4])
    msg = (
        "┌───────────────────┐\n"
        "👤    *USER SUBSCRIPTION* 👤\n"
        "└───────────────────┘\n\n"
        f"» *User ID:* `{user_id}`\n"
        f"» *Account Level:* {'👑 SYSTEM OWNER' if is_admin(user_id) else ('⚜️ PREMIUM' if has_plan else '📝 STANDARD FREE')}\n"
        f"» *Credits Left:* `{user[2] if not is_admin(user_id) else '∞'}`\n"
    )
    if has_plan:
        msg += f"» *Plan Expiry:* `{user[4]}`\n"
        
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_refer(query, user):
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user[3]}"
    msg = (
        "┌───────────────────┐\n"
        "🤝    *INVITE & EARN SYSTEM* 🤝\n"
        "└───────────────────┘\n\n"
        "Share your custom link below with group members or friends. When they authorize the bot, they get free bonuses, and you receive instant payouts.\n\n"
        f"🔗 *Your Referral Link:*\n`{ref_link}`\n\n"
        "💎 *Reward Tier:* `2 Credits Per Referral`"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    msg = (
        "⚡ *BHAT MAGIC OS v2.0* ⚡\n"
        "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
        f"👋 Welcome @{query.from_user.username or 'User'}!\n\n"
        f"💳 Balance: `{user[2]}` Credits\n"
        f"🔑 Ref Code: `{user[3]}`\n\n"
        "⚡ *Select a Tool from below dashboard:*"
    )
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

# ==================== ADMIN SYSTEM PANEL ====================
async def show_admin_panel(query):
    keyboard = [
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users"), InlineKeyboardButton("📊 DB Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 Gift Premium Plan", callback_data="admin_grant"), InlineKeyboardButton("📢 Global Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Ban Criminal", callback_data="admin_ban"), InlineKeyboardButton("✅ Revoke Ban", callback_data="admin_unban")],
        [InlineKeyboardButton("📋 System Audits / Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("🔙 Return Back", callback_data="back")]
    ]
    msg = (
        "👑 *ROOT APPLICATION ADMIN PANEL* 👑\n"
        "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
        "Secure administrator interface active. Select a module to process backend tasks."
    )
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ System Exception: Restricted root permission.")
        return
        
    data = query.data
    if data == "admin_users":
        await show_admin_users(query)
    elif data == "admin_stats":
        await show_admin_stats(query)
    elif data == "admin_logs":
        await show_admin_logs(query)
    elif data == "admin_grant":
        await query.edit_message_text("⚙️ *Grant Premium Plan*\n\nSend Command via chat:\n`/plan @username days`\nExample: `/plan @viru_113 30`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 *Global Broadcast*\n\nSend Command via chat:\n`/broadcast Message text here`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
    elif data == "admin_ban":
        await query.edit_message_text("🚫 *Blacklist User*\n\nSend Command via chat:\n`/ban @username Spamming`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
    elif data == "admin_unban":
        await query.edit_message_text("✅ *Pardon User*\n\nSend Command via chat:\n`/unban @username`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))

async def show_admin_users(query):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT user_id, username, credits FROM users ORDER BY created_at DESC LIMIT 7") as cursor:
            users = await cursor.fetchall()
            
    msg = "👥 *Recent Registered Accounts:*\n\n"
    for u in users:
        msg += f"• `{u[0]}` | @{u[1] or 'Unknown'} | Balance: `{u[2]}`\n"
        
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]]))

async def show_admin_stats(query):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT COUNT(*) FROM users") as c1:
            users = (await c1.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM referrals") as c2:
            refs = (await c2.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1") as c3:
            banned = (await c3.fetchone())[0]
            
    msg = (
        "📊 *SYSTEM DATABASE INSIGHTS*\n\n"
        f"• Total Users Index: `{users}`\n"
        f"• Network Referrals: `{refs}`\n"
        f"• Blacklisted Nodes: `{banned}`"
    )
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]]))

async def show_admin_logs(query):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT user_id, action, timestamp FROM logs ORDER BY timestamp DESC LIMIT 8") as cursor:
            logs = await cursor.fetchall()
            
    msg = "📋 *Recent Application Logs:*\n\n"
    for l in logs:
        msg += f"• `{l[0]}` - `{l[1]}` at _{l[2][11:16]}_\n"
        
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]]))

# ==================== CONTROLLER COMMANDS ====================
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: `/ban @username reason`", parse_mode='Markdown')
        return
        
    target = context.args[0]
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Term violation"
    
    async with aiosqlite.connect(DB_NAME) as conn:
        if target.startswith('@'):
            async with conn.execute("SELECT user_id FROM users WHERE username=?", (target[1:],)) as cursor:
                res = await cursor.fetchone()
            target_id = res[0] if res else None
        else:
            target_id = int(target) if target.isdigit() else None
            
        if not target_id or target_id in ADMINS:
            await update.message.reply_text("❌ Connection rejected. Invalid node parameters.")
            return
            
        await ban_user(target_id, user_id, reason)
        
    await update.message.reply_text(f"✅ Node `{target_id}` blacklisted.")
    try:
        await context.bot.send_message(target_id, f"🚫 *You have been Banned!*\n\nReason: {reason}\nContact Support: {ADMIN_USERNAME}", parse_mode='Markdown')
    except Exception: pass

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: `/unban @username`", parse_mode='Markdown')
        return
        
    target = context.args[0]
    
    async with aiosqlite.connect(DB_NAME) as conn:
        if target.startswith('@'):
            async with conn.execute("SELECT user_id FROM users WHERE username=?", (target[1:],)) as cursor:
                res = await cursor.fetchone()
            target_id = res[0] if res else None
        else:
            target_id = int(target) if target.isdigit() else None
            
        if target_id:
            await unban_user(target_id)
            
    await update.message.reply_text(f"✅ Node `{target_id}` ban successfully revoked.")
    try:
        await context.bot.send_message(target_id, "✅ *You have been Unbanned!*\n\nYou can access system parameters.", parse_mode='Markdown')
    except Exception: pass

async def admin_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/plan @username days`", parse_mode='Markdown')
        return
        
    target = context.args[0]
    days = int(context.args[1]) if context.args[1].isdigit() else 0
    
    async with aiosqlite.connect(DB_NAME) as conn:
        if target.startswith('@'):
            async with conn.execute("SELECT user_id FROM users WHERE username=?", (target[1:],)) as cursor:
                res = await cursor.fetchone()
            target_id = res[0] if res else None
        else:
            target_id = int(target) if target.isdigit() else None
            
        if target_id:
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            await conn.execute("UPDATE users SET plan_expiry=? WHERE user_id=?", (expiry, target_id))
            await conn.commit()
            await update.message.reply_text(f"🔥 Premium license granted to `{target_id}` for {days} days.")
            try:
                await context.bot.send_message(target_id, f"🎉 *Premium License Activated!*\n\n👑 Unlimited API queries granted for `{days}` days.", parse_mode='Markdown')
            except Exception: pass

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args: return
    
    msg = ' '.join(context.args)
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT user_id FROM users WHERE is_banned=0") as cursor:
            users = await cursor.fetchall()
            
    status = await update.message.reply_text("📢 *Deploying Global Broadcast...*", parse_mode='Markdown')
    sent = 0
    failed = 0
    
    for u in users:
        try:
            await context.bot.send_message(u[0], f"📢 *GLOBAL ANNOUNCEMENT:*\n\n{msg}", parse_mode='Markdown')
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
            
    await status.edit_text(f"✅ Sent: `{sent}`\n❌ Failed: `{failed}`", parse_mode='Markdown')

# ==================== LIFECYCLE MANAGEMENT ====================
async def post_init(application: Application) -> None:
    await init_db()
    application.bot_data['http_session'] = aiohttp.ClientSession()
    print("✅ Asynchronous Core Engine Initialized Completely.")

async def post_shutdown(application: Application) -> None:
    session = application.bot_data.get('http_session')
    if session:
        await session.close()
    print("🛑 Asynchronous Core Closed Safely.")

# ==================== RUNNER ====================
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plan", admin_plan))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(mobile|email|telegram|aadhaar|ifsc|gst|pincode|ip|vehicle|truecaller|freefire|balance|refer|back)$"))
    app.add_handler(CallbackQueryHandler(admin_panel_handlers, pattern="^admin_"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 BHAT MAGIC BOT OS v2.0 IS ONLINE...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
