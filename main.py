import discord
from discord.ext import commands, tasks
import json
import datetime

TOKEN = 'MTI2NDU1NDIzNDA1NDE4NDk5MA.GGe5Ll.T_KBg6KbnWtPYfwm9m5XhnRf6Sp_-31i8bn-ag'
GUILD_ID = 1176897566512783431
NICKNAMES_FILE = 'nicknames.json'
POINTS_FILE = 'points.json'
PARTNER_MESSAGES_FILE = 'partner_messages.json'
ROLE_ID = 1199399881173901402
UNREG_ROLE_ID = 1264203752940765225
NO_UNREG_ROLE_ID = 1264348553313124402
HELP_CHANNEL_ID = 1263375097368940638
PARTNER_CHANNEL_ID = 1176897570166018066
ACTIVITY_CHANNEL_ID = 123456789012345678  # Etkinlik mesajlarının gönderileceği kanal ID'si

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# JSON dosyasını yükle
def load_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# JSON dosyasına yaz
def save_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

# Kullanıcıların puanlarını yönet
points_dict = load_json(POINTS_FILE)

# Takma isim değişikliklerini yönet
nicknames_dict = load_json(NICKNAMES_FILE)

# Partner mesajlarını yönet
partner_messages_dict = load_json(PARTNER_MESSAGES_FILE)

# Etkinlikler
active_events = {}

# Ban/Kick koruma sistemi için gerekli veriler
ban_kick_logs = {}

@bot.event
async def on_ready():
    print(f'Bot is ready.')
    check_active_events.start()

