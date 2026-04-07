# handlers/support.py — Бот поддержки @SpaceDonutSupportBot
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

import config

logger = logging.getLogger(__name__)

# ─── Список администраторов, получающих заявки ───────────────────────────────
# ADMIN_ID уже определён в config.py; при необходимости добавь сюда
# дополнительные Telegram ID других модераторов.
SUPPORT_ADMIN_IDS: list[int] = [config.ADMIN_ID]

# ─── FSM ─────────────────────────────────────────────────────────────────────

class SupportFSM(StatesGroup):
    lang         = State()   # выбор языка
    category     = State()   # выбор категории
    topup_type   = State()   # подкатегория «не пополняется баланс»
    free_text    = State()   # пользователь описывает «другую проблему»
    in_chat      = State()   # диалог с оператором


# ─── Тексты ──────────────────────────────────────────────────────────────────

TEXTS = {
    "ru": {
        "welcome": (
            "👋 <b>Добро пожаловать в поддержку Space Donut!</b>\n\n"
            "Выберите язык / Please select your language:"
        ),
        "choose_lang": "Пожалуйста, выберите язык:",
        "choose_category": (
            "📋 <b>Выберите тему обращения:</b>"
        ),
        "cat1": "🎁 Не приходит подарок",
        "cat2": "💰 Не пополняется баланс",
        "cat3": "❓ Другая проблема",
        "gift_help": (
            "🎁 <b>Не приходит подарок</b>\n\n"
            "Попробуйте следующее:\n\n"
            "1️⃣ Убедитесь, что вы отправили подарок на аккаунт "
            "<b>@SpaceDonutGifts</b> — именно туда принимаются все NFT-подарки.\n\n"
            "2️⃣ Подождите около <b>30 минут</b> — обработка может занять время.\n\n"
            "Если после ожидания подарок всё ещё не зачислен, свяжитесь с оператором."
        ),
        "topup_choose": (
            "💰 <b>Не пополняется баланс</b>\n\n"
            "Уточните способ пополнения:"
        ),
        "topup_nft": "🖼 NFT-подарком",
        "topup_stars": "⭐️ Звёздами",
        "topup_nft_help": (
            "🖼 <b>Пополнение NFT-подарком</b>\n\n"
            "Убедитесь, что подарок был отправлен на аккаунт <b>@SpaceDonutGifts</b>.\n\n"
            "Если всё верно — напишите туда ещё раз и подождите <b>30 минут</b>.\n\n"
            "Если баланс по-прежнему не зачислен, нажмите кнопку ниже, "
            "чтобы связаться с оператором."
        ),
        "topup_stars_help": (
            "⭐️ <b>Пополнение звёздами</b>\n\n"
            "Пополнение звёздами обрабатывается автоматически сразу после оплаты.\n\n"
            "Если средства списались, но баланс не пополнился — "
            "нажмите кнопку ниже, чтобы связаться с оператором. "
            "Пожалуйста, сохраните подтверждение платежа."
        ),
        "operator_btn": "📞 Связаться с оператором",
        "back_btn": "⬅️ Назад",
        "other_prompt": (
            "✏️ <b>Опишите вашу проблему</b>\n\n"
            "Напишите подробное сообщение — оператор ответит вам в ближайшее время."
        ),
        "other_sent": (
            "✅ <b>Ваше обращение отправлено!</b>\n\n"
            "Оператор рассмотрит его и ответит вам здесь."
        ),
        "operator_connecting": (
            "📞 <b>Соединяем с оператором…</b>\n\n"
            "Опишите вашу проблему в следующем сообщении — "
            "оператор ответит вам в этом чате."
        ),
        "operator_notified": (
            "✅ Ваше сообщение отправлено оператору. Ожидайте ответа."
        ),
        "admin_ticket": (
            "🆘 <b>Новая заявка в поддержку</b>\n"
            "👤 Пользователь: <a href=\"tg://user?id={uid}\">{name}</a> "
            "(<code>{uid}</code>)\n"
            "📌 Тема: <b>{topic}</b>\n"
            "💬 Сообщение:\n{text}"
        ),
        "admin_reply_hint": (
            "↩️ Ответить: <code>/reply {uid} текст ответа</code>"
        ),
        "reply_sent": "✅ Ответ отправлен пользователю.",
        "reply_fail": "❌ Не удалось доставить ответ пользователю {uid}.",
        "user_reply": "💬 <b>Ответ оператора:</b>\n\n{text}",
        "chat_prompt": (
            "💬 <b>Вы в режиме диалога с оператором.</b>\n"
            "Напишите следующее сообщение — оно будет передано оператору."
        ),
        "chat_forwarded": "✅ Сообщение отправлено оператору.",
    },
    "en": {
        "welcome": (
            "👋 <b>Welcome to Space Donut Support!</b>\n\n"
            "Выберите язык / Please select your language:"
        ),
        "choose_lang": "Please select your language:",
        "choose_category": (
            "📋 <b>Choose a support topic:</b>"
        ),
        "cat1": "🎁 Gift not received",
        "cat2": "💰 Balance not topped up",
        "cat3": "❓ Other issue",
        "gift_help": (
            "🎁 <b>Gift not received</b>\n\n"
            "Please try the following:\n\n"
            "1️⃣ Make sure you sent the gift to <b>@SpaceDonutGifts</b> — "
            "that is the only account that accepts NFT gifts.\n\n"
            "2️⃣ Wait around <b>30 minutes</b> — processing can take some time.\n\n"
            "If the gift has still not arrived, please contact an operator."
        ),
        "topup_choose": (
            "💰 <b>Balance not topped up</b>\n\n"
            "Please select your top-up method:"
        ),
        "topup_nft": "🖼 NFT gift",
        "topup_stars": "⭐️ Stars",
        "topup_nft_help": (
            "🖼 <b>Top-up via NFT gift</b>\n\n"
            "Make sure the gift was sent to <b>@SpaceDonutGifts</b>.\n\n"
            "If confirmed — send it again and wait <b>30 minutes</b>.\n\n"
            "If your balance is still not credited, press the button below "
            "to contact an operator."
        ),
        "topup_stars_help": (
            "⭐️ <b>Top-up via Stars</b>\n\n"
            "Star payments are processed automatically immediately after payment.\n\n"
            "If the amount was charged but your balance was not updated — "
            "press the button below to contact an operator. "
            "Please keep your payment confirmation."
        ),
        "operator_btn": "📞 Contact operator",
        "back_btn": "⬅️ Back",
        "other_prompt": (
            "✏️ <b>Describe your issue</b>\n\n"
            "Write a detailed message — an operator will reply shortly."
        ),
        "other_sent": (
            "✅ <b>Your request has been submitted!</b>\n\n"
            "An operator will review it and reply here."
        ),
        "operator_connecting": (
            "📞 <b>Connecting to an operator…</b>\n\n"
            "Describe your issue in the next message — "
            "the operator will reply in this chat."
        ),
        "operator_notified": (
            "✅ Your message has been sent to the operator. Please wait for a reply."
        ),
        "admin_ticket": (
            "🆘 <b>New support ticket</b>\n"
            "👤 User: <a href=\"tg://user?id={uid}\">{name}</a> "
            "(<code>{uid}</code>)\n"
            "📌 Topic: <b>{topic}</b>\n"
            "💬 Message:\n{text}"
        ),
        "admin_reply_hint": (
            "↩️ Reply: <code>/reply {uid} reply text</code>"
        ),
        "reply_sent": "✅ Reply sent to user.",
        "reply_fail": "❌ Could not deliver reply to user {uid}.",
        "user_reply": "💬 <b>Operator reply:</b>\n\n{text}",
        "chat_prompt": (
            "💬 <b>You are in a live chat with an operator.</b>\n"
            "Write your next message — it will be forwarded to the operator."
        ),
        "chat_forwarded": "✅ Message forwarded to the operator.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def kb_lang() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="sup_lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="sup_lang:en"),
        ]
    ])


