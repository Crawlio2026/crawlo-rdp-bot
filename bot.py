import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8631667551:AAG9s0aeNBGwiqJlJRYRFwhErLbM74NmbPE"
ADMIN_IDS = [6959395726, 8912362600]

REQUIRED_CHANNEL_ID = "@crawlionetwork"
REQUIRED_CHANNEL_LINK = "https://t.me/crawlionetwork"
ABOUT_LINK = "https://crawlio.xyz/about"

PLANS = [
    {"id": "p1", "name": "2 CPU Cores · 4GB RAM · 40GB NVMe",   "usd": 6.99,  "oxa": "https://pay.oxapay.com/15717787"},
    {"id": "p2", "name": "2 CPU Cores · 6GB RAM · 60GB NVMe",   "usd": 10.99, "oxa": "https://pay.oxapay.com/17621324"},
    {"id": "p3", "name": "4 CPU Cores · 8GB RAM · 80GB NVMe",   "usd": 14.99, "oxa": "https://pay.oxapay.com/17119172"},
    {"id": "p4", "name": "6 CPU Cores · 16GB RAM · 160GB NVMe", "usd": 19.99, "oxa": "https://pay.oxapay.com/12873741"},
    {"id": "p5", "name": "8 CPU Cores · 24GB RAM · 240GB NVMe", "usd": 25.99, "oxa": "https://pay.oxapay.com/19276455"},
    {"id": "p6", "name": "10 CPU Cores · 32GB RAM · 320GB NVMe","usd": 31.99, "oxa": "https://pay.oxapay.com/15496968"},
]

OPERATING_SYSTEMS = [
    "Windows Server 2025",
    "Windows Server 2022",
    "Windows Server 2019",
    "Ubuntu 24.04",
    "Ubuntu 22.04",
    "Debian 13",
    "Debian 12",
    "CentOS 9",
    "Fedora 42",
    "AlmaLinux 10",
    "Rocky Linux 10",
    "Alpine Linux 3.23",
    "FreeBSD 15.0",
    "openSUSE Leap 15",
    "Oracle Linux 9",
    "Arch Linux Latest",
    "CloudLinux 9",
]

LOCATIONS = [
    {"name": "USA",    "available": True},
    {"name": "Poland", "available": False},
    {"name": "France", "available": False},
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ORDERS = []
VERIFIED_USERS = set()


def is_admin(user_id):
    return user_id in ADMIN_IDS


def find_plan(plan_id):
    return next((p for p in PLANS if p["id"] == plan_id), None)


def store_order(user, plan, location, os_name, email):
    order = {
        "id": f"ord_{int(datetime.now().timestamp() * 1000)}",
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name or "",
        "plan": plan["name"],
        "usd": plan["usd"],
        "oxa": plan["oxa"],
        "location": location,
        "os": os_name,
        "email": email,
        "time": datetime.now(),
    }
    ORDERS.append(order)
    return order


async def is_member(context, user_id):
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Channel check failed for {user_id}: {e}")
        return None


async def check_join(context, user_id):
    if user_id in VERIFIED_USERS:
        return True
    status = await is_member(context, user_id)
    if status is True:
        VERIFIED_USERS.add(user_id)
        return True
    if status is None:
        return False
    return False


def join_gate_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join channel", url=REQUIRED_CHANNEL_LINK)],
        [InlineKeyboardButton("I've joined", callback_data="verify_join")],
    ])


(
    CHOOSING_PLAN,
    CHOOSING_OS,
    CHOOSING_LOCATION,
    ENTERING_EMAIL,
) = range(4)


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Buy an RDP", callback_data="buy")],
        [InlineKeyboardButton("Crawlio Network", url=ABOUT_LINK)],
        [InlineKeyboardButton("How it works", callback_data="how")],
        [InlineKeyboardButton("Contact support", url="https://t.me/wavuy")],
    ])


def plans_keyboard():
    kb = [[InlineKeyboardButton(f"{p['name']} — ${p['usd']}", callback_data=f"plan:{p['id']}")] for p in PLANS]
    kb.append([InlineKeyboardButton("Back", callback_data="menu")])
    return InlineKeyboardMarkup(kb)


