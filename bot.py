import discord
import asyncio
import random
import datetime
import json, ast
import traceback
from mcstatus import JavaServer
import time
import pytz
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

giveaways = []
global players_before
players_before = 0

def get_minecraft_status():
    server = JavaServer.lookup(f"{private_server_ip}:{private_server_port}")
    return server.status()

def convert_duration(duration):
    if 's' in duration:
        return duration.replace('s', ' másodperc')
    if 'm' in duration:
        return duration.replace('m', ' perc')
    if 'h' in duration:
        return duration.replace('h', ' óra')
    if 'd' in duration:
        return duration.replace('d', ' nap')
    if 'w' in duration:
        return duration.replace('w', ' hét')
    if 'mo' in duration:
        return duration.replace('mo', ' hónap')

def convert_duration_to_seconds(duration):
    time_convert = {"s": 1, "m": 60, "h": 3600,
                    "d": 86400, "w": 604800, "mo": 31536000}

    return int(duration.split(duration[-1])[0]) * time_convert[duration[-1]]

def convert_seconds_to_date(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    result = ""
    if days > 0:
        result += "{} nap ".format(int(days))
    if hours > 0:
        result += "{} óra ".format(int(hours))
    if minutes > 0:
        result += "{} perc ".format(int(minutes))
    if seconds > 0 or not any([days, hours, minutes]):
        result += "{} másodperc".format(int(seconds))

    return result.strip()

@tasks.loop(minutes=1)
async def update_mc_status():
    minecraft_status = get_minecraft_status()
    player_num, ping = minecraft_status.players.online, minecraft_status.latency
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | {player_num} Online | /help"))
    global players_before
    if players_before == 0 or player_num != players_before:
        await discord.utils.get(bot.guilds[0].channels, id=players_status_channel_id).edit(name=f"Játékosok: {player_num}")
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
                title="🎉 Giveaway 🎉", description=f"Reagálj 🎉 emotikonnal hogy jelentkezz!\nHátralevő idő: **{time_left_in_str}**\nNyeremény: **{giveaway['prize']}**\nNyertesek száma: **{giveaway['winner_num']}**", color=0xFFFF00)
            if not bot.user.avatar == None:
                embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
            else:
                embed.set_footer(text=f"{server_name} Bot")
            await message.edit(embed=embed)
            await asyncio.sleep(1)
@bot.event
async def on_member_join(member):
    if not join_channel_id == -1:
        embed = discord.Embed(title=f'Üdvözöllek, {member.name}', color=discord.Colour.red(), description=f"👋 Üdvözöllek a(z) {server_name} discord szerverén, **{member.display_name}**!\nReméljük jól fogod érezni magad a szerverünkön!")
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
    await bot.sync_commands()
    for giveaway_dict in giveaways_json_list:
        try:
            channel = await bot.guilds[0].fetch_channel(giveaway_dict['channel_id'])
            message = await channel.fetch_message(giveaway_dict['message_id'])
            giveaways.append({"message_id": giveaway_dict['message_id'], "message": message, "winner_num": giveaway_dict['winner_num'],
                                "duration": convert_duration(giveaway_dict['_duration']), "_duration": giveaway_dict['_duration'], "prize": giveaway_dict['prize'], "ended": giveaway_dict['ended'], "end_time": giveaway_dict['start_time']+convert_duration_to_seconds(giveaway_dict['_duration'])})
        except:
            continue
    if not server_ip == 'example.com':
        if not server_ip == 'HAMAROSAN!':
            update_mc_status.start()
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | /help"))
            if not ping_status_channel_id == -1:
                await discord.utils.get(bot.guilds[0].channels, id=ping_status_channel_id).edit(name=f"Ping: HAMAROSAN!")
            if not players_status_channel_id == -1:
                await discord.utils.get(bot.guilds[0].channels, id=players_status_channel_id).edit(name=f"Játékosok: HAMAROSAN!")
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{server_name} | /help"))
    print(f'{server_name} bot online')
    update_giveaways.start()