def kb_category(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cat1"), callback_data="sup_cat:1")],
        [InlineKeyboardButton(text=t(lang, "cat2"), callback_data="sup_cat:2")],
        [InlineKeyboardButton(text=t(lang, "cat3"), callback_data="sup_cat:3")],
    ])


def kb_gift_help(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "operator_btn"), callback_data="sup_op:gift")],
        [InlineKeyboardButton(text=t(lang, "back_btn"), callback_data="sup_back:category")],
    ])


def kb_topup_type(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "topup_nft"),   callback_data="sup_topup:nft")],
        [InlineKeyboardButton(text=t(lang, "topup_stars"), callback_data="sup_topup:stars")],
        [InlineKeyboardButton(text=t(lang, "back_btn"),    callback_data="sup_back:category")],
    ])


def kb_topup_help(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "operator_btn"), callback_data="sup_op:topup")],
        [InlineKeyboardButton(text=t(lang, "back_btn"),     callback_data="sup_back:topup")],
    ])


# ─── Уведомление администраторов ─────────────────────────────────────────────

async def notify_admins(
    bot: Bot,
    user: "aiogram.types.User",
    lang: str,
    topic: str,
    text: str,
) -> None:
    msg = (
        t(lang, "admin_ticket", uid=user.id, name=user.full_name, topic=topic, text=text)
        + "\n\n"
        + t(lang, "admin_reply_hint", uid=user.id)
    )
    for admin_id in SUPPORT_ADMIN_IDS:
        try:
            await bot.send_message(admin_id, msg, parse_mode="HTML")
        except Exception as exc:
            logger.warning(f"Не удалось уведомить администратора {admin_id}: {exc}")


