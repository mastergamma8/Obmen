# database.py
# Единая точка входа для всего кода проекта.
# Весь остальной код (routers, handlers, workers) импортирует отсюда —
# ничего менять в роутерах не нужно.
#
# Структура модулей:
#   db_core.py        — константы подключения (DB_NAME, кулдауны)
#   db_init.py        — создание таблиц и миграции (init_db, init_bank→здесь реэкспорт из db_bank)
#   db_users.py       — пользователи, баланс, подарки, кулдауны
#   db_history.py     — история действий, задания
#   db_referrals.py   — реферальная система
#   db_leaderboard.py — таблицы лидеров
#   db_bank.py        — банк, RTP, выплаты

from db_core import DB_NAME, GIFT_WITHDRAW_COOLDOWN, GIFT_CLAIM_COOLDOWN  # noqa: F401

from db_init import init_db  # noqa: F401

from db_users import (  # noqa: F401
    upsert_user,
    get_user_profile,
    get_user_data,
    get_all_user_ids,
    add_points_to_user,
    add_stars_to_user,
    deduct_stars,
    update_last_free_spin,
    get_users_to_notify,
    mark_user_notified,
    get_last_free_case,
    update_last_free_case,
    get_users_to_notify_free_case,
    mark_user_notified_free_case,
    claim_main_gift,
    get_last_gift_claim,
    update_last_gift_claim,
    get_users_to_notify_gift_claim,
    mark_user_notified_gift_claim,
    get_last_gift_withdraw,
    update_last_gift_withdraw,
    get_users_to_notify_gift_withdraw,
    mark_user_notified_gift_withdraw,
    add_gift_to_user,
    remove_gift_from_user,
    get_user_gifts,
)

from db_history import (  # noqa: F401
    get_completed_tasks,
    mark_task_completed,
    add_history_entry,
    log_action,
    get_user_history,
    get_user_history_count,
)

from db_referrals import (  # noqa: F401
    set_referrer,
    get_referrer,
    get_referrals,
    distribute_referral_bonus,
)

from db_leaderboard import (  # noqa: F401
    get_leaderboard,
    get_rocket_leaderboard,
    get_lucky_leaderboard,
)

from db_bank import (  # noqa: F401
    init_bank,
    get_bank,
    bank_deposit,
    bank_can_payout,
    bank_payout,
    bank_get_max_payout,
    bank_add_stars,
    bank_add_donuts,
)
