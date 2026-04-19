# План автоматизации: Multi-Agent System

**Дата:** 2026-04-19  
**Статус:** Проектирование  
**Цель:** Автоматизация разработки с помощью AI агентов

---

## 🎯 Цели автоматизации

1. **Real-time синхронизация** между админ-панелью и клиентом
2. **Multi-agent system** с shared memory
3. **Автоматизация рутинных задач** разработки
4. **Минимизация ошибок** из-за потери контекста

---

## 📊 Часть 1: Real-time синхронизация

### Проблема
Сейчас: Админ обновляет запись → БД обновляется → ❌ Клиент НЕ видит → Перезагрузка

Нужно: Админ обновляет → БД обновляется → ✅ WebSocket уведомление → Клиент видит сразу

### Решение: WebSocket с FastAPI

#### Архитектура

```
Админ-панель (React)
    ↓ WebSocket
FastAPI Backend
    ↓ WebSocket
Клиентский Mini App (React)
```

#### Реализация

**Backend (FastAPI):**
```python
from fastapi import FastAPI, WebSocket
from typing import Dict, Set
import json

app = FastAPI()

# Хранилище активных подключений
active_connections: Dict[int, WebSocket] = {}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка сообщений от клиента
    finally:
        del active_connections[user_id]

# Функция отправки уведомления конкретному пользователю
async def notify_user(user_id: int, message: dict):
    if user_id in active_connections:
        await active_connections[user_id].send_json(message)

# Функция отправки broadcast всем
async def broadcast(message: dict):
    for connection in active_connections.values():
        await connection.send_json(message)
```

**Админ-панель (React):**
```typescript
const socket = new WebSocket(`ws://api.example.com/ws/${adminId}`);

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Обновление UI при изменениях
    if (data.type === 'booking_updated') {
        updateBooking(data.booking);
    }
};

// При обновлении записи
function updateBooking(booking: Booking) {
    fetch('/api/admin/update-client', {
        method: 'POST',
        body: JSON.stringify(booking)
    });
}
```

**Клиентский Mini App (React):**
```typescript
const socket = new WebSocket(`ws://api.example.com/ws/${userId}`);

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Обновление записи в реальном времени
    if (data.type === 'booking_updated') {
        setMyBooking(data.booking);
        showNotification('Запись обновлена администратором');
    }
};
```

#### Интеграция с существующим кодом

**В `api/routes/admin.py` после обновления записи:**
```python
@router.post("/update-client")
async def update_client_endpoint(...):
    # ... существующий код обновления ...
    
    # Добавляем отправку уведомления
    await notify_user(existing_booking["user_id"], {
        "type": "booking_updated",
        "booking": updated
    })
    
    return {"success": True, "message": "Клиент обновлен"}
```

#### Альтернатива: Server-Sent Events (SSE)

Если WebSocket слишком сложный:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

@app.get("/events/{user_id}")
async def events(user_id: int):
    async def event_generator():
        while True:
            # Ждем изменений в БД
            if await has_booking_changes(user_id):
                booking = await get_user_booking(user_id)
                yield f"data: {json.dumps({'booking': booking})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

#### Альтернатива: Polling (простейший)

```typescript
// Клиент опрашивает сервер каждые 5 секунд
setInterval(async () => {
    const booking = await fetch(`/api/booking/my-bookings/${userId}`);
    setMyBooking(booking);
}, 5000);
```

**Рекомендация:** Начать с polling (простейший), потом перейти на WebSocket.

---

## 🤖 Часть 2: Multi-Agent System с Shared Memory

### Архитектура

```
User (Architect)
    ↓
Orchestrator Agent
    ↓
├── Memory MCP (Shared Context)
├── Filesystem MCP (Code Access)
├── Frontend Dev Agent
├── Backend Dev Agent
├── Code Review Agent
└── Testing Agent
    ↓
Knowledge Graph (Relations)
```

### Компоненты

#### 1. Memory MCP (Shared Context)

**Назначение:** Хранить общий контекст для всех агентов

**Использование:**
```python
# Сохранение контекта проекта
await memory.create_entities([
    {
        "name": "Liquid Glass Calendar Design",
        "entityType": "project",
        "observations": [
            "Telegram bot for eyelash extensions booking",
            "Backend: Python 3.13 + aiogram + FastAPI",
            "Frontend: React 19 + TypeScript"
        ]
    }
])

