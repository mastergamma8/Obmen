// =====================================================
// ПРОФИЛЬ И ВЫВОД
// =====================================================
function isRealTgGift(giftId) {
    return !!(tgGifts && tgGifts[giftId] && tgGifts[giftId].tg_gift_id);
}

function getGiftDefinitionById(giftId) {
    return mainGifts[giftId] || tgGifts[giftId] || baseGifts[giftId] || null;
}

function getTgGiftExchangeStars(giftId) {
    const giftDef = getGiftDefinitionById(giftId);
    const baseValue = giftDef ? parseInt(giftDef.required_value || giftDef.value || 0) : 0;
    return isRealTgGift(giftId) ? baseValue + 10 : 0;
}

async function performGiftAction(giftId, action) {
    const endpoint = action === 'exchange' ? '/api/exchange' : '/api/withdraw';
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({ gift_id: giftId })
    });
    const data = await res.json();
    return { res, data };
}

function syncGiftStateFromResponse(data) {
    if (!data) return;
    if (data.balance !== undefined) myBalance = data.balance;
    if (data.stars !== undefined) myStars = data.stars;
    if (data.user_gifts) myGifts = data.user_gifts;
    if (typeof updateUI === 'function') updateUI();
    if (typeof renderProfile === 'function') renderProfile();
}

function renderProfile() {
    const el = (id) => document.getElementById(id);
    if (tgUser.first_name) el('profile-name').innerText = tgUser.first_name;
    if (tgUser.username)   el('profile-username').innerText = `@${tgUser.username}`;
    if (tgUser.photo_url)  el('profile-avatar').src = tgUser.photo_url;
    
    const grid = el('profile-gifts-grid');
    if (!grid) return;
    grid.innerHTML = '';
    let hasGifts = false;
    
    for (const [id, amount] of Object.entries(myGifts)) {
        const giftDef = getGiftDefinitionById(id);
        
        if (amount > 0 && giftDef) {
            hasGifts = true;
            grid.innerHTML += `
                <div onclick="openWithdrawModal('${id}')" class="glass rounded-2xl p-4 flex flex-col items-center relative transition-transform active:scale-95 cursor-pointer border border-green-500/20 bg-green-500/5">
                    <div class="absolute -top-2 -right-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold w-7 h-7 rounded-full flex items-center justify-center border-2 border-[#0f172a] shadow-lg z-10">${amount}</div>
                    <div class="bg-black/20 w-16 h-16 rounded-xl flex items-center justify-center mb-3 border border-white/5 shadow-inner">
                        <img src="${escapeHtml(getImgSrc(giftDef.photo))}" class="w-12 h-12 object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/48'">
                    </div>
                    <span class="text-xs text-center font-bold text-white mb-1 leading-tight">${escapeHtml(giftDef.name)}</span>
                    <span class="text-[10px] font-bold text-gray-400 bg-black/30 px-2 py-0.5 rounded-full mt-auto">${i18n[currentLang].click}</span>
                </div>`;
        }
    }
    if (!hasGifts) {
        grid.innerHTML = `<div class="col-span-3 text-center text-blue-200/40 text-sm mt-6 border border-white/5 border-dashed rounded-2xl p-6">${i18n[currentLang].no_gifts_yet}</div>`;
    }
}

let currentWithdrawGiftId = null;
let currentWithdrawIsTgGift = false;
let currentWithdrawExchangeStars = 0;
let withdrawFeeAmount = (window.appConfig && window.appConfig.withdraw_fee) ? window.appConfig.withdraw_fee : 25;

