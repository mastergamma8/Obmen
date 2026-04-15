// =====================================================
// i18n.js — Локализация
// =====================================================

const i18n = {
     ru: {
            nav_main: 'Главная', nav_top: 'Топ', nav_earn: 'Заработок', nav_profile: 'Профиль', nav_games: 'Игры',
            roulette_daily: 'Ежедневная Рулетка', roulette_desc: 'Крути и выигрывай призы!',
            roulette_demo: 'Демо',
            avail_gifts: 'Доступные подарки',
            collect_desc: 'Соберите <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> для разблокировки подарков',
            leaderboard: 'Таблица лидеров', earn_title: 'Заработок',
            tab_refs: 'Рефералы', tab_tasks: 'Задания',
            invite_friends: 'Приглашайте друзей',
            ref_desc: 'Вы будете получать <strong class=\"text-blue-400 glow-text\">10%</strong> пончиков с каждого подарка друга, и <strong class=\"text-yellow-400 glow-text\">10%</strong> звёзд с каждого его пополнения! <br><span class=\"text-xs opacity-70\">(Например: друг пополнил 10 <img src=\"/gifts/stars.png\" class=\"w-3 h-3 inline-block align-middle object-contain\"> — вы получите 1 <img src=\"/gifts/stars.png\" class=\"w-3 h-3 inline-block align-middle object-contain\">. Или добавил подарок за 10 <img src=\"/gifts/dount.png\" class=\"w-3 h-3 inline-block align-middle object-contain\"> — вы получите 1 <img src=\"/gifts/dount.png\" class=\"w-3 h-3 inline-block align-middle object-contain\">)</span>',            btn_invite: 'Пригласить друзей', your_refs: 'Ваши приглашенные',
            tasks_desc: 'Выполняйте задания, чтобы получать больше пончиков <img src="/gifts/dount.png" class="w-4 h-4 inline object-contain">',
            add_gift: '+ Добавить подарок', my_gifts: 'Мои подарки', for_withdraw: 'на вывод',
            wheel_fortune: 'Колесо Фортуны', spin_free: 'Крутить бесплатно',
            loading: 'Загрузка...',
            no_refs: 'У вас пока нет приглашенных друзей.', no_tasks: 'Нет доступных заданий.',
            completed: 'Выполнено', check: 'Проверить', go: 'Перейти',
            available: 'ДОСТУПНО', progress: 'ПРОГРЕСС',
            claim_gift: 'Забрать подарок', close: 'Закрыть',
            withdraw_q: 'Вы хотите вывести этот подарок? Он исчезнет из вашего профиля.',
            btn_withdraw: 'Вывести подарок', cancel: 'Отмена',
            withdraw_success: 'Подарок выведен!',
            withdraw_msg: 'Пожалуйста, напишите любое сообщение <br><span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-green-400 text-lg font-bold cursor-pointer underline decoration-green-400/50 underline-offset-4">@SpaceDonutGifts</span><br> для получения вашего подарка.',
            excellent: 'Отлично', how_to_get: 'Как получить',
            how_to_desc: 'Отправьте NFT-подарок на аккаунт <span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-blue-400 cursor-pointer underline font-bold decoration-blue-400/50 underline-offset-4">@SpaceDonutGifts</span>. После проверки он появится у вас. Подарки автоматически конвертируются в <img src="/gifts/dount.png" class="w-4 h-4 inline-block align-middle object-contain"> для открытия главных подарков!',
            understood: 'Понятно', you: 'Вы',
            no_gifts_yet: 'У вас пока нет подарков.<br><span class="inline-flex items-center gap-1 mt-1">Копите <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> чтобы получить подарок!</span>',
            click: 'Нажми', win: 'Победа!', take_prize: 'Забрать приз!',
            accumulated: 'Накоплено:', what_gifts_give: 'Какие подарки дают',
            spin_for: 'Крутить за', until_free: 'До бесплатной прокрутки:',
            h: 'ч.', free_24h: 'Раз в 24 часа бесплатно!', ref_copied: 'Реферальная ссылка скопирована!',
            task_done: 'Задание выполнено! Награда начислена.', err_check: 'Ошибка проверки.',
            err_conn: 'Ошибка соединения', err_conn_srv: 'Ошибка соединения с сервером.',
            processing: '⏳ Обработка...', gift_added: 'Подарок успешно добавлен в ваш профиль!',
            promo_title: 'Промокод', promo_input_ph: 'Введите промокод',
            promo_redeem: 'Активировать', promo_empty: 'Введите промокод',
            promo_success: 'Промокод активирован!',
            promo_case_success: 'Вы получили бесплатный кейс: {case}.',
            promo_stars_success: 'Начислено {value} ⭐ по промокоду.',
            promo_donuts_success: 'Начислено {value} 🍩 по промокоду.',
            promo_case_reward: 'Кейс по промокоду',
            promo_stars_reward: 'Звёзды по промокоду',
            promo_donuts_reward: 'Пончики по промокоду',
            promo_case_opened: 'Кейс открыт бесплатно!',
            promo_open_free: 'Открыть бесплатно',
            promo_error: 'Не удалось активировать промокод',
            withdrawing: '⏳ Выводим...', err_network: 'Ошибка сети. Попробуйте позже.',
            share_text: 'Заходи в Space Donut и забирай крутые подарки! 🎁',
            donuts_text: 'пончиков!',
            search_ph: 'Поиск...', sort_title: 'Сортировка',
            sort_val_desc: 'Сначала дорогие', sort_val_asc: 'Сначала дешевые',
            sort_name_asc: 'По имени (А-Я)', sort_name_desc: 'По имени (Я-А)', not_found: 'Ничего не найдено',
            history_btn: 'История операций', history_title: 'История операций',
            history_empty: 'История пуста. Совершите первые действия!',
            hist_gift_added: 'Добавлен подарок', hist_roulette_paid: 'Платная рулетка',
            hist_roulette_win: 'Выигрыш в рулетке', hist_roulette_free: 'Бесплатная рулетка',
            hist_claim_gift: 'Куплен подарок', hist_withdraw: 'Вывод подарка',
            hist_task: 'Задание выполнено', hist_referral: 'Реферальный бонус', hist_referral_stars: 'Реферальный бонус ⭐',
            ref_bonus_donuts_label: '10% пончиков', ref_bonus_donuts_sub: 'с подарка друга',
            ref_bonus_stars_label: '10% звёзд', ref_bonus_stars_sub: 'с пополнения друга',

            // КЕЙСЫ
            games_title: 'Игры',
            cases_title: 'Кейсы', cases_desc: 'Открывай и выигрывай редкие подарки!',
            cases_list_title: 'Доступные кейсы',
            open_for: 'Открыть за', possible_drops: 'Возможный дроп:',
            not_enough_donuts: 'Недостаточно пончиков!',
            not_enough_stars: 'Недостаточно звёзд!',
            case_opening: 'Открываем...', case_opened: 'Кейс открыт!',
            case_almost: 'Почти...',
            case_spinning: 'Вращается...',
            case_opening_label: 'Открываем кейс',
            case_victory: 'Победа!',
            cases_demo: 'Демо',
            type_donuts: 'Пончики',
            type_stars: 'Звёзды',
            type_gift: 'Подарок',
            take_prize_case: 'Забрать приз!',

            // БЕСПЛАТНЫЙ КЕЙС
            free_case_title: 'Бесплатный кейс',
            free_case_desc: 'Открывай бесплатно раз в 24 часа!',
            free_case_open_btn: 'Открыть бесплатно!',
            free_case_cooldown: 'Следующий бесплатный кейс через:',
            free_case_wait: 'Ожидайте',
            free_case_not_yet: 'Бесплатный кейс будет доступен через {h}ч {m}мин.',

            // РАКЕТА И ПОПОЛНЕНИЕ
            rocket_title: 'Ракета', rocket_desc: 'Успей забрать иксы до краша!',
            bet_amount: 'Сумма ставки:', place_bet: 'Полететь',
            cashout: 'Забрать', crashed: 'Улетела!', you_won: 'Вы выиграли',
            rocket_starting: 'Подготовка к взлету...',
            rocket_win_btn: 'Успех!',
            rocket_err_limits: 'Ставка вне лимитов',
            rocket_cant_close: 'Дождитесь окончания полета!',
            rocket_demo: 'Демо',
            auto_cashout_label: 'Авто-вывод (множитель):',
            auto_cashout_triggered: 'Авто-вывод сработал!',
            topup_title: 'Пополнение', topup_desc: 'Выберите количество или введите свое',
            btn_buy: 'Купить', topup_success: 'Звезды успешно зачислены!', err_invalid_amount: 'Неверная сумма',
            tab_rich: 'Богачи',
            tab_rocket: 'Сорвиголовы',
            tab_lucky: 'Счастливчики',
            lb_empty_rocket: 'Пока нет данных за эту неделю 🚀',
            lb_empty_lucky: 'Пока никто не открывал кейсы 🍀',
            gift_cooldown_claim: 'Вы уже покупали подарок за пончики.',
            gift_cooldown_withdraw: 'Вы уже выводили подарок.',
            cooldown_claim_wait: 'Вы уже покупали подарок. Следующая покупка доступна через {h}ч {m}мин.',
            cooldown_withdraw_wait: 'Вы уже выводили подарок. Следующий вывод доступен через {h}ч {m}мин.',

            // ВЫВОД С КОМИССИЕЙ
            withdraw_confirm_title: 'Вывод подарка',
            withdraw_confirm_desc: 'Для вывода этого подарка необходимо оплатить комиссию сети.',
            withdraw_confirm_btn: 'Вывести за',
            btn_pay_withdraw: 'Вывести за',
            not_enough_stars_alert: 'Недостаточно звезд для вывода!',

            // TG ПОДАРКИ
            tg_gift_modal_title: 'Telegram подарок',
            tg_gift_modal_desc: 'Можно вывести его в Telegram, обменять на звёзды или оставить в инвентаре.',
            btn_tg_withdraw: 'Вывести подарок',
            btn_tg_exchange: 'Обменять',
            btn_tg_keep: 'Оставить в инвентаре',
            tg_withdraw_success: 'Подарок отправлен в Telegram!',
            tg_exchange_success: 'Подарок обменян на звёзды!',
            btn_exchange_donuts: 'Обменять на пончики',
            exchange_donuts_success: 'Подарок обменян на пончики!',
            btn_exchange_stars: 'Обменять на',
            exchange_stars_success: 'Подарок обменян на звёзды!',
            hist_exchange_gift_donuts: 'Обмен подарка на пончики',
            tg_withdraw_error: 'Не удалось отправить подарок. Попробуйте позже.',
            hist_tg_withdraw: 'Вывод Telegram-подарка',
            hist_tg_exchange: 'Обмен Telegram-подарка',
            hist_tg_win_roulette: 'Выигрыш Telegram-подарка в рулетке',
            hist_tg_win_case: 'Выигрыш Telegram-подарка из кейса',

            // УВЕДОМЛЕНИЯ (notify-modal заголовки)
            notify_error: 'Ошибка',
            notify_success: 'Успешно',
            notify_warning: 'Внимание',
            notify_info: 'Информация',
            err_payment: 'Ошибка оплаты',
            err_invoice: 'Ошибка создания инвойса',
            no_name: 'Без имени',

            // МОДАЛ ТРЕБОВАНИЙ ДЛЯ ВЫВОДА
            wr_modal_title: 'Условия вывода',
            wr_modal_subtitle: 'Выполните все условия, чтобы вывести подарок',
            wr_check_btn: 'Проверить выполнение',
            wr_checking: 'Проверяем...',
            wr_all_done: 'Все условия выполнены!',
            wr_unmet_label: 'Не выполнено:',
            wr_btn_invite: 'Пригласить',
            wr_btn_complete: 'Выполнить',
            wr_err_network: 'Ошибка сети. Попробуйте позже.',
            limit_reached: 'Лимит достигнут. Попробуйте позже.',

            // TG МАГАЗИН
            tg_shop_title: 'Лимитированные подарки',
            tg_shop_banner_desc: 'Купи подарок за <span class="font-bold text-yellow-300 inline-flex items-center gap-1">{price} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle object-contain"></span> и получи в Telegram!',
            tg_shop_header_desc: 'Цена: <span class="font-bold text-yellow-300 inline-flex items-center gap-1">{price} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle object-contain"></span> за подарок',
            tg_buy_modal_title: 'Купить подарок?',
            tg_buy_modal_desc: 'Подарок будет отправлен вам в Telegram',
            tg_buy_cost_label: 'Стоимость',
            tg_buy_balance_label: 'Ваш баланс',
            tg_buy_confirm_btn: 'Купить за {price}',
            tg_buy_sending: '⏳ Отправляем...',
            tg_buy_success: '🎁 Подарок успешно отправлен в Telegram!',
            tg_buy_error: 'Произошла ошибка',
        },
        en: {
            nav_main: 'Main', nav_top: 'Top', nav_earn: 'Earn', nav_profile: 'Profile', nav_games: 'Games',
            roulette_daily: 'Daily Roulette', roulette_desc: 'Spin and win prizes!',
            roulette_demo: 'Demo',
            avail_gifts: 'Available gifts',
            collect_desc: 'Collect <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> to unlock gifts',
            leaderboard: 'Leaderboard', earn_title: 'Earn',
            tab_refs: 'Referrals', tab_tasks: 'Tasks',
            invite_friends: 'Invite friends',
            ref_desc: 'You will receive <strong class=\"text-blue-400 glow-text\">10%</strong> donuts from each friend&#39;s gift, and <strong class=\"text-yellow-400 glow-text\">10%</strong> stars from each top-up they make! <br><span class=\"text-xs opacity-70\">(Example: friend tops up 10 <img src=\"/gifts/stars.png\" class=\"w-3 h-3 inline-block align-middle object-contain\"> — you get 1 <img src=\"/gifts/stars.png\" class=\"w-3 h-3 inline-block align-middle object-contain\">. Or adds a gift for 10 <img src=\"/gifts/dount.png\" class=\"w-3 h-3 inline-block align-middle object-contain\"> — you get 1 <img src=\"/gifts/dount.png\" class=\"w-3 h-3 inline-block align-middle object-contain\">)</span>',            btn_invite: 'Invite friends', your_refs: 'Your referrals',
            tasks_desc: 'Complete tasks to get more donuts <img src="/gifts/dount.png" class="w-4 h-4 inline object-contain">',
            add_gift: '+ Add gift', my_gifts: 'My gifts', for_withdraw: 'for withdraw',
            wheel_fortune: 'Wheel of Fortune', spin_free: 'Spin for free',
            loading: 'Loading...',
            no_refs: 'You have no invited friends yet.', no_tasks: 'No tasks available.',
            completed: 'Completed', check: 'Check', go: 'Go',
            available: 'AVAILABLE', progress: 'PROGRESS',
            claim_gift: 'Claim gift', close: 'Close',
            withdraw_q: 'Do you want to withdraw this gift? It will be removed from your profile.',
            btn_withdraw: 'Withdraw gift', cancel: 'Cancel',
            withdraw_success: 'Gift withdrawn!',
            withdraw_msg: 'Please write any message to <br><span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-green-400 text-lg font-bold cursor-pointer underline decoration-green-400/50 underline-offset-4">@SpaceDonutGifts</span><br> to receive your gift.',
            excellent: 'Excellent', how_to_get: 'How to get',
            how_to_desc: 'Send an NFT gift to the account <span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-blue-400 cursor-pointer underline font-bold decoration-blue-400/50 underline-offset-4">@SpaceDonutGifts</span>. After verification, it will appear here. Gifts are automatically converted to <img src="/gifts/dount.png" class="w-4 h-4 inline-block align-middle object-contain"> to unlock main gifts!',
            understood: 'Understood', you: 'You',
            no_gifts_yet: 'You have no gifts yet.<br><span class="inline-flex items-center gap-1 mt-1">Collect <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> to get a gift!</span>',
            click: 'Click', win: 'Victory!', take_prize: 'Take prize!',
            accumulated: 'Accumulated:', what_gifts_give: 'What gifts give',
            spin_for: 'Spin for', until_free: 'Until free spin:',
            h: 'h.', free_24h: 'Once per 24 hours free!', ref_copied: 'Referral link copied!',
            task_done: 'Task completed! Reward credited.', err_check: 'Verification error.',
            err_conn: 'Connection error', err_conn_srv: 'Server connection error.',
            processing: '⏳ Processing...', gift_added: 'Gift successfully added to your profile!',
            promo_title: 'Promo code', promo_input_ph: 'Enter promo code',
            promo_redeem: 'Redeem', promo_empty: 'Enter a promo code',
            promo_success: 'Promo code activated!',
            promo_case_success: 'You received a free case: {case}.',
            promo_stars_success: '{value} ⭐ added via promo code.',
            promo_donuts_success: '{value} 🍩 added via promo code.',
            promo_case_reward: 'Case promo code',
            promo_stars_reward: 'Stars promo code',
            promo_donuts_reward: 'Donuts promo code',
            promo_case_opened: 'Case opened for free!',
            promo_open_free: 'Open for free',
            promo_error: 'Could not redeem promo code',
            withdrawing: '⏳ Withdrawing...', err_network: 'Network error. Try again later.',
            share_text: 'Join Space Donut and claim cool gifts! 🎁',
            donuts_text: 'donuts!',
            search_ph: 'Search...', sort_title: 'Sort by',
            sort_val_desc: 'Highest value', sort_val_asc: 'Lowest value',
            sort_name_asc: 'By name (A-Z)', sort_name_desc: 'By name (Z-A)', not_found: 'Nothing found',
            history_btn: 'Transaction history', history_title: 'Transaction history',
            history_empty: 'History is empty. Make your first actions!',
            hist_gift_added: 'Gift added', hist_roulette_paid: 'Paid roulette',
            hist_roulette_win: 'Roulette win', hist_roulette_free: 'Free roulette',
            hist_claim_gift: 'Gift purchased', hist_withdraw: 'Gift withdrawn',
            hist_task: 'Task completed', hist_referral: 'Referral bonus', hist_referral_stars: 'Referral bonus ⭐',
            ref_bonus_donuts_label: '10% donuts', ref_bonus_donuts_sub: "from friend&#39;s gift",
            ref_bonus_stars_label: '10% stars', ref_bonus_stars_sub: "from friend&#39;s top-up",

            // CASES
            games_title: 'Games',
            cases_title: 'Cases', cases_desc: 'Open and win rare gifts!',
            cases_list_title: 'Available Cases',
            open_for: 'Open for', possible_drops: 'Possible drops:',
            not_enough_donuts: 'Not enough donuts!',
            not_enough_stars: 'Not enough stars!',
            case_opening: 'Opening...', case_opened: 'Case opened!',
            case_almost: 'Almost...',
            case_spinning: 'Spinning...',
            case_opening_label: 'Opening case',
            case_victory: 'Victory!',
            cases_demo: 'Demo',
            type_donuts: 'Donuts',
            type_stars: 'Stars',
            type_gift: 'Gift',
            take_prize_case: 'Claim prize!',

            // FREE CASE
            free_case_title: 'Free Case',
            free_case_desc: 'Open for free once every 24 hours!',
            free_case_open_btn: 'Open for Free!',
            free_case_cooldown: 'Next free case in:',
            free_case_wait: 'Wait',
            free_case_not_yet: 'Free case available in {h}h {m}m.',

            // ROCKET & TOP-UP
            rocket_title: 'Rocket', rocket_desc: 'Grab the multiplier before it crashes!',
            bet_amount: 'Bet Amount:', place_bet: 'Fly',
            cashout: 'Cashout', crashed: 'Crashed!', you_won: 'You won',
            rocket_starting: 'Preparing for launch...',
            rocket_win_btn: 'Success!',
            rocket_err_limits: 'Bet out of limits',
            rocket_cant_close: 'Wait until the flight ends!',
            rocket_demo: 'Demo',
            auto_cashout_label: 'Auto-cashout (multiplier):',
            auto_cashout_triggered: 'Auto-cashout triggered!',
            topup_title: 'Top up', topup_desc: 'Select amount or enter custom',
            btn_buy: 'Buy', topup_success: 'Stars successfully credited!', err_invalid_amount: 'Invalid amount',
            tab_rich: 'Whales',
            tab_rocket: 'Daredevils',
            tab_lucky: 'Lucky Ones',
            lb_empty_rocket: 'No data for this week yet 🚀',
            lb_empty_lucky: 'No cases opened yet 🍀',
            gift_cooldown_claim: 'You have already purchased a gift with donuts.',
            gift_cooldown_withdraw: 'You have already withdrawn a gift.',
            cooldown_claim_wait: 'You have already bought a gift. Next purchase available in {h}h {m}m.',
            cooldown_withdraw_wait: 'You have already withdrawn a gift. Next withdrawal available in {h}h {m}m.',

            // WITHDRAW WITH FEE
            withdraw_confirm_title: 'Withdraw Gift',
            withdraw_confirm_desc: 'To withdraw this gift, you need to pay the network fee.',
            withdraw_confirm_btn: 'Withdraw for',
            btn_pay_withdraw: 'Withdraw for',
            not_enough_stars_alert: 'Not enough stars to withdraw!',

            // TG GIFTS
            tg_gift_modal_title: 'Telegram Gift',
            tg_gift_modal_desc: 'You can send it to Telegram, exchange it for stars, or keep it in your inventory.',
            btn_tg_withdraw: 'Send to Telegram',
            btn_tg_exchange: 'Exchange',
            btn_tg_keep: 'Keep in inventory',
            tg_withdraw_success: 'Gift sent to Telegram!',
            tg_exchange_success: 'Gift exchanged for stars!',
            btn_exchange_donuts: 'Exchange for donuts',
            exchange_donuts_success: 'Gift exchanged for donuts!',
            btn_exchange_stars: 'Exchange for',
            exchange_stars_success: 'Gift exchanged for stars!',
            hist_exchange_gift_donuts: 'Gift exchanged for donuts',
            tg_withdraw_error: 'Failed to send the gift. Please try again later.',
            hist_tg_withdraw: 'Telegram gift withdrawn',
            hist_tg_exchange: 'Telegram gift exchanged',
            hist_tg_win_roulette: 'Telegram gift won in roulette',
            hist_tg_win_case: 'Telegram gift won from case',

            // NOTIFICATIONS (notify-modal titles)
            notify_error: 'Error',
            notify_success: 'Success',
            notify_warning: 'Warning',
            notify_info: 'Information',
            err_payment: 'Payment error',
            err_invoice: 'Failed to create invoice',
            no_name: 'No name',

            // WITHDRAW REQUIREMENTS MODAL
            wr_modal_title: 'Withdrawal Requirements',
            wr_modal_subtitle: 'Complete all requirements to withdraw your gift',
            wr_check_btn: 'Check completion',
            wr_checking: 'Checking...',
            wr_all_done: 'All requirements met!',
            wr_unmet_label: 'Not completed:',
            wr_btn_invite: 'Invite',
            wr_btn_complete: 'Complete',
            wr_err_network: 'Network error. Please try again.',
            limit_reached: 'Limit reached. Please try again later.',

            // TG SHOP
            tg_shop_title: 'Limited gifts',
            tg_shop_banner_desc: 'Buy a gift for <span class="font-bold text-yellow-300 inline-flex items-center gap-1">{price} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle object-contain"></span> and receive it in Telegram!',
            tg_shop_header_desc: 'Price: <span class="font-bold text-yellow-300 inline-flex items-center gap-1">{price} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle object-contain"></span> per gift',
            tg_buy_modal_title: 'Buy a gift?',
            tg_buy_modal_desc: 'The gift will be sent to your Telegram',
            tg_buy_cost_label: 'Cost',
            tg_buy_balance_label: 'Your balance',
            tg_buy_confirm_btn: 'Buy for {price}',
            tg_buy_sending: '⏳ Sending...',
            tg_buy_success: '🎁 Gift successfully sent to Telegram!',
            tg_buy_error: 'An error occurred',
        }
};

