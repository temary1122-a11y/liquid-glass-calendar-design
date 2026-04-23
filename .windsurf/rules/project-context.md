---
description: Project context and architecture for Telegram booking bot
trigger: model_decision
---

# PROJECT CONTEXT — Telegram Booking Bot

## ARCHITECTURE
- **Frontend:** React + Vite, deployed to GitHub Pages
- **Backend:** FastAPI + PostgreSQL (Supabase), deployed to Render
- **Bot:** Python Telegram Bot with webhook
- **Real-time:** WebSocket for live updates

## CRITICAL RULES — NEVER VIOLATE
1. NEVER divide fees or slippage by leverage
2. NEVER change calc_vol_brush() without explicit approval
3. NEVER add new files without checking imports
4. ALWAYS read the FULL function before editing it
5. ALWAYS show diff before applying changes

## CODE STYLE
- Use log("TAG", ...) for all output, never bare print()
- Keep functions under 50 lines
- Add comments for non-obvious logic

## TESTING
- After ANY change to should_enter() — run test manually
- After ANY change to close_brush() — verify PnL math
- After ANY fee change — show example calculation

## FILE OWNERSHIP
- brush_bot_core.py: MAIN logic, careful edits only
- ai_filter.py: AI integration, ask before changing
- modules/self_tuner.py: parameters, DO NOT auto-tune
- modules/fee_model.py: READ ONLY unless explicitly asked

## DEPLOYMENT
- Frontend: GitHub Actions → GitHub Pages
- Backend: Render
- Database: PostgreSQL (Supabase) - persistent, data NOT lost on deploy

## KEY ENDPOINTS
- POST /api/booking/book — create booking
- POST /api/admin/update-client — admin confirmation
- WebSocket: /ws — real-time updates

## ADMIN CONFIRMATION FLOW
1. Client creates booking with username
2. Admin confirms booking → backend returns open_chat data
3. Frontend opens Telegram chat with client using username

## IMPORTANT URLS
- Frontend: https://temary1122-a11y.github.io/liquid-glass-calendar-design/
- Backend: Render deployment
- Admin video: https://t.me/lashessoto4ka/8
- Prices: https://t.me/lashessoto4ka/185
