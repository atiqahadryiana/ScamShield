from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.detection import analyze_text
from app.telegram_bot import bot


def update(text):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(effective_message=message, effective_chat=SimpleNamespace(id=42, type='private'))


@pytest.mark.asyncio
async def test_bot_shared_engine_and_routing(monkeypatch):
    text = 'Congratulations! Pay RM50 registration fee immediately.'
    called = []
    def analyze(value, url_mode=False):
        called.append((value, url_mode))
        return analyze_text(value)
    monkeypatch.setattr(bot, 'analyze_and_record', analyze)
    monkeypatch.setattr(bot, 'limiter', bot.RateLimiter())
    event = update(text)
    context = SimpleNamespace(bot=SimpleNamespace(send_chat_action=AsyncMock()))
    await bot.handle_text(event, context)
    assert called == [(text, False)]
    response = event.effective_message.reply_text.call_args.args[0]
    assert bot.render_result(analyze_text(text)) == response
    assert 'HIGH' in response
    event = update('https://example.com')
    await bot.handle_text(event, context)
    assert called[-1][1] is True


@pytest.mark.asyncio
async def test_bot_rejects_group_and_invalid_input():
    event = update('short')
    event.effective_chat.type = 'group'
    await bot.handle_text(event, SimpleNamespace())
    assert 'private chat' in event.effective_message.reply_text.call_args.args[0]
    event = update('x')
    await bot.handle_text(event, SimpleNamespace())
    assert '3 and 10,000' in event.effective_message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_screenshot_requires_review_and_does_not_auto_scan(monkeypatch):
    event = update('')
    event.effective_message.photo = [SimpleNamespace(file_id='fictional', file_size=100)]
    event.effective_message.document = None
    remote = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=bytearray(b'fictional image')))
    context = SimpleNamespace(bot=SimpleNamespace(get_file=AsyncMock(return_value=remote)))
    monkeypatch.setattr(bot, 'extract_text', lambda *args: 'Fictional OCR text for review')
    monkeypatch.setattr(bot, 'limiter', bot.RateLimiter())
    def forbidden(*args, **kwargs):
        raise AssertionError('OCR must not automatically analyze before user review')
    monkeypatch.setattr(bot, 'analyze_and_record', forbidden)
    await bot.image_message(event, context)
    responses = [call.args[0] for call in event.effective_message.reply_text.call_args_list]
    assert 'Fictional OCR text for review' in responses
    assert 'Review and remove personal details' in responses[-1]


@pytest.mark.asyncio
async def test_unsupported_attachment():
    event = update('')
    await bot.unsupported(event, SimpleNamespace())
    assert 'not supported' in event.effective_message.reply_text.call_args.args[0]
