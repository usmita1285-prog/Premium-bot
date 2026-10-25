
import os
import re
import io
import time
import threading
from urllib.parse import urlparse

import requests
import telebot
import instaloader
from telebot import types


# =========================================================
# HYPER X | INSTAGRAM REEL DOWNLOADER
# SYMBOL ONLY | BLUE / PINK THEME
# =========================================================

BOT_TOKEN = os.getenv("8875210307:AAFMDSTHkD8JWsZpH8qTNcHOWWJqcdmLVPk", "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN missing. Set it in your hosting environment."
    )

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- LINKS ----------

CHANNEL_URL = "https://t.me/your_channel"
OWNER_URL = "https://t.me/your_username"

# ---------- SYMBOL COLLECTION: NO EMOJI ----------

ALL_SYMBOLS = (
    "✓ × ! → • ▸ ◆ ★ ✦ ↲ ▶ ⊕ ⊖ ◉ ○ "
    "━━━━━━━━━━━━━━━━━━━━━━━━━━ "
    "══════════════════════════ "
    "┈┈┈┈┈┈┈┈┈┈┈┈ "
    "■ □ ▣ ▢ ◈ ❖ ◇ ◎ ♔ ⌬ ✶ ✿ "
    "▪ ▲ ▤ ▫ ▴ ▾ ⌁ ⌗ ⌘ ⌖ ⌑ ⌕ "
    "⟡ ⟢ ⟣ ⟠ ⟐ ⟊ ⟟ ⟒ ⟓ ⟔ ⟕ ⟖ "
    "⇧ ⇩ ⇦ ⇨ ↻ ↺ ⟳ ⌁ ⌂ ⌐ ⌑ ⌔ "
    "ϟ ⌘ ⌬ ⊞ ⊟ ⊠ ⊡ ⊙ ⊚ ⊛ ⊜"
)

BUTTON_SYMBOLS = "◆ ✦ ✓ ◈"

# ---------- BLUE / PINK TEXT FRAMES ----------
# Telegram chat background colors cannot be forced by a bot.
# These borders provide a consistent premium box-style look.

TOP_BORDER = "◆━━━━━━━━━━━━━━━━━━━━━━━━━━◆"
BOTTOM_BORDER = "◇━━━━━━━━━━━━━━━━━━━━━━━━━━◇"


def ce(key):
    """Return a symbol only. Never return emoji."""
    symbols = {
        "film": "▣",
        "bolt": "ϟ",
        "check": "✓",
        "cross": "×",
        "hourglass": "◷",
        "download": "⇩",
        "upload": "⇧",
        "diamond": "◇",
        "rocket": "➤",
        "sparkle": "✧",
        "free": "○",
        "target": "◎",
        "bulb": "⌁",
        "pin": "⌖",
        "party": "✳",
        "search": "⌕",
        "sad": "⊖",
        "robot": "⌘",
    }
    return symbols.get(key, "◆")


def premium_text(content):
    """Full symbol frame for all bot messages."""
    return (
        f"<code>{TOP_BORDER}</code>\n"
        "<b>◆ HYPER X | REEL DOWNLOADER ◆</b>\n"
        f"<code>{ALL_SYMBOLS}</code>\n"
        f"<code>{TOP_BORDER}</code>\n\n"
        f"{content}\n\n"
        f"<code>{BOTTOM_BORDER}</code>\n"
        f"<code>{ALL_SYMBOLS}</code>\n"
        "<b>◇ BLUE / PINK PREMIUM THEME ◇</b>"
    )


# ---------- INLINE BUTTONS ----------

def btn(text, style=None, symbol=None, **kwargs):
    """
    Symbol-only buttons.
    Colors depend on Telegram Bot API/client support.
    """
    prefix = f"{BUTTON_SYMBOLS} "
    suffix = " ◇"

    max_label_length = 48
    available = max_label_length - len(prefix) - len(suffix)
    label = prefix + text[:available] + suffix

    options = {}

    if style:
        options["style"] = style

    try:
        return types.InlineKeyboardButton(
            label,
            **options,
            **kwargs
        )
    except (TypeError, ValueError):
        return types.InlineKeyboardButton(
            label,
            **kwargs
        )


