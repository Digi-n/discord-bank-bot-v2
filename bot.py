import json
import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1451761878089990257

BANK_CHANNEL_NAME = "💰-black-bank"
LEDGER_CHANNEL_NAME = "🧾-bank-ledger"
MANAGEMENT_ROLE = "Management"
BANKER_ROLE = "Banker"
GROWER_ROLE = "Grower"
COOK_ROLE = "Cook"
DISTRIBUTOR_ROLE = "Distributor"

NAME_CHANGE_CHANNEL = "name-change"
WELCOME_CHANNEL_NAME = "🤝welcome"

BANK_DATA_FILE = "bank_data.json"
STOCK_FILE = "stock_data.json"
NAME_LOCK_FILE = "name_locks.json"

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# GLOBAL DATA
# ======================
weed_stock = 0
meth_stock = 0
distributed_total = 0
black_balance = 0

# ======================
# SHOP ITEMS
# ======================
SHOP_ITEMS = {
    "Advanced Lockpick": 200000,
    "Weed OG Seed": 10000,
    "Pestle & Mortar": 20000,
    "Chemical Beaker": 15000,
    "Portable Meth Lab": 25000,
    "Meth Test Kit": 5000,
    "Egg Timer": 10000,
    "Hydrochloric Acid": 20000,
    "Red Phosphorus": 25000,
    "Lithium": 22000,
    "Pseudoephedrine": 23000,
    "Acetone": 10000,
    "5.56×45 Ammo": 500,
    "Liquid Fertilizer": 8000,
    "Watering Can": 4000,
    "Fertilizer": 1200,
    "Advanced Fertilizer": 6000
}
SHOP_PAGES = [
    {
        "title": "🛒 Shop Page 1",
        "items": [
            "Advanced Lockpick",
            "Weed OG Seed",
            "Pestle & Mortar",
            "Chemical Beaker",
            "Portable Meth Lab"
        ]
    },
    {
        "title": "🛒 Shop Page 2",
        "items": [
            "Meth Test Kit",
            "Egg Timer",
            "Hydrochloric Acid",
            "Red Phosphorus",
            "Lithium"
        ]
    },
    {
        "title": "🛒 Shop Page 3",
        "items": [
            "Pseudoephedrine",
            "Acetone",
            "5.56×45 Ammo",
            "Liquid Fertilizer",
            "Watering Can"
        ]
    },
]

# ======================
# PERMISSION CHECK
# ======================
def is_management(member: discord.Member) -> bool:
    return any(role.name == MANAGEMENT_ROLE for role in member.roles)
def management_only(interaction: discord.Interaction) -> bool:
    return is_management(interaction.user)
def management_or_banker(interaction: discord.Interaction) -> bool:
    return (
        any(role.name == MANAGEMENT_ROLE for role in interaction.user.roles)
        or any(role.name == BANKER_ROLE for role in interaction.user.roles)
    )
def can_update_stock(interaction: discord.Interaction) -> bool:
    allowed_roles = {MANAGEMENT_ROLE, GROWER_ROLE, COOK_ROLE, DISTRIBUTOR_ROLE}
    return any(role.name in allowed_roles for role in interaction.user.roles)




