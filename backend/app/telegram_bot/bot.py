"""Run separately: python -m app.telegram_bot.bot. No token is logged."""
import asyncio
import logging
import re
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import RateLimiter
from app.services.detection import assess_text, assess_url
from app.services.ocr import extract_text, OCRUnavailable, MAX_BYTES
from app.services.resources import RESOURCES
from app.services.storage import record_metric
from app.schemas.requests import Assessment

logger = logging.getLogger('scamshield.telegram')
limiter = RateLimiter()


def render_result(assessment: Assessment) -> str:
    ms = assessment.language == 'ms'
    flags = '\n'.join('• ' + (i.title_ms if ms else i.title) for i in assessment.indicators) or ('Tiada petunjuk kuat dikenal pasti.' if ms else 'No strong indicators identified.')
    actions = '\n'.join('• ' + x for x in (assessment.recommendations_ms if ms else assessment.recommendations))
    return f'ScamShield AI — {"Keputusan Analisis" if ms else "Analysis Result"}\n\nRisk / Risiko: {assessment.risk}\nIndicator score / Skor petunjuk: {assessment.score}/100 (heuristic)\n\n{flags}\n\n{actions}\n\n{assessment.disclaimer_ms if ms else assessment.disclaimer}'


async def private(update: Update) -> bool:
    if not update.effective_message or not update.effective_chat:
        return False
    if update.effective_chat.type != 'private':
        await update.effective_message.reply_text('For your privacy, send messages to ScamShield AI in a private chat.')
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await private(update):
        await update.effective_message.reply_text('Welcome to ScamShield AI Bot.\nDetect the Scam. Protect Your Money. Empower the Community.\n\nSend or forward suspicious text, an HTTP(S) link, or a screenshot. Use /scan, /url, /help, /report or /privacy.\n\nDo not send passwords, OTPs, TACs, banking PINs or recovery codes. Automated checks cannot guarantee safety. Telegram processes messages under its own privacy policy.')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await private(update):
        await update.effective_message.reply_text('Send or forward a message (3–10,000 characters), send a link, or upload a PNG/JPEG/WEBP screenshot up to 5 MB.\n\n/scan [message] — analyze text\n/url [address] — lexical URL check; links are never opened\n/report — official resources\n/privacy — retention information\n\nOCR text must be reviewed and resubmitted before analysis. Rules may miss scams or flag legitimate communications. Verify independently.')


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await private(update):
        await update.effective_message.reply_text('The bot processes your message to produce an assessment. Raw messages, screenshots, usernames and Telegram IDs are not saved to our database. Only daily aggregate counts (risk, category, language and channel) are kept. Salted rate-limit keys expire in memory. OCR images are temporary and not retained by this app. Telegram retains its own conversation and processes your messages under its privacy policy. No content is sent to a third-party AI provider. Delete messages in Telegram to manage that conversation.')


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await private(update):
        await update.effective_message.reply_text('If money was transferred, contact your bank immediately and NSRC 997.\n\nOfficial websites (external links; no government API integration):\n\n' + '\n\n'.join(f'{r["name"]}\n{r["url"]}' for r in RESOURCES), disable_web_page_preview=True)


def analyze_and_record(text: str, url_mode: bool = False) -> Assessment:
    assessment = assess_url(text) if url_mode else assess_text(text)
    with SessionLocal() as db:
        record_metric(db, assessment, 'telegram')
        db.commit()
    return assessment


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str | None = None, force_url: bool = False):
    if not await private(update):
        return
    if not limiter.allow(str(update.effective_chat.id), 15):
        await update.effective_message.reply_text('Too many requests. Please wait one minute.')
        return
    text = (text if text is not None else update.effective_message.text or '').strip()
    if not 3 <= len(text) <= 10000:
        await update.effective_message.reply_text('Please send between 3 and 10,000 characters.')
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.effective_message.reply_text('Checking the warning signs… / Menyemak petunjuk…')
    try:
        url_mode = force_url or bool(re.fullmatch(r'https?://\S+', text))
        result = await asyncio.to_thread(analyze_and_record, text, url_mode)
        await update.effective_message.reply_text(render_result(result), disable_web_page_preview=True)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
    except Exception as exc:
        logger.error('analysis_failed type=%s', type(exc).__name__)
        await update.effective_message.reply_text('Analysis is temporarily unavailable. Please try again.')


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await handle_text(update, context, ' '.join(context.args))
    elif await private(update):
        await update.effective_message.reply_text('Send or forward the suspicious message as your next message. Remove personal details and never include OTPs or passwords.')


async def url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await handle_text(update, context, ' '.join(context.args), force_url=True)
    elif await private(update):
        await update.effective_message.reply_text('Send an HTTP or HTTPS link, or use /url https://example.com. We inspect the address without opening it.')


async def image_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await private(update):
        return
    if not limiter.allow(str(update.effective_chat.id), 15):
        await update.effective_message.reply_text('Too many requests. Please wait one minute.')
        return
    message = update.effective_message
    file = message.photo[-1] if message.photo else message.document
    content_type = 'image/jpeg' if message.photo else file.mime_type
    if not file.file_size or file.file_size > MAX_BYTES:
        await message.reply_text('Please upload a screenshot smaller than 5 MB.')
        return
    await message.reply_text('Reading screenshot text… / Membaca teks tangkap layar…')
    try:
        remote = await context.bot.get_file(file.file_id)
        data = bytes(await remote.download_as_bytearray())
        text = await asyncio.to_thread(extract_text, data, content_type)
        if not text:
            await message.reply_text('No readable text found. Try a clearer screenshot or paste the text.')
            return
        # Do not retain OCR or any per-user pending content on this server.
        for offset in range(0, len(text), 3500):
            await message.reply_text(text[offset:offset + 3500], disable_web_page_preview=True)
        await message.reply_text('Review and remove personal details from the extracted text, then send the reviewed text back to receive an assessment. No image has been retained by this app.')
    except (ValueError, OCRUnavailable) as exc:
        await message.reply_text(str(exc))
    except Exception as exc:
        logger.error('ocr_failed type=%s', type(exc).__name__)
        await message.reply_text('Unable to read this image. Paste the text instead.')


async def unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await private(update):
        await update.effective_message.reply_text('This attachment is not supported. Send text, an HTTP(S) link, or a PNG/JPEG/WEBP screenshot.')


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error('telegram_handler_error type=%s', type(context.error).__name__)


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit('Set TELEGRAM_BOT_TOKEN in .env after creating your bot with BotFather. See docs/telegram.md.')
    app = Application.builder().token(settings.telegram_bot_token).build()
    for name, callback in [('start', start), ('scan', scan_command), ('url', url_command), ('help', help_command), ('report', report), ('privacy', privacy_command)]:
        app.add_handler(CommandHandler(name, callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, image_message))
    app.add_handler(MessageHandler(filters.ALL, unsupported))
    app.add_error_handler(error_handler)
    return app


def main():
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    settings = get_settings()
    app = build_application()
    if settings.telegram_webhook_url:
        if not settings.telegram_webhook_url.startswith('https://') or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', settings.telegram_webhook_secret):
            raise SystemExit('Production webhooks require an HTTPS URL and a 32–256 character secret using A-Z, a-z, 0-9, _ or -.')
        app.run_webhook(listen='0.0.0.0', port=settings.telegram_port, url_path='telegram', webhook_url=settings.telegram_webhook_url.rstrip('/') + '/telegram', secret_token=settings.telegram_webhook_secret, drop_pending_updates=True)
    else:
        app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