def start_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.row(
        btn(
            "How To Use",
            style="primary",
            symbol="bulb",
            callback_data="howto"
        )
    )

    kb.row(
        btn(
            "Channel",
            style="success",
            symbol="rocket",
            url=CHANNEL_URL
        ),
        btn(
            "Owner",
            style="danger",
            symbol="diamond",
            url=OWNER_URL
        )
    )

    return kb


def done_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.row(
        btn(
            "Download Another",
            style="success",
            symbol="download",
            callback_data="again"
        )
    )

    kb.row(
        btn(
            "Channel",
            style="primary",
            symbol="rocket",
            url=CHANNEL_URL
        ),
        btn(
            "Owner",
            style="danger",
            symbol="diamond",
            url=OWNER_URL
        )
    )

    return kb


def error_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        btn(
            "Try Again",
            style="danger",
            symbol="bolt",
            callback_data="again"
        )
    )

    kb.row(
        btn(
            "How To Use",
            style="primary",
            symbol="bulb",
            callback_data="howto"
        )
    )

    return kb


# ---------- INSTALOADER ----------

L = instaloader.Instaloader(
    save_metadata=False,
    download_comments=False,
    post_metadata_txt_pattern="",
    quiet=True,
)

# ---------- CACHE ----------

CACHE = {}
CACHE_LIMIT = 20
MAX_VIDEO_BYTES = 45 * 1024 * 1024


def extract_shortcode(url):
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()

        if host not in ("instagram.com", "www.instagram.com"):
            return None

        match = re.search(
            r"/(?:reel|reels|p|tv)/([^/?#]+)",
            parsed.path
        )

        return match.group(1) if match else None

    except Exception:
        return None


def get_best_video_url(post):
    if post.is_video and post.video_url:
        return post.video_url

    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if node.is_video and node.video_url:
                return node.video_url

    return None


def fetch_reel_bytes(url):
    """Fetch video into memory; no local video file is created."""
    shortcode = extract_shortcode(url)

    if not shortcode:
        return None

    if shortcode in CACHE:
        cached = io.BytesIO(CACHE[shortcode])
        cached.name = "reel.mp4"
        return cached

    try:
        post = instaloader.Post.from_shortcode(
            L.context,
            shortcode
        )

        video_url = get_best_video_url(post)

        if not video_url:
            return None

        headers = {
            "User-Agent": L.context.user_agent,
            "Accept": "*/*",
        }

        chunks = []
        total_size = 0

        with requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=(15, 90)
        ) as response:

            response.raise_for_status()

            for chunk in response.iter_content(
                chunk_size=256 * 1024
            ):
                if not chunk:
                    continue

                total_size += len(chunk)

                if total_size > MAX_VIDEO_BYTES:
                    print("Video exceeds configured size limit.")
                    return None

                chunks.append(chunk)

        data = b"".join(chunks)

        if not data:
            return None

        if len(CACHE) >= CACHE_LIMIT:
            CACHE.pop(next(iter(CACHE)))

        CACHE[shortcode] = data

        result = io.BytesIO(data)
        result.name = "reel.mp4"
        return result

    except Exception as error:
        print(f"[FETCH ERROR] {error}")
        return None


# ---------- TEXTS ----------

def start_text():
    return premium_text(
        f"{ce('film')} <b>INSTAGRAM REEL BOT</b> {ce('bolt')}\n\n"
        f"{ce('sparkle')} <b>Welcome!</b>\n\n"
        f"{ce('download')} Send an Instagram Reel link. "
        "The bot will try to fetch the video.\n\n"
        f"{ce('rocket')} <b>FEATURES</b>\n"
        f"  {ce('check')} HD when available\n"
        f"  {ce('bolt')} Fast delivery\n"
        f"  {ce('target')} Direct video delivery\n"
        f"  {ce('free')} Free service\n\n"
        f"{ce('pin')} <b>EXAMPLE</b>\n"
        "<code>https://www.instagram.com/reel/xxxxx/</code>"
    )


