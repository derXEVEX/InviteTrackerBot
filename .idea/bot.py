import discord
from discord import app_commands
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
invite_cache = {}


def load_joins_data():
    if not os.path.exists("joins.json"):
        with open("joins.json", "w") as f:
            json.dump({}, f)

    try:
        with open("joins.json", "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except json.JSONDecodeError:
        return {}

def save_joins_data(data):
    with open("joins.json", "w") as f:
        json.dump(data, f, indent=4)



@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user}")
    for guild in bot.guilds:
        invite_cache[guild.id] = await guild.invites()
    try:
        synced = await bot.tree.sync()
        print(f"Slash-Befehle synchronisiert: {len(synced)}")
    except Exception as e:
        print(f"Fehler beim Syncen: {e}")


@bot.event
async def on_member_join(member):
    new_invites = await member.guild.invites()
    old_invites = invite_cache.get(member.guild.id, [])
    used_invite = None

    for new in new_invites:
        for old in old_invites:
            if new.code == old.code and new.uses > old.uses:
                used_invite = new
                break

    invite_cache[member.guild.id] = new_invites

    if used_invite:
        data = load_joins_data()
        inviter_id = str(used_invite.inviter.id)
        member_id = str(member.id)

        if inviter_id not in data:
            data[inviter_id] = {"invites": 0, "invited_users": []}

        data[inviter_id]["invites"] += 1
        data[inviter_id]["invited_users"].append(member_id)
        save_joins_data(data)
        print(f"{member} wurde von {used_invite.inviter} eingeladen")



@bot.event
async def on_member_remove(member):
    data = load_joins_data()
    leaver_id = str(member.id)

    for inviter_id, info in data.items():
        if leaver_id in info.get("invited_users", []):
            info["invites"] -= 1
            info["invited_users"].remove(leaver_id)
            save_joins_data(data)
            print(f"{member} hat den Server verlassen, -1 Invite für {inviter_id}")
            break


@bot.tree.command(name="invites", description="Zeigt, wie viele Invites ein Benutzer hat.")
@app_commands.describe(user="Der Benutzer, dessen Invites du sehen willst (optional)")
async def invites(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    user_id = str(target.id)
    data = load_joins_data()
    invites = data.get(user_id, {}).get("invites", 0)
    await interaction.response.send_message(f"👤 {target.mention} hat **{invites}** Invite(s) ✉ | 👤 {target.mention} has **{invites}** Invite(s) ✉", ephemeral=False)

@bot.tree.command(name="invites-leaderboard", description="Zeigt die Top 10 mit den meisten Invites")
async def invites_leaderboard(interaction: discord.Interaction):
    data = load_joins_data()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("invites", 0), reverse=True)
    top10 = sorted_users[:10]

    if not top10:
        await interaction.response.send_message("Noch keine Invites vorhanden | No invites yet")
        return

    description = ""
    for index, (user_id, info) in enumerate(top10, start=1):
        user = await interaction.client.fetch_user(int(user_id))
        description += f"**{index}. {user.display_name}** – {info.get('invites', 0)} Invite(s)\n"

    embed = discord.Embed(
        title="🏆 Top 10 Invite Leaderboard",
        description=description,
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="invites-set", description="Setzt die Anzahl der Invites für einen User")
@app_commands.describe(user="Der User, dessen Invites geändert werden sollen", amount="Anzahl der Invites (z. B. -1, 1, 5...)")
async def invites_set(interaction: discord.Interaction, user: discord.User, amount: int):
    # Nur Admins (mit Administrator-Recht)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ Nur Administratoren dürfen diesen Befehl nutzen.", ephemeral=True)
        return

    data = load_joins_data()
    user_id = str(user.id)

    if user_id not in data:
        data[user_id] = {"invites": 0, "invited_users": []}

    data[user_id]["invites"] += amount
    save_joins_data(data)

    await interaction.response.send_message(
        f"✅ {user.display_name} hat jetzt **{data[user_id]['invites']}** Invite(s). (Änderung: {amount:+})"
    )

@bot.tree.command(name="who-invited", description="Zeigt, wer einen User eingeladen hat")
@app_commands.describe(user="Der User, dessen Einlader du sehen willst")
async def who_invited(interaction: discord.Interaction, user: discord.User):
    data = load_joins_data()
    user_id = str(user.id)
    inviter_id = None


    for inviter, info in data.items():
        if user_id in info.get("invited_users", []):
            inviter_id = inviter
            break

    if inviter_id:
        inviter_user = await bot.fetch_user(int(inviter_id))
        await interaction.response.send_message(
            f"👤 {user.mention} wurde eingeladen von **{inviter_user.mention} | 👤 {user.mention} invited by **{inviter_user.mention}**", ephemeral=False
        )
    else:
        await interaction.response.send_message(
            f"❓ Es wurde kein Einlader für {user.mention} gefunden. | No invitation for {user.mention} was found", ephemeral=False
        )




bot.run("TOKEN")
