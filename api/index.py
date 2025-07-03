# api/index.py (Version 9 - DUMMY TEST)

import os
import json
from fastapi import FastAPI, Request
from telegram import Bot

# --- Bot and API Setup ---
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# --- Vercel Webhook - SIMPLIFIED FOR TESTING ---
@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """
    This is a super simple webhook to see if we receive anything from Telegram.
    """
    print("--- WEBHOOK RECEIVED! ---") # If we see this in the logs, the connection is working.
    
    try:
        data = await request.json()
        chat_id = data['message']['chat']['id']
        text = data['message']['text']
        
        print(f"Message from chat_id {chat_id}: {text}")
        
        # We will just send a simple, hardcoded reply for this test
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Test successful! The connection is working. I will now be upgraded."
        )
    except Exception as e:
        print(f"ERROR processing webhook: {e}")
        # Even if there's an error, we know the webhook was hit.

    return {"status": "ok"}


@app.get("/")
def home():
    return "Bot is alive and ready for the final test."