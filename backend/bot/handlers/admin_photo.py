"""
Admin photo handler — change Mini App background image.
Admin sends a photo → bot analyzes dimensions/size/resolution → saves as new background.

Usage:
  /setbg — shows help
  Send any photo — becomes the new Mini App background
"""

import json
import logging
import os
from datetime import datetime
from io import BytesIO

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from PIL import Image

from config import ADMIN_ID_INT

logger = logging.getLogger(__name__)

router = Router()

# Paths — resolve relative to backend/ directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(_BACKEND_DIR, "static")
BG_FILE = "background.jpg"
META_FILE = "background_meta.json"


def _ensure_static_dir() -> None:
    os.makedirs(STATIC_DIR, exist_ok=True)


# ── /setbg command ──────────────────────────────────────

@router.message(Command("setbg"), F.from_user.id == ADMIN_ID_INT)
async def cmd_setbg(message: types.Message) -> None:
    """Explain how to set the background."""
    await message.answer(
        "🖼 <b>Смена фона Mini App</b>\n\n"
        "Просто отправьте мне фотографию — она станет новым фоном в Mini App.\n\n"
        "📱 <i>Рекомендуется вертикальное фото (9:16) в хорошем разрешении.</i>\n"
        "📏 <i>Минимум: 750×1334px. Оптимально: 1080×1920px.</i>\n"
        "📦 <i>Telegram сжимает фото — для максимального качества отправьте как файл (без сжатия).</i>\n\n"
        "🔄 <b>/resetbg</b> — вернуть дефолтный фон из репозитория.",
        parse_mode="HTML",
    )


@router.message(Command("setbg"))
async def cmd_setbg_denied(message: types.Message) -> None:
    pass  # Silent ignore for non-admins


# ── /resetbg command ────────────────────────────────────

@router.message(Command("resetbg"), F.from_user.id == ADMIN_ID_INT)
async def cmd_resetbg(message: types.Message) -> None:
    """Remove custom background, restore default."""
    _ensure_static_dir()
    removed = False

    for fname in (BG_FILE, META_FILE):
        fpath = os.path.join(STATIC_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            removed = True

    if removed:
        await message.answer(
            "🔄 <b>Фон сброшен!</b>\n\n"
            "Mini App снова использует дефолтный фон из репозитория.\n"
            "<i>Изменения применятся при следующем открытии.</i>",
            parse_mode="HTML",
        )
        logger.info("Background reset to default")
    else:
        await message.answer(
            "ℹ️ Кастомный фон не установлен — и так используется дефолтный.",
        )


@router.message(Command("resetbg"))
async def cmd_resetbg_denied(message: types.Message) -> None:
    pass


# ── Photo handler ───────────────────────────────────────

def _analyze_image(bio: BytesIO) -> dict:
    """Analyze image: dimensions, size, DPI, mode, orientation."""
    img = Image.open(bio)
    width, height = img.size
    file_size_kb = bio.getbuffer().nbytes / 1024
    dpi = img.info.get("dpi", (72, 72))
    mode = img.mode

    # Aspect ratio
    ratio = width / height if height > 0 else 1
    if ratio > 0.95:
        orientation = "квадратное"
    elif ratio > 0.7:
        orientation = "горизонтальное"
    else:
        orientation = "вертикальное 📱"

    # Quality check
    issues = []
    if width < 750:
        issues.append("⚠️ Ширина меньше 750px — на больших экранах будет размыто")
    if height < 1000:
        issues.append("⚠️ Высота меньше 1000px — на больших экранах будет размыто")
    if file_size_kb > 5000:
        issues.append("⚠️ Файл больше 5 MB — может долго загружаться у клиентов")

    return {
        "width": width,
        "height": height,
        "file_size_kb": round(file_size_kb, 1),
        "dpi": dpi,
        "mode": mode,
        "orientation": orientation,
        "issues": issues,
        "aspect_ratio": f"{width}:{height}",
    }


@router.message(F.photo, F.from_user.id == ADMIN_ID_INT)
async def handle_admin_photo(message: types.Message, bot: Bot) -> None:
    """Admin sent a photo — save as Mini App background."""
    status_msg = await message.reply("🖼 <b>Обрабатываю фото...</b>", parse_mode="HTML")

    try:
        # Get the highest resolution version (last in array)
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)

        # Download to memory
        bio = BytesIO()
        await bot.download_file(file_info.file_path, bio)
        bio.seek(0)

        # Analyze
        info = _analyze_image(bio)

        # Save as JPEG (optimized)
        _ensure_static_dir()
        bg_path = os.path.join(STATIC_DIR, BG_FILE)
        bio.seek(0)
        img = Image.open(bio)
        img_rgb = img.convert("RGB")
        img_rgb.save(bg_path, "JPEG", quality=85, optimize=True)

        # Save metadata
        meta = {
            "width": info["width"],
            "height": info["height"],
            "file_size_kb": info["file_size_kb"],
            "dpi_x": info["dpi"][0],
            "dpi_y": info["dpi"][1],
            "mode": info["mode"],
            "orientation": info["orientation"],
            "updated_at": datetime.utcnow().isoformat(),
        }
        meta_path = os.path.join(STATIC_DIR, META_FILE)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Build response
        lines = [
            "✅ <b>Фон обновлён!</b>\n",
            f"📐 <b>Разрешение:</b> {info['width']}×{info['height']} px",
            f"📏 <b>Соотношение:</b> {info['aspect_ratio']} ({info['orientation']})",
            f"📦 <b>Размер:</b> {info['file_size_kb']:.0f} KB",
            f"🖨 <b>DPI:</b> {info['dpi'][0]:.0f}×{info['dpi'][1]:.0f}",
            f"🎨 <b>Глубина цвета:</b> {info['mode']}",
        ]
        if info["issues"]:
            lines.append(f"\n{chr(10).join(info['issues'])}")
        lines.append("\n<i>Фон обновится в Mini App при следующем открытии.</i>")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
        logger.info(
            "Background updated: %dx%d, %.1fKB, mode=%s",
            info["width"], info["height"], info["file_size_kb"], info["mode"],
        )

    except Exception as exc:
        logger.exception("Failed to process background photo: %s", exc)
        await status_msg.edit_text(
            f"❌ <b>Ошибка обработки фото:</b>\n<code>{exc}</code>",
            parse_mode="HTML",
        )