function setLang(lang) {
    vibrate('light');
    currentLang = lang;
    try { localStorage.setItem('appLang', lang); } catch(e) {}

    const btnRu = document.getElementById('lang-ru');
    const btnEn = document.getElementById('lang-en');
    const activeClass   = 'px-3 py-1 rounded-full text-[10px] font-extrabold transition-all bg-blue-500 text-white shadow-[0_0_10px_rgba(59,130,246,0.5)]';
    const inactiveClass = 'px-3 py-1 rounded-full text-[10px] font-extrabold transition-all text-white/50 hover:text-white';
    if (btnRu) btnRu.className = lang === 'ru' ? activeClass : inactiveClass;
    if (btnEn) btnEn.className = lang === 'en' ? activeClass : inactiveClass;

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[lang][key] !== undefined) {
            let val = i18n[lang][key];
            if (key === 'tg_shop_banner_desc' || key === 'tg_shop_header_desc' || key === 'tg_buy_confirm_btn') {
                const _p = (typeof tgGifts !== 'undefined' && tgGifts[2011])
                    ? (tgGifts[2011].price ?? 60) : 60;
                val = val.replace(/\{price\}/g, _p);
            }
            el.innerHTML = val;
        }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (i18n[lang][key] !== undefined) el.placeholder = i18n[lang][key];
    });

    const el = (id) => document.getElementById(id);
    if (el('collect-text'))  el('collect-text').innerHTML  = i18n[lang].collect_desc;
    if (el('ref-desc'))      el('ref-desc').innerHTML      = i18n[lang].ref_desc;
    if (el('tasks-desc'))    el('tasks-desc').innerHTML    = i18n[lang].tasks_desc;
    if (el('how-to-desc'))   el('how-to-desc').innerHTML   = i18n[lang].how_to_desc;
    if (el('withdraw-msg'))  el('withdraw-msg').innerHTML  = i18n[lang].withdraw_msg;

    // Подставляем реальную цену вместо {price} в описаниях TG-магазина
    const _tgShopPrice = (typeof tgGifts !== 'undefined' && tgGifts[2011])
        ? (tgGifts[2011].price ?? 60) : 60;
    const _fillPrice = (key) => (i18n[lang][key] || '').replace(/\{price\}/g, _tgShopPrice);
    if (el('tg-shop-banner-desc')) el('tg-shop-banner-desc').innerHTML = _fillPrice('tg_shop_banner_desc');
    if (el('tg-shop-header-desc')) el('tg-shop-header-desc').innerHTML = _fillPrice('tg_shop_header_desc');

    updateUI();
    if (el('page-leaderboard') && !el('page-leaderboard').classList.contains('hidden-tab') && typeof loadLeaderboard === 'function') loadLeaderboard();
    if (el('page-earn')        && !el('page-earn').classList.contains('hidden-tab') && typeof loadEarnData === 'function') loadEarnData();
    if (el('page-roulette')    && !el('page-roulette').classList.contains('hidden-tab') && typeof fetchRouletteInfo === 'function') fetchRouletteInfo();
    if (el('page-games')       && !el('page-games').classList.contains('hidden-tab') && typeof renderCasesGrid === 'function') renderCasesGrid();
    if (rouletteConfig?.items  && el('page-roulette') && !el('page-roulette').classList.contains('hidden-tab') && typeof renderRouletteWheel === 'function') renderRouletteWheel();
    if (el('main-gift-modal')  && !el('main-gift-modal').classList.contains('hidden') && typeof renderBaseGiftsList === 'function') renderBaseGiftsList();
}

window.setLang = setLang;