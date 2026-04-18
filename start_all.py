#!/usr/bin/env python3
import asyncio
import threading
import uvicorn
from bot import bot

def run_api():
    """Запускает API сервер"""
    uvicorn.run('api.app:app', host='0.0.0.0', port=10000)

def run_bot():
    """Запускает Telegram бота"""
    asyncio.run(bot.start_polling())

if __name__ == '__main__':
    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # Запускаем бота в главном потоке
    run_bot()