if not server_ip == 'example.com':
    @bot.event
    async def on_message(message):
        if not message.author.bot:
            if any(i in message.content.lower() for i in [' ip', ' ipje', ' ip ']) and message.content.endswith('?'):
                await message.reply(f'A szerver ipje: **{server_ip}**')

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
            embed.add_field(name='Felhasználó által megkapott rangok:',value=','.join(new_roles))

        removed_roles = [role.name for role in before.roles if role not in after.roles]
        if len(removed_roles) != 0:
            roles_changed = True
            embed.add_field(name='Felhasználótól elvett rangok:',value=','.join(removed_roles))

        if roles_changed:
            embed.title += ' rangjai'

        if before.nick != after.nick:
            nick_changed = True
            embed.title += (' és beceneve' if roles_changed else ' beceneve')
            embed.add_field(name='Felhasználó régi beceneve', value=str(before.nick).replace('None','Nincs becenév'))
            embed.add_field(name='Felhasználó új beceneve', value=str(after.nick).replace('None','Nincs becenév'))

        if before.display_name != after.display_name:
            name_changed = True
            embed.title += (' és neve' if roles_changed or nick_changed else ' neve')
            embed.add_field(name='Felhasználó régi neve', value=str(before.nick))
            embed.add_field(name='Felhasználó új neve', value=str(after.nick))

        if roles_changed and not name_changed and not nick_changed:
            embed.title += ' megváltoztak!' # Egy felhasználó rangjai megváltoztak!
        else:
            embed.title += ' megváltozott!'
        if not embed.title == f'{after.name} megváltozott!':
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
            embed = discord.Embed(title=f'{message.author.name} üzenetét törölték a ' +
                                message.channel.name+f' csatornában!', color=discord.Colour.red())
            if not message.author.avatar == None:
                embed.set_thumbnail(url=message.author.avatar.url)
            embed.add_field(name='Tartalma: ', value=message.content)
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
            embed = discord.Embed(title=creator.name+' létrehozta a ' +
                                channel.name+' csatornát!', color=discord.Colour.red())
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
            embed = discord.Embed(title=deleter.name+' törölte a ' +
                                channel.name+' csatornát!', color=discord.Colour.red())
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
                embed = discord.Embed(title=after.author.name+' módosította a saját üzenetét itt: ' +
                                    after.channel.name+'!', color=discord.Colour.red())
                if not after.avatar == None:
                    embed.set_thumbnail(url=after.author.avatar.url)
                embed.add_field(name='Eredeti tartalma:',
                                value=before.content)
                embed.add_field(name='Módosított tartalma:', value=after.content)
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
            embed = discord.Embed(title=deleter.name+' törölt '+str(len(messages))+' üzenetet a ' +
                                messages[0].channel.name+' csatornában!', color=discord.Colour.red())
            if not deleter.avatar == None:
                embed.set_thumbnail(url=deleter.avatar.url)
            await log_channel.send(embed=embed)
    except:
        traceback.print_exc()

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
        embed = discord.Embed(title="🎉 Giveaway Vége 🎉",
                            description=f"Háralevő idő: **A giveawaynek már vége van**\nNyeremény: **{giveaway['prize']}**\nNyertesek száma: **{giveaway['winner_num']}**\nSajnálom de senki sem nyert.", color=0xFF0000)
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        await message.edit(embed=embed)
    else:
        embed = discord.Embed(title="🎉 Giveaway Vége 🎉",
                            description=f"Hátralevő idő: **A giveawaynek már vége van**\nNyeremény: **{giveaway['prize']}**\nNyertesek száma: **{giveaway['winner_num']}**\nNyertes(ek): {', '.join(winner_list)}", color=0xFF0000)
        await message.edit(content=', '.join(winner_list), embed=embed)

    giveaways[n]['ended'] = True
    giveaways_json_list[n]['ended'] = True
    with open('giveaways.json','w') as file:
        file.write(json.dumps(giveaways_json_list, indent=4))