def howto_text():
    return premium_text(
        f"{ce('bulb')} <b>HOW TO USE</b>\n\n"
        f"{ce('pin')} <b>01</b> Open an Instagram Reel\n"
        f"{ce('pin')} <b>02</b> Tap Share\n"
        f"{ce('pin')} <b>03</b> Select Copy Link\n"
        f"{ce('pin')} <b>04</b> Send the link here\n\n"
        f"{ce('check')} The bot will try to deliver the video."
    )


# ---------- ANIMATED STATUS ----------

def animate_status(chat_id, message_id, stop_event, stage):
    frames = [
        "▰▱▱▱▱",
        "▰▰▱▱▱",
        "▰▰▰▱▱",
        "▰▰▰▰▱",
        "▰▰▰▰▰",
        "▱▰▰▰▰",
    ]

    dots = ["·", "··", "···", "··"]
    index = 0

    while not stop_event.wait(2.5):
        frame = frames[index % len(frames)]
        dot = dots[index % len(dots)]

        if stage == "download":
            body = (
                f"{ce('hourglass')} <b>PROCESSING{dot}</b>\n\n"
                f"{ce('search')} Fetching Reel data\n"
                f"<code>{frame}</code>\n"
                f"{ce('download')} Preparing video"
            )
        else:
            body = (
                f"{ce('upload')} <b>UPLOADING{dot}</b>\n\n"
                f"{ce('rocket')} Sending video to Telegram\n"
                f"<code>{frame}</code>\n"
                f"{ce('sparkle')} Please wait"
            )

        try:
            bot.edit_message_text(
                premium_text(body),
                chat_id,
                message_id
            )
        except Exception:
            # Ignore temporary errors and unchanged-message responses.
            pass

        index += 1


def start_animation(chat_id, message_id, stage):
    stop_event = threading.Event()

    worker = threading.Thread(
        target=animate_status,
        args=(chat_id, message_id, stop_event, stage),
        daemon=True
    )

    worker.start()
    return stop_event, worker


def stop_animation(animation):
    if not animation:
        return

    stop_event, worker = animation
    stop_event.set()
    worker.join(timeout=3)


# ---------- START / HELP ----------

@bot.message_handler(commands=["start", "help"])
def cmd_start(msg):
    bot.send_message(
        msg.chat.id,
        start_text(),
        reply_markup=start_keyboard()
    )


# ---------- CALLBACKS ----------

@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    try:
        if call.data == "howto":
            bot.answer_callback_query(call.id)

            bot.send_message(
                call.message.chat.id,
                howto_text(),
                reply_markup=start_keyboard()
            )

        elif call.data == "again":
            bot.answer_callback_query(call.id)

            body = (
                f"{ce('download')} <b>SEND NEXT REEL LINK</b>\n\n"
                f"{ce('pin')} <code>"
                "https://www.instagram.com/reel/xxxxx/"
                "</code>\n\n"
                f"{ce('bolt')} Ready for the next link."
            )

            bot.send_message(
                call.message.chat.id,
                premium_text(body),
                reply_markup=start_keyboard()
            )

        else:
            bot.answer_callback_query(call.id)

    except Exception as error:
        print(f"[CALLBACK ERROR] {error}")


# ---------- MAIN LINK HANDLER ----------

