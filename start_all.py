#!/usr/bin/env python3
import asyncio
import uvicorn
from bot import main
import threading
import time

def run_api():
    """Запускает API сервер"""
    uvicorn.run('api.app:app', host='0.0.0.0', port=10000, log_level='info')

if __name__ == '__main__':
    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Даем время API запуститься
    time.sleep(2)

    # Запускаем бота в главном потоке
    asyncio.run(main())