# ─── Регистрация хендлеров ───────────────────────────────────────────────────

def register(dp: Dispatcher, bot: Bot) -> None:

    # ── /start ──────────────────────────────────────────────────────────────

    @dp.message(F.text == "/start")
    async def support_start(message: Message, state: FSMContext):
        await state.clear()
        await message.answer(
            t("ru", "welcome"),
            reply_markup=kb_lang(),
            parse_mode="HTML",
        )
        await state.set_state(SupportFSM.lang)

    # ── Выбор языка ─────────────────────────────────────────────────────────

    @dp.callback_query(SupportFSM.lang, F.data.startswith("sup_lang:"))
    async def cb_lang(call: CallbackQuery, state: FSMContext):
        lang = call.data.split(":")[1]
        await state.update_data(lang=lang)
        await call.message.edit_text(
            t(lang, "choose_category"),
            reply_markup=kb_category(lang),
            parse_mode="HTML",
        )
        await state.set_state(SupportFSM.category)
        await call.answer()

    # ── Выбор категории ─────────────────────────────────────────────────────

    @dp.callback_query(SupportFSM.category, F.data.startswith("sup_cat:"))
    async def cb_category(call: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        lang = data.get("lang", "ru")
        cat = call.data.split(":")[1]

        if cat == "1":
            await call.message.edit_text(
                t(lang, "gift_help"),
                reply_markup=kb_gift_help(lang),
                parse_mode="HTML",
            )

        elif cat == "2":
            await call.message.edit_text(
                t(lang, "topup_choose"),
                reply_markup=kb_topup_type(lang),
                parse_mode="HTML",
            )
            await state.set_state(SupportFSM.topup_type)

        elif cat == "3":
            await call.message.edit_text(
                t(lang, "other_prompt"),
                parse_mode="HTML",
            )
            await state.update_data(topic=t(lang, "cat3"))
            await state.set_state(SupportFSM.free_text)

        await call.answer()

    # ── Подкатегория пополнения ─────────────────────────────────────────────

    @dp.callback_query(SupportFSM.topup_type, F.data.startswith("sup_topup:"))
    async def cb_topup_type(call: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        lang = data.get("lang", "ru")
        ttype = call.data.split(":")[1]

        if ttype == "nft":
            await call.message.edit_text(
                t(lang, "topup_nft_help"),
                reply_markup=kb_topup_help(lang),
                parse_mode="HTML",
            )
        else:
            await call.message.edit_text(
                t(lang, "topup_stars_help"),
                reply_markup=kb_topup_help(lang),
                parse_mode="HTML",
            )

        await call.answer()

    # ── Кнопка «Назад» ──────────────────────────────────────────────────────

    @dp.callback_query(F.data.startswith("sup_back:"))
    async def cb_back(call: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        lang = data.get("lang", "ru")
        dest = call.data.split(":")[1]

        if dest == "category":
            await call.message.edit_text(
                t(lang, "choose_category"),
                reply_markup=kb_category(lang),
                parse_mode="HTML",
            )
            await state.set_state(SupportFSM.category)

        elif dest == "topup":
            await call.message.edit_text(
                t(lang, "topup_choose"),
                reply_markup=kb_topup_type(lang),
                parse_mode="HTML",
            )
            await state.set_state(SupportFSM.topup_type)

        await call.answer()

    # ── Связаться с оператором ──────────────────────────────────────────────

    @dp.callback_query(F.data.startswith("sup_op:"))
    async def cb_operator(call: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        lang = data.get("lang", "ru")
        topic_key = call.data.split(":")[1]

        topic_map = {
            "gift":  t(lang, "cat1"),
            "topup": t(lang, "cat2"),
        }
        topic = topic_map.get(topic_key, topic_key)
        await state.update_data(topic=topic)

        await call.message.edit_text(
            t(lang, "operator_connecting"),
            parse_mode="HTML",
        )
        await state.set_state(SupportFSM.in_chat)
        await call.answer()

    # ── Получение свободного текста («другая проблема») ─────────────────────

    @dp.message(SupportFSM.free_text)
    async def handle_free_text(message: Message, state: FSMContext):
        data = await state.get_data()
        lang  = data.get("lang", "ru")
        topic = data.get("topic", t(lang, "cat3"))

        await notify_admins(bot, message.from_user, lang, topic, message.text or "")
        await message.answer(t(lang, "other_sent"), parse_mode="HTML")
        # Переводим в режим диалога, чтобы пользователь мог продолжить общение
        await state.set_state(SupportFSM.in_chat)

    # ── Режим живого диалога ─────────────────────────────────────────────────

    @dp.message(SupportFSM.in_chat)
    async def handle_in_chat(message: Message, state: FSMContext):
        data = await state.get_data()
        lang  = data.get("lang", "ru")
        topic = data.get("topic", "—")

        await notify_admins(bot, message.from_user, lang, topic, message.text or "")
        await message.answer(t(lang, "operator_notified"), parse_mode="HTML")

    # ── Команда /reply для администратора ───────────────────────────────────

    @dp.message(F.text.startswith("/reply "))
    async def cmd_reply(message: Message):
        if message.from_user.id not in SUPPORT_ADMIN_IDS:
            return

        parts = message.text.split(" ", 2)
        if len(parts) < 3:
            await message.answer("Использование: /reply <user_id> <текст>")
            return

        try:
            target_uid = int(parts[1])
        except ValueError:
            await message.answer("Некорректный user_id.")
            return

        reply_text = parts[2]

        try:
            await bot.send_message(
                target_uid,
                TEXTS["ru"]["user_reply"].format(text=reply_text),
                parse_mode="HTML",
            )
            await message.answer(t("ru", "reply_sent"))
        except Exception as exc:
            logger.warning(f"Ошибка отправки ответа {target_uid}: {exc}")
            await message.answer(t("ru", "reply_fail", uid=target_uid))
