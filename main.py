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
TEST_CHANNEL_ID = 1519054759682637966      # Single players ke liye details aur join channel
SQUAD_CHANNEL_ID = 1519253849486135380    # Jahan automatic squads post hongi
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
    await bot.change_presence(activity=discord.Game(name="Free Fire Tournaments 🏆"))

# Helper function: Message se Player ka In-Game Name (IGN) filter karna
def extract_ign(text):
    lines = text.split('\n')
    for line in lines:
        if 'name' in line.lower():
            cleaned = re.sub(r'(?i).*name\s*[:\-=]?\s*', '', line).strip()
            if cleaned:
                return cleaned
    return None

# ====================================================================
# 📩 MESSAGE FILTER & TRIGGER EVENTS
# ====================================================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    is_admin = message.author.id == message.guild.owner_id or message.author.guild_permissions.administrator
    msg_text = message.content.lower().strip()

    # 1. SINGLE PLAYER CHANNEL LOGIC
    if message.channel.id == TEST_CHANNEL_ID:
        if msg_text == "!join" or msg_text == "join" or msg_text.startswith("join"):
            global waiting_queue, all_teams, user_names

            if message.author.id not in verified_users:
                fail = await message.channel.send(f"⚠️ {message.author.mention}, pehle upar bataye gaye format me details submit karo! Phir `join` likhna.")
                await asyncio.sleep(5)
                try:
                    await fail.delete()
                    await message.delete()
                except: pass
                return

            if message.author in waiting_queue:
                fail = await message.channel.send(f"⚠️ {message.author.mention}, aap pehle se waiting list me hain!")
                await asyncio.sleep(4)
                try:
                    await fail.delete()
                    await message.delete()
                except: pass
                return

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

            waiting_queue.append(message.author)
            count = len(waiting_queue)
            
            status = await message.channel.send(f"✅ {message.author.mention} entered the queue! **({count}/4 Players Ready)**")
            await asyncio.sleep(4)
            try:
                await status.delete()
                await message.delete()
            except: pass

            if len(waiting_queue) >= 4:
                random.shuffle(waiting_queue)
                new_squad = [waiting_queue.pop(0) for _ in range(4)]
                all_teams.append(new_squad)
                
                squad_channel = bot.get_channel(SQUAD_CHANNEL_ID)
                team_num = len(all_teams)
                
                if squad_channel:
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

        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        if not is_admin:
            if "name" in msg_text and "id" in msg_text and "instagram" in msg_text:
                ign = extract_ign(message.content)
                if not ign:
                    ign = message.author.name
                
                user_names[message.author.id] = ign
                verified_users.add(message.author.id)
                await message.add_reaction("✅")
                
                confirm_msg = await message.channel.send(
                    f"🎉 {message.author.mention}, aapka IGN **'{ign}'** verify ho gaya hai!\nAb ready ho toh niche **`join`** type karo!"
                )
                await asyncio.sleep(6)
                try: await confirm_msg.delete()
                except: pass
            else:
                try:
                    await message.delete()
                    warning_msg = await message.channel.send(
                        f"⚠️ {message.author.mention}, is channel me sirf details allowed hain!\n""```\nFormat:\n1. In Game Name (IGN):\n2. Game ID:\n3. Instagram ID Link:\n```" )
                    await asyncio.sleep(5)
                    await warning_msg.delete()
                except: pass
                return

    # 2. FULL SQUAD REGISTRATION CHANNEL LOGIC
    if message.channel.id == TEAM_DETAILS_CHANNEL_ID:
        if message.content.startswith("!") or is_admin:
            await bot.process_commands(message)
            return

        total_mentions = len(message.mentions)
        if "team name" in msg_text and total_mentions == 4:
            await message.add_reaction("✅")
            team_members = [user for user in message.mentions]
            all_teams.append(team_members)
            
            for member in team_members:
                user_names[member.id] = member.nick if member.nick else member.name
            
            confirm_team = await message.channel.send(
                f"🔥 **Team Registered!** {message.author.mention} aapki team **Slot #{len(all_teams)}** me save ho gayi hai."
            )
            await asyncio.sleep(7)
            try: await confirm_team.delete()
            except: pass
        else:
            try:
                await message.delete()
                error_team = await message.channel.send(
                    f"❌ {message.author.mention}, **Format Galat hai!** Apni poori team ko register karne ke liye ye format use karein:\n"
                    "```\nTeam Name: Team_Name\nP1: @tag | P2: @tag | P3: @tag | P4: @tag\n```"
                )
                await asyncio.sleep(7)
                await error_team.delete()
            except: pass
            return

    await bot.process_commands(message)

# ====================================================================
# 💬 COMMANDS SECTION (Live Slot List & Resets)
# ====================================================================
@bot.command()
async def slots(ctx):
    global all_teams, user_names
    if not all_teams or len(all_teams) == 0:
        await ctx.send("🚫 **Abhi tak koi bhi team nahi bani hai!**")
        return

    try:
        embed = discord.Embed(
            title="🏆 TOURNAMENT OFFICIAL SLOTS (MAX 12) 🏆",
            description="Registered squads ki list (Sirf In-Game Names):\n",
            color=discord.Color.orange()
        )
        for index, team in enumerate(all_teams):
            slot_num = index + 1
            players_display = []
            for p in team:
                if p is not None:
                    ign_name = user_names.get(p.id, p.name)
                    players_display.append(ign_name)
                    
            players_string = " | ".join(players_display)
            embed.add_field(name=f"Slot {slot_num} 🟢", value=f"👥 **{players_string}**", inline=False)

        embed.set_footer(text=f"Total Registered Teams: {len(all_teams)}/12")
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Slots print error: {e}")
        await ctx.send("❌ Slots load karne me koi error aaya hai.")

@bot.command()
async def teamlist(ctx):
    await slots(ctx)

@bot.command()
@commands.has_permissions(administrator=True)
async def clearqueue(ctx):
    global waiting_queue
    waiting_queue = []
    await ctx.send("🧹 **Waiting queue clear ho gayi hai!**")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetall(ctx):
    global waiting_queue, verified_users, all_teams, user_names
    waiting_queue = []
    verified_users.clear()
    user_names.clear()
    all_teams = []
    await ctx.send("🔄 **Database full reset successful!** Sabhi purana data clear ho gaya hai.")

# ====================================================================
# 🚀 BOT RUN SECTION (Yahan apna real Token paste karo ek hi line me)
# ====================================================================
keep_alive()

# 🔴 DHAYAN SE: Niche "PASTE_YOUR_DISCORD_BOT_TOKEN_HERE" ko mitao 
# aur uski jagah apna asli lambi chabi (Token) daal do.
# Yaad rakhna, quotes "" ke andar hi hona chahiye aur enter dabakar todna nahi hai!

bot.run("MTUxOTE2NjI5NDc2NTg2NzExOA.GtDfOI.fggk-zgtWhyw_FPNwAALmPHqr4VSHaFn5y5yhE")
