# /api/index.py (Version 8 - Interactive Analyst Bot)

import os
import requests
import pandas as pd
import pandas_ta as ta
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Bot and API Setup ---
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# --- Analysis Logic (Copied from previous version, with minor changes) ---
def get_crypto_data(symbol, interval='1h', limit=300):
    # (This function is the same as before)
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception:
        return pd.DataFrame()

def get_full_analysis(symbol):
    """Performs the complete analysis and returns a formatted message string."""
    df_1h = get_crypto_data(symbol, interval='1h')
    df_1d = get_crypto_data(symbol, interval='1d')
    if df_1h.empty or df_1d.empty:
        return f"Could not retrieve complete market data for `{symbol}`. Please check the symbol and try again."

    # Pre-calculate all indicators
    df_1d.ta.sma(length=20, append=True)
    df_1h.ta.rsi(length=14, append=True)
    df_1h.ta.bbands(length=20, append=True)
    df_1h.ta.sma(close='volume', length=50, append=True, col_names=('volume_sma_50',))

    # --- Check for Breakout/Breakdown ---
    high_50 = df_1h['high'].rolling(50).max().iloc[-2]
    low_50 = df_1h['low'].rolling(50).min().iloc[-2]
    
    # Breakout (BUY)
    if df_1d['close'].iloc[-1] > df_1d['SMA_20'].iloc[-1] and df_1h['close'].iloc[-1] > high_50 and df_1h['volume'].iloc[-1] > df_1h['volume_sma_50'].iloc[-1] * 1.5:
        return f"🚀 *Momentum Breakout Signal (BUY)*\n\n*Asset:* `{symbol}`\n\n*Analysis:*\n• Price broke 50-hour high of ${high_50:.2f}\n• Confirmed with high volume"
    
    # Breakdown (SELL)
    if df_1d['close'].iloc[-1] < df_1d['SMA_20'].iloc[-1] and df_1h['close'].iloc[-1] < low_50 and df_1h['volume'].iloc[-1] > df_1h['volume_sma_50'].iloc[-1] * 1.5:
        return f"💥 *Momentum Breakdown Signal (SELL)*\n\n*Asset:* `{symbol}`\n\n*Analysis:*\n• Price broke 50-hour low of ${low_50:.2f}\n• Confirmed with high volume"

    # --- If no breakout, check for overbought/oversold ---
    rsi_val = df_1h['RSI_14'].iloc[-1]
    
    # Oversold (BUY)
    if rsi_val < 30:
        return f"📉 *Contrarian Signal (BUY)*\n\n*Asset:* `{symbol}`\n\n*Analysis:*\n• Hourly RSI is oversold at *{rsi_val:.2f}*."
    
    # Overbought (SELL)
    if rsi_val > 70:
        return f"📈 *Overbought Warning (SELL)*\n\n*Asset:* `{symbol}`\n\n*Analysis:*\n• Hourly RSI is overbought at *{rsi_val:.2f}*."

    return f"⚪️ *Neutral Signal*\n\n*Asset:* `{symbol}`\n\n*Analysis:*\nNo strong buy or sell signals found at this time. RSI is {rsi_val:.2f}."

# --- Telegram Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    welcome_text = (
        "Hello! I am your On-Demand Crypto Analyst Bot.\n\n"
        "To get an analysis, use the `/analyze` command followed by a symbol.\n\n"
        "*Example:* `/analyze BTCUSDT`"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /analyze command."""
    try:
        symbol = context.args[0].upper()
        chat_id = update.message.chat_id
        
        # Acknowledge the command immediately
        await bot.send_message(chat_id=chat_id, text=f"Analyzing `{symbol}`... Please wait.", parse_mode='Markdown')
        
        # Run the blocking analysis function in a separate thread
        analysis_result = await asyncio.to_thread(get_full_analysis, symbol)
        
        # Send the final result
        await bot.send_message(chat_id=chat_id, text=analysis_result, parse_mode='Markdown')

    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a symbol.\n*Example:* `/analyze BTCUSDT`", parse_mode='Markdown')

# --- Vercel Webhook Setup ---

@app.post("/api/webhook")
async def webhook(request: Request):
    """This endpoint receives updates from Telegram."""
    data = await request.json()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('analyze', analyze_command))

    async with application:
        await application.process_update(Update.de_json(data, application.bot))
    
    return {"status": "ok"}

@app.get("/")
def home():
    return "Bot is alive."