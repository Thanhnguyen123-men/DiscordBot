import discord
from discord.ext import commands, tasks
import random
import requests
import os
import time
from datetime import datetime

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_PREFIX = "!"
OWNER_ID = 1379310041903140895

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents, help_command=None)

# =========================
# GLOBAL STATE
# =========================
has_started = False
user_messages = {}
statuses = [
    discord.Game("tao đang đi làm lọ 🐧"),
    discord.Game("đang cào phím 💻")
]

# =========================
# STATUS ROTATION
# =========================
@tasks.loop(hours=24)
async def rotate_status():
    await bot.wait_until_ready()
    current = bot.activity
    next_status = statuses[0] if current != statuses[0] else statuses[1]
    await bot.change_presence(activity=next_status)

# =========================
# ON READY
# =========================
@bot.event
async def on_ready():
    global has_started
    if has_started:
        return
    has_started = True

    # Start status rotation
    rotate_status.start()

    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] Synced {len(synced)} commands")
    except Exception as e:
        print("Slash sync error:", e)

    print(f"[ONLINE] {bot.user}")

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    state_file = os.path.join(os.getcwd(), "last_start.txt")
    first_boot = not os.path.exists(state_file)
    with open(state_file, "w", encoding="utf-8") as f:
        f.write(now)

    try:
        owner = await bot.fetch_user(OWNER_ID)
        msg = (
            "🟢 **BOT ONLINE – FIRST BOOT**\n" if first_boot else "🔁 **BOT RESTARTED**\n"
        ) + f"🤖 `{bot.user}`\n🕒 `{now}`"
        await owner.send(msg)
    except Exception as e:
        print("DM owner failed:", e)

# =========================
# MOD LOG
# =========================
async def get_log_channel(guild: discord.Guild):
    channel = discord.utils.get(guild.text_channels, name="mod-log")
    if channel is None:
        channel = await guild.create_text_channel("mod-log")
    return channel

async def send_log(guild, title, description):
    ch = await get_log_channel(guild)
    embed = discord.Embed(title=title, description=description, color=0xff5555)
    await ch.send(embed=embed)

# =========================
# ANTI-SPAM
# =========================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]

    if len(user_messages[uid]) >= 5:
        try:
            await message.delete()
            await message.author.timeout(
                discord.utils.utcnow() + discord.timedelta(seconds=10),
                reason="Spam"
            )
            await message.channel.send(
                f"⚠️ {message.author.mention} spam ít thôi!",
                delete_after=5
            )
        except:
            pass
        user_messages[uid].clear()

    await bot.process_commands(message)

# =========================
# BASIC COMMANDS
# =========================
@bot.hybrid_command(description="Kiểm tra độ trễ")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.hybrid_command(description="Tung đồng xu")
async def flip(ctx):
    await ctx.send(random.choice(["🪙 Sấp", "🪙 Ngửa"]))

@bot.hybrid_command(description="Tung xúc xắc")
async def roll(ctx):
    await ctx.send(f"🎲 {random.randint(1, 6)}")

@bot.hybrid_command(description="Đoán số từ 1–10")
async def guess(ctx, number: int):
    x = random.randint(1, 10)
    await ctx.send("🎉 Đúng rồi!" if number == x else f"❌ Sai! Đáp án là **{x}**")

# =========================
# SAY COMMAND
# =========================
@bot.hybrid_command(description="Bot nói hộ bạn")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    if ctx.message:
        try:
            await ctx.message.delete()
        except:
            pass
    await ctx.send(message)

# =========================
# FUN / MEME
# =========================
@bot.hybrid_command(description="Meme ngẫu nhiên")
async def meme(ctx):
    try:
        res = requests.get("https://meme-api.com/gimme", timeout=5).json()
        embed = discord.Embed(title=res["title"], color=0x00ff99)
        embed.set_image(url=res["url"])
        embed.set_footer(text=f"👍 {res['ups']} | r/{res['subreddit']}")
        await ctx.send(embed=embed)
    except:
        await ctx.send("💀 Meme chết tạm thời, thử lại sau!")

EIGHT_BALL = [
    "Chắc chắn luôn 💯", "Có, nhưng đừng tin quá 😏", "Không nha, mơ tiếp đi",
    "Sus vcl 🤨", "Có khả năng, nhưng thấp hơn FPS máy mày", "Tao thấy mùi điêu",
    "Hỏi câu khác đi 💀", "Thần linh bảo: KHÔNG", "Câu hỏi này vi phạm điều khoản vũ trụ"
]