# ======================
# NAME LOCK STORAGE (NO ROLES)
# ======================
def load_name_locks():
    if os.path.exists(NAME_LOCK_FILE):
        with open(NAME_LOCK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_name_locks(data):
    with open(NAME_LOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ======================
# LOAD / SAVE
# ======================
def load_stock():
    global weed_stock, meth_stock, distributed_total
    if os.path.exists(STOCK_FILE):
        with open(STOCK_FILE, "r") as f:
            data = json.load(f)
            weed_stock = data.get("weed", 0)
            meth_stock = data.get("meth", 0)
            distributed_total = data.get("distribution", 0)

def save_stock():
    with open(STOCK_FILE, "w") as f:
        json.dump({
            "weed": weed_stock,
            "meth": meth_stock,
            "distribution": distributed_total
        }, f, indent=4)

def load_bank():
    global black_balance
    if os.path.exists(BANK_DATA_FILE):
        with open(BANK_DATA_FILE, "r") as f:
            black_balance = json.load(f).get("black_balance", 0)

def save_bank():
    with open(BANK_DATA_FILE, "w") as f:
        json.dump({"black_balance": black_balance}, f, indent=4)

# ======================
# BANK ANIMATION
# ======================
async def public_animation(channel: discord.TextChannel):
    msg = await channel.send("💳 **Processing transaction**")
    await asyncio.sleep(1)
    await msg.edit(content="🔐 Verifying source")
    await asyncio.sleep(1)
    await msg.edit(content="🧾 Updating ledger")
    await asyncio.sleep(1)
    await msg.edit(content="✅ Transaction Approved")

# ======================
# STOCK MODAL
# ======================
class StockModal(discord.ui.Modal):
    def __init__(self, title, stock_type):
        super().__init__(title=title)
        self.stock_type = stock_type
        self.amount = discord.ui.TextInput(label="Enter amount", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        if not can_update_stock(interaction):
         await interaction.response.send_message(
        "❌ Only Management, Grower, Distributor or Cook can update stock.",
        ephemeral=True
 )
         return


        global weed_stock, meth_stock, distributed_total

        try:
            value = int(self.amount.value)
            if value < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Invalid number", ephemeral=True)
            return

        if self.stock_type == "weed":
            weed_stock = value
            text = f"🌿 **WEED STOCK**\n\nCurrent Stock: **{weed_stock} g**"
        elif self.stock_type == "meth":
            meth_stock = value
            text = f"🧪 **METH STOCK**\n\nCurrent Stock: **{meth_stock} g**"
        else:
            distributed_total += value
            text = f"🚚 **DISTRIBUTION LOG**\n\nTotal Distributed: **{distributed_total} g**"

        save_stock()
        await interaction.message.edit(content=text)
        await interaction.response.send_message("✅ Stock updated", ephemeral=True)
# ======================
# CART SYSTEM
# ======================

user_carts = {}

CART_PAGES = {
    1: ["Advanced Lockpick", "Weed OG Seed", "Pestle & Mortar", "Chemical Beaker"],
    2: ["Portable Meth Lab", "Meth Test Kit", "Egg Timer", "Hydrochloric Acid"],
    3: ["Red Phosphorus", "Lithium", "Pseudoephedrine", "Acetone"],
    4: ["5.56×45 Ammo", "Liquid Fertilizer", "Watering Can", "Fertilizer", "Advanced Fertilizer"]
}


class CartModal(discord.ui.Modal):
    def __init__(self, user_id, cart_number):
        super().__init__(title=f"Cart {cart_number}")
        self.user_id = user_id
        self.cart_number = cart_number

        self.inputs = {}
        for item in CART_PAGES[cart_number]:
            field = discord.ui.TextInput(
                label=item,
                placeholder="Enter quantity",
                required=False
            )
            self.add_item(field)
            self.inputs[item] = field

    async def on_submit(self, interaction: discord.Interaction):
        user_carts.setdefault(self.user_id, {})

        for item, field in self.inputs.items():
            if field.value:
                user_carts[self.user_id][item] = int(field.value)

        await interaction.response.send_message(
            f"✅ Cart {self.cart_number} updated.",
            ephemeral=True
        )


class ShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="🛒 Cart 1", style=discord.ButtonStyle.primary)
    async def cart1(self, interaction, button):
        await interaction.response.send_modal(CartModal(self.user_id, 1))

    @discord.ui.button(label="🛒 Cart 2", style=discord.ButtonStyle.primary)
    async def cart2(self, interaction, button):
        await interaction.response.send_modal(CartModal(self.user_id, 2))

    @discord.ui.button(label="🛒 Cart 3", style=discord.ButtonStyle.primary)
    async def cart3(self, interaction, button):
        await interaction.response.send_modal(CartModal(self.user_id, 3))

    @discord.ui.button(label="🛒 Cart 4", style=discord.ButtonStyle.primary)
    async def cart4(self, interaction, button):
        await interaction.response.send_modal(CartModal(self.user_id, 4))

    @discord.ui.button(label="✅ Final Submit", style=discord.ButtonStyle.success)
    async def submit(self, interaction, button):
        cart = user_carts.get(self.user_id)

        if not cart:
            await interaction.response.send_message("❌ Cart is empty.", ephemeral=True)
            return

        total = 0
        text = ""

        for item, qty in cart.items():
            price = SHOP_ITEMS[item]
            total += price * qty
            text += f"• **{item}** × {qty} = ₹{price * qty:,}\n"

        embed = discord.Embed(
            title="🧾 FINAL ORDER",
            description=text,
            color=0x8B0000
        )
        embed.add_field(name="💰 Total", value=f"₹{total:,}")
        embed.add_field(name="👤 Buyer", value=interaction.user.mention)

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Order placed!", ephemeral=True)

        user_carts.pop(self.user_id, None)

# ======================
# SHOP MODAL
# ======================
class ShopModal(discord.ui.Modal, title="🕷️ Black Market Order"):
    def __init__(self):
        super().__init__()
        self.inputs = {}

        for item in list(SHOP_ITEMS.keys())[:5]:
            field = discord.ui.TextInput(
                label=item,
                placeholder="Enter quantity",
                required=False
            )
            self.add_item(field)
            self.inputs[item] = field

    async def on_submit(self, interaction: discord.Interaction):
        total = 0
        summary = ""

        for item, field in self.inputs.items():
            if field.value:
                qty = int(field.value)
                price = SHOP_ITEMS[item]
                total += qty * price
                summary += f"• **{item}** × {qty} = ₹{qty * price:,}\n"

        if not summary:
            await interaction.response.send_message(
                "❌ No items selected.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🧾 BLACK MARKET PURCHASE",
            description=summary,
            color=0x8B0000
        )

        embed.add_field(name="💰 Total", value=f"₹{total:,}", inline=False)
        embed.add_field(name="👤 Buyer", value=interaction.user.mention, inline=False)

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Order submitted.", ephemeral=True)

# ======================
# BUTTON VIEWS (PERSISTENT + MANAGEMENT ONLY)
# ======================
class WeedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Update Weed Stock",
        style=discord.ButtonStyle.green,
        custom_id="weed_update"
    )
    async def weed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            StockModal("Update Weed Stock", "weed")
        )

