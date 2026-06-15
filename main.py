#!/usr/bin/env python3
"""
Telegram Dedicated Multi-Account Control-Panel (MongoDB Edition)
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
    if clean_chat.startswith('-') and clean_chat[1:].isdigit(): return int(clean_chat)
    if clean_chat.isdigit(): return int(clean_chat)
    return clean_chat

SOURCE_CHAT = parse_chat_identifier(SOURCE_CHAT_RAW)

# Runtime Global States
IS_FORWARDER_ACTIVE = True
IS_TIMER_ACTIVE = True

DB_DATA = {
    "id1_session": "", "id1_name": "[Not Connected]", "group1_targets": [],
    "id2_session": "", "id2_name": "[Not Connected]", "group2_targets": []
}

CUSTOM_MESSAGES = {
    "msg1": "J0!N£ M¥ ‡}!0",
    "msg2": "J0!N£ M¥ ‡}!0", "msg3": "J0!N£ M¥ ‡}!0"
}

# MongoDB Helper Functions
db_collection = None
if MONGO_URL:
    try:
        mongo_client = MongoClient(MONGO_URL)
        # 'telegram_bot' naam ka DB aur 'settings' naam ka table/collection banega
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

def get_status_text():
    f_status = "🟢 ON" if IS_FORWARDER_ACTIVE else "🔴 OFF"
    t_status = "🟢 ON" if IS_TIMER_ACTIVE else "🔴 OFF"
    return (
        f"🤖 **Easy Multi-Account Panel (MongoDB)**\n"
        f"-----------------------------------\n"
        f"📡 **Live Forwarder:** {f_status}\n"
        f"⏳ **7-10 Min Timer:** {t_status}\n\n"
        f"📥 **Source Chat:** `{SOURCE_CHAT}`\n\n"
        f"👤 **Account 1:** {DB_DATA['id1_name']}\n"
        f"🎯 **Target Group 1:** `{DB_DATA['group1_targets']}`\n\n"
        f"👤 **Account 2:** {DB_DATA['id2_name']}\n"
        f"🎯 **Target Group 2:** `{DB_DATA['group2_targets']}`"
    )

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

    @bot_client.on(events.NewMessage(chats=ADMIN_ID, pattern='/start'))
    async def start_handler(event):
        buttons = [
            [Button.inline("📡 Forwarder ON", b"f_on"), Button.inline("📡 Forwarder OFF", b"f_off")],
            [Button.inline("⏳ Timer ON", b"t_on"), Button.inline("⏳ Timer OFF", b"t_off")],
            [Button.inline("📊 Check Status", b"check_status")]
        ]
        await event.respond(
            "⚙️ **Easy Account Router Control Panel (MongoDB)** ⚙️\n\n"
            "➡️ **Account 1 Setup:**\n"
            "• `/add_id1 <string_session>`\n"
            "• `/add_group1 @group1, @group2`\n\n"
            "➡️ **Account 2 Setup:**\n"
            "• `/add_id2 <string_session>`\n"
            "• `/add_group2 @group3, @group4`\n\n"
            "• `/clear_all` — Sab delete karne ke liye.",
            buttons=buttons
        )

    @bot_client.on(events.CallbackQuery(chats=ADMIN_ID))
    async def callback_handler(event):
        global IS_FORWARDER_ACTIVE, IS_TIMER_ACTIVE
        if event.data == b"f_on": IS_FORWARDER_ACTIVE = True
        elif event.data == b"f_off": IS_FORWARDER_ACTIVE = False
        elif event.data == b"t_on": IS_TIMER_ACTIVE = True
        elif event.data == b"t_off": IS_TIMER_ACTIVE = False
            
        await event.edit(get_status_text(), buttons=[
            [Button.inline("📡 Forwarder ON", b"f_on"), Button.inline("📡 Forwarder OFF", b"f_off")],
            [Button.inline("⏳ Timer ON", b"t_on"), Button.inline("⏳ Timer OFF", b"t_off")],
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
            
            @temp_client.on(events.NewMessage(chats=SOURCE_CHAT))
            async def forward_handler(ev):
                if not IS_FORWARDER_ACTIVE or isinstance(ev.message, MessageService): return
                targets = DB_DATA["group1_targets"] if key_prefix == "id1" else DB_DATA["group2_targets"]
                for target in targets:
                    try:
                        await asyncio.sleep(random.uniform(2, 5))
                        await ev.client.send_message(target, ev.message)
                    except Exception: pass
            
            loop.create_task(temp_client.run_until_disconnected())
            await status_msg.edit(f"✅ **Account {key_prefix[-1]} Connected!**\nUser: **{name_display}**")
        except Exception as e:
            await status_msg.edit(f"❌ Connection Error: {e}")

    @bot_client.on(events.NewMessage(chats=ADMIN_ID))
    async def text_commands(event):
        global DB_DATA
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
        elif text.startswith("/add_id2"):
            session = text.replace("/add_id2", "").strip()
            if session: await connect_and_save_user(session, "id2", event)
        elif text.startswith("/add_group2"):
            args = text.replace("/add_group2", "").strip()
            if args:
                DB_DATA["group2_targets"] = [parse_chat_identifier(t) for t in args.split(",") if t.strip()]
                save_cloud_data()
                await event.respond(f"✅ **Target Group 2 Updated!**\nLive Targets: `{DB_DATA['group2_targets']}`")
        elif text == "/clear_all":
            for cl in user_clients.values():
                try: await cl.disconnect()
                except Exception: pass
            user_clients.clear()
            DB_DATA.update({"id1_session": "", "id1_name": "[Not Connected]", "group1_targets": [], "id2_session": "", "id2_name": "[Not Connected]", "group2_targets": []})
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
    
    if DB_DATA["id1_session"]:
        try:
            u1 = TelegramClient(StringSession(DB_DATA["id1_session"]), API_ID, API_HASH)
            await u1.connect()
            if await u1.is_user_authorized():
                user_clients["id1"] = u1
                @u1.on(events.NewMessage(chats=SOURCE_CHAT))
                async def u1_forwarder(event):
                    if not IS_FORWARDER_ACTIVE or isinstance(event.message, MessageService): return
                    for target in DB_DATA["group1_targets"]:
                        try:
                            await asyncio.sleep(random.uniform(2, 5))
                            await event.client.send_message(target, event.message)
                        except Exception: pass
                loop.create_task(u1.run_until_disconnected())
        except Exception: pass

    if DB_DATA["id2_session"]:
        try:
            u2 = TelegramClient(StringSession(DB_DATA["id2_session"]), API_ID, API_HASH)
            await u2.connect()
            if await u2.is_user_authorized():
                user_clients["id2"] = u2
                @u2.on(events.NewMessage(chats=SOURCE_CHAT))
                async def u2_forwarder(event):
                    if not IS_FORWARDER_ACTIVE or isinstance(event.message, MessageService): return
                    for target in DB_DATA["group2_targets"]:
                        try:
                            await asyncio.sleep(random.uniform(2, 5))
                            await event.client.send_message(target, event.message)
                        except Exception: pass
                loop.create_task(u2.run_until_disconnected())
        except Exception: pass

    asyncio.create_task(periodic_broadcaster(user_clients))
    logger.info("🚀 MongoDB Protected Router Engine Online!")
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
