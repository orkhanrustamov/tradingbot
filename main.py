import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- STRATEGY LOGIC ---
def get_signals(ticker, timeframe="1h"):
    # 1. Download Data
    df = yf.download(ticker, period="5d", interval=timeframe)
    if df.empty or len(df) < 144: return None
    
    # 2. SMC Logic: Find Order Blocks (High Volatility Bars)
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=200)
    # Volatility Bar = Range >= 2 * ATR [cite: 72]
    df['is_ob'] = (df['High'] - df['Low']) >= (2 * df['atr'])
    
    # 3. Auto Fib Logic: 144 Length [cite: 155]
    high_h = df['High'].rolling(window=144).max().iloc[-1]
    low_l = df['Low'].rolling(window=144).min().iloc[-1]
    fib_786 = high_h - ((high_h - low_l) * 0.786)
    
    current_price = df['Close'].iloc[-1]
    
    # 4. Signal Condition: Price at Top Fib + Near Bearish OB [cite: 13, 158]
    if current_price >= fib_786 and any(df['is_ob'].tail(10)):
        return "⚠️ SELL SIGNAL: Price in Premium Fib zone + Order Block detected."
    return None

# --- BOT COMMANDS ---
watchlist = []

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper()
    watchlist.append(ticker)
    await update.message.reply_text(f"Added {ticker} to watchlist.")

async def check_all(context: ContextTypes.DEFAULT_TYPE):
    for ticker in watchlist:
        msg = get_signals(ticker)
        if msg:
            await context.bot.send_message(chat_id=context.job.chat_id, text=f"{ticker}: {msg}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Set the monitor to run every 15 minutes
    context.job_queue.run_repeating(check_all, interval=900, first=10, chat_id=update.effective_chat.id)
    await update.message.reply_text("Monitoring started! Use /add TICKER to add stocks.")

if __name__ == '__main__':
    # We use an Environment Variable for safety
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    
    app.run_polling()