def os_keyboard():
    kb = []
    row = []
    for i, os_name in enumerate(OPERATING_SYSTEMS):
        row.append(InlineKeyboardButton(os_name, callback_data=f"os:{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("Back", callback_data="back_to_plans")])
    return InlineKeyboardMarkup(kb)


def location_keyboard():
    kb = []
    for i, loc in enumerate(LOCATIONS):
        if loc["available"]:
            kb.append([InlineKeyboardButton(f"{loc['name']} — Available", callback_data=f"loc:{i}")])
        else:
            kb.append([InlineKeyboardButton(f"{loc['name']} — Maintenance", callback_data=f"loc_disabled:{i}")])
    kb.append([InlineKeyboardButton("Back", callback_data="back_to_os")])
    return InlineKeyboardMarkup(kb)


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirm order", callback_data="email_ok")],
        [InlineKeyboardButton("Change email", callback_data="email_change")],
        [InlineKeyboardButton("Cancel", callback_data="menu")],
    ])


def summary_keyboard(plan):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay with OxaPay", url=plan["oxa"])],
        [InlineKeyboardButton("Contact support", url="https://t.me/wavuy")],
        [InlineKeyboardButton("Main menu", callback_data="menu")],
    ])


async def send_join_gate(update, context):
    text = (
        "<b>Before you can use this bot</b>\n\n"
        "You need to join our channel first.\n"
        "Click the button below to join, then tap \"I've joined\"."
    )
    kb = join_gate_keyboard()
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def verify_join(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    status = await is_member(context, user_id)
    if status is False:
        await q.answer("You haven't joined yet.", show_alert=True)
        return
    VERIFIED_USERS.add(user_id)
    context.user_data.clear()
    text = (
        "<b>Crawlio Network</b>\n\n"
        "Buy an RDP in a few steps:\n"
        "1. Pick your plan\n"
        "2. Pick your OS\n"
        "3. Pick your location\n"
        "4. Enter your email\n"
        "5. Pay with crypto\n\n"
        "Your credentials will be sent by email."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


async def start(update, context):
    user_id = update.effective_user.id
    if not await check_join(context, user_id):
        await send_join_gate(update, context)
        return ConversationHandler.END
    context.user_data.clear()
    text = (
        "<b>Crawlio Network</b>\n\n"
        "Buy an RDP in a few steps:\n"
        "1. Pick your plan\n"
        "2. Pick your OS\n"
        "3. Pick your location\n"
        "4. Enter your email\n"
        "5. Pay with crypto\n\n"
        "Your credentials will be sent by email."
    )
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())
    return CHOOSING_PLAN


async def menu(update, context):
    context.user_data.clear()
    q = update.callback_query
    await q.answer()
    text = "Main menu. Pick an option below."
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())
    return CHOOSING_PLAN


async def buy_start(update, context):
    q = update.callback_query
    await q.answer()
    if not await check_join(context, q.from_user.id):
        await q.answer("Join the channel first.", show_alert=True)
        await send_join_gate(update, context)
        return ConversationHandler.END
    await q.edit_message_text("Choose your RDP plan.", reply_markup=plans_keyboard())
    return CHOOSING_PLAN


async def plan_chosen(update, context):
    q = update.callback_query
    await q.answer()
    plan_id = q.data.split(":")[1]
    plan = find_plan(plan_id)
    if not plan:
        await q.edit_message_text("Plan not found. Try again.", reply_markup=main_menu_keyboard())
        return CHOOSING_PLAN
    context.user_data["plan"] = plan
    text = (
        f"Selected plan: <b>{plan['name']}</b>\n"
        f"Price: <b>${plan['usd']} / month</b>\n\n"
        "Now choose your operating system."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=os_keyboard())
    return CHOOSING_OS


async def os_chosen(update, context):
    q = update.callback_query
    await q.answer()
    idx = int(q.data.split(":")[1])
    os_name = OPERATING_SYSTEMS[idx]
    context.user_data["os"] = os_name
    text = (
        f"Selected OS: <b>{os_name}</b>\n\n"
        "Now choose your location."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=location_keyboard())
    return CHOOSING_LOCATION


async def location_disabled(update, context):
    q = update.callback_query
    await q.answer("This location is under maintenance.", show_alert=True)
    return CHOOSING_LOCATION


