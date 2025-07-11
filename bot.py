import discord
from discord.ext import tasks, commands
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

TOKEN = "MTM5MzMwMDg4MDEwMjc4OTMxMQ.G182zw.bDk5HF6j8FIVFfOmrOSUSVVnWRRxc6kIvKTQ7o"
CHANNEL_ID = 1354342058755756083
CHECK_INTERVAL_MINUTES = 1

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

posted_file = "posted.json"
keywords_file = "keywords.json"

if not os.path.exists(posted_file) or os.path.getsize(posted_file) == 0:
    with open(posted_file, "w") as f:
        json.dump([], f)

if not os.path.exists(keywords_file) or os.path.getsize(keywords_file) == 0:
    with open(keywords_file, "w") as f:
        json.dump({}, f)

def extract_deal_details(link):
    try:
        response = requests.get(link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find("meta", property="og:title")
        image_tag = soup.find("meta", property="og:image")

        title = title_tag["content"] if title_tag else "Untitled"
        image = image_tag["content"] if image_tag else None

        price_text = ""
        possible_price = soup.find_all(string=lambda text: "$" in text if text else False)
        for text in possible_price:
            if "$" in text and len(text.strip()) < 20:
                price_text = text.strip()
                break

        return title, image, price_text
    except Exception as e:
        print(f"❌ Error scraping {link}: {e}")
        return "Untitled", None, ""

def load_keywords():
    with open(keywords_file, "r") as f:
        return json.load(f)

def save_keywords(data):
    with open(keywords_file, "w") as f:
        json.dump(data, f)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    post_deals.start()

@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def post_deals():
    print(f"🔁 Checking for new deals... ({datetime.now().strftime('%H:%M:%S')})")
    feed = feedparser.parse("https://slickdeals.net/newsearch.php?searcharea=deals&rss=1")

    with open(posted_file, "r") as f:
        posted = json.load(f)

    new_entries = [entry for entry in feed.entries if entry.link not in posted]

    if not new_entries:
        return

    channel = bot.get_channel(CHANNEL_ID)
    keywords = load_keywords()

    for entry in new_entries[:5]:
        title_scraped, image_url, price = extract_deal_details(entry.link)
        embed = discord.Embed(
            title=title_scraped,
            url=entry.link,
            description=f"**{price}**" if price else "",
            color=discord.Color.blue()
        )
        if image_url:
            embed.set_thumbnail(url=image_url)

        await channel.send(embed=embed)
        posted.append(entry.link)

        rss_title = entry.title
        combined_text = f"{rss_title} {title_scraped}".lower()

        for user_id, tracked_keywords in keywords.items():
            for keyword in tracked_keywords:
                keyword_parts = keyword.lower().split()
                if all(part in combined_text for part in keyword_parts):
                    try:
                        user = await bot.fetch_user(int(user_id))
                        await user.send(f"🔔 Matched keyword **{keyword}**:", embed=embed)
                    except:
                        print(f"❌ Could not DM user {user_id}")

    with open(posted_file, "w") as f:
        json.dump(posted[-200:], f)

@bot.command()
async def deals(ctx):
    await post_deals()

@bot.command()
async def track(ctx, *, keyword):
    keyword = keyword.lower()
    keywords = load_keywords()
    uid = str(ctx.author.id)

    if uid not in keywords:
        keywords[uid] = []

    if keyword in keywords[uid]:
        await ctx.send("❗ You’re already tracking that.")
    else:
        keywords[uid].append(keyword)
        save_keywords(keywords)
        await ctx.send(f"✅ Now tracking: `{keyword}`")

@bot.command()
async def untrack(ctx, *, keyword):
    keyword = keyword.lower()
    keywords = load_keywords()
    uid = str(ctx.author.id)

    if uid in keywords and keyword in keywords[uid]:
        keywords[uid].remove(keyword)
        save_keywords(keywords)
        await ctx.send(f"🗑️ Removed `{keyword}` from your alerts.")
    else:
        await ctx.send("That keyword wasn’t being tracked.")

@bot.command()
async def untrackall(ctx):
    keywords = load_keywords()
    uid = str(ctx.author.id)

    if uid in keywords and keywords[uid]:
        keywords[uid] = []
        save_keywords(keywords)
        await ctx.send("🗑️ All your tracked keywords have been removed.")
    else:
        await ctx.send("❌ You aren't tracking anything.")

@bot.command()
async def tracking(ctx):
    keywords = load_keywords()
    uid = str(ctx.author.id)

    if uid not in keywords or not keywords[uid]:
        await ctx.send("📭 You're not tracking anything.")
    else:
        await ctx.send(f"📦 You’re tracking: `{', '.join(keywords[uid])}`")

@bot.command()
async def testdm(ctx):
    embed = discord.Embed(
        title="🧪 Test Deal Alert",
        url="https://example.com/deal",
        description="This is a test deal sent via DM.\n\n*If you received this, your DM alerts are working!*",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2164/2164899.png")

    try:
        await ctx.author.send("✅ DM test successful!", embed=embed)
        await ctx.send("📩 Check your DMs!")
    except:
        await ctx.send("❌ I couldn't DM you. Make sure DMs are enabled.")

@bot.command()
async def fakedm(ctx):
    fake_title = "RTX 4090 Founders Edition Monitor Deal - $899"
    fake_link = "https://example.com"
    fake_price = "$899"
    keywords = load_keywords()

    embed = discord.Embed(
        title=fake_title,
        url=fake_link,
        description=f"**{fake_price}**",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2164/2164899.png")

    for user_id, tracked in keywords.items():
        for keyword in tracked:
            keyword_parts = keyword.lower().split()
            if all(part in fake_title.lower() for part in keyword_parts):
                user = await bot.fetch_user(int(user_id))
                await user.send(f"🔔 Matched keyword **{keyword}**:", embed=embed)

    await ctx.send("✅ Simulated deal sent to matched users.")

bot.run(TOKEN)