function openWithdrawModal(giftId) {
    vibrate('medium');
    currentWithdrawGiftId = giftId;
    const giftDef = getGiftDefinitionById(giftId);
    if (!giftDef) return;

    currentWithdrawIsTgGift = isRealTgGift(giftId);
    currentWithdrawExchangeStars = getTgGiftExchangeStars(giftId);

    const titleEl = document.getElementById('wcm-title');
    const descEl = document.getElementById('wcm-desc');
    const imgEl = document.getElementById('wcm-gift-img');
    const nameEl = document.getElementById('wcm-gift-name');
    const feeRow = document.getElementById('wcm-fee-row');
    const tgActions = document.getElementById('wcm-tg-actions');
    const exchangeInfo = document.getElementById('wcm-exchange-info');
    const btnConfirm = document.getElementById('wcm-btn-confirm');
    const btnConfirmLabel = document.getElementById('wcm-btn-confirm-label');
    const feeAmount = document.getElementById('wcm-fee-amount');

    imgEl.src = getImgSrc(giftDef.photo);
    nameEl.innerText = giftDef.name;

    if (currentWithdrawIsTgGift) {
        titleEl.innerText = i18n[currentLang].tg_gift_modal_title;
        descEl.innerText = i18n[currentLang].tg_gift_modal_desc;
        feeRow.classList.add('hidden');
        tgActions.classList.remove('hidden');
        exchangeInfo.classList.remove('hidden');
        
        // Используем иконку звезды вместо емодзи
        exchangeInfo.innerHTML = `${i18n[currentLang].btn_tg_exchange}: +${currentWithdrawExchangeStars} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle pb-[2px] object-contain">`;
        document.getElementById('wcm-btn-withdraw-tg').textContent = i18n[currentLang].btn_tg_withdraw;
        document.getElementById('wcm-btn-exchange').innerHTML = `<div class="flex items-center justify-center gap-1.5"><span>${i18n[currentLang].btn_tg_exchange} +${currentWithdrawExchangeStars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
        document.getElementById('wcm-btn-keep').textContent = i18n[currentLang].btn_tg_keep;
        
        document.getElementById('wcm-btn-withdraw-tg').onclick = () => confirmWithdrawGift(giftId, true);
        document.getElementById('wcm-btn-exchange').onclick = () => confirmExchangeGift(giftId);
        document.getElementById('wcm-btn-keep').onclick = () => closeModal('withdraw-confirm-modal');
    } else {
        titleEl.innerText = i18n[currentLang].withdraw_confirm_title;
        descEl.innerText = i18n[currentLang].withdraw_confirm_desc;
        feeRow.classList.remove('hidden');
        tgActions.classList.add('hidden');
        exchangeInfo.classList.add('hidden');
        btnConfirmLabel.innerText = 'Вывести за';
        feeAmount.innerText = withdrawFeeAmount;
        btnConfirm.onclick = () => confirmWithdrawGift(giftId, false);
    }

    openModal('withdraw-confirm-modal');
}

async function confirmWithdrawGift(giftId, isTgGift = false) {
    vibrate('heavy');
    const btn = isTgGift ? document.getElementById('wcm-btn-withdraw-tg') : document.getElementById('wcm-btn-confirm');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = `<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;
    btn.disabled = true;

    try {
        const { res, data } = await performGiftAction(giftId, 'withdraw');

        if (res.status === 429) {
            if (data.detail && data.detail.error === 'cooldown') {
                const msg = i18n[currentLang].cooldown_withdraw_wait
                    .replace('{h}', data.detail.hours)
                    .replace('{m}', data.detail.minutes);
                closeModal('withdraw-confirm-modal');
                tg.showAlert(`⏳ ${msg}`);
            } else {
                tg.showAlert(`⏳ ${data.detail || 'Limit reached'}`);
            }
            return;
        }

        if (!res.ok) {
            if (data.detail === 'not_enough_stars') {
                closeModal('withdraw-confirm-modal');
                tg.showAlert(i18n[currentLang].not_enough_stars_alert, () => {
                    openModal('topup-stars-modal');
                });
                return;
            }
            throw new Error(data.detail || 'Withdraw error');
        }

        syncGiftStateFromResponse(data);
        closeModal('withdraw-confirm-modal');

        if (isTgGift) {
            tg.showAlert('Подарок отправлен.');
        } else {
            setTimeout(() => openModal('success-withdraw-modal'), 300);
        }

    } catch(e) {
        console.error(e);
        tg.showAlert(i18n[currentLang].err_conn);
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

async function confirmExchangeGift(giftId) {
    vibrate('heavy');
    const btn = document.getElementById('wcm-btn-exchange');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = `<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;
    btn.disabled = true;

    try {
        const { res, data } = await performGiftAction(giftId, 'exchange');
        if (!res.ok) throw new Error(data.detail || 'Exchange error');
        syncGiftStateFromResponse(data);
        closeModal('withdraw-confirm-modal');
        tg.showAlert(`${i18n[currentLang].tg_exchange_success} +${data.exchange_stars || getTgGiftExchangeStars(giftId)} ⭐`);
    } catch (e) {
        console.error(e);
        tg.showAlert(i18n[currentLang].err_conn);
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

function configureCaseGiftActionsIfNeeded(giftId, source = 'case', isDemo = false) {
    const actionsBox = document.getElementById(source === 'case' ? 'cam-gift-actions' : 'rr-gift-actions');
    const closeBtn = document.getElementById(source === 'case' ? 'cam-btn-close' : 'rr-btn-close');
    const withdrawBtn = document.getElementById(source === 'case' ? 'cam-btn-withdraw' : 'rr-btn-withdraw');
    const exchangeBtn = document.getElementById(source === 'case' ? 'cam-btn-exchange' : 'rr-btn-exchange');
    const keepBtn = document.getElementById(source === 'case' ? 'cam-btn-keep' : 'rr-btn-keep');

    if (!actionsBox || !closeBtn || !withdrawBtn || !exchangeBtn || !keepBtn) return;

    const giftDef = getGiftDefinitionById(giftId);
    if (!giftDef || !isRealTgGift(giftId)) {
        actionsBox.classList.add('hidden');
        closeBtn.classList.remove('hidden');
        return;
    }

    const exchangeStars = getTgGiftExchangeStars(giftId);
    actionsBox.classList.remove('hidden');
    closeBtn.classList.add('hidden');
    withdrawBtn.textContent = i18n[currentLang].btn_tg_withdraw;
    
    // Используем иконку звезды вместо емодзи
    exchangeBtn.innerHTML = `<div class="flex items-center justify-center gap-1.5"><span>${i18n[currentLang].btn_tg_exchange} +${exchangeStars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
    keepBtn.textContent = i18n[currentLang].btn_tg_keep;

    withdrawBtn.onclick = async () => {
        if (isDemo) {
            if (source === 'case') closeCaseAnimation();
            else closeModal('roulette-result-modal');
            return;
        }
        try {
            const { res, data } = await performGiftAction(giftId, 'withdraw');
            if (!res.ok) throw new Error(data.detail || 'Withdraw error');
            syncGiftStateFromResponse(data);
            if (source === 'case') closeCaseAnimation();
            else closeModal('roulette-result-modal');
            tg.showAlert(i18n[currentLang].tg_withdraw_success);
        } catch (e) {
            console.error(e);
            tg.showAlert((e && e.message) ? e.message : (i18n[currentLang].err_conn || 'Connection error'));
        }
    };

    exchangeBtn.onclick = async () => {
        if (isDemo) {
            if (source === 'case') closeCaseAnimation();
            else closeModal('roulette-result-modal');
            return;
        }
        try {
            const { res, data } = await performGiftAction(giftId, 'exchange');
            if (!res.ok) throw new Error(data.detail || 'Exchange error');
            syncGiftStateFromResponse(data);
            if (source === 'case') closeCaseAnimation();
            else closeModal('roulette-result-modal');
            tg.showAlert(`${i18n[currentLang].tg_exchange_success} +${data.exchange_stars || exchangeStars} ⭐`);
        } catch (e) {
            console.error(e);
            tg.showAlert((e && e.message) ? e.message : (i18n[currentLang].err_conn || 'Connection error'));
        }
    };

    keepBtn.onclick = () => {
        if (source === 'case') closeCaseAnimation();
        else closeModal('roulette-result-modal');
    };
}

// =====================================================
// ИСТОРИЯ ОПЕРАЦИЙ
// =====================================================

// Список иконок и цветов для всех типов событий истории
const HISTORY_ICONS = {
    topup_stars:          { icon: '⭐', color: 'green',  sign: '+' },
    gift_added:           { icon: '🎁', color: 'green',  sign: '+' },
    roulette_win_donuts:  { icon: '🎰', color: 'green',  sign: '+' },
    roulette_win_stars:   { icon: '🎰', color: 'green',  sign: '+' },
    roulette_win_gift:    { icon: '🎁', color: 'green',  sign: null },
    roulette_win_tg_gift: { icon: '🎁', color: 'green',  sign: null },
    roulette_paid_donuts: { icon: '🎰', color: 'red',    sign: '-' },
    roulette_paid_stars:  { icon: '🎰', color: 'red',    sign: '-' },
    roulette_paid:        { icon: '🎰', color: 'red',    sign: '-' },
    case_win_donuts:      { icon: '📦', color: 'green',  sign: '+' },
    case_win_stars:       { icon: '📦', color: 'green',  sign: '+' },
    case_win_gift:        { icon: '🎁', color: 'green',  sign: null },
    case_win_tg_gift:     { icon: '🎁', color: 'green',  sign: null },
    case_paid_donuts:     { icon: '📦', color: 'red',    sign: '-' },
    case_paid_stars:      { icon: '📦', color: 'red',    sign: '-' },
    rocket_win_donuts:    { icon: '🚀', color: 'green',  sign: '+' },
    rocket_win_stars:     { icon: '🚀', color: 'green',  sign: '+' },
    rocket_lose_donuts:   { icon: '💥', color: 'red',    sign: '-' },
    rocket_lose_stars:    { icon: '💥', color: 'red',    sign: '-' },
    claim_gift:           { icon: '🛍️', color: 'red',    sign: '-' },
    withdraw_gift:        { icon: '📤', color: 'gray',   sign: null },
    withdraw_tg_gift:     { icon: '📤', color: 'gray',   sign: null },
    exchange_tg_gift:     { icon: '🔁', color: 'amber',  sign: '+' },
    task_reward:          { icon: '✅', color: 'green',  sign: '+' },
    task_reward_stars:    { icon: '✅', color: 'green',  sign: '+' },
    referral_bonus:       { icon: '👥', color: 'green',  sign: '+' },
    referral_bonus_stars: { icon: '👥', color: 'green',  sign: '+' },
};

// Служебные типы, которые не показываются в истории пользователю
const HISTORY_HIDDEN_TYPES = new Set(['case_lucky_ratio']);

// Читаемые названия событий на двух языках
const HISTORY_LABELS = {
    ru: {
        topup_stars:          'Пополнение баланса',
        gift_added:           'Получен подарок',
        roulette_win_donuts:  'Выигрыш в рулетке',
        roulette_win_stars:   'Выигрыш в рулетке',
        roulette_win_gift:    'Выигрыш подарка в рулетке',
        roulette_win_tg_gift: 'Выигрыш Telegram-подарка в рулетке',
        roulette_paid_donuts: 'Ставка в рулетке',
        roulette_paid_stars:  'Ставка в рулетке',
        roulette_paid:        'Ставка в рулетке',
        case_win_donuts:      'Выигрыш из кейса',
        case_win_stars:       'Выигрыш из кейса',
        case_win_gift:        'Выигрыш подарка из кейса',
        case_win_tg_gift:     'Выигрыш Telegram-подарка из кейса',
        case_paid_donuts:     'Открытие кейса',
        case_paid_stars:      'Открытие кейса',
        rocket_win_donuts:    'Выигрыш в ракете',
        rocket_win_stars:     'Выигрыш в ракете',
        rocket_lose_donuts:   'Проигрыш в ракете',
        rocket_lose_stars:    'Проигрыш в ракете',
        claim_gift:           'Получение подарка',
        withdraw_gift:        'Вывод подарка',
        withdraw_tg_gift:     'Вывод Telegram-подарка',
        exchange_tg_gift:     'Обмен Telegram-подарка',
        task_reward:          'Награда за задание',
        referral_bonus:       'Реферальный бонус',
        referral_bonus_stars: 'Реферальный бонус ⭐',
    },
    en: {
        topup_stars:          'Balance top-up',
        gift_added:           'Gift received',
        roulette_win_donuts:  'Roulette win',
        roulette_win_stars:   'Roulette win',
        roulette_win_gift:    'Gift won in roulette',
        roulette_win_tg_gift: 'Telegram gift won in roulette',
        roulette_paid_donuts: 'Roulette bet',
        roulette_paid_stars:  'Roulette bet',
        roulette_paid:        'Roulette bet',
        case_win_donuts:      'Case win',
        case_win_stars:       'Case win',
        case_win_gift:        'Gift won from case',
        case_win_tg_gift:     'Telegram gift won from case',
        case_paid_donuts:     'Case opened',
        case_paid_stars:      'Case opened',
        rocket_win_donuts:    'Rocket win',
        rocket_win_stars:     'Rocket win',
        rocket_lose_donuts:   'Rocket loss',
        rocket_lose_stars:    'Rocket loss',
        claim_gift:           'Gift claimed',
        withdraw_gift:        'Gift withdrawn',
        withdraw_tg_gift:     'Telegram gift withdrawn',
        exchange_tg_gift:     'Telegram gift exchanged',
        task_reward:          'Task reward',
        task_reward_stars:    'Task reward',
        referral_bonus:       'Referral bonus',
        referral_bonus_stars: 'Referral bonus ⭐',
    }
};

function formatHistoryDate(ts) {
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Функция для поиска фото подарка по gift_id из описания истории
function getHistoryGiftPhoto(entry) {
    // Только для типов, связанных с подарками
    const giftTypes = new Set([
        'gift_added', 'claim_gift', 'withdraw_gift', 'withdraw_tg_gift',
        'exchange_tg_gift', 'roulette_win_gift', 'roulette_win_tg_gift',
        'case_win_gift', 'case_win_tg_gift'
    ]);
    if (!giftTypes.has(entry.action_type)) return null;

    if (!entry.description) return null;

    // Извлекаем gift_id из тега [gift_id:...] в описании
    const match = entry.description.match(/\[gift_id:([^\]]+)\]/);
    if (!match) return null;

    const giftDef = getGiftDefinitionById(match[1]);
    return giftDef ? giftDef.photo : null;
}

// =====================================================
// ИСТОРИЯ ОПЕРАЦИЙ (с бесконечной прокруткой)
// =====================================================

let historyOffset = 0;
const HISTORY_PAGE_SIZE = 30;
let historyLoading = false;
let historyAllLoaded = false;
let historyGrouped = {}; // накопленная сгруппированная история

function resetHistoryState() {
    historyOffset = 0;
    historyLoading = false;
    historyAllLoaded = false;
    historyGrouped = {};
}

async function openHistoryModal() {
    vibrate('light');
    openModal('history-modal');
    resetHistoryState();

    const list = document.getElementById('history-list');
    list.innerHTML = `<div class="text-center text-blue-300/50 py-10 animate-pulse font-bold tracking-widest uppercase text-sm">${i18n[currentLang].loading}</div>`;

    // Вешаем обработчик прокрутки
    const modal = document.getElementById('history-modal');
    if (modal) {
        modal._historyScrollHandler = () => {
            const scrollEl = modal.querySelector('.overflow-y-auto') || modal;
            const nearBottom = scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 120;
            if (nearBottom && !historyLoading && !historyAllLoaded) {
                loadMoreHistory();
            }
        };
        const scrollEl = modal.querySelector('.overflow-y-auto') || modal;
        scrollEl.removeEventListener('scroll', modal._historyScrollHandler);
        scrollEl.addEventListener('scroll', modal._historyScrollHandler);
    }

    await loadMoreHistory(true);
}

async function loadMoreHistory(isFirstLoad = false) {
    if (historyLoading || historyAllLoaded) return;
    historyLoading = true;

    const list = document.getElementById('history-list');

    // Показываем спиннер внизу при догрузке
    let spinner = document.getElementById('history-load-spinner');
    if (!isFirstLoad) {
        if (!spinner) {
            spinner = document.createElement('div');
            spinner.id = 'history-load-spinner';
            spinner.className = 'text-center text-blue-300/50 py-6 animate-pulse font-bold tracking-widest uppercase text-xs';
            spinner.textContent = i18n[currentLang].loading || 'Загрузка...';
            list.appendChild(spinner);
        }
    }

    try {
        const res = await fetch(`/api/history?offset=${historyOffset}&limit=${HISTORY_PAGE_SIZE}`, { headers: getApiHeaders() });
        const data = await res.json();

        // Удаляем спиннер
        spinner = document.getElementById('history-load-spinner');
        if (spinner) spinner.remove();

        if (!data.history || data.history.length === 0) {
            if (isFirstLoad) {
                list.innerHTML = `<div class="text-center text-blue-200/40 text-sm py-10 border border-white/5 border-dashed rounded-2xl px-4">${i18n[currentLang].history_empty}</div>`;
            } else {
                // Все записи загружены
                const endMsg = document.createElement('div');
                endMsg.className = 'text-center text-blue-200/30 text-xs py-4 font-semibold tracking-widest uppercase';
                endMsg.textContent = currentLang === 'ru' ? 'Больше записей нет' : 'No more records';
                list.appendChild(endMsg);
            }
            historyAllLoaded = true;
            historyLoading = false;
            return;
        }

        // Проверяем, все ли записи загружены
        historyOffset += data.history.length;
        if (historyOffset >= data.total || data.history.length < HISTORY_PAGE_SIZE) {
            historyAllLoaded = true;
        }

        // Группируем новые записи по дате и добавляем к накопленным
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(today.getDate() - 1);

        data.history.forEach(entry => {
            // Скрываем служебные записи (luck ratio и т.п.)
            if (HISTORY_HIDDEN_TYPES.has(entry.action_type)) return;

            const dateObj = new Date(entry.created_at * 1000);
            let displayDate = dateObj.toLocaleDateString(currentLang === 'ru' ? 'ru-RU' : 'en-US', {
                day: 'numeric', month: 'long'
            });
            if (dateObj.toDateString() === today.toDateString()) {
                displayDate = currentLang === 'ru' ? 'Сегодня' : 'Today';
            } else if (dateObj.toDateString() === yesterday.toDateString()) {
                displayDate = currentLang === 'ru' ? 'Вчера' : 'Yesterday';
            }
            if (!historyGrouped[displayDate]) historyGrouped[displayDate] = [];
            historyGrouped[displayDate].push(entry);
        });

        // Склонение для русского языка
        const getPlural = (n, one, two, five) => {
            let mod = Math.abs(n) % 100;
            if (mod >= 5 && mod <= 20) return five;
            mod %= 10;
            if (mod === 1) return one;
            if (mod >= 2 && mod <= 4) return two;
            return five;
        };

        // Перерисовываем полный список
        let htmlContent = '';
        for (const [dateLabel, entries] of Object.entries(historyGrouped)) {
            const actionsCount = entries.length;
            const actionText = currentLang === 'ru'
                ? `${actionsCount} ${getPlural(actionsCount, 'действие', 'действия', 'действий')}`
                : `${actionsCount} action${actionsCount !== 1 ? 's' : ''}`;

            htmlContent += `
                <div class="sticky top-[-5px] z-20 flex items-center justify-between bg-[#0f172a]/80 backdrop-blur-xl py-2.5 px-3 mt-5 mb-3 first:mt-0 rounded-xl border border-white/10 shadow-lg">
                    <div class="flex items-center gap-3">
                        <div class="w-1.5 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full shadow-[0_0_10px_rgba(99,102,241,0.6)]"></div>
                        <span class="text-sm font-bold text-white/90 capitalize tracking-wide drop-shadow-md">${escapeHtml(dateLabel)}</span>
                    </div>
                    <div class="flex items-center gap-1.5 bg-white/5 text-white/70 px-2.5 py-1 rounded-full border border-white/10 shadow-inner">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 opacity-70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                        <span class="text-[10px] font-bold uppercase tracking-wider">${actionText}</span>
                    </div>
                </div>
                <div class="flex flex-col gap-2 relative z-10">
            `;

            htmlContent += entries.map(entry => {
                const meta = HISTORY_ICONS[entry.action_type] || { icon: '📋', color: 'gray', sign: null };
                const giftPhotoUrl = getHistoryGiftPhoto(entry);
                let displayIconHtml = giftPhotoUrl
                    ? `<img src="${escapeHtml(getImgSrc(giftPhotoUrl))}" class="w-7 h-7 object-contain drop-shadow-md">`
                    : meta.icon;

                // Читаемое название события
                const labels = HISTORY_LABELS[currentLang] || HISTORY_LABELS['ru'];
                const entryTitle = labels[entry.action_type] || entry.description || entry.action_type;

                let currencyIconUrl = (entry.action_type.includes('stars') || entry.action_type === 'exchange_tg_gift') ? '/gifts/stars.png' : '/gifts/dount.png';
                let amountHtml = '';

                if (entry.action_type === 'topup_stars' && entry.amount > 0) {
                    // Пополнение звёздами: показываем +N зелёным с иконкой звезды
                    amountHtml = `<span class="text-green-400 font-extrabold text-base flex items-center gap-1.5">+${entry.amount} <img src="/gifts/stars.png" class="w-4 h-4 object-contain"></span>`;
                } else if (meta.sign === '+' && entry.amount > 0) {
                    amountHtml = `<span class="text-green-400 font-extrabold text-base flex items-center gap-1">+${entry.amount} <img src="${currencyIconUrl}" class="w-4 h-4 object-contain"></span>`;
                } else if (meta.sign === '-' && entry.amount !== 0) {
                    amountHtml = `<span class="text-red-400 font-extrabold text-base flex items-center gap-1">-${Math.abs(entry.amount)} <img src="${currencyIconUrl}" class="w-4 h-4 object-contain"></span>`;
                } else {
                    amountHtml = `<span class="text-gray-400 font-bold text-sm">—</span>`;
                }

                const borderColor = meta.color === 'green' ? 'border-green-500/20 bg-green-500/5'
                                  : meta.color === 'red'   ? 'border-red-500/20 bg-red-500/5'
                                  : 'border-white/5 bg-black/20';

                return `
                    <div class="glass rounded-2xl px-4 py-3 flex items-center justify-between border ${borderColor} gap-3">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center text-xl
                                ${meta.color === 'green' ? 'bg-green-500/20 border border-green-400/30'
                                : meta.color === 'red'   ? 'bg-red-500/20 border border-red-400/30'
                                : 'bg-white/5 border border-white/10'}">
                                ${displayIconHtml}
                            </div>
                            <div class="min-w-0">
                                <div class="font-semibold text-white text-sm leading-tight truncate">${escapeHtml(entryTitle)}</div>
                                <div class="text-[11px] text-blue-200/40 mt-0.5">${formatHistoryDate(entry.created_at)}</div>
                            </div>
                        </div>
                        <div class="flex-shrink-0 ml-2">${amountHtml}</div>
                    </div>`;
            }).join('');

            htmlContent += `</div>`;
        }

        if (isFirstLoad) {
            list.innerHTML = htmlContent;
        } else {
            list.innerHTML = htmlContent;
        }

    } catch(e) {
        spinner = document.getElementById('history-load-spinner');
        if (spinner) spinner.remove();
        if (isFirstLoad) {
            list.innerHTML = `<div class="text-center text-red-400/70 text-sm py-10">${i18n[currentLang].err_network}</div>`;
        }
    }

    historyLoading = false;
}

window.renderProfile = renderProfile; 
window.openWithdrawModal = openWithdrawModal;
window.confirmWithdraw = confirmWithdraw;
window.openHistoryModal = openHistoryModal;