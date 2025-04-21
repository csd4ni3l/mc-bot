import discord
import asyncio
import random
import datetime
import json, ast
import traceback
from mcstatus import JavaServer
import time
from discord.ext import tasks
import discord.utils

intents = discord.Intents().all()
bot = discord.Bot(intents=intents)

global warns

with open('warns.json', 'r') as file:
    warns = json.loads(file.read())

with open('giveaways.json','r') as file:
    giveaways_json_list: list = json.loads(file.read())

with open('settings.json','r') as file:
    global settings
    settings: dict = json.loads(file.read())

ticket_categories = settings['ticket_categories']
log_channel_id = settings['log_channel_id']
join_channel_id = settings['join_channel_id']
join_autorole_id = settings['join_autorole_id']
ticket_support_role_ids = settings['ticket_support_role_ids']
emergency_admin_ids = settings['emergency_admin_user_ids']
partner_manager_role_id = settings['partner_manager_role_id']
reaction_roles = settings['reaction_roles']
transcript_channel_id = settings['transcript_channel_id']
ticket_category_id = settings['ticket_category_id']
suggestion_channel_id = settings['suggestion_channel_id']
players_status_channel_id = settings['players_status_channel_id']
ping_status_channel_id = settings['ping_status_channel_id']
server_ip =  settings["minecraft_server_domain_ip"]
private_server_ip = settings["private_minecraft_server_ip"]
private_server_port = settings["private_minecraft_server_port"]
server_name = settings["server_name"]

commands = {
    'Mod': [
        ['/clear {amount}', 'Deletes messages in the current channel'],
        ['/warn {user mention}', 'Gives a warning to the specified user, if they reach a certain number of warnings, it also gives a punishment.'],
        ['/mute {username}', 'Mutes a user'],
        ['/kick {user mention}', 'Kicks a user'],
        ['/ban {user mention}', 'Bans a user'],
        ['/unban {username}', 'Unbans a user'],
        ['/clear_member_msg {user mention} {number of messages}', 'Deletes only messages from a selected user in the current channel']],
    'Fun': [
        ['/say {text}', 'The bot sends what you write.'],
        ['/suggest {idea}','Help us with an idea!'],
        ['/screenshot {link}','Take a screenshot of a page!']],
    'Info': [
        ['/help', 'This command'],
        ['/userinfo {user mention} or /ui {user mention}','Information about a user'],
        ['/serverinfo or /si {user mention}','Information about our Discord server'],
        ['/ip', 'Shows the IP address of our Minecraft server'],
        ['/mcstats','Find out our server\'s current ping and player count']],
    'Admin': [
        ['/giveaway {time} {number of winners} {prize}','Creates a giveaway in the current channel.'],
        ['/greroll {message id}','Rerolls the giveaway based on the given message ID.'],
        ['/send_reaction_role_message {channel mention}','Sends the reaction role panel in the mentioned channel'],
        ['/send_ticket_message {channel mention}','Sends the ticket panel in the mentioned channel'],
        ['/autoclose {time}','Closes the ticket after a given time if no messages are found'],
        ['/lock','Locks the current channel.'],
        ['/unlock','Unlocks the current channel.']]
}
categories = {
    'Info': 'Information Commands e.g. /userinfo',
    'Admin': 'Commands for admins',
    'Mod': 'Commands for moderators.',
    "Fun": 'Fun commands e.g. /say'}

time_convert = {"s": 1, "m": 60, "h": 3600,
                "d": 86400, "w": 604800, "mo": 31536000}

giveaways = []
global players_before
players_before = 0

def get_minecraft_status():
    server = JavaServer.lookup(f"{private_server_ip}:{private_server_port}")
    return server.status()

def convert_duration(duration):
    if 's' in duration:
        return duration.replace('s', ' seconds')
    if 'm' in duration:
        return duration.replace('m', ' minutes')
    if 'h' in duration:
        return duration.replace('h', ' hours')
    if 'd' in duration:
        return duration.replace('d', ' days')
    if 'w' in duration:
        return duration.replace('w', ' weeks')
    if 'mo' in duration:
        return duration.replace('mo', ' months')

