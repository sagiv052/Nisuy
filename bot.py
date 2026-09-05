import asyncio
import csv
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / os.getenv("RULES_FILE", "BOT.csv")
PORT = int(os.getenv("PORT", "10000"))
RESET_INTERVAL_SECONDS = 10 * 60
LIST_BUTTON = "📚 רשימה"
SEARCH_BUTTON = "🔎 חיפוש"
HELP_BUTTON = "❓ עזרה"


@dataclass(frozen=True)
class Rule:
    received_message: str
    reply_message: str
    priority: int
    disabled: bool


def load_rules(path: Path) -> list[Rule]:
    """Load exact Telegram message rules from the exported CSV."""
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = csv_file.readlines()

    if rows and rows[0].strip().lower() == '"sep=,"':
        rows = rows[1:]

    reader = csv.DictReader(rows)
    rules: list[Rule] = []
    for row in reader:
        message = (row.get("received_message") or "").strip()
        reply = (row.get("reply_message") or "").replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
        if not message or not reply:
            continue
        rules.append(
            Rule(
                received_message=message,
                reply_message=reply,
                priority=int(row.get("_id") or row.get("priority") or 0),
                disabled=(row.get("disabled") or "0").strip() == "1",
            )
        )

    return sorted(rules, key=lambda rule: rule.priority)


def find_reply(message: str, rules: list[Rule]) -> Optional[str]:
    normalized_message = message.strip().casefold()
    matches = [
        rule.reply_message
        for rule in rules
        if not rule.disabled and rule.received_message.casefold() == normalized_message
    ]
    if not matches:
        return None
    if normalized_message == "רשימה":
        return max(matches, key=len)
    return matches[0]


def search_titles(query: str, rules: list[Rule]) -> list[str]:
    normalized_query = query.strip().casefold()
    titles: list[str] = []
    normalized_titles: set[str] = set()
    for rule in rules:
        if rule.disabled or normalized_query not in rule.received_message.casefold():
            continue
        normalized_title = rule.received_message.casefold()
        if normalized_title not in normalized_titles:
            titles.append(rule.received_message)
            normalized_titles.add(normalized_title)
    return titles[:20]


def keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[LIST_BUTTON, SEARCH_BUTTON], [HELP_BUTTON]],
        resize_keyboard=True,
        is_persistent=True,
    )


async def send_reply(update: Update, reply: str) -> None:
    if not update.message:
        return
    for start in range(0, len(reply), 4096):
        await update.message.reply_text(
            reply[start : start + 4096],
            reply_markup=keyboard() if start == 0 else None,
        )


def help_text() -> str:
    return (
        "שלום! 👋\n\n"
        "🎬 כתבו שם של סרט או סדרה ואשלח תקציר וקישור.\n"
        "📚 לחצו על רשימה כדי לראות את כל התכנים.\n"
        "🔎 לחצו על חיפוש כדי למצוא שם מתוך הקטלוג.\n\n"
        "פקודות:\n"
        "/list - הצגת הרשימה המלאה\n"
        "/search שם - חיפוש תוכן\n"
        "/help - עזרה"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_reply(update, help_text())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_reply(update, help_text())


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rules: list[Rule] = context.bot_data["rules"]
    reply = find_reply("רשימה", rules)
    if reply:
        await send_reply(update, reply)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args or []).strip()
    user_data = context.user_data
    if not query:
        if user_data is not None:
            user_data["awaiting_search"] = True
        await send_reply(update, "🔎 כתבו את שם הסרט או הסדרה לחיפוש:")
        return
    await search_for_title(update, context, query)


async def search_for_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: str
) -> None:
    rules: list[Rule] = context.bot_data["rules"]
    reply = find_reply(query, rules)
    if reply:
        await send_reply(update, reply)
        return

    titles = search_titles(query, rules)
    if titles:
        result = "🔎 תוצאות חיפוש:\n\n" + "\n".join(f"• {title}" for title in titles)
        result += "\n\nשלחו את השם המדויק כדי לקבל תקציר וקישור."
    else:
        result = "😕 לא מצאתי תוצאה. נסו מילה אחרת או לחצו על 📚 רשימה."
    await send_reply(update, result)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    message = update.message.text.strip()
    if message == LIST_BUTTON:
        await list_command(update, context)
        return
    if message == SEARCH_BUTTON:
        if context.user_data is not None:
            context.user_data["awaiting_search"] = True
        await send_reply(update, "🔎 כתבו את שם הסרט או הסדרה לחיפוש:")
        return
    if message == HELP_BUTTON:
        await help_command(update, context)
        return
    if context.user_data is not None and context.user_data.pop("awaiting_search", False):
        await search_for_title(update, context, message)
        return

    rules: list[Rule] = context.bot_data["rules"]
    reply = find_reply(message, rules)
    if reply:
        await send_reply(update, reply)


async def run_health_server(rules: list[Rule]) -> None:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in ("/", "/health"):
                self.send_error(404)
                return
            body = f'{{"status":"ok","rules":{len(rules)}}}'.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server listening on port %s", PORT)

    try:
        await asyncio.to_thread(server.serve_forever)
    finally:
        server.shutdown()
        server.server_close()


async def reset_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh the Telegram connection periodically without losing the rules."""
    try:
        bot_info = await context.bot.get_me()
        logger.info("10-minute refresh completed for @%s", bot_info.username)
    except Exception:
        logger.exception("10-minute refresh failed")


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Rules file was not found: {CSV_PATH}")

    rules = load_rules(CSV_PATH)
    application = Application.builder().token(token).build()
    application.bot_data["rules"] = rules
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    if application.job_queue is None or application.updater is None:
        raise RuntimeError("Telegram job queue and updater are required")
    application.job_queue.run_repeating(reset_check, interval=RESET_INTERVAL_SECONDS, first=RESET_INTERVAL_SECONDS)

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    health_task = asyncio.create_task(run_health_server(rules))
    logger.info("Bot is running with %s rules", len(rules))

    try:
        await asyncio.Event().wait()
    finally:
        health_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