# Создание связей
await memory.create_relations([
    {
        "from": "Liquid Glass Calendar Design",
        "to": "bot.py",
        "relationType": "contains"
    }
])

# Чтение контекста
context = await memory.search_nodes("Liquid Glass Calendar Design")
```

**Что хранить:**
- Структура проекта
- Технологический стек
- Архитектурные решения
- Known issues
- TODO задачи
- Code style guidelines

#### 2. Orchestrator Agent

**Назначение:** Управлять workflow и координировать агентов

**Функции:**
1. Разбивать задачи на подзадачи
2. Распределять задачи между агентами
3. Управлять порядком выполнения
4. Объединять результаты
5. Обрабатывать ошибки и retry

**Пример workflow:**
```
User: "Добавить real-time синхронизацию"

Orchestrator:
1. Прочитать контекст проекта из Memory MCP
2. Выбрать агентов: Backend Dev + Frontend Dev
3. Backend Dev: Реализовать WebSocket в FastAPI
4. Frontend Dev: Реализовать WebSocket в React
5. Code Review: Проверить код
6. Testing: Написать тесты
7. Объединить результаты и вернуть пользователю
```

#### 3. Специализированные агенты

**Frontend Dev Agent:**
- Роль: React/TypeScript разработка
- Модель: Groq Llama 70B (heavy_quality)
- Задачи: UI/UX, компоненты, интеграция с API

**Backend Dev Agent:**
- Роль: Python/FastAPI разработка
- Модель: Groq Llama 70B (heavy_quality)
- Задачи: API endpoints, бизнес-логика, БД

**Code Review Agent:**
- Роль: Code review и рефакторинг
- Модель: Groq DeepSeek (reasoning)
- Задачи: Проверка качества, безопасность, best practices

**Testing Agent:**
- Роль: Написание тестов
- Модель: Groq Llama 70B (heavy_quality)
- Задачи: Unit tests, integration tests, E2E

**Documentation Agent:**
- Роль: Документация
- Модель: Groq Llama 8B (ultra_fast)
- Задачи: README, API docs, comments

#### 4. Knowledge Graph

**Назначение:** Хранить связи между сущностями

**Пример:**
```
Liquid Glass Calendar Design
    ├── contains → bot.py
    ├── contains → api/
    ├── contains → src/
    ├── uses → aiogram
    ├── uses → FastAPI
    ├── uses → React
    └── has_issue → BOT_TOKEN duplication
```

### Реализация в MCP сервере

**Добавить orchestrator инструмент:**
```python
@server.call_tool()
async def orchestrate_task(
    task: str,
    agents: list[str],
    context: dict
) -> list[TextContent]:
    """Оркестрация задачи между агентами"""
    
    # 1. Прочитать контекст из Memory MCP
    project_context = await read_memory_context()
    
    # 2. Разбить задачу на подзадачи
    subtasks = await break_down_task(task, project_context)
    
    # 3. Распределить между агентами
    results = []
    for subtask, agent in zip(subtasks, agents):
        result = await call_agent(agent, subtask, context)
        results.append(result)
    
    # 4. Объединить результаты
    final_result = await combine_results(results)
    
    # 5. Сохранить в Memory MCP
    await save_to_memory(final_result)
    
    return [TextContent(type="text", text=str(final_result))]
```

### Минимизация ошибок из-за потери контекста

#### Проблема
AI агенты не имеют контекстной памяти между вызовами.

#### Решение

**1. Memory MCP как единое хранилище:**
- Все агенты читают/пишут в одно место
- Контекст всегда доступен
- Автоматическая синхронизация

**2. Knowledge Graph для связей:**
- Понимание зависимостей
- Отслеживание изменений
- Восстановление контекста

**3. Orchestrator для координации:**
- Управляет порядком выполнения
- Передает контекст между агентами
- Объединяет результаты

**4. Контекстные промпты:**
```python
async def call_agent(agent: str, task: str):
    # Читаем полный контекст проекта
    context = await read_memory_context("Liquid Glass Calendar Design")
    
    # Формируем промпт с контекстом
    prompt = f"""
    Project Context:
    {context}
    
    Task: {task}
    
    Use the project context to understand the codebase structure,
    tech stack, and existing patterns. Follow the established code style.
    """
    
    return await ask_by_role(agent, prompt)
```

**5. Validation и Verification:**
- Code Review Agent проверяет результаты
- Testing Agent пишет тесты
- Orchestrator валидирует финальный результат

---

## 🆓 Часть 3: Дополнительные бесплатные API

### Mistral AI (1B tokens/mo free)

**Роли:**
- Text Analysis Agent
- Documentation Generator
- Code Summarizer

**Интеграция:**
```python
import requests

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