def convert_duration_to_seconds(duration):
    return int(duration.split(duration[-1])[0]) * time_convert[duration[-1]]

def convert_seconds_to_date(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    result = ""
    if days > 0:
        result += "{} days ".format(int(days))
    if hours > 0:
        result += "{} hours ".format(int(hours))
    if minutes > 0:
        result += "{} minutes ".format(int(minutes))
    if seconds > 0 or not any([days, hours, minutes]):
        result += "{} seconds".format(int(seconds))

    return result.strip()

@tasks.loop(minutes=1)
async def update_mc_status():
    minecraft_status = get_minecraft_status()
    player_num, ping = minecraft_status.players.online, minecraft_status.latency
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | {player_num} Online | /help"))
    global players_before
    if players_before == 0 or player_num != players_before:
        await discord.utils.get(bot.guilds[0].channels, id=players_status_channel_id).edit(name=f"Players: {player_num}")
        players_before = player_num
    await discord.utils.get(bot.guilds[0].channels, id=ping_status_channel_id).edit(name=f"Ping: {round(ping,2)} ms")

@tasks.loop(seconds=15)
async def update_giveaways():
    for n in range(len(giveaways)):
        giveaway = giveaways[n]
        if not giveaway['ended']:
            if giveaway['end_time'] <= time.time():
                await end_giveaway(n, giveaway)
                continue
            message = giveaway['message']
            time_left_in_seconds = giveaway['end_time'] - time.time()
            time_left_in_str = convert_seconds_to_date(time_left_in_seconds)
            embed = discord.Embed(
                title="🎉 Giveaway 🎉", description=f"React with 🎉 emoji to participate!\nTime remaining: **{time_left_in_str}**\nPrize: **{giveaway['prize']}**\nNumber of winners: **{giveaway['winner_num']}**", color=0xFFFF00)
            if not bot.user.avatar == None:
                embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
            else:
                embed.set_footer(text=f"{server_name} Bot")
            await message.edit(embed=embed)
            await asyncio.sleep(1)
@bot.event
async def on_member_join(member: discord.Member):
    if not join_channel_id == -1:
        embed = discord.Embed(title=f'Welcome, {member.name}', color=discord.Colour.red(), description=f"👋 Welcome to the {server_name} discord server, **{member.display_name}**!\nWe hope you'll enjoy your time on our server!")
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        embed.set_thumbnail(url=bot.user.avatar.url)
        await bot.get_channel(join_channel_id).send(embed=embed)
    if not join_autorole_id == -1:
        await member.add_roles(discord.utils.get(member.guild.roles, id=join_autorole_id))

@bot.event
async def on_ready():
    for giveaway_dict in giveaways_json_list:
        try:
            channel = await bot.guilds[0].fetch_channel(giveaway_dict['channel_id'])
            message = await channel.fetch_message(giveaway_dict['message_id'])
            giveaways.append({"message_id": giveaway_dict['message_id'], "message": message, "winner_num": giveaway_dict['winner_num'],
                                "duration": convert_duration(giveaway_dict['_duration']), "_duration": giveaway_dict['_duration'], "prize": giveaway_dict['prize'], "ended": giveaway_dict['ended'], "end_time": giveaway_dict['start_time']+convert_duration_to_seconds(giveaway_dict['_duration'])})
        except:
            continue

    if not server_ip == 'example.com':
        if not server_ip == 'COMING SOON!':
            update_mc_status.start()
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | /help"))
            if not ping_status_channel_id == -1:
                await discord.utils.get(bot.guilds[0].channels, id=ping_status_channel_id).edit(name=f"Ping: COMING SOON!")
            if not players_status_channel_id == -1:
                await discord.utils.get(bot.guilds[0].channels, id=players_status_channel_id).edit(name=f"Players: COMING SOON!")
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | /help"))
    print(f'{server_name} bot online')
    update_giveaways.start()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        await discord.Bot.on_interaction(bot, interaction)
        return
    custom_id = interaction.data['custom_id']
    if custom_id == 'ticket':
        await ticket(interaction, interaction.data['values'][0])
    elif custom_id.startswith('ticket_') and custom_id.endswith('_close_button'):
        await close_ticket(interaction)

@bot.event
async def on_message(message):
    if not server_ip == 'example.com':
        if not message.author.bot:
            if any(i in message.content.lower() for i in [' ip', ' ipje', ' ip ']) and message.content.endswith('?'):
                await message.reply(f'The server IP is: **{server_ip}**')

@bot.event
async def on_member_update(before, after):
    try:
        if log_channel_id == -1:
            return
        channel = bot.get_channel(log_channel_id)
        embed = discord.Embed(title=f'{after.name}', color=discord.Colour.red())
        roles_changed = False
        nick_changed = False
        name_changed = False

        new_roles = [role.name for role in after.roles if role not in before.roles]
        if len(new_roles) != 0:
            roles_changed = True
            embed.add_field(name='Roles received by user:',value=','.join(new_roles))

        removed_roles = [role.name for role in before.roles if role not in after.roles]
        if len(removed_roles) != 0:
            roles_changed = True
            embed.add_field(name='Roles removed from user:',value=','.join(removed_roles))

        if roles_changed:
            embed.title += ' roles'

        if before.nick != after.nick:
            nick_changed = True
            embed.title += (' and nickname' if roles_changed else ' nickname')
            embed.add_field(name='User\'s old nickname', value=str(before.nick).replace('None','No nickname'))
            embed.add_field(name='User\'s new nickname', value=str(after.nick).replace('None','No nickname'))

        if before.display_name != after.display_name:
            name_changed = True
            embed.title += (' and name' if roles_changed or nick_changed else ' name')
            embed.add_field(name='User\'s old name', value=str(before.nick))
            embed.add_field(name='User\'s new name', value=str(after.nick))

        if roles_changed and not name_changed and not nick_changed:
            embed.title += ' have changed!' # A user's roles have changed!
        else:
            embed.title += ' has changed!'
        if not embed.title == f'{after.name} has changed!':
            if not after.avatar == None:
                embed.set_thumbnail(url=after.avatar.url)
            await channel.send(embed=embed)
    except:
        traceback.print_exc()

@bot.event
async def on_message_delete(message):
    try:
        if log_channel_id == -1:
            return
        log_channel: discord.channel.TextChannel = bot.get_channel(log_channel_id)
        if not log_channel == '':
            embed = discord.Embed(title=f'{message.author.name}\'s message was deleted in ' +
                                message.channel.name+f' channel!', color=discord.Colour.red())
            if not message.author.avatar == None:
                embed.set_thumbnail(url=message.author.avatar.url)
            embed.add_field(name='Content: ', value=message.content)
            await log_channel.send(embed=embed)
    except:
        traceback.print_exc()

@bot.event
async def on_guild_channel_create(channel):
    try:
        if log_channel_id == -1:
            return
        log_channel: discord.channel.TextChannel = bot.get_channel(log_channel_id)
        if not log_channel == '':
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                creator = entry.user
            embed = discord.Embed(title=creator.name+' created the ' +
                                channel.name+' channel!', color=discord.Colour.red())
            if not creator.avatar == None:
                embed.set_thumbnail(url=creator.avatar.url)
            await log_channel.send(embed=embed)
    except:
        traceback.print_exc()

@bot.event
async def on_guild_channel_delete(channel):
    try:
        if log_channel_id == -1:
            return
        log_channel: discord.channel.TextChannel = bot.get_channel(log_channel_id)
        if not log_channel == '':
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                deleter = entry.user
            embed = discord.Embed(title=deleter.name+' deleted the ' +
                                channel.name+' channel!', color=discord.Colour.red())
            if not deleter.avatar == None:
                embed.set_thumbnail(url=deleter.avatar.url)
            await log_channel.send(embed=embed)
    except:
        traceback.print_exc()

@bot.event
async def on_message_edit(before, after):
    try:
        if not after.author.bot:
            if log_channel_id == -1:
                return
            log_channel: discord.channel.TextChannel = bot.get_channel(log_channel_id)
            if not log_channel == '':
                embed = discord.Embed(title=after.author.name+' modified their own message in: ' +
                                    after.channel.name+'!', color=discord.Colour.red())
                if not after.avatar == None:
                    embed.set_thumbnail(url=after.author.avatar.url)
                embed.add_field(name='Original content:',
                                value=before.content)
                embed.add_field(name='Modified content:', value=after.content)
                await log_channel.send(embed=embed)
    except:
        traceback.print_exc()

@bot.event
async def on_bulk_message_delete(messages):
    try:
        if log_channel_id == -1:
            return
        log_channel: discord.channel.TextChannel = bot.get_channel(log_channel_id)
        if not log_channel == '':
            async for entry in messages[0].guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                deleter = entry.user
            embed = discord.Embed(title=deleter.name+' deleted '+str(len(messages))+' messages in ' +
                                messages[0].channel.name+' channel!', color=discord.Colour.red())
            if not deleter.avatar == None:
                embed.set_thumbnail(url=deleter.avatar.url)
            await log_channel.send(embed=embed)
    except:
        traceback.print_exc()


async def on_reaction_add(emoji, message, user: discord.Member):
    global settings
    if not user.bot and message.id == settings['reaction_role_message_id'] and emoji.name in reaction_roles:
        await user.add_roles(discord.utils.get(message.guild.roles, id=reaction_roles[emoji.name]['role_id']))

async def on_reaction_remove(emoji, message, user: discord.Member):
    global settings
    if not user.bot and message.id == settings['reaction_role_message_id'] and emoji.name in reaction_roles:
        await user.remove_roles(discord.utils.get(message.guild.roles, id=reaction_roles[emoji.name]['role_id']))

@bot.event
async def on_raw_reaction_add(payload): # trigger on_reaction_add for all messages not just cached ones.
    channel = await bot.fetch_channel(payload.channel_id)
    await on_reaction_add(payload.emoji, await channel.fetch_message(payload.message_id), discord.utils.get(channel.guild.members,id=payload.user_id))

@bot.event
async def on_raw_reaction_remove(payload):
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = discord.utils.get(channel.guild.members,id=payload.user_id)
    await on_reaction_remove(payload.emoji, message, user)

async def end_giveaway(n, giveaway):
    message = await bot.get_channel(giveaway['message'].channel.id).fetch_message(giveaway["message_id"])
    participant_mentions = [
        participant.mention for participant in [user async for user in message.reactions[0].users()]]
    if bot.user.mention in participant_mentions:
        participant_mentions.remove(bot.user.mention)
    if len(participant_mentions) > giveaway['winner_num']:
        winner_list = random.sample(
            participant_mentions, giveaway['winner_num'])
    else:
        winner_list = participant_mentions
    if len(winner_list) == 0:
        embed = discord.Embed(title="🎉 Giveaway Ended 🎉",
                            description=f"Time remaining: **The giveaway has ended**\nPrize: **{giveaway['prize']}**\nNumber of winners: **{giveaway['winner_num']}**\nI'm sorry but no one won.", color=0xFF0000)
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        await message.edit(embed=embed)
    else:
        embed = discord.Embed(title="🎉 Giveaway Ended 🎉",
                            description=f"Time remaining: **The giveaway has ended**\nPrize: **{giveaway['prize']}**\nNumber of winners: **{giveaway['winner_num']}**\nWinner(s): {', '.join(winner_list)}", color=0xFF0000)
        await message.edit(content=', '.join(winner_list), embed=embed)

    giveaways[n]['ended'] = True
    giveaways_json_list[n]['ended'] = True
    with open('giveaways.json','w') as file:
        file.write(json.dumps(giveaways_json_list, indent=4))

@bot.slash_command()
async def greroll(interaction: discord.Interaction, message_id):
    if interaction.user.guild_permissions.administrator:
        for n,giveaway in enumerate(giveaways):
            if int(message_id) == giveaway["message_id"]:
                try:
                    await end_giveaway(n, giveaway)
                    await interaction.response.send_message('Giveaway successfully rerolled!')
                    return
                except:
                    traceback.print_exc()
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def giveaway(interaction: discord.Interaction, duration: str, winners: int, prize: str):
    if interaction.user.guild_permissions.administrator:
        try:
            embed = discord.Embed(
                title="🎉 Giveaway 🎉", description=f"React with 🎉 emoji to participate!\nTime remaining: **{convert_duration(duration)}**\nPrize: **{prize}**\nNumber of winners: **{winners}**", color=0xFFFF00)
            if not bot.user.avatar == None:
                embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
            else:
                embed.set_footer(text=f"{server_name} Bot")
            message = await interaction.channel.send(embed=embed)
            await message.add_reaction("🎉")
            giveaways.append({"message_id": message.id, "message": message, "winner_num": winners,
                            "duration": convert_duration_to_seconds(duration), "_duration": duration, "prize": prize, 'end_time': time.time()+convert_duration_to_seconds(duration), "ended": False})
            giveaways_json_list.append({"message_id": message.id, "channel_id": interaction.channel.id, "winner_num": winners, "_duration": duration, "prize": prize, "start_time": time.time(), "ended": False})
            with open("giveaways.json",'w') as file:
                file.write(json.dumps(giveaways_json_list, indent=4))
        except:
            traceback.print_exc()
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def send_reaction_role_message(interaction: discord.Interaction, channel: discord.channel.TextChannel):
    global settings
    embed_description = "React to the appropriate emojis for roles!"
    for reaction_role_emoji, reaction_role_dict in reaction_roles.items():
        embed_description += f"\n{reaction_role_emoji}: {reaction_role_dict['description']}"

    embed = discord.Embed(title="Reaction Roles", description=embed_description, color=discord.Colour.red())
    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    message: discord.Message = await channel.send(embed=embed)
    await interaction.response.send_message("Message sent to the specified channel!\nMessage ID: " + str(message.id), ephemeral=True)

    for reaction_role_emoji, _ in reaction_roles.items():
        await message.add_reaction(reaction_role_emoji)

    settings['reaction_role_message_id'] = message.id

    with open('settings.json', 'w') as file:
        file.write(json.dumps(settings, indent=4))

@bot.slash_command()
async def suggest(interaction: discord.Interaction, suggestion):
    if not suggestion_channel_id == -1:
        embed = discord.Embed(title=str(interaction.user.name)+'\'s new suggestion', description=suggestion, color=discord.Colour.red())
        embed.set_thumbnail(url=interaction.user.avatar.url)
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        message = await bot.get_channel(suggestion_channel_id).send(embed=embed)

        await message.add_reaction('✅')
        await message.add_reaction('❌')
        await interaction.response.send_message('Suggestion successfully published!')
    else:
        await interaction.response.send_message('This command is not configured!', ephemeral=True)

async def close_ticket(interaction):
    channel = interaction.message.channel
    closer = interaction.user

    await interaction.response.pong()

    message = await interaction.channel.send(f'Deletion in 5 seconds!')
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        await message.edit(content=f'Deletion in {i} seconds!')
    await asyncio.sleep(0.5)
    await channel.delete()
    if not transcript_channel_id == -1:
        transcript_channel = discord.utils.get(interaction.guild.channels, id=transcript_channel_id)
        transcript_embed = discord.Embed(title=f"Ticket #{channel.name.split('-')[1]} closed")

        transcript_embed.add_field(name="Closed by", value=closer.mention)

        await transcript_channel.send(embed=transcript_embed)

@bot.slash_command()
async def lock(interaction):
    if interaction.user.guild_permissions.manage_channels:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f'Channel locked by {interaction.user.mention}!')
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def unlock(interaction):
    if interaction.user.guild_permissions.manage_channels:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(f'Channel unlocked by {interaction.user.mention}!')
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

