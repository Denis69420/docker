import discord
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import os
import json

load_dotenv()

def load_ticket_state(filename="tickets.json"):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return {}

def save_ticket_state(state, filename="tickets.json"):
    with open(filename, "w") as file:
        json.dump(state, file, indent=4)

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_state = load_ticket_state()
        self.db_config = {
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME')
        }

    def get_db_connection(self):
        return mysql.connector.connect(**self.db_config)

    def fetch_category_id(self, guild_id, ticket_type):
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT category_id FROM ticket_categories WHERE guild_id = %s AND ticket_type = %s", (guild_id, ticket_type))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result['category_id']
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            for channel_id, ticket_info in self.ticket_state.items():
                channel = guild.get_channel(int(channel_id))
                if channel:
                    await self.create_ticket_view(channel, ticket_info['user_id'], ticket_info['selected_option'])
        print('Bot is ready and persistent views are restored.')

    async def create_ticket_view(self, channel, user_id, selected_option):
        view = TicketView(self.bot, channel.id, user_id, selected_option)
        role = channel.guild.get_role(1264193995081515141)
        await channel.send(
            f"Hallo <@{user_id}>, dein Ticket für '{selected_option}' wurde erstellt. {role.mention}",
            view=view
        )

    @commands.command(name='ticket')
    @commands.has_role(1264193995081515140)
    async def ticket(self, ctx):
        await ctx.message.delete()

        embed = discord.Embed(
            title="Nevora City | Ticket System",
            description=(
                "Reagiere hier auf das korrekte Feld um dein gewünschtes Ticket zu eröffnen\n\n"
                "**Allgemeines Anliegen**\n"
                "Ansprechpartner:  Team\n\n"
                "**Donator Anliegen**\n"
                "Ansprechpartner: Management | Projektleitung\n\n"
                "**Player Report**\n"
                "Ansprechpartner:  Team\n\n"
                "**Fraktions Anliegen**\n"
                "Ansprechpartner: Fraktionsverwaltung | Fraktionsverwaltungsleitung\n\n"
                "**Analyse Anliegen**\n"
                "Ansprechpartner: Head Analyst | Analyst\n\n"
                "**Team Anliegen**\n"
                "Ansprechpartner: Teamleitung\n\n"
                "**Rückerstattung Anliegen**\n"
                "Ansprechpartner: Team\n\n"
                "**Event Anliegen**\n"
                "Ansprechpartner: Event-manager\n\n"
                "**Bug Report**\n"
                "Ansprechpartner: Entwickler - Team\n\n"
                "**Ausnutzung des Supports wird streng sanktioniert.**"
            ),
            color=discord.Color.red()
        )

        options = [
            discord.SelectOption(label='Allgemeines Anliegen', description='Allgemeine Fragen'),
            discord.SelectOption(label='Donator Anliegen', description='Donator Ticket'),
            discord.SelectOption(label='Player Report', description='Spieler Report'),
            discord.SelectOption(label='Fraktions Anliegen', description='Fraktions Anliegen'),
            discord.SelectOption(label='Analyse Anliegen', description='Analysten anfragen'),
            discord.SelectOption(label='Team Anliegen', description='Team anliegen'),
            discord.SelectOption(label='Rückerstattung Anliegen', description='Refund Ticket'),
            discord.SelectOption(label='Event Anliegen', description='Event Ticket'),
            discord.SelectOption(label='Bug Report', description='Report a bug'),
        ]

        select = PersistentSelect(self.bot, options, placeholder='Wähle ein Anliegen aus')
        view = discord.ui.View(timeout=None)
        view.add_item(select)

        await ctx.send(embed=embed, view=view)
        print('Ticket embed sent.')

    @commands.command(name='renameticket')
    @commands.has_role(1264193995081515141)
    async def ticket_rename(self, ctx, *, new_name: str):
        channel = ctx.channel
        await channel.edit(name=new_name)
        await ctx.send(f"Der Kanal wurde in '{new_name}' umbenannt.", delete_after=10)