async def call_mistral(prompt: str):
    response = await httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
        json={
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

### Google Gemini (permanent free)

**Роли:**
- Multilingual Agent
- Translation Agent
- Cultural Context Agent

**Интеграция:**
```python
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

async def call_gemini(prompt: str):
    model = genai.GenerativeModel('gemini-pro')
    response = await model.generate_content_async(prompt)
    return response.text
```

### OpenRouter (30+ free models)

**Роли:**
- Multi-model Agent (выбор лучшей модели)
- A/B Testing Agent
- Model Comparison Agent

**Интеграция:**
```python
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

async def call_openrouter(prompt: str, model: str):
    response = await httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://your-app.com"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

---

## 📋 Часть 4: План реализации

### Этап 1: Real-time синхронизация (Priority 1)

**Задачи:**
1. ✅ Проанализировать текущую архитектуру
2. ⏳ Выбрать технологию (WebSocket/SSE/Polling)
3. ⏳ Реализовать backend (FastAPI)
4. ⏳ Реализовать frontend (React)
5. ⏳ Тестировать синхронизацию
6. ⏳ Задеплоить

**Оценка:** 2-3 дня

### Этап 2: Memory MCP интеграция (Priority 2)

**Задачи:**
1. ✅ Создать структуру контекста проекта
2. ⏳ Наполнить Memory MCP данными
3. ⏳ Создать Knowledge Graph
4. ⏳ Тестировать чтение/запись
5. ⏳ Документировать использование

**Оценка:** 1 день

### Этап 3: Orchestrator Agent (Priority 3)

**Задачи:**
1. ⏳ Спроектировать orchestrator workflow
2. ⏳ Реализовать в MCP сервере
3. ⏳ Добавить инструменты для координации
4. ⏳ Тестировать на простых задачах
5. ⏳ Оптимизировать

**Оценка:** 3-4 дня

### Этап 4: Специализированные агенты (Priority 4)

**Задачи:**
1. ⏳ Определить роли агентов
2. ⏳ Реализовать каждого агента
3. ⏳ Интегрировать с orchestrator
4. ⏳ Тестировать workflow
5. ⏳ Оптимизировать промпты

**Оценка:** 5-7 дней

### Этап 5: Дополнительные API (Priority 5)

**Задачи:**
1. ⏳ Получить API ключи
2. ⏳ Интегрировать Mistral AI
3. ⏳ Интегрировать Google Gemini
4. ⏳ Интегрировать OpenRouter
5. ⏳ Добавить новые роли
6. ⏳ Тестировать

**Оценка:** 2-3 дня

---

## 🎯 Итоговая архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    User (Architect)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Agent (MCP)                    │
│  - Разбивает задачи                                      │
│  - Координирует агентов                                  │
│  - Управляет контекстом                                  │
└──────┬────────────────────────────────────────┬─────────┘
       │                                        │
       ↓                                        ↓
┌──────────────────┐                  ┌──────────────────┐
│  Memory MCP      │                  │ Filesystem MCP   │
│  - Project ctx    │                  │  - Read files    │
│  - Knowledge G   │                  │  - Write code    │
└──────────────────┘                  └──────────────────┘
       │                                        │
       ↓                                        ↓
┌─────────────────────────────────────────────────────────┐
│                   Specialized Agents                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Frontend Dev │  │ Backend Dev  │  │ Code Review  │  │
│  │ (Groq 70B)   │  │ (Groq 70B)   │  │ (DeepSeek)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Testing      │  │ Documentation│  │ Multilingual  │  │
│  │ (Groq 70B)   │  │ (Mistral)    │  │ (Gemini)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 API ключи для получения

Для полной автоматизации нужны:

1. ✅ GROQ_API_KEY (уже есть)
2. ✅ GROQ_API_KEY_2 (уже есть)
3. ✅ CEREBRAS_API_KEY (уже есть)
4. ⏳ MISTRAL_API_KEY (https://console.mistral.ai/)
5. ⏳ GEMINI_API_KEY (https://makersuite.google.com/app/apikey)
6. ⏳ OPENROUTER_API_KEY (https://openrouter.ai/keys)

---

**Создано:** 2026-04-19  
**Статус:** Проектирование  
**Следующий шаг:** Реализация real-time синхронизации