async def ticket(interaction: discord.Interaction, ticket_topic):
    guild = interaction.guild
    if not ticket_category_id == -1:
        ticket_category = discord.utils.get(
            interaction.guild.categories, id=ticket_category_id)
    else:
        await interaction.response.send_message('Ticket creation failed. Ticket category not configured.')
        return
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
    }
    for role_id in ticket_support_role_ids:
        role = discord.utils.get(guild.roles, id=role_id)
        if not role == None:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True)
        else:
            print(f'Invalid role ID found in Ticket Support roles!\nID: {role_id}')

    if ticket_topic == "Partnership" and not partner_manager_role_id == -1:
        overwrites[discord.utils.get(guild.roles, id=partner_manager_role_id)] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True)

    with open('values.json', 'r') as file:
        values_json = json.loads(file.read())
        values_json['ticket_number'] += 1
        ticket_number = values_json['ticket_number']

    with open('values.json', 'w') as file:
        file.write(json.dumps(values_json, indent=4))

    channel = await guild.create_text_channel('ticket-'+str(ticket_number), category=ticket_category, overwrites=overwrites)
    await interaction.response.send_message(f'Ticket successfully opened: <#{channel.id}>', ephemeral=True)

    view = discord.ui.View(timeout=None)
    embed = discord.Embed(title='Ticket Created!')
    button = discord.ui.Button(label='Close Ticket', custom_id=f'ticket_{ticket_number}_close_button')

    view.add_item(button)
    bot.add_view(view)

    embed.add_field(name='Ticket topic:',value=ticket_topic)
    embed.add_field(name='Created by:', value=interaction.user.mention)

    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await channel.send(embed=embed, view=view)

    if not transcript_channel_id == -1:
        transcript_channel = discord.utils.get(interaction.guild.channels, id=transcript_channel_id)
        transcript_embed = discord.Embed(title=f"Ticket #{channel.name.split('-')[1]} created")
        transcript_embed.add_field(name='Ticket topic:',value=ticket_topic)
        transcript_embed.add_field(name="Created by", value=interaction.user.mention)
        await transcript_channel.send(embed=transcript_embed)