class MethView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Update Meth Stock",
        style=discord.ButtonStyle.blurple,
        custom_id="meth_update"
    )
    async def meth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            StockModal("Update Meth Stock", "meth")
        )

class DistributionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Log Distribution",
        style=discord.ButtonStyle.red,
        custom_id="distribution_update"
    )
    async def dist(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            StockModal("Log Distribution", "distribution")
        )

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    load_stock()
    load_bank()

    await bot.tree.sync(guild=discord.Object(id=1451761878089990257))

    # REGISTER PERSISTENT VIEWS
    bot.add_view(WeedView())
    bot.add_view(MethView())
    bot.add_view(DistributionView())

    print("✅ Bot online, commands & buttons ready")

# ======================
# WELCOME
# ======================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if channel:
        await channel.send(
            f"🕷️ **WELCOME TO THE SYNDICATE**\n\n"
            f"{member.mention}\n"
            f"Use `/setname Firstname Lastname` in **#{NAME_CHANGE_CHANNEL}**\n"
            f"⚠️ One-time only."
        )

# ======================
# /SETNAME (ONE TIME)
# ======================
@bot.tree.command(name="setname", guild=discord.Object(id=1451761878089990257))
@app_commands.describe(name="Firstname Lastname")
async def setname(interaction: discord.Interaction, name: str):

    if interaction.channel.name != NAME_CHANGE_CHANNEL:
        await interaction.response.send_message(
            f"❌ Use this command only in #{NAME_CHANGE_CHANNEL}",
            ephemeral=True
        )
        return

    name_locks = load_name_locks()
    uid = str(interaction.user.id)

    if uid in name_locks:
        await interaction.response.send_message(
            "❌ You already set your RP name.",
            ephemeral=True
        )
        return

    if len(name.split()) < 2:
        await interaction.response.send_message(
            "❌ Use: Firstname Lastname",
            ephemeral=True
        )
        return

    await interaction.user.edit(nick=name.title())
    name_locks[uid] = True
    save_name_locks(name_locks)

    await interaction.response.send_message(
        "✅ RP name set successfully.",
        ephemeral=True
    )

# ======================
# MANAGEMENT COMMANDS (HIDDEN)
# ======================
@bot.tree.command(name="resetname", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_only)
async def resetname(interaction: discord.Interaction, member: discord.Member):

    name_locks = load_name_locks()
    uid = str(member.id)

    if uid not in name_locks:
        await interaction.response.send_message(
            "❌ This member has no locked name.",
            ephemeral=True
        )
        return

    del name_locks[uid]
    save_name_locks(name_locks)
    await member.edit(nick=None)

    await interaction.response.send_message(
        f"✅ {member.mention} can set name again.",
        ephemeral=True
    )