@bot.slash_command()
async def greroll(interaction, message_id):
    if interaction.user.guild_permissions.administrator:
        for n,giveaway in enumerate(giveaways):
            if int(message_id) == giveaway["message_id"]:
                try:
                    await end_giveaway(n, giveaway)
                    await interaction.response.send_message('Giveaway sikeresen újrasorsolva!')
                    return
                except:
                    traceback.print_exc()
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def giveaway(interaction: discord.Interaction, duration: str, winners: int, prize: str):
    if interaction.user.guild_permissions.administrator:
        try:
            embed = discord.Embed(
                title="🎉 Giveaway 🎉", description=f"Reagálj 🎉 emotikonnal hogy jelentkezz!\nHátralevő idő: **{convert_duration(duration)}**\nNyeremény: **{prize}**\nNyertesek száma: **{winners}**", color=0xFFFF00)
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
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def send_reaction_role_message(interaction, channel: discord.channel.TextChannel):
    global settings
    embed_description = "Reagálj a megfelelő emojikra a rangokért!"
    for reaction_role_emoji, reaction_role_dict in reaction_roles.items():
        embed_description += f"\n{reaction_role_emoji}: {reaction_role_dict['description']}"

    embed = discord.Embed(title="Reakció Rangok", description=embed_description, color=discord.Colour.red())
    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    message: discord.Message = await channel.send(embed=embed)
    await interaction.response.send_message("Üzenet elküldve a megadott csatornába!\nÜzenet ID: " + str(message.id), ephemeral=True)

    for reaction_role_emoji, _ in reaction_roles.items():
        await message.add_reaction(reaction_role_emoji)

    settings['reaction_role_message_id'] = message.id

    with open('settings.json', 'w') as file:
        file.write(json.dumps(settings, indent=4))

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

@bot.slash_command()
async def suggest(interaction, suggestion):
    if not suggestion_channel_id == -1:
        embed = discord.Embed(title=str(interaction.user.name)+' új javaslata', description=suggestion, color=discord.Colour.red())
        embed.set_thumbnail(url=interaction.user.avatar.url)
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        message = await bot.get_channel(suggestion_channel_id).send(embed=embed)

        await message.add_reaction('✅')
        await message.add_reaction('❌')
        await interaction.response.send_message('Ötlet sikeresen közzétéve!')
    else:
        await interaction.response.send_message('Ez a parancs nincs beállítva!', ephemeral=True)

async def close_ticket(interaction):
    channel = interaction.message.channel
    closer = interaction.user

    await interaction.response.pong()

    message = await interaction.channel.send(f'Törlés 5 másodperc múlva!')
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        await message.edit(content=f'Törlés {i} másodperc múlva!')
    await asyncio.sleep(0.5)
    await channel.delete()
    if not transcript_channel_id == -1:
        transcript_channel = discord.utils.get(interaction.guild.channels, id=transcript_channel_id)
        transcript_embed = discord.Embed(title=f"Jegy #{channel.name.split('-')[1]} bezárva")

        transcript_embed.add_field(name="Bezárta", value=closer.mention)

        await transcript_channel.send(embed=transcript_embed)

@bot.slash_command()
async def lock(interaction):
    if interaction.user.guild_permissions.manage_channels:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f'Csatorna lezárva {interaction.user.mention} által!')
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def unlock(interaction):
    if interaction.user.guild_permissions.manage_channels:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(f'Csatorna megnyitva {interaction.user.mention} által!')
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

