// =====================================================
// ПРОФИЛЬ И ВЫВОД
// =====================================================
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
        // Проверяем: это Главный подарок или Базовый подарок?
        const giftDef = mainGifts[id] || baseGifts[id];
        
        if (amount > 0 && giftDef) {
            hasGifts = true;
            grid.innerHTML += `
                <div onclick="openWithdrawModal(${id})" class="glass rounded-2xl p-4 flex flex-col items-center relative transition-transform active:scale-95 cursor-pointer border border-green-500/20 bg-green-500/5">
                    <div class="absolute -top-2 -right-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold w-7 h-7 rounded-full flex items-center justify-center border-2 border-[#0f172a] shadow-lg z-10">${amount}</div>
                    <div class="bg-black/20 w-16 h-16 rounded-xl flex items-center justify-center mb-3 border border-white/5 shadow-inner">
                        <img src="${getImgSrc(giftDef.photo)}" class="w-12 h-12 object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/48'">
                    </div>
                    <span class="text-xs text-center font-bold text-white mb-1 leading-tight">${giftDef.name}</span>
                    <span class="text-[10px] font-bold text-gray-400 bg-black/30 px-2 py-0.5 rounded-full mt-auto">${i18n[currentLang].click}</span>
                </div>`;
        }
    }
    if (!hasGifts) {
        grid.innerHTML = `<div class="col-span-3 text-center text-blue-200/40 text-sm mt-6 border border-white/5 border-dashed rounded-2xl p-6">${i18n[currentLang].no_gifts_yet}</div>`;
    }
}

let currentWithdrawGiftId = null;

// Берет значение из бэкенда (appConfig.withdraw_fee из /init) либо 25 по умолчанию
let withdrawFeeAmount = (window.appConfig && window.appConfig.withdraw_fee) ? window.appConfig.withdraw_fee : 25;

function openWithdrawModal(giftId) {
    vibrate('medium');
    currentWithdrawGiftId = giftId;
    const giftDef = mainGifts[giftId] || baseGifts[giftId];
    if (!giftDef) return;

    // Подставляем данные в модалку
    document.getElementById('wcm-gift-img').src = getImgSrc(giftDef.photo);
    document.getElementById('wcm-gift-name').innerText = giftDef.name;
    document.getElementById('wcm-fee-amount').innerText = withdrawFeeAmount;

    // Вешаем обработчик на кнопку подтверждения
    document.getElementById('wcm-btn-confirm').onclick = () => confirmWithdraw(giftId);

    openModal('withdraw-confirm-modal');
}

async function confirmWithdraw(giftId) {
    vibrate('heavy');
    const btn = document.getElementById('wcm-btn-confirm');
    const originalHtml = btn.innerHTML;

    // Показываем лоадер на кнопке
    btn.innerHTML = `<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;
    btn.disabled = true;

    try {
        const res = await fetch('/api/withdraw', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ tg_id: tgUser.id, gift_id: giftId })
        });
        const data = await res.json();

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
            // Если не хватает звезд — закрываем модалку, показываем алерт и открываем пополнение
            if (data.detail === 'not_enough_stars') {
                closeModal('withdraw-confirm-modal');
                tg.showAlert(i18n[currentLang].not_enough_stars_alert, () => {
                    openModal('topup-stars-modal');
                });
                return;
            }
            throw new Error(data.detail || 'Withdraw error');
        }

        // Успех
        myGifts = data.user_gifts;

        // Отнимаем звезды визуально
        const starsEl = document.getElementById('user-stars');
        if (starsEl) {
            let currentStars = parseInt(starsEl.innerText) || 0;
            starsEl.innerText = Math.max(0, currentStars - withdrawFeeAmount);
        }

        closeModal('withdraw-confirm-modal');
        updateUI();
        if (typeof renderProfile === 'function') renderProfile();
        setTimeout(() => openModal('success-withdraw-modal'), 300);

    } catch(e) {
        console.error(e);
        tg.showAlert(i18n[currentLang].err_conn);
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// =====================================================
// ИСТОРИЯ ОПЕРАЦИЙ
// =====================================================

// Расширенный список иконок для всех событий (включая звезды и новые игры)
const HISTORY_ICONS = {
    gift_added:           { icon: '🎁', color: 'green',  sign: '+' },
    roulette_win_donuts:  { icon: '🎰', color: 'green',  sign: '+' },
    roulette_win_stars:   { icon: '🎰', color: 'green',  sign: '+' },
    roulette_win_gift:    { icon: '🎁', color: 'green',  sign: null },
    roulette_paid_donuts: { icon: '🎰', color: 'red',    sign: '-' },
    roulette_paid_stars:  { icon: '🎰', color: 'red',    sign: '-' },
    roulette_paid:        { icon: '🎰', color: 'red',    sign: '-' },
    case_win_donuts:      { icon: '📦', color: 'green',  sign: '+' },
    case_win_stars:       { icon: '📦', color: 'green',  sign: '+' },
    case_win_gift:        { icon: '🎁', color: 'green',  sign: null },
    case_paid_donuts:     { icon: '📦', color: 'red',    sign: '-' },
    case_paid_stars:      { icon: '📦', color: 'red',    sign: '-' },
    rocket_win_donuts:    { icon: '🚀', color: 'green',  sign: '+' },
    rocket_win_stars:     { icon: '🚀', color: 'green',  sign: '+' },
    rocket_lose_donuts:   { icon: '💥', color: 'red',    sign: '-' },
    rocket_lose_stars:    { icon: '💥', color: 'red',    sign: '-' },
    claim_gift:           { icon: '🛍️', color: 'red',    sign: '-' },
    withdraw_gift:        { icon: '📤', color: 'gray',   sign: null },
    task_reward:          { icon: '✅', color: 'green',  sign: '+' },
    referral_bonus:       { icon: '👥', color: 'green',  sign: '+' },
};

function formatHistoryDate(ts) {
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Функция для поиска фото подарка по его названию в описании истории
function getHistoryGiftPhoto(description) {
    if (!description) return null;
    const allGifts = { ...mainGifts, ...baseGifts };
    for (const key in allGifts) {
        if (description.includes(allGifts[key].name)) {
            return allGifts[key].photo;
        }
    }
    return null;
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
        const res = await fetch(`/api/history?tg_id=${tgUser.id}&offset=${historyOffset}&limit=${HISTORY_PAGE_SIZE}`, { headers: getApiHeaders() });
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
                        <span class="text-sm font-bold text-white/90 capitalize tracking-wide drop-shadow-md">${dateLabel}</span>
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
                const giftPhotoUrl = getHistoryGiftPhoto(entry.description);
                let displayIconHtml = giftPhotoUrl
                    ? `<img src="${getImgSrc(giftPhotoUrl)}" class="w-7 h-7 object-contain drop-shadow-md">`
                    : meta.icon;

                let currencyIconUrl = entry.action_type.includes('stars') ? '/gifts/stars.png' : '/gifts/dount.png';
                let amountHtml = '';
                if (meta.sign === '+' && entry.amount > 0) {
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
                                <div class="font-semibold text-white text-sm leading-tight truncate">${entry.description}</div>
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