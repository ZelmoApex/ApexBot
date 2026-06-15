#!/usr/bin/env python3
"""
Telegram Dedicated Multi-Account Control-Panel (With Isolated Approval Groups)
======================================================================
"""

import os
import sys
import asyncio
import random
import logging
from typing import List, Union, Dict

# Telethon & MongoDB Dependencies
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from telethon.tl.types import MessageService
from telethon.tl.functions.messages import HideChatJoinRequestRequest
from telethon import Button
from pymongo import MongoClient

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MongoMultiAccount")

# =====================================================================
# CONFIGURATION & MONGODB STORAGE
# =====================================================================
ADMIN_ID = 8705901135  
API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SOURCE_CHAT_RAW = os.environ.get("SOURCE_CHAT", "")
MONGO_URL = os.environ.get("MONGO_URL", "") 

def parse_chat_identifier(chat: str) -> Union[str, int]:
    if not chat: return ""
    clean_chat = str(chat).strip()
    if clean_chat.startswith('https://t.me/+') or clean_chat.startswith('https://t.me/joinchat/'):
        return clean_chat # Keep raw link for private chat joins if needed
    if clean_chat.startswith('-') and clean_chat[1:].isdigit(): return int(clean_chat)
    if clean_chat.isdigit(): return int(clean_chat)
    return clean_chat

SOURCE_CHAT = parse_chat_identifier(SOURCE_CHAT_RAW)

# Runtime Global States
IS_FORWARDER_ACTIVE = True
IS_TIMER_ACTIVE = True
IS_APPROVAL_ACTIVE = True

DB_DATA = {
    "id1_session": "", "id1_name": "[Not Connected]", "group1_targets": [], "approve1_chat": "",
    "id2_session": "", "id2_name": "[Not Connected]", "group2_targets": [], "approve2_chat": ""
}

CUSTOM_MESSAGES = {
    "msg1": "Hello! Welcome to our automated channel.",
    "msg2": "", "msg3": ""
}

# MongoDB Helper Functions
db_collection = None
if MONGO_URL:
    try:
        mongo_client = MongoClient(MONGO_URL)
        db_collection = mongo_client["telegram_bot"]["settings"]
        logger.info("🍃 MongoDB Connected Successfully!")
    except Exception as e:
        logger.error(f"❌ MongoDB Connection Error: {e}")

def fetch_cloud_data():
    global DB_DATA
    if db_collection is None: return
    try:
        document = db_collection.find_one({"_id": "bot_configuration"})
        if document:
            DB_DATA = document.get("easy_mult_map", DB_DATA)
            logger.info("☁️ Data loaded from MongoDB successfully.")
    except Exception as e:
        logger.error(f"❌ MongoDB Fetch Error: {e}")