async def ticket(interaction: discord.Interaction, ticket_tema):
    guild = interaction.guild
    if not ticket_category_id == -1:
        ticket_category = discord.utils.get(
            interaction.guild.categories, id=ticket_category_id)
    else:
        await interaction.response.send_message('Ticket létrehozása sikertelen. Ticket kategória nincs beállítva.')
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
            print(f'Invalid rang ID találva a Ticket Support rangokhoz!\nID: {role_id}')

    if ticket_tema == "Partnerkedés" and not partner_manager_role_id == -1:
        overwrites[discord.utils.get(guild.roles, id=partner_manager_role_id)] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True)

    with open('values.json', 'r') as file:
        values_json = json.loads(file.read())
        values_json['ticket_number'] += 1
        ticket_number = values_json['ticket_number']

    with open('values.json', 'w') as file:
        file.write(json.dumps(values_json, indent=4))

    channel = await guild.create_text_channel('jegy-'+str(ticket_number), category=ticket_category, overwrites=overwrites)
    await interaction.response.send_message(f'Ticket sikeresen megnyitva: <#{channel.id}>', ephemeral=True)

    view = discord.ui.View(timeout=None)
    embed = discord.Embed(title='Ticket Létrehozva!')
    button = discord.ui.Button(label='Ticket bezárása', custom_id=f'ticket_{ticket_number}_close_button')

    view.add_item(button)
    bot.add_view(view)

    embed.add_field(name='Ticket témája:',value=ticket_tema)
    embed.add_field(name='Létrehozója:', value=interaction.user.mention)

    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await channel.send(embed=embed, view=view)

    if not transcript_channel_id == -1:
        transcript_channel = discord.utils.get(interaction.guild.channels, id=transcript_channel_id)
        transcript_embed = discord.Embed(title=f"Jegy #{channel.name.split('-')[1]} létrehozva")
        transcript_embed.add_field(name='Ticket témája:',value=ticket_tema)
        transcript_embed.add_field(name="Létrehozta", value=interaction.user.mention)
        await transcript_channel.send(embed=transcript_embed)

@bot.slash_command()
async def send_ticket_message(interaction, channel: discord.channel.TextChannel):
    if interaction.user.guild_permissions.administrator:
        if len(ticket_categories) == 0:
            await interaction.response.send_message('Nincsenek hibajegy kategóriák beállítva!', ephemeral=True)
            return
        embed = discord.Embed(
            title="Ticket nyitás", description='''
    ⁉️ Problémát találtál? Bugot találtál? Nyiss ticketet!

    📌| Kérlek írd le a problémádat a ticket megnyitása után.
    ⚡| Egyik csapattagunk máris válaszolni fog!''')
        if not bot.user.avatar == None:
            embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{server_name} Bot")
        view = discord.ui.View(timeout=None)
        select = discord.ui.Select(options=[discord.SelectOption(
            label=dolog, value=dolog, emoji=emoji) for emoji, dolog in ticket_categories], custom_id='ticket')
        view.add_item(select)
        bot.add_view(view)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message('Ticket Panel sikeresen elküldve a megadott csatornába!', ephemeral=True)
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

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

