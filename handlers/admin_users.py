# handlers/admin_users.py
# Commands: /genfakeusers, /delfakeusers, /addtester, /deltester, /testers,
#           /setexchangerate
import random
import time

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

import config
import database
from db.db_core import DB_NAME
from .admin_constants import E_STOP, E_CHECK, E_CROSS, E_TIME


def register(dp: Dispatcher, bot: Bot):

    # ── /setexchangebonus ─────────────────────────────────────────────────────

    @dp.message(Command("setexchangebonus"))
    async def cmd_set_exchange_bonus(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        from db.db_settings import get_exchange_bonus_percent, set_exchange_bonus_percent

        args = message.text.split()
        if len(args) != 2:
            current = await get_exchange_bonus_percent()
            await message.answer(
                "<b>Бонус при обмене подарков на звёзды</b>\n\n"
                f"Текущий бонус: <b>+{current}%</b>\n\n"
                "Использование: <code>/setexchangebonus &lt;процент&gt;</code>\n"
                "Пример: <code>/setexchangebonus 15</code>\n\n"
                "<i>При бонусе 10% пользователь получает на 10% звёзд больше рыночной цены портала.</i>",
                parse_mode="HTML",
            )
            return

        try:
            new_bonus = float(args[1])
            if new_bonus < 0:
                await message.answer(f"{E_CROSS} Бонус не может быть отрицательным.", parse_mode="HTML")
                return
            if new_bonus > 1000:
                await message.answer(f"{E_CROSS} Бонус не может быть больше 1000%.", parse_mode="HTML")
                return

            old_bonus = await get_exchange_bonus_percent()
            await set_exchange_bonus_percent(new_bonus)

            await message.answer(
                f"{E_CHECK} <b>Бонус обмена обновлён!</b>\n\n"
                f"Было: <b>+{old_bonus}%</b>\n"
                f"Стало: <b>+{new_bonus}%</b>\n\n"
                f"<i>Пользователи получат на {new_bonus}% больше звёзд от рыночной цены портала.</i>",
                parse_mode="HTML",
            )
        except ValueError:
            await message.answer(
                f"{E_CROSS} Некорректное значение. Введите число, например: <code>10</code>",
                parse_mode="HTML",
            )

    # ── /genfakeusers ──────────────────────────────────────────────────────────

    FAKE_NAMES = [
        "Алексей", "Мария", "Дмитрий", "Анна", "Сергей", "Екатерина",
        "Иван", "Ольга", "Андрей", "Наталья", "Михаил", "Татьяна",
        "Николай", "Юлия", "Артём", "Елена", "Кирилл", "Ирина",
        "Владимир", "Светлана", "Павел", "Ксения", "Роман", "Виктория",
        "Денис", "Людмила", "Евгений", "Дарья", "Антон", "Полина",
        "Максим", "Валерия", "Тимур", "Алина", "Глеб", "Вероника",
        "Илья", "Маргарита", "Руслан", "Кристина", "Степан", "Диана",
        "Константин", "Надежда", "Юрий", "Милана", "Геннадий", "Таисия",
        "Борис", "Регина",
    ]
    AVATARS = [f"https://i.pravatar.cc/150?img={i}" for i in range(1, 71)]
    _FAKE_TG_ID_START = 9_000_000_000

    @dp.message(Command("genfakeusers"))
    async def cmd_gen_fake_users(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        await message.answer(
            f"{E_TIME} Генерирую 100 фейковых пользователей...", parse_mode="HTML"
        )

        now      = int(time.time())
        week_ago = now - 6 * 86400

        async with aiosqlite.connect(DB_NAME) as db:
            for i in range(100):
                tg_id    = _FAKE_TG_ID_START + i
                name     = random.choice(FAKE_NAMES) + f"_{i + 1}"
                username = f"fake_user_{i + 1}"
                avatar   = random.choice(AVATARS)
                balance  = random.randint(10, 50_000)

                await db.execute(
                    """
                    INSERT INTO users (
                        tg_id, username, first_name, photo_url,
                        balance, stars, last_free_spin, notified_free_spin,
                        last_gift_withdraw, notified_gift_withdraw,
                        last_gift_claim, notified_gift_claim,
                        last_free_case, notified_free_case
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 0, 1, 0, 1, 0, 1, 0, 1)
                    ON CONFLICT(tg_id) DO UPDATE SET
                        username=excluded.username,
                        first_name=excluded.first_name,
                        photo_url=excluded.photo_url,
                        balance=excluded.balance
                    """,
                    (tg_id, username, name, avatar, balance),
                )

                if random.random() < 0.7:
                    multiplier = round(random.uniform(1.2, 50.0), 2)
                    ts = random.randint(week_ago, now)
                    await db.execute(
                        """
                        INSERT INTO user_history
                            (user_id, action_type, description, amount, created_at)
                        VALUES (?, 'rocket_win_fake', ?, ?, ?)
                        """,
                        (tg_id, f"Ракета: x{multiplier}", int(multiplier * 100), ts),
                    )

                if random.random() < 0.6:
                    ratio_x100 = random.randint(110, 2000)
                    await db.execute(
                        """
                        INSERT INTO user_history
                            (user_id, action_type, description, amount, created_at)
                        VALUES (?, 'case_lucky_ratio', 'Фейк: кейс', ?, ?)
                        """,
                        (tg_id, ratio_x100, random.randint(week_ago, now)),
                    )

            await db.commit()

        await message.answer(
            f"{E_CHECK} <b>Готово!</b>\n\n"
            f"Создано <b>100 фейковых пользователей</b>"
            f" (tg_id {_FAKE_TG_ID_START}–{_FAKE_TG_ID_START + 99}).\n"
            "Данные добавлены во все три таблицы лидеров.\n\n"
            "<i>Для удаления фейков используйте /delfakeusers</i>",
            parse_mode="HTML",
        )

    # ── /delfakeusers ──────────────────────────────────────────────────────────

    @dp.message(Command("delfakeusers"))
    async def cmd_del_fake_users(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        fake_end = _FAKE_TG_ID_START + 99

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "DELETE FROM user_history WHERE user_id BETWEEN ? AND ?",
                (_FAKE_TG_ID_START, fake_end),
            )
            result = await db.execute(
                "DELETE FROM users WHERE tg_id BETWEEN ? AND ?",
                (_FAKE_TG_ID_START, fake_end),
            )
            deleted = result.rowcount
            await db.commit()

        await message.answer(
            f"{E_CHECK} Удалено <b>{deleted}</b> фейковых пользователей и их история.",
            parse_mode="HTML",
        )

    # ── /addtester ─────────────────────────────────────────────────────────────

    @dp.message(Command("addtester"))
    async def cmd_add_tester(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()[1:]
        if not args:
            await message.answer(
                "<b>👁 Добавление beta-тестеров</b>\n\n"
                "Использование:\n"
                "<code>/addtester &lt;ID&gt; [ID2 ID3 ...]</code>\n\n"
                "Можно указать один или несколько ID через пробел.\n"
                "<i>Beta-тестеры видят приложение даже при maintenance mode "
                "и при отключённых разделах/кейсах.</i>",
                parse_mode="HTML",
            )
            return

        added, already, invalid = [], [], []

        for raw in args:
            try:
                uid = int(raw)
            except ValueError:
                invalid.append(raw)
                continue
            ok = await database.add_beta_tester(uid)
            (added if ok else already).append(uid)

        lines = []
        if added:
            lines.append(f"{E_CHECK} Добавлены: " + ", ".join(f"<code>{i}</code>" for i in added))
        if already:
            lines.append("ℹ️ Уже в списке: " + ", ".join(f"<code>{i}</code>" for i in already))
        if invalid:
            lines.append(f"{E_CROSS} Неверный формат ID: " + ", ".join(f"<code>{i}</code>" for i in invalid))

        await message.answer("\n".join(lines) or "Нет данных для обработки.", parse_mode="HTML")

    # ── /deltester ─────────────────────────────────────────────────────────────

    @dp.message(Command("deltester"))
    async def cmd_del_tester(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()[1:]
        if not args:
            await message.answer(
                "<b>🗑 Удаление beta-тестера</b>\n\n"
                "Использование:\n"
                "<code>/deltester &lt;ID&gt; [ID2 ID3 ...]</code>",
                parse_mode="HTML",
            )
            return

        removed, not_found, invalid = [], [], []

        for raw in args:
            try:
                uid = int(raw)
            except ValueError:
                invalid.append(raw)
                continue
            ok = await database.remove_beta_tester(uid)
            (removed if ok else not_found).append(uid)

        lines = []
        if removed:
            lines.append(f"{E_CHECK} Удалены: " + ", ".join(f"<code>{i}</code>" for i in removed))
        if not_found:
            lines.append("ℹ️ Не найдены: " + ", ".join(f"<code>{i}</code>" for i in not_found))
        if invalid:
            lines.append(f"{E_CROSS} Неверный формат ID: " + ", ".join(f"<code>{i}</code>" for i in invalid))

        await message.answer("\n".join(lines) or "Нет данных для обработки.", parse_mode="HTML")

    # ── /testers ───────────────────────────────────────────────────────────────

    @dp.message(Command("testers"))
    async def cmd_testers(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        testers = await database.get_beta_testers()

        if not testers:
            await message.answer(
                "<b>👁 Beta-тестеры</b>\n\nСписок пуст.\n\n"
                "Добавить: <code>/addtester &lt;ID&gt;</code>",
                parse_mode="HTML",
            )
            return

        lines = ["<b>👁 Beta-тестеры</b>\n"]
        for i, t in enumerate(testers, 1):
            lines.append(f"{i}. <code>{t['user_id']}</code>  — добавлен {t['added_at'][:10]}")

        lines.append(
            f"\n<i>Всего: {len(testers)}</i>\n\n"
            "Добавить: <code>/addtester &lt;ID&gt;</code>\n"
            "Удалить:  <code>/deltester &lt;ID&gt;</code>"
        )

        await message.answer("\n".join(lines), parse_mode="HTML")