def save_cloud_data():
    if db_collection is None: return False
    try:
        db_collection.update_one(
            {"_id": "bot_configuration"},
            {"$set": {"easy_mult_map": DB_DATA}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB Save Error: {e}")
    return False

# Initialize Data Load
fetch_cloud_data()

# Help text layout
HELP_TEXT = (
    "⚙️ **Ultimate Easy Router Help Menu** ⚙️\n\n"
    "👇 **Sabhi Commands Ki List:**\n\n"
    "🟢 **ACCOUNT 1 SETUP:**\n"
    "• `/add_id1 <string_session>` ➔ Account 1 connect karein.\n"
    "• `/add_group1 @grp1, @grp2` ➔ Forwarding targets dalein.\n"
    "• `/add_approve1 <link/id>` ➔ Alag se approval group jodein.\n\n"
    "🔵 **ACCOUNT 2 SETUP:**\n"
    "• `/add_id2 <string_session>` ➔ Account 2 connect karein.\n"
    "• `/add_group2 @grp3, @grp4` ➔ Forwarding targets dalein.\n"
    "• `/add_approve2 <link/id>` ➔ Alag se approval group jodein.\n\n"
    "📢 **TIMER MESSAGES (7-10 Min Ads):**\n"
    "• `/msg1 <text>` | `/msg2 <text>`\n\n"
    "⚙️ **SYSTEM CONTROL:**\n"
    "• `/status` ➔ Status dekhein | `/clear_all` ➔ Data reset."
)

def get_status_text():
    f_status = "🟢 ON" if IS_FORWARDER_ACTIVE else "🔴 OFF"
    t_status = "🟢 ON" if IS_TIMER_ACTIVE else "🔴 OFF"
    a_status = "🟢 ON" if IS_APPROVAL_ACTIVE else "🔴 OFF"
    return (
        f"🤖 **Easy Multi-Account Panel (Isolated Approvals)**\n"
        f"-----------------------------------\n"
        f"📡 **Live Forwarder:** {f_status}\n"
        f"⏳ **7-10 Min Timer:** {t_status}\n"
        f"⚡ **Auto-Request Approver:** {a_status}\n\n"
        f"👤 **Account 1:** {DB_DATA['id1_name']}\n"
        f"🎯 **Target Group 1:** `{DB_DATA['group1_targets']}`\n"
        f"🔐 **Approval Group 1:** `{DB_DATA.get('approve1_chat', 'Not Set')}`\n\n"
        f"👤 **Account 2:** {DB_DATA['id2_name']}\n"
        f"🎯 **Target Group 2:** `{DB_DATA['group2_targets']}`\n"
        f"🔐 **Approval Group 2:** `{DB_DATA.get('approve2_chat', 'Not Set')}`"
    )

# =====================================================================
# BACKGROUND PENDING REQUESTS CLEARER (Using Isolated Approval Settings)
# =====================================================================
async def old_requests_cleaner(user_clients):
    """Har 3 minute me alag se diye gaye approval groups ki requests accept karega"""
    await asyncio.sleep(20)
    while True:
        if IS_APPROVAL_ACTIVE:
            # Process Account 1 Dedicated Approval Group
            if "id1" in user_clients and DB_DATA.get("approve1_chat"):
                client = user_clients["id1"]
                target = DB_DATA["approve1_chat"]
                try:
                    async for request in client.iter_chat_join_requests(target):
                        if not IS_APPROVAL_ACTIVE: break
                        try:
                            await client(HideChatJoinRequestRequest(
                                peer=target, user_id=request.user_id, approve=True
                            ))
                            await asyncio.sleep(random.uniform(2, 4))
                        except Exception: pass
                except Exception: pass

            # Process Account 2 Dedicated Approval Group
            if "id2" in user_clients and DB_DATA.get("approve2_chat"):
                client = user_clients["id2"]
                target = DB_DATA["approve2_chat"]
                try:
                    async for request in client.iter_chat_join_requests(target):
                        if not IS_APPROVAL_ACTIVE: break
                        try:
                            await client(HideChatJoinRequestRequest(
                                peer=target, user_id=request.user_id, approve=True
                            ))
                            await asyncio.sleep(random.uniform(2, 4))
                        except Exception: pass
                except Exception: pass
        await asyncio.sleep(180)

# =====================================================================
# AUTOMATIC 7-10 MINUTES PERIODIC BROADCASTER
# =====================================================================
async def periodic_broadcaster(user_clients):
    await asyncio.sleep(15)
    while True:
        if IS_TIMER_ACTIVE:
            active_msgs = [v for k, v in CUSTOM_MESSAGES.items() if v]
            if active_msgs:
                chosen_msg = random.choice(active_msgs)
                if "id1" in user_clients and DB_DATA["group1_targets"]:
                    for target in DB_DATA["group1_targets"]:
                        try: await user_clients["id1"].send_message(target, chosen_msg)
                        except Exception: pass
                        await asyncio.sleep(random.uniform(2, 5))
                if "id2" in user_clients and DB_DATA["group2_targets"]:
                    for target in DB_DATA["group2_targets"]:
                        try: await user_clients["id2"].send_message(target, chosen_msg)
                        except Exception: pass
                        await asyncio.sleep(random.uniform(2, 5))
        await asyncio.sleep(random.randint(420, 600))

# =====================================================================
# BOT HANDLERS & SECURITY CHECK
# =====================================================================
def register_bot_handlers(bot_client: TelegramClient, user_clients, loop):

    @bot_client.on(events.NewMessage())
    async def security_guard(event):
        if event.sender_id != ADMIN_ID and event.raw_text.startswith('/'):
            await event.reply("bot tumare liye nahi hai")
            raise events.StopPropagation

    @bot_client.on(events.CallbackQuery())
    async def button_security_guard(event):
        if event.sender_id != ADMIN_ID:
            await event.answer("bot tumare liye nahi hai", alert=True)
            raise events.StopPropagation

    # --- START COMMAND ---
    @bot_client.on(events.NewMessage(chats=ADMIN_ID, pattern='/start'))
    async def start_handler(event):
        buttons = [
            [Button.inline("📡 Forwarder ON", b"f_on"), Button.inline("📡 Forwarder OFF", b"f_off")],
            [Button.inline("⏳ Timer ON", b"t_on"), Button.inline("⏳ Timer OFF", b"t_off")],
            [Button.inline("⚡ Approver ON", b"a_on"), Button.inline("⚡ Approver OFF", b"a_off")],
            [Button.inline("📊 Check Status", b"check_status")]
        ]
        await event.respond(
            "⚙️ **Easy Account Router Control Panel (Isolated Approval)** ⚙️\n\n"
            "Bot active hai! Commands ki list ke liye `/help` bhein.\n\n"
            "👇 **Quick Controls:**",
            buttons=buttons
        )

    # --- HELP COMMAND ---
    @bot_client.on(events.NewMessage(chats=ADMIN_ID, pattern='/help'))
    async def help_handler(event):
        await event.respond(HELP_TEXT)

    # --- STATUS COMMAND ---
    @bot_client.on(events.NewMessage(chats=ADMIN_ID, pattern='/status'))
    async def status_command_handler(event):
        await event.respond(get_status_text())

    @bot_client.on(events.CallbackQuery(chats=ADMIN_ID))
    async def callback_handler(event):
        global IS_FORWARDER_ACTIVE, IS_TIMER_ACTIVE, IS_APPROVAL_ACTIVE
        if event.data == b"f_on": IS_FORWARDER_ACTIVE = True
        elif event.data == b"f_off": IS_FORWARDER_ACTIVE = False
        elif event.data == b"t_on": IS_TIMER_ACTIVE = True
        elif event.data == b"t_off": IS_TIMER_ACTIVE = False
        elif event.data == b"a_on": IS_APPROVAL_ACTIVE = True
        elif event.data == b"a_off": IS_APPROVAL_ACTIVE = False
            
        await event.edit(get_status_text(), buttons=[
            [Button.inline("📡 Forwarder ON", b"f_on"), Button.inline("📡 Forwarder OFF", b"f_off")],
            [Button.inline("⏳ Timer ON", b"t_on"), Button.inline("⏳ Timer OFF", b"t_off")],
            [Button.inline("⚡ Approver ON", b"a_on"), Button.inline("⚡ Approver OFF", b"a_off")],
            [Button.inline("📊 Check Status", b"check_status")]
        ])

    async def connect_and_save_user(session_str, key_prefix, event):
        status_msg = await event.respond(f"⏳ Account {key_prefix[-1]} ko connect kiya ja raha hai...")
        try:
            temp_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await temp_client.connect()
            if not await temp_client.is_user_authorized():
                return await status_msg.edit("❌ Error: String Session invalid hai!")
            
            me = await temp_client.get_me()
            name_display = f"{me.first_name} (@{me.username or 'NoUser'})"
            
            if key_prefix in user_clients and user_clients[key_prefix]:
                try: await user_clients[key_prefix].disconnect()
                except Exception: pass
                
            DB_DATA[f"{key_prefix}_session"] = session_str
            DB_DATA[f"{key_prefix}_name"] = name_display
            save_cloud_data()
            user_clients[key_prefix] = temp_client
            
            # Setup Live Forwarder
            @temp_client.on(events.NewMessage(chats=SOURCE_CHAT))
            async def forward_handler(ev):
                if not IS_FORWARDER_ACTIVE or isinstance(ev.message, MessageService): return
                targets = DB_DATA["group1_targets"] if key_prefix == "id1" else DB_DATA["group2_targets"]
                for target in targets:
                    try:
                        await asyncio.sleep(random.uniform(2, 5))
                        await ev.client.send_message(target, ev.message)
                    except Exception: pass

            # Setup Live Auto-Request Approval (For incoming live requests on dedicated approval group)
            @temp_client.on(events.ChatAction)
            async def approval_handler(ev):
                if not IS_APPROVAL_ACTIVE: return
                target_approval = DB_DATA.get("approve1_chat") if key_prefix == "id1" else DB_DATA.get("approve2_chat")
                if target_approval and ev.user_joined and ev.action_message and getattr(ev.action_message, 'action', None):
                    if ev.chat_id == target_approval or (ev.chat and getattr(ev.chat, 'username', '') == target_approval):
                        try:
                            await ev.client(HideChatJoinRequestRequest(
                                peer=ev.chat_id, user_id=ev.user_id, approve=True
                            ))
                        except Exception: pass
            
            loop.create_task(temp_client.run_until_disconnected())
            await status_msg.edit(f"✅ **Account {key_prefix[-1]} Connected!**\nUser: **{name_display}**")
        except Exception as e:
            await status_msg.edit(f"❌ Connection Error: {e}")

    @bot_client.on(events.NewMessage(chats=ADMIN_ID))
    async def text_commands(event):
        global DB_DATA, CUSTOM_MESSAGES
        text = event.raw_text.strip()
        
        if text.startswith("/add_id1"):
            session = text.replace("/add_id1", "").strip()
            if session: await connect_and_save_user(session, "id1", event)
        elif text.startswith("/add_group1"):
            args = text.replace("/add_group1", "").strip()
            if args:
                DB_DATA["group1_targets"] = [parse_chat_identifier(t) for t in args.split(",") if t.strip()]
                save_cloud_data()
                await event.respond(f"✅ **Target Group 1 Updated!**\nLive Targets: `{DB_DATA['group1_targets']}`")
        elif text.startswith("/add_approve1"):
            arg = text.replace("/add_approve1", "").strip()
            if arg:
                DB_DATA["approve1_chat"] = parse_chat_identifier(arg)
                save_cloud_data()
                await event.respond(f"✅ **Isolated Approval Group 1 Connected:** `{DB_DATA['approve1_chat']}`")
                
        elif text.startswith("/add_id2"):
            session = text.replace("/add_id2", "").strip()
            if session: await connect_and_save_user(session, "id2", event)
        elif text.startswith("/add_group2"):
            args = text.replace("/add_group2", "").strip()
            if args:
                DB_DATA["group2_targets"] = [parse_chat_identifier(t) for t in args.split(",") if t.strip()]
                save_cloud_data()
                await event.respond(f"✅ **Target Group 2 Updated!**\nLive Targets: `{DB_DATA['group2_targets']}`")
        elif text.startswith("/add_approve2"):
            arg = text.replace("/add_approve2", "").strip()
            if arg:
                DB_DATA["approve2_chat"] = parse_chat_identifier(arg)
                save_cloud_data()
                await event.respond(f"✅ **Isolated Approval Group 2 Connected:** `{DB_DATA['approve2_chat']}`")

        elif text.startswith("/msg1"):
            msg_text = text.replace("/msg1", "").strip()
            if msg_text:
                CUSTOM_MESSAGES["msg1"] = msg_text
                await event.respond("✅ **Timer Message 1 Saved!**")
        elif text.startswith("/msg2"):
            msg_text = text.replace("/msg2", "").strip()
            if msg_text:
                CUSTOM_MESSAGES["msg2"] = msg_text
                await event.respond("✅ **Timer Message 2 Saved!**")
        elif text == "/clear_all":
            for cl in user_clients.values():
                try: await cl.disconnect()
                except Exception: pass
            user_clients.clear()
            DB_DATA.update({"id1_session": "", "id1_name": "[Not Connected]", "group1_targets": [], "approve1_chat": "", "id2_session": "", "id2_name": "[Not Connected]", "group2_targets": [], "approve2_chat": ""})
            save_cloud_data()
            await event.respond("🗑️ Everything reset permanently in MongoDB.")

# =====================================================================
# MAIN ENGINE RUNNER
# =====================================================================
async def main():
    loop = asyncio.get_running_loop()
    user_clients = {} 
    
    bot_client = TelegramClient('bot_controller', API_ID, API_HASH)
    register_bot_handlers(bot_client, user_clients, loop)
    await bot_client.start(bot_token=BOT_TOKEN)
    
    # Reload Account 1
    if DB_DATA.get("id1_session"):
        try:
            u1 = TelegramClient(StringSession(DB_DATA["id1_session"]), API_ID, API_HASH)
            await u1.connect()
            if await u1.is_user_authorized():
                user_clients["id1"] = u1
                loop.create_task(u1.run_until_disconnected())
        except Exception: pass

    # Reload Account 2
    if DB_DATA.get("id2_session"):
        try:
            u2 = TelegramClient(StringSession(DB_DATA["id2_session"]), API_ID, API_HASH)
            await u2.connect()
            if await u2.is_user_authorized():
                user_clients["id2"] = u2
                loop.create_task(u2.run_until_disconnected())
        except Exception: pass

    # Tasks Activation
    asyncio.create_task(periodic_broadcaster(user_clients))
    asyncio.create_task(old_requests_cleaner(user_clients))
    
    logger.info("🚀 Isolated Auto-Approval System Engine Online!")
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