@bot.slash_command()
async def warn(interaction, member: discord.Member, *, reason='Ok nem megadva'):
    if interaction.user.guild_permissions.moderate_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('Saját magadat nem figyelmeztetheted!', ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message('Egy botot nem figyelmeztethetsz!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("Nincs jogod ezt a felhasználót figyelmeztetni!", ephemeral=True)
            return

        if member.id in warns:
            warns[member.id].append(reason)
        else:
            warns[member.id] = [reason]

        await member.send(f'Figyelmeztetve lettél a következő okból: {reason}')
        await interaction.response.send_message(f'A figyelmeztetést elküldtem, a következő okból: {reason}')

        if len(warns[member.id]) == 2:
            await member.timeout(datetime.timedelta(hours=1))
        if len(warns[member.id]) == 3:
            await member.kick()
        if len(warns[member.id]) == 4:
            await member.timeout(datetime.timedelta(days=1))
        if len(warns[member.id]) == 5:
            await member.timeout(datetime.timedelta(days=3))
        if len(warns[member.id]) == 6:
            await member.ban(reason='Elérte a 6 figyelmeztetést, ezért automatikusan bannoltam')

        with open('warns.json', 'w') as file:
            file.write(json.dumps(warns, indent=4))

    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def mcstats(interaction: discord.Interaction):
    if not server_ip == 'example.com':
        if not server_ip == 'HAMAROSAN!':
            try:
                await interaction.response.defer()
                status = get_minecraft_status()
            except:
                traceback.print_exc()
                await interaction.followup.send('A szerver nem elérhető!')
                return
            embed = discord.Embed(title='MC Statisztikák', color=discord.Colour.red())
            embed.add_field(name="Online Játékosok",value=str(status.players.online))
            embed.add_field(name="Ping",value=f"{round(status.latency,2)} ms")
            if not bot.user.avatar == None:
                embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
            else:
                embed.set_footer(text=f"{server_name} Bot")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message("IP HAMAROSAN!")
    else:
        await interaction.response.send_message("Ez a parancs ki van kapcsolva!", ephemeral=True)

@bot.slash_command()
async def kick(interaction, member: discord.Member, reason=None):
    if interaction.user.guild_permissions.kick_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('Saját magadat nem rúghatod ki!', ephemeral=True)
            return
        if bot.user.id == member.id:
            await interaction.response.send_message('A botot nem rúghatod ki!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("Nincs jogod ezt a felhasználót kirúgni!", ephemeral=True)
            return
        await member.kick(reason=reason)
        await interaction.response.send_message(f'A {member.name} felhasználó ki lett rúgva!')

    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def ban(interaction: discord.Interaction, member: discord.Member, reason=None):
    if interaction.user.guild_permissions.ban_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('Saját magadat nem tilthatod ki!', ephemeral=True)
            return
        if bot.user.id == member.id:
            await interaction.response.send_message('A botot nem tilthatod ki!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            await interaction.response.send_message("Nincs jogod ezt a felhasználót kitiltani!", ephemeral=True)
            return
        if not reason == None:
            await member.ban(reason=reason)
        else:
            await member.ban()
            await interaction.response.send_message(f'A {member.name} felhasználó ki lett tiltva!')

    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def unban(interaction, member_id: int, reason=None):
    if interaction.user.guild_permissions.ban_members and interaction.user.guild_permissions.administrator:
        banned_users = await interaction.guild.bans()

        for ban_entry in banned_users:
            user = ban_entry.user

            if member_id == user.id:
                if not reason == None:
                    await interaction.guild.unban(user, reason=reason)
                else:
                    await interaction.guild.unban(user)
                    await interaction.response.send_message(f'A {user.name} felhasználó kitiltása fel lett oldva!')

    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def mute(interaction, member: discord.Member, time):
    if interaction.user.guild_permissions.moderate_members:
        if interaction.user.id == member.id:
            await interaction.response.send_message('Saját magadat nem muteolhatod!', ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message('Egy botot nem muteolhatsz!', ephemeral=True)
            return
        if not interaction.user.id == interaction.guild.owner_id and interaction.user.id in emergency_admin_ids and not interaction.user.top_role.position > member.top_role.position:
            time_convert = {"s": 1, "m": 60, "h": 3600,
                            "d": 86400, "w": 604800, "mo": 31536000}
            seconds = int(time.split(time[-1])[0]) * time_convert[time[-1]]
            duration = datetime.timedelta(seconds=seconds)
            await member.timeout(duration)
            await interaction.response.send_message(f'{member.name} muteolva lett {seconds} másodpercig')

        else:
            await interaction.response.send_message('Nem muteolhatsz nálad magasabb rangú felhasználót!!')
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def userinfo(interaction, tag: discord.Member = None):
    member = tag or interaction.user
    roles = [i.name for i in member.roles]
    roles.remove("@everyone")

    account_age = (discord.utils.utcnow() - member.created_at).days

    boosting_since = member.premium_since
    is_boosting = bool(boosting_since)

    activity = member.activity.name if member.activity else "N/A"

    embed = discord.Embed(title='User Info', color=discord.Colour.red())

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    embed.add_field(name='Felhasználó neve', value=f"{member.name}", inline=False)
    embed.add_field(name='ID', value=str(member.id), inline=False)
    embed.add_field(name='Státusz', value=str(member.status).replace('idle', 'Tétlen').replace('dnd', 'Elfoglalt').replace('online', 'Elérhető').replace('offline', 'Nem elérhető'), inline=False)
    embed.add_field(name='Profil Létrehozva', value=member.created_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name='Fiók Kor', value=f"{account_age} nap", inline=False)
    embed.add_field(name='Csatlakozott a Szerverre', value=member.joined_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name='Jelenlegi Tevékenység', value=activity, inline=False)

    embed.add_field(name='Rangok', value='\n'.join(roles) or "Nincs rangja", inline=False)
    embed.add_field(name='Legmagasabb rang', value=roles[-1] if roles else "Nincs rangja", inline=False)

    embed.add_field(name='Nitro Boost?', value='Igen' if is_boosting else 'Nem', inline=False)
    if is_boosting:
        embed.add_field(name='Boostolás kezdete', value=boosting_since.strftime("%b %d, %Y"), inline=False)

    embed.add_field(name='Bot?', value='Igen' if member.bot else 'Nem', inline=False)

    if bot.user.avatar:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")

    await interaction.response.send_message(embed=embed)

@bot.slash_command()
async def ui(interaction, member: discord.Member = None):
    await userinfo(interaction, member)

if not server_ip == 'example.com':
    @bot.slash_command()
    async def ip(interaction):
        await interaction.response.send_message(f'A szerver ipje: **{server_ip}**')

@bot.slash_command()
async def help(interaction, help_tema=None):
    embed = discord.Embed(title='Bot Parancsok', color=discord.Colour.red())
    parancsok = {
        'Mod': [
            ['/clear {mennyiség}', 'Törli a jelenlegi csatornában lévő üzeneteket'],
            ['/warn {felhasználó említése}', 'Egy figyelmeztetést ad a megadott felhasználónak, ha az elért egy számú figyelmeztetést, büntetést is ad.'],
            ['/mute {felhasználó neve}', 'Lenémít egy felhasználót'],
            ['/kick {felhasználó említése}', 'Kirúg egy felhasználót'],
            ['/ban {felhasználó említése}', 'Kitilt egy felhasználót'],
            ['/unban {felhasználó neve}', 'Unbannol egy felhasználót'],
            ['/clear_member_msg {felhasználó említése} {üzenetek száma}', 'Csak egy kiválszott felhasználó üzeneteit törli a jelenlegi csatornában']],
        'Fun': [
            ['/say {szöveg}', 'A bot elküldi amit írsz.'],
            ['/suggest {ötlet}','Segíts nekünk egy ötlet írásával!'],
            ['/screenshot {link}','Készíts egy screenshotot egy oldalról!']],
        'Infó': [
            ['/help', 'Ez a parancs'],
            ['/userinfo {felhasználó említés} vagy /ui {felhasználó említés}','Információk egy felhasználóról'],
            ['/serverinfo vagy /si {felhasználó említés}','Információk a dc szerverünkről'],
            ['/ip', 'Kiírja a minecraft szerverünk ip címét'],
            ['/mcstats','Tudd meg szerverünk jelenlegi pingjét és játékos számát']],
        'Admin': [
            ['/giveaway {idő} {nyertesek száma} {nyeremény}','Csinál egy giveawayt a jelenlegi csatornában.'],
            ['/greroll {üzenet idja}','A megadott üzenet id alapján a giveawayt fogja újrasorsolni..'],
            ['/send_reaction_role_message {csatorna említése}','Elküldi a reakció rang panelt az említett csatornában'],
            ['/send_ticket_message {csatorna említése}','Elküldi a hibajegy panelt az említett csatornában'],
            ['/autoclose {idő}','Adott idő után ha nem talál üzenetet, akkor bezárja a ticketet'],
            ['/lock','Lezárja a jelenlegi csatornát.'],
            ['/unlock','Felnyitja a jelenlegi csatornát.']]
    }
    kategoria_leirasok = {
        'Infó': 'Információs Parancsok pl /userinfo',
        'Admin': 'Adminoknak szánt parancsok',
        'Mod': 'Moderátoroknak szánt parancsok.',
        "Fun": 'Fun parancsok pl. /say'}
    if help_tema != None:
        if parancsok.get(help_tema.title()) != None:
            for parancs in parancsok[help_tema.title()]:
                embed.add_field(name=parancs[0], value=parancs[1])
        else:
            await interaction.response.send_message('Ez a help kategória nem létezik!')
            return
        # for kategoria in parancsok:
        #     for parancs in parancsok[kategoria]:
        #         if parancs[0].replace('/', '').startswith(str(help_tema)):
        #             embed.add_field(name=parancs[0], value=parancs[1])
        #             break
    else:
        for kategoria in parancsok:
            embed.add_field(name=kategoria, value=kategoria_leirasok[kategoria])
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
    embed = discord.Embed(title='Szerver infó', color=discord.Colour.red())
    embed.add_field(name='Név', value=server.name, inline=False)
    embed.add_field(name='ID', value=server.id, inline=False)
    embed.add_field(name='Rangok száma', value=str(len(server.roles)), inline=False)
    embed.add_field(name='Tagok száma', value=str(len(server.members)), inline=False)
    embed.add_field(name='Emberek száma', value=str(sum([1 if not member.bot else 0 for member in server.members])), inline=False)
    embed.add_field(name='Botok száma', value=str(sum([1 if member.bot else 0 for member in server.members])), inline=False)
    embed.add_field(name='Legmagasabb rang', value=roles[0], inline=False)
    embed.add_field(name="Boostok száma", value=server.premium_subscription_count, inline=False)
    #embed.add_field(name="Botok", value=server.premium_subscription_count, inline=False)
    if not bot.user.avatar == None:
        embed.set_footer(text=f"{server_name} Bot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{server_name} Bot")
    await interaction.response.send_message(embed=embed)

@bot.slash_command()
async def si(interaction):
    await serverinfo(interaction)

@bot.slash_command()
async def clear(interaction: discord.Interaction, mennyiseg: int):
    if interaction.user.guild_permissions.manage_messages:
        await interaction.channel.purge(limit=mennyiseg+1)
        response = await interaction.response.send_message(f'{mennyiseg} üzenet törölve!')
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

@bot.slash_command()
async def say(interaction, szoveg):
    if interaction.user.guild_permissions.manage_messages:
        if '<@' in szoveg or "@everyone" in szoveg or "@here" in szoveg:
            await interaction.response.send_message('Pinget nem használhatsz egy say parancsban!', ephemeral=True)
            return
        await interaction.channel.send(szoveg)
        #await interaction.response.send_message(szoveg)
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

def check_member_msg_purge(message, member, amount):
    global cleared_num
    if member == message.author:
        cleared_num += 1
    return cleared_num <= amount

@bot.slash_command()
async def clear_member_msg(interaction, amount: int, member: discord.Member):
    if interaction.user.guild_permissions.manage_messages:
        global cleared_num
        cleared_num = 0
        if not amount == 'all':
            await interaction.channel.purge(check=lambda message: member == message.author)
        else:
            await interaction.channel.purge(check=lambda message, member=member, amount=amount:check_member_msg_purge(message, member, amount))
        await interaction.channel.send(amount.replace('all', 'összes')+' '+str(member)+' által írt üzenet törölve')

@bot.slash_command()
async def autoclose(interaction, duration):
    if interaction.user.guild_permissions.manage_channels:
        ticket_category = discord.utils.get(
            interaction.channel.guild.categories, id=ticket_category_id)
        if interaction.channel.category == ticket_category:
            time_convert = {"s": 1, "m": 60, "h": 3600,
                            "d": 86400, "w": 604800, "mo": 31536000}

            seconds = int(duration.split(duration[-1])[0]) * time_convert[duration[-1]]
            await interaction.response.send_message(f'Sikeres autoclose művelet! Ha ticketben nem lesz üzenet {seconds} másodperc után, a ticket automatikusan zárolva lesz!')
            await asyncio.sleep(seconds)
            messages = await interaction.channel.history(limit=1).flatten()

            last_message = messages[0]
            time_difference = datetime.datetime.now(pytz.timezone('Europe/Berlin')) - last_message.created_at.replace(tzinfo=pytz.UTC)
            if time_difference.total_seconds() >= seconds:
                await interaction.channel.send("Ticket inaktivitás miatt zárolva.")
                await asyncio.sleep(3)
                await interaction.channel.delete()
        else:
            await interaction.response.send_message('Ezt a parancsot csak ticketekben lehet használni!')
    else:
        await interaction.response.send_message("Nincs jogod használni ezt a parancsot!", ephemeral=True)

if not settings['token'] == 'TOKEN':
    bot.run(settings['token'])
else:
    print('Írd át a token változót a settings.json fájlban a bot elindításához!')
