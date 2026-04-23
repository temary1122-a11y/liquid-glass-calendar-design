---
description: Project context for Telegram Booking Bot
trigger: model_decision
---

# PROJECT CONTEXT — Telegram Booking Bot

## ARCHITECTURE
- **Frontend:** React + Vite + TailwindCSS, deployed to GitHub Pages
- **Backend:** FastAPI + PostgreSQL (Supabase), deployed to Render
- **Bot:** Python Telegram Bot with webhook
- **Real-time:** WebSocket for live updates

## DEPLOYMENT
- **Frontend URL:** https://temary1122-a11y.github.io/liquid-glass-calendar-design/
- **Backend:** Render deployment
- **Database:** PostgreSQL (Supabase) - persistent, data NOT lost on deploy
- **Deploy workflow:** GitHub Actions for frontend, auto-deploy for backend

## KEY ENDPOINTS
- **POST /api/booking/book** — create new booking
- **POST /api/admin/update-client** — admin updates booking status
- **GET /api/booking/available-dates** — get available slots
- **WebSocket /ws** — real-time updates for admin panel

## ADMIN CONFIRMATION FLOW
1. Client creates booking with username (from Telegram or manual input)
2. Admin confirms booking status to "confirmed"
3. Backend returns `open_chat` data with username and prefilled message
4. Frontend opens Telegram chat with client using `Telegram.WebApp.openTelegramLink`

## IMPORTANT URLS
- **Frontend:** https://temary1122-a11y.github.io/liquid-glass-calendar-design/
- **Admin video:** https://t.me/lashessoto4ka/8
- **Prices:** https://t.me/lashessoto4ka/185
- **Admin username:** lashessoto4ka

## CODE STRUCTURE
- **src/components/** — React components (BookingForm, SelectedDayPanel, etc.)
- **src/api/client.ts** — API client for backend communication
- **src/config.ts** — Configuration (API URLs, templates, admin ID)
- **backend/api/routes/** — FastAPI routes (booking.py, admin.py)
- **backend/database/db.py** — SQLAlchemy models (Booking, TimeSlot, WorkDay)
- **backend/bot/handlers/** — Telegram bot handlers

## RECENT CHANGES
- Added username field to booking form for browser testing
- Added username validation (5-32 chars, letters/numbers/underscores only)
- Fixed admin confirmation chat opening with username instead of user_id