@tasks.loop(seconds=60)
async def check_active_events():
    now = datetime.datetime.utcnow()
    for event_id, end_time in list(active_events.items()):
        if now >= end_time:
            channel = bot.get_channel(ACTIVITY_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="Etkinlik Bitti",
                    description=f"Etkinlik {event_id} sona erdi.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
            del active_events[event_id]
    save_json('active_events.json', active_events)

@bot.event
async def on_member_update(before, after):
    if before.guild.id != GUILD_ID:
        return

    if before.nick != after.nick:
        member_id = str(after.id)
        if member_id not in nicknames_dict:
            nicknames_dict[member_id] = []

        if before.nick and before.nick != after.display_name:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nicknames_dict[member_id].append((before.nick, timestamp))
            save_json(NICKNAMES_FILE, nicknames_dict)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Mesaj başına puan verme
    if any(role.id == 1264348553313124402 for role in message.author.roles):
        user_id = str(message.author.id)
        if user_id not in points_dict:
            points_dict[user_id] = 0

        points_dict[user_id] += 1
        save_json(POINTS_FILE, points_dict)

    # Partner mesajları yönetimi
    if message.channel.id == PARTNER_CHANNEL_ID:
        user_id = str(message.author.id)
        if user_id not in partner_messages_dict:
            partner_messages_dict[user_id] = 0

        partner_messages_dict[user_id] += 1
        save_json(PARTNER_MESSAGES_FILE, partner_messages_dict)

        embed = discord.Embed(title="Partnerlik Onaylandı", description=f"Partnerliğiniz onaylandı {message.author.mention}, toplam partnerlik sayınız: {partner_messages_dict[user_id]}", color=discord.Color.green())
        await message.channel.send(embed=embed)

    # Etkinlik puanları
    if message.channel.id == ACTIVITY_CHANNEL_ID:
        if active_events.get(message.channel.id):
            if any(role.id == 1264348553313124402 for role in message.author.roles):
                user_id = str(message.author.id)
                if user_id not in points_dict:
                    points_dict[user_id] = 0

                points_dict[user_id] += 1
                save_json(POINTS_FILE, points_dict)

    await bot.process_commands(message)

@bot.event
async def on_member_ban(guild, user):
    if guild.id != GUILD_ID:
        return

    ban_kick_logs.setdefault(str(user.id), {'bans': 0, 'kicks': 0, 'last_action': datetime.datetime.now()})
    ban_kick_logs[str(user.id)]['bans'] += 1
    ban_kick_logs[str(user.id)]['last_action'] = datetime.datetime.now()

    await check_ban_kick_logs(user.id)

@bot.event
async def on_member_remove(member):
    if member.guild.id != GUILD_ID:
        return

    ban_kick_logs.setdefault(str(member.id), {'bans': 0, 'kicks': 0, 'last_action': datetime.datetime.now()})
    ban_kick_logs[str(member.id)]['kicks'] += 1
    ban_kick_logs[str(member.id)]['last_action'] = datetime.datetime.now()

    await check_ban_kick_logs(member.id)

async def check_ban_kick_logs(user_id):
    log = ban_kick_logs.get(str(user_id))
    if not log:
        return

    if log['bans'] >= 5 or log['kicks'] >= 5:
        if (datetime.datetime.now() - log['last_action']).total_seconds() <= 30:
            guild = bot.get_guild(GUILD_ID)
            user = guild.get_member(int(user_id))
            if user:
                try:
                    timeout_duration = datetime.timedelta(minutes=120)
                    await user.timeout(timeout_duration)
                    embed = discord.Embed(title="Kullanıcı Zaman Aşımı", description=f"{user.name} çok sayıda ban veya kick işlemi gerçekleştirdiği için 120 dakika süreyle zaman aşımına uğradı.", color=discord.Color.red())
                    await bot.get_channel(HELP_CHANNEL_ID).send(embed=embed)
                except discord.Forbidden:
                    print(f"Cannot timeout user {user.name} due to lack of permissions.")
                except discord.HTTPException as e:
                    print(f"HTTPException occurred while timing out user {user.name}: {e}")
            log['bans'] = 0
            log['kicks'] = 0

@bot.command()
async def isimler(ctx, member: discord.Member):
    if not any(role.id == 1263868273808900127 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    member_id = str(member.id)
    if member_id not in nicknames_dict or not nicknames_dict[member_id]:
        embed = discord.Embed(title="Takma İsim Bulunamadı", description="Bu üyenin eski takma isimleri bulunamadı.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    nicknames = nicknames_dict[member_id]
    embed = discord.Embed(title=f"{member.name}'ın Eski Takma İsimleri", color=discord.Color.blue())
    for nick, date in nicknames:
        embed.add_field(name=date, value=nick, inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def b(ctx, *, new_nick):
    if ROLE_ID not in [role.id for role in ctx.author.roles]:
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    member = ctx.author
    try:
        await member.edit(nick=new_nick)
        embed = discord.Embed(title="Takma Ad Değiştirildi", description=f"Takma adınız başarıyla {new_nick} olarak değiştirildi.", color=discord.Color.green())
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(title="Yetki Hatası", description="Takma adınızı değiştirme yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
async def p(ctx, user: discord.Member = None):
    if not any(role.id == 1264348553313124402 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if user is None:
        user = ctx.author  # Eğer kullanıcı belirtilmemişse, komutu yazan kullanıcıya puan göster

    user_id = str(user.id)
    if user_id not in points_dict:
        points_dict[user_id] = 0
        save_json(POINTS_FILE, points_dict)

    embed = discord.Embed(title="Puan Durumu", description=f"{user.mention} adlı kullanıcının puanı: {points_dict[user_id]}", color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command()
async def puanver(ctx, user: discord.Member, amount: int):
    if not any(role.id == 1264348553313124402 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Geçersiz Miktar", description="Puan miktarı pozitif bir değer olmalıdır.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    user_id = str(user.id)
    if user_id not in points_dict:
        points_dict[user_id] = 0

    points_dict[user_id] += amount
    save_json(POINTS_FILE, points_dict)

    embed = discord.Embed(title="Puan Güncelleme", description=f"{user.mention} adlı kullanıcıya {amount} puan eklendi. Toplam puanı: {points_dict[user_id]}", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def psıfırla(ctx):
    if not any(role.id in [1176897566919622718, 1176897566944792587, 1176897566781214787, 1176897566781214786] for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    points_dict.clear()
    save_json(POINTS_FILE, points_dict)
    embed = discord.Embed(title="Puanlar Sıfırlandı", description="Tüm puanlar sıfırlandı.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def stat(ctx):
    if not any(role.id == 1264348553313124402 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    sorted_users = sorted(points_dict.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="Puan Sıralaması", color=discord.Color.blue())
    for index, (user_id, points) in enumerate(sorted_users[:10], start=1):
        member = bot.get_user(int(user_id))
        if member:
            embed.add_field(name=f"{index}. {member.name}", value=f"Puan: {points}", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def xetkinlik(ctx):
    if ctx.channel.id != ACTIVITY_CHANNEL_ID:
        embed = discord.Embed(title="Yanlış Kanal", description="Bu komut yalnızca etkinlik kanalında kullanılabilir.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if not any(role.id == 1264348553313124402 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if ctx.message.content.startswith('.xetkinlik'):
        active_events[ctx.channel.id] = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        save_json('active_events.json', active_events)

        embed = discord.Embed(title="Etkinlik Başladı", description="Etkinlik başladı ve 30 dakika sürecek.", color=discord.Color.green())
        await ctx.send(embed=embed)

@bot.command()
async def taglı(ctx, user: discord.Member):
    if not any(role.id == 1263868273808900127 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="Tag Onaylandı", description=f"{user.mention} adlı kullanıcının tagı onaylandı.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def ptop(ctx):
    if ctx.channel.id != PARTNER_CHANNEL_ID:
        embed = discord.Embed(title="Yanlış Kanal", description="Bu komut yalnızca partner kanalında kullanılabilir.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    sorted_partners = sorted(partner_messages_dict.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="Partnerlik Sıralaması", color=discord.Color.blue())
    for index, (user_id, count) in enumerate(sorted_partners[:10], start=1):
        member = bot.get_user(int(user_id))
        if member:
            embed.add_field(name=f"{index}. {member.name}", value=f"Partnerlik Sayısı: {count}", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def ceza(ctx, user: discord.Member, amount: int):
    if not any(role.id == 1264348553313124402 for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Ceza puanı güncelle
    user_id = str(user.id)
    if user_id not in points_dict:
        points_dict[user_id] = 0

    points_dict[user_id] -= amount
    save_json(POINTS_FILE, points_dict)

    embed = discord.Embed(title="Ceza Güncelleme", description=f"{user.mention} adlı kullanıcıya {amount} ceza puanı eklendi. Toplam ceza puanı: {points_dict[user_id]}", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command()
async def unreg(ctx, user: discord.Member):
    if not any(role.id in [1176897566919622716, 1263868273808900127] for role in ctx.author.roles):
        embed = discord.Embed(title="Yetki Eksik", description="Bu komutu kullanma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if any(role.id == NO_UNREG_ROLE_ID for role in user.roles):
        embed = discord.Embed(title="İşlem Geçersiz", description="Bu kullanıcı için işlem yapılamaz.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Kullanıcının rollerini kaldır ve UNREG_ROLE_ID rolünü ekle
    roles = [role for role in user.roles if role.id != NO_UNREG_ROLE_ID]
    try:
        await user.edit(roles=[discord.Object(id=UNREG_ROLE_ID)] + roles)
        embed = discord.Embed(title="Rol Güncelleme", description=f"{user.mention} adlı kullanıcının rollerini güncelledim. UNREG_ROLE_ID rolü eklendi.", color=discord.Color.green())
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(title="Yetki Hatası", description="Bu kullanıcı üzerinde işlem yapma yetkiniz yok.", color=discord.Color.red())
        await ctx.send(embed=embed)

bot.run(TOKEN)
