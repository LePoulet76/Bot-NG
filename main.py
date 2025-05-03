# -*- coding: utf-8 -*-
import os
import csv
import re
import discord
from discord import Embed
from discord.ext import commands, tasks
from playwright.async_api import async_playwright
from datetime import datetime

TOKEN = "MTM2NDYwNzEwNzI5NDI5ODIyMw.GZNeS0.r_8x-tE4Q18e2rcyw2RxjGZi7-q5NQHuhLMc3Y"
CHANNEL_ID = 1364642147499774053
LOG_FILE = "historique_pourcentages.csv"
LAST_POURCENTAGE_FILE = "dernier_pourcentage.txt"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def read_last_pourcentage():
    if os.path.exists(LAST_POURCENTAGE_FILE):
        with open(LAST_POURCENTAGE_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return None
    return None

def save_last_pourcentage(pourcentage):
    with open(LAST_POURCENTAGE_FILE, "w") as f:
        f.write(str(pourcentage))

def log_changement(old_value, new_value):
    write_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["Heure", "Ancien %", "Nouveau %"])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, old_value, new_value])

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} !")
    check_plaque_loop.start()

@bot.command()
async def plaque(ctx):
    await ctx.send("🧭 Recherche du pourcentage de pétrole sur la plaque Asie...")
    pourcentage, content = await get_plaque_pourcentage()
    if pourcentage is not None:
        await ctx.send(f"🛢️ Pétrole sur Asie : **{pourcentage}%**")
        if pourcentage >= 90:
            await ctx.send("🚨 La plaque est presque pleine, go go go !")
    else:
        await ctx.send("❌ Impossible de lire la plaque Asie.")

last_pourcentage = None

@tasks.loop(minutes=3)
async def check_plaque_loop():
    global last_pourcentage
    if last_pourcentage is None:
        last_pourcentage = read_last_pourcentage()

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Canal introuvable.")
        return

    pourcentage, content = await get_plaque_pourcentage()
    if pourcentage is not None:
        # S'il y a eu une augmentation
        if last_pourcentage is None or pourcentage > last_pourcentage:
            embed = Embed(
                title="🛢️ Mise à jour des plaques !",
                description=f"Il est temps d'aller pomper sur Edora !",
                color=0xFFA500  # orange pétrole
            )

            embed.set_footer(text="NationsGlory - Serveur Orange")
            embed.set_thumbnail(url="https://img.freepik.com/premium-vector/gas-cylinder-icon_734906-392.jpg?w=740")  # une icône pétrolière par exemple
            embed.set_author(name="NGlouGlou", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            await channel.send(content="<@&1364725817648615504>", embed=embed)
        # Mets à jour la valeur précédente
        if last_pourcentage is None or pourcentage > last_pourcentage:
            log_changement(last_pourcentage or 0, pourcentage)
        last_pourcentage = pourcentage
    else:
        print("❌ Aucune donnée lisible.")  

async def get_plaque_pourcentage():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://orange.nationsglory.fr", timeout=60000)
        await page.wait_for_timeout(8000)

        # Active proprement la couche "Ressources"
        try:
            checkbox = await page.locator("label:has-text('Ressources')").element_handle()
            if checkbox:
                await page.evaluate("(el) => el.click()", checkbox)
                await page.wait_for_timeout(3000)
                print("✅ Couche Ressources activée.")
        except Exception as e:
            print("❌ Erreur activation Ressources :", e)

        # Clique exactement à l'endroit déjà validé
        await page.mouse.click(900, 100)
        print("🖱️ Clic sur la carte effectué.") 
        await page.wait_for_timeout(2000)
        

        # Lis le popup directement
        popup = page.locator(".leaflet-popup-content")
        try:
            await popup.wait_for(timeout=10000)
            content = await popup.inner_text()
            print("🧪 Popup détecté :\n", content)

            match = re.search(r"Pétrole\s*:\s*(\d+)%", content)
            if match:
                pourcentage = int(match.group(1))
                await browser.close()
                return pourcentage, content
            else:
                print("❌ Aucun pourcentage trouvé dans le popup.")
        except Exception as e:
            print(f"❌ Erreur popup : {e}")

        await browser.close()
        return None, None

bot.run(TOKEN)