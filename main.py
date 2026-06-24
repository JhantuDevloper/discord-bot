import os
import asyncio
import random
import re
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# ====================================================================
# 🌐 KEEP-ALIVE WEB SERVER (Bot ko 24/7 online rakhne ke liye)
# ====================================================================
app = Flask('')

@app.route('/')
def home():
    # Render ya Koyeb jab is page par ping karega toh ye 200 OK dega
    return "Bot is Online and Running 24/7! 🚀"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ====================================================================
# 🤖 DISCORD BOT SETUP (Intents aur prefix config)
# ====================================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ====================================================================
# ⚠️ CONFIGURATION: Apne Server ke Channels ki ID yahan badlo!
# ====================================================================
TEST_CHANNEL_ID = 1519054759682637966      # Jahan single players details aur join bhejenge
SQUAD_CHANNEL_ID = 1519253849486135380    # Jahan automatic bani hui squads post hongi
TEAM_DETAILS_CHANNEL_ID = 1519195214978355300  # Jahan full squads register karengi

# Global Memory Database
waiting_queue = []     # Line me khade active players
verified_users = set()  # Verified players ki ID
user_names = {}        # Player ID -> Real In-Game Name (IGN)
all_teams = []         # Bani hui sabhi squads (Slots list)

@bot.event
async def on_ready():
    print(f'\n=======================================')
    print(f'🔥 FREE FIRE PROFESSIONAL BOT READY!')
    print(f'Logged in as: {bot.user.name}')
    print(f'=======================================\n')
    # Bot ka status set karna
    await bot.change_presence(activity=discord.Game(name="Free Fire Tournaments 🏆"))

# Helper function: Message se Player ka In-Game Name (IGN) filter karna
def extract_ign(text):
    lines = text.split('\n')
    for line in lines:
        if 'name' in line.lower():
            # Colon (:), hyphens (-) aur extra space hata kar name nikalna
            cleaned = re.sub(r'(?i).*name\s*[:\-=]?\s*', '', line).strip()
            if cleaned:
                return cleaned
    return None

# ====================================================================
# 📩 MESSAGE FILTER & TRIGGER EVENTS
# ====================================================================
@bot.event
async def on_message(message):
    # Rule 1: Khud ke message ko ignore karo
    if message.author == bot.user:
        return

    # Server Admin check karne ke liye (Admins ke messages safe rahenge)
    is_admin = message.author.id == message.guild.owner_id or message.author.guild_permissions.administrator
    msg_text = message.content.lower().strip()

    # ----------------------------------------------------------------
    # 1. SINGLE PLAYER CHANNEL LOGIC
    # ----------------------------------------------------------------
    if message.channel.id == 1519054759682637966:
        
        # Flexi-Join Trigger (Player chahe '!join' likhe ya sirf 'join')
        if msg_text == "!join" or msg_text == "join" or msg_text.startswith("join"):
            global waiting_queue, all_teams, user_names

            # Check 1: User ne pehle details di hain ya nahi?
            if message.author.id not in verified_users:
                fail = await message.channel.send(f"⚠️ {message.author.mention}, pehle upar bataye gaye format me details submit karo! Phir `join` likhna.")
                await asyncio.sleep(5)
                try:
                    await fail.delete()
                    await message.delete()
                except: pass
                return

            # Check 2: Player pehle se hi queue me toh nahi hai?
            if message.author in waiting_queue:
                fail = await message.channel.send(f"⚠️ {message.author.mention}, aap pehle se waiting list me hain!")
                await asyncio.sleep(4)
                try:
                    await fail.delete()
                    await message.delete()
                except: pass
                return

            # Check 3: Player pehle se kisi slot/squad me toh nahi hai?
            for team in all_teams:
                team_member_ids = [m.id if isinstance(m, discord.Member) else m for m in team]
                if message.author.id in team_member_ids:
                    fail = await message.channel.send(f"⚠️ {message.author.mention}, aapki team pehle hi ban chuki hai!")
                    await asyncio.sleep(4)
                    try:
                        await fail.delete()
                        await message.delete()
                    except: pass
                    return

            # Active List me add karo
            waiting_queue.append(message.author)
            count = len(waiting_queue)
            
            status = await message.channel.send(f"✅ {message.author.mention} entered the queue! **({count}/4 Players Ready)**")
            await asyncio.sleep(4)
            try:
                await status.delete()
                await message.delete()
            except: pass

            # Jaise hi exact 4 players honge, random team banegi
            if len(waiting_queue) >= 4:
                random.shuffle(waiting_queue)
                new_squad = [waiting_queue.pop(0) for _ in range(4)]
                all_teams.append(new_squad)
                
                squad_channel = bot.get_channel(SQUAD_CHANNEL_ID)
                team_num = len(all_teams)
                
                if squad_channel:
                    # Mentions ke badle unke registered IGN fetch karna
                    p1_name = user_names.get(new_squad[0].id, new_squad[0].name)
                    p2_name = user_names.get(new_squad[1].id, new_squad[1].name)
                    p3_name = user_names.get(new_squad[2].id, new_squad[2].name)
                    p4_name = user_names.get(new_squad[3].id, new_squad[3].name)

                    embed = discord.Embed(
                        title=f"🎮 SQUAD #{team_num} FOR TEST IS READY! 🎮",
                        description=(
                            f"➔ **Player 1:** {p1_name} ({new_squad[0].mention})\n"
                            f"➔ **Player 2:** {p2_name} ({new_squad[1].mention})\n"
                            f"➔ **Player 3:** {p3_name} ({new_squad[2].mention})\n"
                            f"➔ **Player 4:** {p4_name} ({new_squad[3].mention})\n"
                        ),
                        color=discord.Color.green()
                    )
                    pings = " ".join([p.mention for p in new_squad])
                    await squad_channel.send(content=f"📢 {pings}", embed=embed)
            return

        # Commands ko bina disturb kiye bypass karo
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        # Single Player Registration Checker
        if not is_admin:
            if "name" in msg_text and "id" in msg_text and "instagram" in msg_text:
                ign = extract_ign(message.content)
                if not ign:
                    ign = message.author.name # Fallback name agar fail ho jaye
                
                user_names[message.author.id] = ign  # Real IGN save ho gaya database me
                verified_users.add(message.author.id)
                await message.add_reaction("✅")
                
                confirm_msg = await message.channel.send(
                    f"🎉 {message.author.mention}, aapka IGN **'{ign}'** verify ho gaya hai!\nAb ready ho toh niche **`join`** type karo!"
                )
                await asyncio.sleep(6)
                try: await confirm_msg.delete()
                except: pass
            else:
                # Agar player ne galat format bheja toh delete kar do
                try:
                    await message.delete()
                    warning_msg = await message.channel.send(
                        f"⚠️ {message.author.mention}, is channel me sirf details allowed hain!\n"
                        "