@bot.hybrid_command(name="8ball", description="Quả cầu tiên tri siêu mặn")
async def eight_ball(ctx, *, question: str):
    answer = random.choice(EIGHT_BALL)
    embed = discord.Embed(
        title="🎱 Quả cầu tiên tri",
        description=f"**Câu hỏi:** {question}\n**Trả lời:** {answer}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

SUS_LINES = [
    "{user} nhìn hơi sus đó 🤨", "{user} là impostor 100%",
    "Không ai nghi ngờ… trừ {user}", "{user} vent trước mặt tao luôn",
    "Tao vote {user}"
]

@bot.hybrid_command(description="Ai đó rất đáng nghi 🤨")
async def sus(ctx, member: discord.Member = None):
    target = member.mention if member else ctx.author.mention
    await ctx.send(random.choice(SUS_LINES).format(user=target))

# =========================
# MOD COMMANDS
# =========================
@bot.hybrid_command(description="Xóa tin nhắn")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await send_log(ctx.guild, "🧹 Clear", f"{ctx.author} xóa {amount} tin nhắn")

@bot.hybrid_command(description="Kick thành viên")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await send_log(ctx.guild, "👢 Kick", f"{member} bị kick bởi {ctx.author}")

@bot.hybrid_command(description="Ban thành viên")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await send_log(ctx.guild, "🔨 Ban", f"{member} bị ban bởi {ctx.author}")

# =========================
# HELP VIEW
# =========================
class HelpView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=60)
        self.bot = bot_instance

    async def get_status_text(self):
        return "🟢 RUNNING" if self.bot.is_ready() else "🔴 STOPPED"

    @discord.ui.button(label="📜 Cơ bản", style=discord.ButtonStyle.primary)
    async def basic(self, interaction: discord.Interaction, button):
        status = await self.get_status_text()
        embed = discord.Embed(title=f"📜 Lệnh cơ bản — {status}", color=0x00ffcc)
        embed.add_field(name="!ping", value="Kiểm tra độ trễ", inline=False)
        embed.add_field(name="!flip", value="Tung xu", inline=False)
        embed.add_field(name="!roll", value="Tung xúc xắc", inline=False)
        embed.add_field(name="!guess", value="Đoán số", inline=False)
        embed.add_field(name="!meme", value="Meme ngẫu nhiên", inline=False)
        embed.add_field(name="!8ball", value="Quả cầu tiên tri", inline=False)
        embed.add_field(name="!sus", value="Ai đó rất sus", inline=False)
        embed.add_field(name="!say /say", value="Bot nói hộ bạn (xóa tin gốc với !say)", inline=False)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="🛠️ Quản trị", style=discord.ButtonStyle.danger)
    async def mod(self, interaction: discord.Interaction, button):
        status = await self.get_status_text()
        embed = discord.Embed(title=f"🛠️ Quản trị — {status}", color=0xff5555)
        embed.add_field(name="!clear", value="Xóa tin nhắn", inline=False)
        embed.add_field(name="!kick", value="Kick member", inline=False)
        embed.add_field(name="!ban", value="Ban member", inline=False)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="ℹ️ About", style=discord.ButtonStyle.secondary)
    async def about(self, interaction: discord.Interaction, button):
        status = await self.get_status_text()
        embed = discord.Embed(
            title=f"ℹ️ Moderation_skibidi — {status}",
            description=(
                "**Founder:** <@1379310041903140895>\n\n"
                "[➕ Invite Bot]"
                "(https://discord.com/oauth2/authorize?"
                "client_id=1433390064611889272&"
                "permissions=4292493394837495&scope=bot)\n\n"
                "Bot moderation + meme + trend 🔥"
            ),
            color=0xaaaaaa
        )
        await interaction.response.edit_message(embed=embed)

# =========================
# HELP COMMAND
# =========================
@bot.hybrid_command(description="Hiện menu trợ giúp")
async def help(ctx):
    embed = discord.Embed(
        title="🛠️ Moderation_skibidi — Help",
        description="Prefix: `!` | Có hỗ trợ Slash `/`",
        color=0x5865f2
    )
    await ctx.send(embed=embed, view=HelpView(bot))

# =========================
bot.run(TOKEN)
