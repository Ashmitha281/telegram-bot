import json
import os
import re
import asyncio
import nest_asyncio
from urllib.parse import urlparse, urlunparse
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from telegram.error import NetworkError, TelegramError

# Apply fix for event loop issues
nest_asyncio.apply()

# JSON file to store taken customer links
DATA_FILE = "my_customers.json"

# Load previous data if available
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        try:
            taken_customers = json.load(f)
        except json.JSONDecodeError:
            taken_customers = {}
else:
    taken_customers = {}

# Clean query strings or fragments from URL
def clean_link(url):
    parsed = urlparse(url)
    cleaned = parsed._replace(query='', fragment='')
    return urlunparse(cleaned)

# Extract profile link from supported platforms
def extract_profile_link(text):
    patterns = [
        r'(https?://(?:www\.)?facebook\.com/[^\s/]+/?(?:[^\s]*)?)',
        r'(https?://(?:www\.)?sharechat\.com/[^\s/]+/?(?:[^\s]*)?)',
        r'(https?://(?:www\.)?shaadi\.com/[^\s/]+/?(?:[^\s]*)?)',
        r'(https?://(?:www\.)?snapchat\.com/add/[^\s/]+/?(?:[^\s]*)?)',
        r'(https?://(?:www\.)?instagram\.com/[^\s/]+/?(?:[^\s]*)?)',
        r'(https?://(?:www\.)?twitter\.com/[^\s/]+/?(?:[^\s]*)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_link(match.group(1).strip())
    return None

# Save data to file with flush and backup
def save_data():
    backup_file = DATA_FILE + ".bak"
    try:
        if os.path.exists(DATA_FILE):
            os.replace(DATA_FILE, backup_file)

        with open(DATA_FILE, "w") as f:
            json.dump(taken_customers, f)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"❌ Error saving data: {e}")

# Handle each message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    username = message.from_user.username or message.from_user.first_name
    profile_link = extract_profile_link(text)

    if not profile_link:
        return

    if profile_link in taken_customers:
        claimed_by = taken_customers[profile_link]
        await message.reply_text(
            f"⚠️ @{username}, Do not contact this customer. Already taken by @{claimed_by}."
        )
    else:
        taken_customers[profile_link] = username
        save_data()
        await message.reply_text(
            f"✅ @{username}, You can take this customer. Fixed for you. KEEP FIGHTING !! FUCK HIM SOON"
        )

# Command to show stats
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not taken_customers:
        await update.message.reply_text("No customers have been claimed yet.")
        return

    user_counts = {}
    for user in taken_customers.values():
        user_counts[user] = user_counts.get(user, 0) + 1

    stats_lines = ["📊 Customer Claims Stats:"]
    for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True):
        stats_lines.append(f"@{user}: {count}")

    await update.message.reply_text("\n".join(stats_lines))

# Bot run loop with network retry
async def run_bot():
    TOKEN = "8134865007:AAFeVD9gN6GJJWBKUKLX9Kqv_6Pi27Kmh8k"

    while True:
        try:
            print("🚀 Starting bot...")
            app = ApplicationBuilder().token(TOKEN).build()
            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
            app.add_handler(CommandHandler("stats", stats_command))

            await app.run_polling()

        except NetworkError as ne:
            print(f"🌐 Network error: {ne}. Retrying in 10 seconds...")
            await asyncio.sleep(10)
        except TelegramError as te:
            print(f"⚠️ Telegram API error: {te}. Retrying in 15 seconds...")
            await asyncio.sleep(15)
        except Exception as e:
            print(f"❌ Unexpected error: {e}. Retrying in 20 seconds...")
            await asyncio.sleep(20)

# Start everything
if __name__ == "__main__":
    asyncio.run(run_bot())