@bot.slash_command()
async def send_ticket_message(interaction: discord.Interaction, channel: discord.channel.TextChannel):
    if interaction.user.guild_permissions.administrator:
        if len(ticket_categories) == 0:
            await interaction.response.send_message('No ticket categories are configured!', ephemeral=True)
            return
        embed = discord.Embed(
            title="Open a Ticket", description='''
    ⁉️ Found a problem? Found a bug? Open a ticket!

    📌| Please describe your problem after opening the ticket.
    ⚡| One of our team members will respond right away!''')
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        view = discord.ui.View(timeout=None)
        select = discord.ui.Select(options=[discord.SelectOption(
            label=thing, value=thing, emoji=emoji) for emoji, thing in ticket_categories], custom_id='ticket')
        view.add_item(select)
        bot.add_view(view)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message('Ticket Panel successfully sent to the specified channel!', ephemeral=True)
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def warn(interaction: discord.Interaction, member: discord.Member, *, reason='Reason not provided'):
    if interaction.user.guild_permissions.moderate_members:
        # if interaction.user.id == member.id:
        #     await interaction.response.send_message('You cannot warn yourself!', ephemeral=True)
        #     return

        if member.bot:
            await interaction.response.send_message('You cannot warn a bot!', ephemeral=True)
            return

        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("You don't have permission to warn this user!", ephemeral=True)
            return

        if str(member.id) in warns:
            warns[str(member.id)].append(reason)
        else:
            warns[str(member.id)] = [reason]

        try:
            await member.send(f'You have been warned for the following reason: {reason}')
        except discord.errors.Forbidden:
            pass

        try:
            if len(warns[str(member.id)]) == 2:
                await member.timeout(datetime.datetime.now() + datetime.timedelta(hours=1))
            if len(warns[str(member.id)]) == 3:
                await member.kick()
            if len(warns[str(member.id)]) == 4:
                await member.timeout(datetime.datetime.now() + datetime.timedelta(days=1))
            if len(warns[str(member.id)]) == 5:
                await member.timeout(datetime.datetime.now() + datetime.timedelta(days=3))
            if len(warns[str(member.id)]) == 6:
                await member.ban(reason='The member reached 6 warns.')

            await interaction.response.send_message(f'Warning sent for the following reason: {reason}')
        except discord.errors.Forbidden:
            await interaction.response.send_message("I was not able to punish the user due to missing permissions.")

        with open('warns.json', 'w') as file:
            file.write(json.dumps(warns, indent=4))

    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def mcstats(interaction: discord.Interaction):
    if not server_ip == 'example.com':
        if not server_ip == 'COMING SOON!':
            try:
                await interaction.response.defer()
                status = get_minecraft_status()
            except:
                traceback.print_exc()
                await interaction.followup.send('The server is not available!')
                return
            embed = discord.Embed(title='MC Statistics', color=discord.Colour.red())
            embed.add_field(name="Online Players",value=str(status.players.online))
            embed.add_field(name="Ping",value=f"{round(status.latency,2)} ms")
            if not bot.user.avatar == None:
                embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
            else:
                embed.set_footer(text=f"{server_name} Bot")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message("IP COMING SOON!")
    else:
        await interaction.response.send_message("This command is disabled!", ephemeral=True)