# ======================
# STOCK PANEL SETUP (MANAGEMENT ONLY)
# ======================
@bot.tree.command(name="setup_weed", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_only)
async def setup_weed(interaction: discord.Interaction):
    await interaction.channel.send(
        f"🌿 **WEED STOCK**\n\nCurrent Stock: **{weed_stock} g**",
        view=WeedView()
    )
    await interaction.response.send_message("✅ Weed panel created", ephemeral=True)

@bot.tree.command(name="setup_meth", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_only)
async def setup_meth(interaction: discord.Interaction):
    await interaction.channel.send(
        f"🧪 **METH STOCK**\n\nCurrent Stock: **{meth_stock} g**",
        view=MethView()
    )
    await interaction.response.send_message("✅ Meth panel created", ephemeral=True)

@bot.tree.command(name="setup_distribution", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_only)
async def setup_distribution(interaction: discord.Interaction):
    await interaction.channel.send(
        f"🚚 **DISTRIBUTION LOG**\n\nTotal Distributed: **{distributed_total} g**",
        view=DistributionView()
    )
    await interaction.response.send_message("✅ Distribution panel created", ephemeral=True)

# ======================
# BANK COMMANDS (MANAGEMENT ONLY)
# ======================
@bot.tree.command(name="deposit", description="Deposit black money", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_or_banker)
async def deposit(interaction: discord.Interaction, amount: int, reason: str):
    global black_balance

    bank = discord.utils.get(interaction.guild.text_channels, name=BANK_CHANNEL_NAME)
    ledger = discord.utils.get(interaction.guild.text_channels, name=LEDGER_CHANNEL_NAME)

    if not bank or not ledger:
        await interaction.response.send_message(
            "❌ Bank or ledger channel not found.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    await public_animation(bank)

    black_balance += amount
    save_bank()

    msg = (
        f"💰 **BLACK MONEY DEPOSIT**\n"
        f"👤 {interaction.user.mention}\n"
        f"➕ ₹{amount:,}\n"
        f"🧾 {reason}\n"
        f"🏦 **Balance: ₹{black_balance:,}**\n"
    )

    await bank.send(msg)

    await interaction.followup.send("✅ Deposit completed", ephemeral=True)


@bot.tree.command(name="withdraw", description="Withdraw black money", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_or_banker)
async def withdraw(interaction: discord.Interaction, amount: int, reason: str):
    global black_balance

    if amount > black_balance:
        await interaction.response.send_message(
            "❌ Insufficient funds.",
            ephemeral=True
        )
        return

    bank = discord.utils.get(interaction.guild.text_channels, name=BANK_CHANNEL_NAME)
    ledger = discord.utils.get(interaction.guild.text_channels, name=LEDGER_CHANNEL_NAME)

    if not bank or not ledger:
        await interaction.response.send_message(
            "❌ Bank or ledger channel not found.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    await public_animation(bank)

    black_balance -= amount
    save_bank()

    msg = (
        f"🚨 **BLACK MONEY WITHDRAWAL**\n"
        f"👤 {interaction.user.mention}\n"
        f"➖ ₹{amount:,}\n"
        f"⚠️ {reason}\n"
        f"🏦 **Balance: ₹{black_balance:,}**"
    )

    await bank.send(msg)
    await ledger.send(msg)

    await interaction.followup.send("✅ Withdrawal completed", ephemeral=True)


@bot.tree.command(name="balance", description="Check black money balance", guild=discord.Object(id=1451761878089990257))
@app_commands.check(management_or_banker)
async def balance(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏦 **Current Black Balance:** ₹{black_balance:,}",
        ephemeral=True
    )
# ======================
# SHOP COMMAND
# ======================
@bot.tree.command(
    name="shop",
    description="Open the black market",
    guild=discord.Object(id=1451761878089990257)
)
async def shop(interaction: discord.Interaction):

    if not any(role.name == "Syndicate Member" for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Only Syndicate Members can use this.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🛒 **Black Market**\nChoose a cart:",
        view=ShopView(interaction.user.id),
        ephemeral=True
    )

# ======================
# RUN
# ======================
bot.run(TOKEN)
