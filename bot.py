import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # Optional: faster slash-command sync in one server

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
    except Exception as exc:
        print(f"Command sync failed: {exc}")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong! {round(bot.latency * 1000)} ms", ephemeral=True
    )

@bot.tree.command(name="clear", description="Delete recent messages")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Number of messages (1–100)")
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(member="Member to kick", reason="Reason (optional)")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
        return await interaction.response.send_message("You cannot moderate a member with an equal or higher role.", ephemeral=True)
    await member.kick(reason=f"{interaction.user}: {reason}")
    await interaction.response.send_message(f"Kicked {member.mention}. Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(member="Member to ban", reason="Reason (optional)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.guild.owner or (member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id):
        return await interaction.response.send_message("You cannot ban that member due to role hierarchy.", ephemeral=True)
    await member.ban(reason=f"{interaction.user}: {reason}")
    await interaction.response.send_message(f"Banned {member.mention}. Reason: {reason}")

@bot.tree.command(name="timeout", description="Temporarily timeout a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="Member", minutes="Duration in minutes (1–10080)", reason="Reason (optional)")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 10080], reason: str = "No reason provided"):
    if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
        return await interaction.response.send_message("You cannot timeout a member with an equal or higher role.", ephemeral=True)
    from datetime import timedelta
    await member.timeout(timedelta(minutes=minutes), reason=f"{interaction.user}: {reason}")
    await interaction.response.send_message(f"Timed out {member.mention} for {minutes} minutes.")

@bot.tree.command(name="lock", description="Lock this text channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Channel locked.")

@bot.tree.command(name="unlock", description="Unlock this text channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Channel unlocked.")

@bot.tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(seconds="0 to disable; maximum 21600")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds} seconds.")

@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=discord.Color.blurple())
    embed.add_field(name="Members", value=str(g.member_count))
    embed.add_field(name="Channels", value=str(len(g.channels)))
    embed.add_field(name="Created", value=discord.utils.format_dt(g.created_at, style="D"), inline=False)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="userinfo", description="Show information about a member")
@app_commands.describe(member="Member to inspect (defaults to you)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"User: {member}", color=discord.Color.blurple())
    embed.add_field(name="ID", value=str(member.id), inline=False)
    embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, style="D") if member.joined_at else "Unknown")
    embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, style="D"))
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_member_join(member: discord.Member):
    # Set WELCOME_CHANNEL_ID in your hosting secrets to enable welcome messages.
    channel_id = os.getenv("WELCOME_CHANNEL_ID")
    if channel_id:
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            await channel.send(f"Welcome {member.mention} to **{member.guild.name}**!")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You don't have permission to use that command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        message = "I need additional server permissions to do that."
    else:
        print(f"Slash command error: {error}")
        message = "Something went wrong while running that command."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")
bot.run(TOKEN)