@bot.slash_command()
async def kick(interaction: discord.Interaction, member: discord.Member, reason=None):
    if interaction.user.guild_permissions.kick_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('You cannot kick yourself!', ephemeral=True)
            return
        if bot.user.id == member.id:
            await interaction.response.send_message('You cannot kick the bot!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("You don't have permission to kick this user!", ephemeral=True)
            return
        await member.kick(reason=reason)
        await interaction.response.send_message(f'User {member.name} has been kicked!')

    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def ban(interaction: discord.Interaction, member: discord.Member, reason=None):
    if interaction.user.guild_permissions.ban_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('You cannot ban yourself!', ephemeral=True)
            return
        if bot.user.id == member.id:
            await interaction.response.send_message('You cannot ban the bot!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("You don't have permission to ban this user!", ephemeral=True)
            return
        if not reason == None:
            await member.ban(reason=reason)
        else:
            await member.ban()
            await interaction.response.send_message(f'User {member.name} has been banned!')

    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def unban(interaction: discord.Interaction, member_id: int, reason=None):
    if interaction.user.guild_permissions.ban_members and interaction.user.guild_permissions.administrator:
        banned_users = interaction.guild.bans()

        for ban_entry in banned_users:
            user = ban_entry.user

            if member_id == user.id:
                if not reason == None:
                    await interaction.guild.unban(user, reason=reason)
                else:
                    await interaction.guild.unban(user)
                    await interaction.response.send_message(f'User {user.name} has been unbanned!')

    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def mute(interaction: discord.Interaction, member: discord.Member, time):
    if interaction.user.guild_permissions.moderate_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('You cannot mute yourself!', ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message('You cannot mute a bot!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            seconds = int(time.split(time[-1])[0]) * time_convert[time[-1]]
            duration = datetime.timedelta(seconds=seconds)
            await member.timeout(duration)
            await interaction.response.send_message(f'{member.name} has been muted for {seconds} seconds')

        else:
            await interaction.response.send_message('You cannot mute a user with a higher role than yours!')
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles = [i.name for i in member.roles]
    roles.remove("@everyone")

    account_age = (discord.utils.utcnow() - member.created_at).days

    boosting_since = member.premium_since
    is_boosting = bool(boosting_since)

    activity = member.activity.name if member.activity else "N/A"

    embed = discord.Embed(title='User Info', color=discord.Colour.red())

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    embed.add_field(name='Username', value=f"{member.name}", inline=False)
    embed.add_field(name='ID', value=str(member.id), inline=False)
    embed.add_field(name='Status', value=str(member.status).replace('idle', 'Idle').replace('dnd', 'Busy').replace('online', 'Available').replace('offline', 'Not Available'), inline=False)
    embed.add_field(name='Profile Created', value=member.created_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name='Account Age', value=f"{account_age} days", inline=False)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name='Current Activity', value=activity, inline=False)

    embed.add_field(name='Roles', value='\n'.join(roles) or "No roles", inline=False)
    embed.add_field(name='Highest Role', value=roles[-1] if roles else "No roles", inline=False)

    embed.add_field(name='Nitro Boost?', value='Yes' if is_boosting else 'No', inline=False)
    if is_boosting:
        embed.add_field(name='Boosting Since', value=boosting_since.strftime("%b %d, %Y"), inline=False)

    embed.add_field(name='Bot?', value='Yes' if member.bot else 'No', inline=False)

    if bot.user.avatar:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await interaction.response.send_message(embed=embed)

@bot.slash_command()
async def ui(interaction: discord.Interaction, member: discord.Member = None):
    await userinfo(interaction, member)

@bot.slash_command()
async def ip(interaction):
    if not server_ip == 'example.com':
        await interaction.response.send_message(f'Server IP: **{server_ip}**')
    else:
        await interaction.response.send_message("This feature is not enabled.")

@bot.slash_command()
async def help(interaction: discord.Interaction, topic=None):
    embed = discord.Embed(title='Bot Commands', color=discord.Colour.red())

    if topic != None:
        if commands.get(topic.title()) != None:
            for parancs in commands[topic.title()]:
                embed.add_field(name=parancs[0], value=parancs[1])
        else:
            await interaction.response.send_message('This help category does not exist!')
            return
    else:
        for category in commands:
            embed.add_field(name=category, value=categories[category])

    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await interaction.response.send_message(embed=embed)

@bot.slash_command()
async def serverinfo(interaction: discord.Interaction):
    server = interaction.guild

    roles = [role.name for role in server.roles]
    roles.reverse()

    embed = discord.Embed(title='Server Info', color=discord.Colour.red())
    embed.add_field(name='Name', value=server.name, inline=False)
    embed.add_field(name='ID', value=server.id, inline=False)
    embed.add_field(name='Number of Roles', value=str(len(server.roles)), inline=False)
    embed.add_field(name='Number of Members', value=str(len(server.members)), inline=False)
    embed.add_field(name='Number of Humans', value=str(sum([1 if not member.bot else 0 for member in server.members])), inline=False)
    embed.add_field(name='Number of Bots', value=str(sum([1 if member.bot else 0 for member in server.members])), inline=False)
    embed.add_field(name='Highest Role', value=roles[0], inline=False)
    embed.add_field(name="Number of Boosts", value=server.premium_subscription_count, inline=False)

    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await interaction.response.send_message(embed=embed)

@bot.slash_command()
async def si(interaction):
    await serverinfo(interaction)

@bot.slash_command()
async def clear(interaction: discord.Interaction, amount: int):
    if interaction.user.guild_permissions.manage_messages:
        await interaction.channel.purge(limit=amount + 1)
        response = await interaction.response.send_message(f'{amount} messages deleted!')
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def say(interaction: discord.Interaction, text):
    if interaction.user.guild_permissions.manage_messages:
        if '<@' in text or "@everyone" in text or "@here" in text:
            await interaction.response.send_message('You cannot use pings in a say command!', ephemeral=True)
            return
        await interaction.channel.send(text)
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

@bot.slash_command()
async def autoclose(interaction: discord.Interaction, duration):
    if interaction.user.guild_permissions.manage_channels:
        ticket_category = discord.utils.get(
            interaction.channel.guild.categories, id=ticket_category_id)
        if interaction.channel.category == ticket_category:
            seconds = int(duration.split(duration[-1])[0]) * time_convert[duration[-1]]
            await interaction.response.send_message(f'Successful autoclose operation! If there are no messages in the ticket after {seconds} seconds, the ticket will be automatically closed!')
            await asyncio.sleep(seconds)
            messages = await interaction.channel.history(limit=1).flatten()

            last_message = messages[0]
            time_difference = time.time() - last_message.created_at.timestamp()
            if time_difference >= seconds:
                await interaction.channel.send("Ticket locked due to inactivity.")
                await asyncio.sleep(3)
                await interaction.channel.delete()
        else:
            await interaction.response.send_message('This command can only be used in tickets!')
    else:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

if settings['token']:
    bot.run(settings['token'])
else:
    print('Change the token variable in the settings.json file to start the bot!')