# ── Document (uncompressed) photo handler ───────────────

@router.message(F.document, F.from_user.id == ADMIN_ID_INT)
async def handle_admin_document(message: types.Message, bot: Bot) -> None:
    """Admin sent a document — check if it's an image, use as background."""
    doc = message.document
    if not doc or not doc.mime_type or not doc.mime_type.startswith("image/"):
        return  # Not an image — ignore

    status_msg = await message.reply("🖼 <b>Обрабатываю изображение...</b>", parse_mode="HTML")

    try:
        file_info = await bot.get_file(doc.file_id)

        bio = BytesIO()
        await bot.download_file(file_info.file_path, bio)
        bio.seek(0)

        info = _analyze_image(bio)

        _ensure_static_dir()
        bg_path = os.path.join(STATIC_DIR, BG_FILE)
        bio.seek(0)
        img = Image.open(bio)
        img_rgb = img.convert("RGB")
        img_rgb.save(bg_path, "JPEG", quality=92, optimize=True)

        meta = {
            "width": info["width"],
            "height": info["height"],
            "file_size_kb": info["file_size_kb"],
            "dpi_x": info["dpi"][0],
            "dpi_y": info["dpi"][1],
            "mode": info["mode"],
            "orientation": info["orientation"],
            "source": "document",
            "updated_at": datetime.utcnow().isoformat(),
        }
        meta_path = os.path.join(STATIC_DIR, META_FILE)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        lines = [
            "✅ <b>Фон обновлён (без сжатия Telegram)!</b>\n",
            f"📐 <b>Разрешение:</b> {info['width']}×{info['height']} px",
            f"📏 <b>Соотношение:</b> {info['aspect_ratio']} ({info['orientation']})",
            f"📦 <b>Размер:</b> {info['file_size_kb']:.0f} KB",
            f"🖨 <b>DPI:</b> {info['dpi'][0]:.0f}×{info['dpi'][1]:.0f}",
            f"🎨 <b>Глубина цвета:</b> {info['mode']}",
        ]
        if info["issues"]:
            lines.append(f"\n{chr(10).join(info['issues'])}")
        lines.append("\n<i>Фон обновится в Mini App при следующем открытии.</i>")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
        logger.info(
            "Background updated (document): %dx%d, %.1fKB",
            info["width"], info["height"], info["file_size_kb"],
        )

    except Exception as exc:
        logger.exception("Failed to process background document: %s", exc)
        await status_msg.edit_text(
            f"❌ <b>Ошибка обработки:</b>\n<code>{exc}</code>",
            parse_mode="HTML",
        )


@router.message(F.photo)
async def handle_photo_denied(message: types.Message) -> None:
    pass  # Silent ignore for non-admin photos


@router.message(F.document)
async def handle_document_denied(message: types.Message) -> None:
    pass  # Silent ignore for non-admin documents (other handlers may catch)