class PersistentSelect(discord.ui.Select):
    def __init__(self, bot, options, placeholder):
        super().__init__(placeholder=placeholder, options=options, custom_id="persistent_select")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        selected_option = self.values[0]
        guild_id = interaction.guild.id
        ticket_system_cog = self.bot.get_cog('TicketSystem')

        category_id = ticket_system_cog.fetch_category_id(guild_id, selected_option)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=category_id)

        if category is None:
            await interaction.response.send_message(
                f"Kategorie für '{selected_option}' nicht gefunden.", ephemeral=True
            )
            return

        channel_name = f"ticket-{interaction.user.name}-{selected_option}"
        channel = await guild.create_text_channel(channel_name, category=category)

        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        view = TicketView(self.bot, channel.id, interaction.user.id, selected_option)
        role = guild.get_role(1264193995081515141)  # ID of the role to ping
        await channel.send(
            f"Hallo <@{interaction.user.id}>, dein Ticket für '{selected_option}' wurde erstellt. {role.mention}",
            view=view
        )

        ticket_system_cog.ticket_state[str(channel.id)] = {
            "user_id": interaction.user.id,
            "selected_option": selected_option
        }
        save_ticket_state(ticket_system_cog.ticket_state)

        await interaction.response.send_message(
            f"Ticket erstellt: {channel.mention}", ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self, bot, channel_id, user_id, selected_option):
        super().__init__(timeout=None)  # Ensure the view has no timeout
        self.bot = bot
        self.channel_id = channel_id
        self.user_id = user_id
        self.selected_option = selected_option

        # Add buttons with unique custom IDs and labels
        claim_button = discord.ui.Button(label="Claim", style=discord.ButtonStyle.primary, custom_id=f"claim_{channel_id}")
        close_button = discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.secondary, custom_id=f"close_{channel_id}")
        delete_button = discord.ui.Button(label="Delete Ticket", style=discord.ButtonStyle.danger, custom_id=f"delete_{channel_id}")

        claim_button.callback = self.claim_callback
        close_button.callback = self.close_callback
        delete_button.callback = self.delete_callback

        self.add_item(claim_button)
        self.add_item(close_button)
        self.add_item(delete_button)

    async def claim_callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(1264193995081515141)
        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"{interaction.user.mention} hat das Ticket beansprucht.", ephemeral=True)

    async def close_callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        ticket_system_cog = self.bot.get_cog('TicketSystem')
        fertig_category_id = ticket_system_cog.fetch_category_id(guild_id, 'fertig')

        if fertig_category_id is None:
            await interaction.response.send_message("Fertig-Kategorie nicht gefunden.", ephemeral=True)
            return

        fertig_category = discord.utils.get(interaction.guild.categories, id=fertig_category_id)
        if fertig_category is None:
            await interaction.response.send_message("Fertig-Kategorie nicht gefunden.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        try:
            await channel.edit(name="fertig", category=fertig_category)
            await channel.set_permissions(self.bot.user, read_messages=True, send_messages=True)
            await interaction.response.send_message("Ticket wird geschlossen und verschoben.", ephemeral=True)
            await channel.send("Dieses Ticket wurde geschlossen und in die Fertig-Kategorie verschoben. Ihr könnt keine Nachrichten mehr senden.")
            
            # Update the ticket state
            ticket_system_cog.ticket_state.pop(str(channel.id), None)
            save_ticket_state(ticket_system_cog.ticket_state)
        except Exception as e:
            await interaction.response.send_message(f"Fehler beim Schließen und Verschieben des Tickets: {e}", ephemeral=True)

    async def delete_callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        try:
            # Update the ticket state
            ticket_system_cog = self.bot.get_cog('TicketSystem')
            ticket_system_cog.ticket_state.pop(str(channel.id), None)
            save_ticket_state(ticket_system_cog.ticket_state)

            await interaction.response.send_message("Ticket wird gelöscht.", ephemeral=True)
            await channel.delete()
        except Exception as e:
            await interaction.response.send_message(f"Fehler beim Löschen des Tickets: {e}", ephemeral=True)

async def setup(bot):
    # Register the persistent view for existing tickets
    for channel_id, ticket_info in load_ticket_state().items():
        bot.add_view(TicketView(bot, int(channel_id), ticket_info['user_id'], ticket_info['selected_option']))
    await bot.add_cog(TicketSystem(bot))
    print('TicketSystem Cog loaded.')