async def location_chosen(update, context):
    q = update.callback_query
    await q.answer()
    idx = int(q.data.split(":")[1])
    loc = LOCATIONS[idx]
    if not loc["available"]:
        await q.answer("This location is under maintenance.", show_alert=True)
        return CHOOSING_LOCATION
    context.user_data["location"] = loc["name"]
    text = (
        f"Selected location: <b>{loc['name']}</b>\n\n"
        "<b>Send your email address.</b>\n"
        "Your RDP credentials will be sent there."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML)
    return ENTERING_EMAIL


async def back_to_plans(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Choose your RDP plan.", reply_markup=plans_keyboard())
    return CHOOSING_PLAN


async def back_to_os(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Choose your operating system.", reply_markup=os_keyboard())
    return CHOOSING_OS


async def email_received(update, context):
    email = update.message.text.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text("That doesn't look like a valid email. Send your email address.")
        return ENTERING_EMAIL
    context.user_data["email"] = email
    plan = context.user_data["plan"]
    os_name = context.user_data["os"]
    loc = context.user_data["location"]
    text = (
        "<b>Confirm your order</b>\n\n"
        f"Plan: {plan['name']}\n"
        f"OS: {os_name}\n"
        f"Location: {loc}\n"
        f"Email: {email}\n\n"
        f"<b>Total: ${plan['usd']} / month</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=confirm_keyboard())
    return ENTERING_EMAIL


async def email_confirm(update, context):
    q = update.callback_query
    await q.answer()
    plan = context.user_data.get("plan")
    os_name = context.user_data.get("os")
    loc = context.user_data.get("location")
    email = context.user_data.get("email")
    if not all([plan, os_name, loc, email]):
        await q.edit_message_text("Something went wrong. Start again with /start", reply_markup=main_menu_keyboard())
        return CHOOSING_PLAN
    order = store_order(q.from_user, plan, loc, os_name, email)
    text = (
        "<b>Order created</b>\n\n"
        f"Plan: {plan['name']}\n"
        f"OS: {os_name}\n"
        f"Location: {loc}\n"
        f"Email: {email}\n"
        f"Total: ${plan['usd']} / month\n\n"
        "Click below to pay with crypto via OxaPay.\n"
        "Once payment is confirmed, we'll email your RDP credentials."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=summary_keyboard(plan))
    admin_text = (
        "<b>NEW ORDER</b>\n\n"
        f"Name: {order['full_name']}\n"
        f"Username: @{order['username'] or '—'}\n"
        f"User ID: <code>{order['user_id']}</code>\n"
        f"Plan: {plan['name']}\n"
        f"OS: {os_name}\n"
        f"Location: {loc}\n"
        f"Email: {email}\n"
        f"Total: ${plan['usd']}\n"
        f"Time: {order['time'].strftime('%Y-%m-%d %H:%M')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")
    context.user_data.clear()
    return CHOOSING_PLAN


async def email_change(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data.pop("email", None)
    await q.edit_message_text("<b>Send your email address.</b>", parse_mode=ParseMode.HTML)
    return ENTERING_EMAIL


async def how_it_works(update, context):
    q = update.callback_query
    await q.answer()
    text = (
        "<b>How it works</b>\n\n"
        "1. Pick a plan that fits your needs\n"
        "2. Choose your operating system\n"
        "3. Choose your server location\n"
        "4. Enter your email\n"
        "5. Pay in crypto via OxaPay\n\n"
        "Once payment confirms, we'll email your RDP credentials within minutes.\n\n"
        "<b>No KYC</b> — we don't want your ID\n"
        "<b>Crypto only</b> — no cards, no chargebacks\n"
        "<b>Worldwide</b> — works from anywhere"
    )
    await q.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Crawlio Network", url=ABOUT_LINK)],
            [InlineKeyboardButton("Back", callback_data="menu")],
        ]),
    )
    return CHOOSING_PLAN


async def admin_command(update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Not authorized.")
        return
    total = len(ORDERS)
    total_usd = sum(o["usd"] for o in ORDERS)
    unique_emails = len(set(o["email"] for o in ORDERS))
    text = (
        "<b>Admin Panel</b>\n\n"
        f"Total orders: <b>{total}</b>\n"
        f"Total revenue: <b>${total_usd:.2f}</b>\n"
        f"Unique customers: <b>{unique_emails}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("View recent orders", callback_data="admin_orders")],
        [InlineKeyboardButton("Stats", callback_data="admin_stats")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def admin_orders(update, context):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return
    if not ORDERS:
        await q.edit_message_text(
            "No orders yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_back")]]),
        )
        return
    lines = []
    for i, o in enumerate(reversed(ORDERS[-20:]), 1):
        when = o["time"].strftime("%d %b %H:%M")
        lines.append(
            f"<b>#{i}</b>\n"
            f"Email: {o['email']}\n"
            f"Plan: {o['plan']}\n"
            f"OS: {o['os']}\n"
            f"Location: {o['location']}\n"
            f"Total: ${o['usd']}\n"
            f"Time: {when}"
        )
    text = "<b>Recent Orders</b>\n\n" + "\n\n".join(lines)
    await q.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Refresh", callback_data="admin_orders")],
            [InlineKeyboardButton("Back", callback_data="admin_back")],
        ]),
    )