@bot.message_handler(
    content_types=["text"],
    func=lambda message: not (
        message.text or ""
    ).startswith("/")
)
def handle_link(msg):
    url = (msg.text or "").strip()
    shortcode = extract_shortcode(url)

    if not shortcode:
        body = (
            f"{ce('cross')} <b>INVALID LINK</b>\n\n"
            f"{ce('bulb')} Send a valid Instagram Reel link.\n\n"
            f"{ce('pin')} <code>"
            "https://www.instagram.com/reel/xxxxx/"
            "</code>"
        )

        bot.reply_to(
            msg,
            premium_text(body),
            reply_markup=error_keyboard()
        )
        return

    started_at = time.time()

    initial_body = (
        f"{ce('hourglass')} <b>PROCESSING</b>\n\n"
        f"{ce('search')} Fetching Reel data\n"
        "<code>▰▱▱▱▱</code>"
    )

    status = bot.reply_to(
        msg,
        premium_text(initial_body)
    )

    download_animation = start_animation(
        msg.chat.id,
        status.message_id,
        "download"
    )

    video_io = fetch_reel_bytes(url)

    stop_animation(download_animation)

    if not video_io:
        failed_body = (
            f"{ce('cross')} <b>DOWNLOAD FAILED</b>\n\n"
            f"{ce('pin')} <b>Possible reasons</b>\n"
            "• Private or unavailable Reel\n"
            "• Instagram rate limit\n"
            "• Unsupported link\n"
            "• Video exceeds the configured size limit\n\n"
            f"{ce('bulb')} Try again later."
        )

        try:
            bot.edit_message_text(
                premium_text(failed_body),
                msg.chat.id,
                status.message_id,
                reply_markup=error_keyboard()
            )
        except Exception as error:
            print(f"[STATUS ERROR] {error}")

        return

    upload_body = (
        f"{ce('upload')} <b>UPLOADING</b>\n\n"
        f"{ce('rocket')} Preparing video delivery\n"
        "<code>▰▰▱▱▱</code>"
    )

    try:
        bot.edit_message_text(
            premium_text(upload_body),
            msg.chat.id,
            status.message_id
        )
    except Exception:
        pass

    upload_animation = start_animation(
        msg.chat.id,
        status.message_id,
        "upload"
    )

    try:
        video_io.seek(0)
        elapsed = time.time() - started_at

        caption = premium_text(
            f"{ce('check')} <b>DOWNLOAD COMPLETE</b>\n\n"
            f"{ce('film')} Your Reel is ready\n"
            f"{ce('diamond')} Quality: HD when available\n"
            f"{ce('bolt')} Processing time: {elapsed:.1f}s\n\n"
            f"{ce('sparkle')} <b>Enjoy!</b>"
        )

        bot.send_video(
            msg.chat.id,
            video_io,
            caption=caption,
            supports_streaming=True,
            reply_markup=done_keyboard(),
            timeout=120
        )

        stop_animation(upload_animation)

        try:
            bot.delete_message(
                msg.chat.id,
                status.message_id
            )
        except Exception:
            pass

    except Exception as error:
        stop_animation(upload_animation)
        print(f"[UPLOAD ERROR] {error}")

        failed_body = (
            f"{ce('cross')} <b>UPLOAD FAILED</b>\n\n"
            f"{ce('sad')} Telegram could not upload this video.\n"
            f"{ce('bulb')} Check the file size and try again."
        )

        try:
            bot.edit_message_text(
                premium_text(failed_body),
                msg.chat.id,
                status.message_id,
                reply_markup=error_keyboard()
            )
        except Exception as status_error:
            print(f"[STATUS ERROR] {status_error}")


# ---------- STARTUP BANNER ----------

print("========================================")
print("  HYPER X | INSTAGRAM REEL BOT")
print("========================================")
print("  ✓ Symbol-only interface")
print("  ◆ Box-style text theme")
print("  ◈ Animated progress status")
print("  ⇩ Waiting for messages")
print("========================================")


# ---------- INFINITY POLLING ----------

while True:
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=30,
            skip_pending=True
        )

    except KeyboardInterrupt:
        print("Bot stopped.")
        break

    except Exception as error:
        print(f"[CONNECTION ERROR] {error}")
        print("↻ Restarting in 3 seconds...")
        time.sleep(3)
