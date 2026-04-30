# handlers/admin_features.py
# Commands: /hide, /show, /featurestatus, /maintenance
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

import config
import database
from .admin_constants import E_STOP, E_CHECK, E_CROSS


# Человекочитаемые названия разделов для сообщений администратору
SECTION_LABELS = {
    "roulette":      "Рулетка",
    "cases":         "Все кейсы",
    "rocket":        "Ракета",
    "limited_gifts": "TG Подарки / Лимитированные подарки",
}

# Псевдонимы, которые пользователь может ввести вместо ключа
_ALIAS_MAP = {
    "limitedgifts": "limited_gifts",
    "limited":      "limited_gifts",
    "tgshop":       "limited_gifts",
}


def register(dp: Dispatcher, bot: Bot):

    # ── /hide ──────────────────────────────────────────────────────────────────

    @dp.message(Command("hide"))
    async def cmd_hide(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                f"<b>{E_STOP} Скрыть раздел</b>\n\n"
                "Использование:\n"
                "<code>/hide roulette</code> — скрыть рулетку\n"
                "<code>/hide cases</code> — скрыть все кейсы\n"
                "<code>/hide case 3</code> — скрыть кейс с ID 3\n"
                "<code>/hide rocket</code> — скрыть ракету\n"
                "<code>/hide limitedgifts</code> — скрыть TG подарки\n\n"
                "Чтобы вернуть раздел: <code>/show &lt;раздел&gt;</code>",
                parse_mode="HTML",
            )
            return

        section = args[1].lower()

        # Специальная обработка: /hide case <id>
        if section == "case" and len(args) >= 3:
            try:
                case_id = int(args[2])
            except ValueError:
                await message.answer(f"{E_CROSS} ID кейса должен быть числом.", parse_mode="HTML")
                return
            await database.set_feature_flag(f"case_{case_id}", False)
            await message.answer(
                f"{E_CHECK} Кейс <b>#{case_id}</b> скрыт из интерфейса.\n"
                f"Вернуть: <code>/show case {case_id}</code>",
                parse_mode="HTML",
            )
            return

        section = _ALIAS_MAP.get(section, section)

        if section not in SECTION_LABELS:
            await message.answer(
                f"{E_CROSS} Неизвестный раздел: <b>{section}</b>\n\n"
                "Доступные разделы: roulette, cases, case &lt;id&gt;, rocket, limitedgifts",
                parse_mode="HTML",
            )
            return

        await database.set_feature_flag(section, False)
        label = SECTION_LABELS[section]
        await message.answer(
            f"{E_CHECK} <b>{label}</b> скрыт из интерфейса.\n"
            f"Вернуть: <code>/show {args[1]}</code>",
            parse_mode="HTML",
        )

    # ── /show ──────────────────────────────────────────────────────────────────

    @dp.message(Command("show"))
    async def cmd_show(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                f"<b>{E_CHECK} Показать раздел</b>\n\n"
                "Использование:\n"
                "<code>/show roulette</code>\n"
                "<code>/show cases</code>\n"
                "<code>/show case 3</code>\n"
                "<code>/show rocket</code>\n"
                "<code>/show limitedgifts</code>",
                parse_mode="HTML",
            )
            return

        section = args[1].lower()

        # Специальная обработка: /show case <id>
        if section == "case" and len(args) >= 3:
            try:
                case_id = int(args[2])
            except ValueError:
                await message.answer(f"{E_CROSS} ID кейса должен быть числом.", parse_mode="HTML")
                return
            await database.set_feature_flag(f"case_{case_id}", True)
            await message.answer(
                f"{E_CHECK} Кейс <b>#{case_id}</b> снова виден в интерфейсе.",
                parse_mode="HTML",
            )
            return

        section = _ALIAS_MAP.get(section, section)

        if section not in SECTION_LABELS:
            await message.answer(
                f"{E_CROSS} Неизвестный раздел: <b>{section}</b>",
                parse_mode="HTML",
            )
            return

        await database.set_feature_flag(section, True)
        label = SECTION_LABELS[section]
        await message.answer(
            f"{E_CHECK} <b>{label}</b> снова виден в интерфейсе.",
            parse_mode="HTML",
        )

    # ── /featurestatus ─────────────────────────────────────────────────────────

    @dp.message(Command("featurestatus"))
    async def cmd_feature_status(message: Message):
        """Показывает текущее состояние всех флагов и режима обслуживания."""
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        flags       = await database.get_feature_flags()
        maintenance = await database.get_maintenance_mode()

        def flag_icon(v):
            return E_CHECK if v else E_CROSS

        maintenance_icon = "🔴" if maintenance else "🟢"
        lines = [
            "<b>📊 Статус интерфейса</b>\n",
            f"{maintenance_icon} Тех. перерыв: <b>{'ВКЛ' if maintenance else 'ВЫКЛ'}</b>\n",
            "<b>Разделы:</b>",
            f"  {flag_icon(flags.get('roulette', True))}  Рулетка",
            f"  {flag_icon(flags.get('cases', True))}  Все кейсы",
            f"  {flag_icon(flags.get('rocket', True))}  Ракета",
            f"  {flag_icon(flags.get('limited_gifts', True))}  TG Подарки",
        ]

        # Добавляем статус отдельных кейсов, если есть
        case_flags = {k: v for k, v in flags.items() if k.startswith("case_")}
        if case_flags:
            lines.append("\n<b>Отдельные кейсы:</b>")
            for k, v in sorted(case_flags.items()):
                cid = k.replace("case_", "")
                lines.append(f"  {flag_icon(v)}  Кейс #{cid}")

        await message.answer("\n".join(lines), parse_mode="HTML")

    # ── /maintenance ───────────────────────────────────────────────────────────

    @dp.message(Command("maintenance"))
    async def cmd_maintenance(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args         = message.text.split()
        current_mode = await database.get_maintenance_mode()

        if len(args) < 2 or args[1].lower() not in ("on", "off"):
            current = "ВКЛ 🔴" if current_mode else "ВЫКЛ 🟢"
            await message.answer(
                "<b>🔧 Режим технического обслуживания</b>\n\n"
                f"Текущий статус: <b>{current}</b>\n\n"
                "Использование:\n"
                "<code>/maintenance on</code>  — включить тех. перерыв\n"
                "<code>/maintenance off</code> — выключить тех. перерыв\n\n"
                "<i>При включении пользователи видят экран обслуживания\n"
                "и не могут выполнять никаких действий в приложении.</i>",
                parse_mode="HTML",
            )
            return

        turn_on = args[1].lower() == "on"

        if turn_on and current_mode:
            await message.answer("ℹ️ Тех. перерыв уже включён.", parse_mode="HTML")
            return
        if not turn_on and not current_mode:
            await message.answer("ℹ️ Тех. перерыв уже выключен.", parse_mode="HTML")
            return

        await database.set_maintenance_mode(turn_on)

        if turn_on:
            await message.answer(
                "🔴 <b>Технический перерыв ВКЛЮЧЁН.</b>\n\n"
                "Пользователи видят экран обслуживания.\n"
                "Выключить: <code>/maintenance off</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                "🟢 <b>Технический перерыв ВЫКЛЮЧЕН.</b>\n\n"
                "Приложение снова доступно для всех пользователей.",
                parse_mode="HTML",
            )