async def admin_stats(update, context):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return
    total = len(ORDERS)
    total_usd = sum(o["usd"] for o in ORDERS)
    unique_emails = len(set(o["email"] for o in ORDERS))
    plan_counts = {}
    for o in ORDERS:
        plan_counts[o["plan"]] = plan_counts.get(o["plan"], 0) + 1
    plan_breakdown = "\n".join(f"{name}: {count}" for name, count in plan_counts.items()) or "None"
    os_counts = {}
    for o in ORDERS:
        os_counts[o["os"]] = os_counts.get(o["os"], 0) + 1
    os_breakdown = "\n".join(f"{name}: {count}" for name, count in os_counts.items()) or "None"
    text = (
        "<b>Stats</b>\n\n"
        f"Orders: <b>{total}</b>\n"
        f"Revenue: <b>${total_usd:.2f}</b>\n"
        f"Unique customers: <b>{unique_emails}</b>\n\n"
        f"<b>By plan</b>\n{plan_breakdown}\n\n"
        f"<b>By OS</b>\n{os_breakdown}"
    )
    await q.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("Back", callback_data="admin_back")],
        ]),
    )


async def admin_back(update, context):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return
    total = len(ORDERS)
    total_usd = sum(o["usd"] for o in ORDERS)
    unique_emails = len(set(o["email"] for o in ORDERS))
    text = (
        "<b>Admin Panel</b>\n\n"
        f"Total orders: <b>{total}</b>\n"
        f"Total revenue: <b>${total_usd:.2f}</b>\n"
        f"Unique customers: <b>{unique_emails}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("View recent orders", callback_data="admin_orders")],
        [InlineKeyboardButton("Stats", callback_data="admin_stats")],
    ])
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cancel(update, context):
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("Cancelled. Send /start to begin again.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(buy_start, pattern=r"^buy$"),
            CallbackQueryHandler(how_it_works, pattern=r"^how$"),
            CallbackQueryHandler(menu, pattern=r"^menu$"),
        ],
        states={
            CHOOSING_PLAN: [
                CallbackQueryHandler(plan_chosen, pattern=r"^plan:"),
                CallbackQueryHandler(back_to_plans, pattern=r"^back_to_plans$"),
                CallbackQueryHandler(menu, pattern=r"^menu$"),
            ],
            CHOOSING_OS: [
                CallbackQueryHandler(os_chosen, pattern=r"^os:"),
                CallbackQueryHandler(back_to_plans, pattern=r"^back_to_plans$"),
                CallbackQueryHandler(back_to_os, pattern=r"^back_to_os$"),
                CallbackQueryHandler(menu, pattern=r"^menu$"),
            ],
            CHOOSING_LOCATION: [
                CallbackQueryHandler(location_disabled, pattern=r"^loc_disabled:"),
                CallbackQueryHandler(location_chosen, pattern=r"^loc:"),
                CallbackQueryHandler(back_to_os, pattern=r"^back_to_os$"),
                CallbackQueryHandler(menu, pattern=r"^menu$"),
            ],
            ENTERING_EMAIL: [
                CallbackQueryHandler(email_confirm, pattern=r"^email_ok$"),
                CallbackQueryHandler(email_change, pattern=r"^email_change$"),
                CallbackQueryHandler(menu, pattern=r"^menu$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, email_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(verify_join, pattern=r"^verify_join$"))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_orders, pattern=r"^admin_orders$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern=r"^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern=r"^admin_back$"))

    logger.info("Crawlio Network bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()