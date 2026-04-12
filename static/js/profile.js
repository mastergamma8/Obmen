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

// Рассчитывает приблизительное кол-во звёзд за BASE/MAIN подарок до запроса к серверу.
// Использует отдельный курс gift_exchange_stars_rate, не банковский.
function calcApproxExchangeStars(giftId) {
    const rate = (window.appConfig && window.appConfig.gift_exchange_stars_rate != null)
        ? window.appConfig.gift_exchange_stars_rate
        : (window.appConfig && window.appConfig.donuts_to_stars_rate
            ? window.appConfig.donuts_to_stars_rate : 0.01);
    const gid = Number(giftId);
    if (baseGifts && baseGifts[gid]) {
        const val = parseInt(baseGifts[gid].value || 0);
        return Math.max(1, Math.floor(val * rate));
    }
    if (mainGifts && mainGifts[gid]) {
        const val = parseInt(mainGifts[gid].required_value || mainGifts[gid].value || 0);
        return Math.max(1, Math.floor(val * rate));
    }
    return 0;
}

// ── Требования для вывода ────────────────────────────────────────────────────

let _pendingWithdrawGiftId = null;

function _renderWithdrawRequirements(items) {
    const list = document.getElementById('wr-list');
    if (!list) return;

    list.innerHTML = items.map(req => {
        const done = req.done;

        // Иконка статуса
        const icon = done
            ? `<div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-400/50 flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(52,211,153,0.2)]">
                   <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
               </div>`
            : `<div class="w-8 h-8 rounded-full bg-red-500/15 border border-red-400/30 flex items-center justify-center flex-shrink-0">
                   <svg class="w-4 h-4 text-red-400/80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
               </div>`;

        // Прогресс для рефералов
        let subtext = '';
        if (req.type === 'referrals') {
            const cur = req.current || 0;
            const req2 = req.required || 0;
            const pct = req2 > 0 ? Math.min(100, Math.round(cur / req2 * 100)) : 0;
            subtext = `
                <div class="flex items-center gap-2 mt-1.5">
                    <div class="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                        <div class="h-full rounded-full ${done ? 'bg-emerald-400' : 'bg-blue-400/70'} transition-all duration-500" style="width:${pct}%"></div>
                    </div>
                    <span class="text-[11px] text-white/40 font-medium tabular-nums">${cur}/${req2}</span>
                </div>`;
        }

        // Кнопка действия
        let actionBtn = '';
        if (!done) {
            if (req.type === 'referrals') {
                actionBtn = `<button onclick="_wrShareInvite()" class="flex-shrink-0 text-xs bg-blue-500/25 border border-blue-400/40 text-blue-300 px-3 py-1.5 rounded-xl font-bold active:scale-95 transition-transform whitespace-nowrap">${i18n[currentLang].wr_btn_invite || 'Пригласить'}</button>`;
            } else if (req.url) {
                actionBtn = `<a href="${req.url}" target="_blank" rel="noopener" class="flex-shrink-0 text-xs bg-blue-500/25 border border-blue-400/40 text-blue-300 px-3 py-1.5 rounded-xl font-bold active:scale-95 transition-transform whitespace-nowrap">${i18n[currentLang].wr_btn_complete || 'Выполнить'}</a>`;
            }
        }

        return `
            <div class="rounded-2xl p-3.5 flex items-start gap-3 border transition-all ${done
                ? 'bg-emerald-500/5 border-emerald-400/20'
                : 'bg-white/[0.03] border-white/8'}">
                <div class="mt-0.5">${icon}</div>
                <div class="flex-1 min-w-0">
                    <span class="text-sm font-semibold leading-tight ${done ? 'text-white/50 line-through decoration-white/30' : 'text-white'}">${req.title}</span>
                    ${subtext}
                </div>
                ${actionBtn}
            </div>`;
    }).join('');
}

function _wrShareInvite() {
    vibrate('medium');
    const link = (typeof getRefLink === 'function') ? getRefLink() : '';
    const text = (i18n && i18n[currentLang] && i18n[currentLang].share_text) || 'Присоединяйся!';
    if (window.Telegram && Telegram.WebApp) {
        Telegram.WebApp.openTelegramLink(
            `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`
        );
    }
}
window._wrShareInvite = _wrShareInvite;

async function recheckWithdrawRequirements() {
    const btn = document.getElementById('wr-check-btn');
    const statusEl = document.getElementById('wr-status');
    if (btn) { btn.disabled = true; btn.innerHTML = `<svg class="animate-spin h-4 w-4 inline mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>${i18n[currentLang].wr_checking || 'Проверяем...'}`; }
    if (statusEl) statusEl.innerHTML = '';

    try {
        const res  = await fetch('/api/withdraw/requirements', { headers: getApiHeaders() });
        const data = await res.json();

        _renderWithdrawRequirements(data.requirements || []);

        if (data.all_done) {
            if (statusEl) statusEl.innerHTML = `<div class="flex items-center justify-center gap-2 text-emerald-400 text-sm font-semibold"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>${i18n[currentLang].wr_all_done || 'Все условия выполнены!'}</div>`;
            setTimeout(() => {
                closeModal('withdraw-requirements-modal');
                setTimeout(() => {
                    if (_pendingWithdrawGiftId !== null) {
                        _openWithdrawModalDirect_impl(_pendingWithdrawGiftId);
                        _pendingWithdrawGiftId = null;
                    }
                }, 320);
            }, 700);
        } else {
            const unmet = (data.requirements || []).filter(r => !r.done).map(r => r.title);
            if (statusEl) {
                statusEl.innerHTML = `
                    <div class="text-left rounded-xl bg-red-500/10 border border-red-400/20 p-3">
                        <p class="text-red-400 text-xs font-bold mb-1.5">${i18n[currentLang].wr_unmet_label || 'Не выполнено:'}</p>
                        ${unmet.map(t => `<p class="text-red-300/80 text-xs flex items-start gap-1.5"><span class="text-red-400 mt-0.5">•</span>${t}</p>`).join('')}
                    </div>`;
            }
        }
    } catch (e) {
        if (statusEl) statusEl.innerHTML = `<p class="text-red-400 text-xs text-center">${i18n[currentLang]?.err_network || 'Ошибка сети'}</p>`;
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = i18n[currentLang].wr_check_btn || 'Проверить выполнение'; }
    }
}
window.recheckWithdrawRequirements = recheckWithdrawRequirements;

// Вспомогательная функция: при нажатии «Вывести» в модале подарка проверяем требования.
// Если всё выполнено — идём сразу к confirmWithdrawGift.
// Если нет — закрываем текущий модал и показываем экран с требованиями.
async function _checkRequirementsAndWithdraw(giftId) {
    _pendingWithdrawGiftId = giftId;
    try {
        const res  = await fetch('/api/withdraw/requirements', { headers: getApiHeaders() });
        const data = await res.json();

        if (data.all_done) {
            _pendingWithdrawGiftId = null;
            confirmWithdrawGift(giftId, false);
        } else {
            closeModal('withdraw-confirm-modal');
            setTimeout(() => {
                _renderWithdrawRequirements(data.requirements || []);
                const statusEl = document.getElementById('wr-status');
                if (statusEl) statusEl.innerHTML = '';
                openModal('withdraw-requirements-modal');
            }, 320);
        }
    } catch (e) {
        // При ошибке сети — продолжаем без проверки
        _pendingWithdrawGiftId = null;
        confirmWithdrawGift(giftId, false);
    }
}

// openWithdrawModal — открывает модал с действиями напрямую.
// Проверка требований происходит только при нажатии кнопки «Вывести» внутри модала.
function openWithdrawModal(giftId) {
    vibrate('medium');
    _openWithdrawModalDirect_impl(giftId);
}

// Оригинальная реализация (без проверки требований)
function _openWithdrawModalDirect_impl(giftId) {
    currentWithdrawGiftId = giftId;
    const giftDef = getGiftDefinitionById(giftId);
    if (!giftDef) return;

    currentWithdrawIsTgGift = isRealTgGift(giftId);
    currentWithdrawExchangeStars = getTgGiftExchangeStars(giftId);

    const titleEl = document.getElementById('wcm-title');
    const descEl = document.getElementById('wcm-desc');
    const imgEl = document.getElementById('wcm-gift-img');
    const nameEl = document.getElementById('wcm-gift-name');
    const feeRow      = document.getElementById('wcm-fee-row');
    const tgActions   = document.getElementById('wcm-tg-actions');
    const baseActions = document.getElementById('wcm-base-actions');
    const keepRow     = document.getElementById('wcm-keep-row');
    const exchangeInfo= document.getElementById('wcm-exchange-info');
    const btnConfirm  = document.getElementById('wcm-btn-confirm');
    const btnConfirmLabel = document.getElementById('wcm-btn-confirm-label');
    const feeAmount   = document.getElementById('wcm-fee-amount');

    imgEl.src = getImgSrc(giftDef.photo);
    nameEl.innerText = giftDef.name;

    // Сбрасываем все блоки перед показом нужных
    feeRow.classList.add('hidden');
    tgActions.classList.add('hidden');
    if (baseActions) baseActions.classList.add('hidden');
    if (keepRow) keepRow.classList.add('hidden');
    exchangeInfo.classList.add('hidden');

    if (currentWithdrawIsTgGift) {
        titleEl.innerText = i18n[currentLang].tg_gift_modal_title;
        descEl.innerText  = i18n[currentLang].tg_gift_modal_desc;
        tgActions.classList.remove('hidden');
        if (keepRow) keepRow.classList.remove('hidden');
        exchangeInfo.classList.remove('hidden');

        exchangeInfo.innerHTML = `${i18n[currentLang].btn_tg_exchange}: +${currentWithdrawExchangeStars} <img src="/gifts/stars.png" class="w-4 h-4 inline-block align-middle pb-[2px] object-contain">`;
        document.getElementById('wcm-btn-withdraw-tg').textContent = i18n[currentLang].btn_tg_withdraw;
        document.getElementById('wcm-btn-exchange').innerHTML = `<div class="flex items-center justify-center gap-1.5"><span>${i18n[currentLang].btn_tg_exchange} +${currentWithdrawExchangeStars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
        document.getElementById('wcm-btn-keep').textContent = i18n[currentLang].btn_tg_keep;

        document.getElementById('wcm-btn-withdraw-tg').onclick = () => confirmWithdrawGift(giftId, true);
        document.getElementById('wcm-btn-exchange').onclick    = () => confirmExchangeGift(giftId);
        document.getElementById('wcm-btn-keep').onclick        = () => closeModal('withdraw-confirm-modal');

    } else if (isBaseGift(Number(giftId)) || isMainGift(Number(giftId))) {
        titleEl.innerText = i18n[currentLang].tg_gift_modal_title || 'Ваш подарок';
        descEl.innerText  = i18n[currentLang].tg_gift_modal_desc  || '';
        if (baseActions) baseActions.classList.remove('hidden');
        feeRow.classList.remove('hidden');
        btnConfirmLabel.innerText = i18n[currentLang].withdraw_confirm_btn || 'Вывести за';
        feeAmount.innerText = withdrawFeeAmount;
        btnConfirm.onclick  = () => _checkRequirementsAndWithdraw(giftId);
        if (keepRow) keepRow.classList.remove('hidden');

        const wcmStarsBtn = document.getElementById('wcm-btn-exchange-donuts');
        if (wcmStarsBtn) {
            const t = i18n[currentLang];
            const approxStars = calcApproxExchangeStars(giftId);

            // Сразу показываем спиннер, затем грузим точное значение с сервера
            const _setLabel = (stars, loading) => {
                const prefix = t.btn_exchange_stars || 'Обменять на';
                wcmStarsBtn.innerHTML = loading
                    ? `<div class="flex items-center justify-center gap-2"><svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg><span>${prefix} ...</span></div>`
                    : `<div class="flex items-center justify-center gap-1.5"><span>${prefix} ${stars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
            };

            _setLabel(approxStars, true);

            // Запрашиваем у сервера точное значение (тот же расчёт, что при реальном обмене)
            fetch(`/api/exchange-preview?gift_id=${Number(giftId)}`, { headers: getApiHeaders() })
                .then(r => r.json())
                .then(data => {
                    _setLabel(data.stars_reward ?? approxStars, false);
                })
                .catch(() => _setLabel(approxStars, false));

            wcmStarsBtn.onclick = async () => {
                wcmStarsBtn.disabled = true;
                wcmStarsBtn._savedHTML = wcmStarsBtn.innerHTML;
                wcmStarsBtn.innerHTML = `<svg class="animate-spin h-5 w-5 text-white mx-auto" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>`;
                try {
                    const res  = await fetch('/api/exchange-for-stars', {
                        method: 'POST',
                        headers: getApiHeaders(),
                        body: JSON.stringify({ gift_id: Number(giftId) })
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Exchange error');
                    syncGiftStateFromResponse(data);
                    closeModal('withdraw-confirm-modal');
                    showNotify(`${t.exchange_stars_success || 'Обменяно!'} +${data.stars_reward} ⭐`, 'success');
                } catch (e) {
                    showNotify((e && e.message) ? e.message : (t.err_conn || 'Connection error'), 'error');
                } finally {
                    wcmStarsBtn.disabled = false;
                    if (wcmStarsBtn._savedHTML) wcmStarsBtn.innerHTML = wcmStarsBtn._savedHTML;
                }
            };
        }

        const keepBtn = document.getElementById('wcm-btn-keep');
        if (keepBtn) {
            keepBtn.textContent = i18n[currentLang].btn_tg_keep;
            keepBtn.onclick = () => closeModal('withdraw-confirm-modal');
        }

    } else {
        titleEl.innerText = i18n[currentLang].withdraw_confirm_title;
        descEl.innerText  = i18n[currentLang].withdraw_confirm_desc;
        feeRow.classList.remove('hidden');
        btnConfirmLabel.innerText = i18n[currentLang].withdraw_confirm_btn || 'Вывести за';
        feeAmount.innerText = withdrawFeeAmount;
        btnConfirm.onclick  = () => _checkRequirementsAndWithdraw(giftId);
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
                showNotify(msg, 'warning');
            } else {
                showNotify(data.detail || 'Limit reached', 'warning');
            }
            return;
        }

        if (!res.ok) {
            if (data.detail === 'not_enough_stars') {
                closeModal('withdraw-confirm-modal');
                showNotify(i18n[currentLang].not_enough_stars_alert, 'error', () => {
                    openModal('topup-stars-modal');
                });
                return;
            }
            throw new Error(data.detail || 'Withdraw error');
        }

        syncGiftStateFromResponse(data);
        closeModal('withdraw-confirm-modal');

        if (isTgGift) {
            showNotify(i18n[currentLang].tg_withdraw_success || 'Подарок отправлен!', 'success');
        } else {
            setTimeout(() => openModal('success-withdraw-modal'), 300);
        }

    } catch(e) {
        console.error(e);
        showNotify(i18n[currentLang].err_conn, 'error');
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
        showNotify(`${i18n[currentLang].tg_exchange_success} +${data.exchange_stars || getTgGiftExchangeStars(giftId)} ⭐`, 'success');
    } catch (e) {
        console.error(e);
        showNotify(i18n[currentLang].err_conn, 'error');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

function isBaseGift(giftId) {
    return !!(baseGifts && baseGifts[giftId] && !isRealTgGift(giftId) && !mainGifts[giftId]);
}

function isMainGift(giftId) {
    return !!(mainGifts && mainGifts[giftId] && !isRealTgGift(giftId));
}

function _closeGameModal(source) {
    if (source === 'case') closeCaseAnimation();
    else closeModal('roulette-result-modal');
}

// ── Спиннер на кнопке во время async-запроса ─────────────────────────────────
const _SPINNER_HTML = `<svg class="animate-spin h-5 w-5 text-white mx-auto" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;

function _setBtnLoading(btn, loading) {
    if (loading) {
        btn._savedHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = _SPINNER_HTML;
    } else {
        btn.disabled = false;
        if (btn._savedHTML !== undefined) btn.innerHTML = btn._savedHTML;
    }
}

// ── Единый обработчик ошибок вывода (cooldown / not_enough_stars / generic) ──
// Возвращает true если ошибка была обработана, false если всё ок.
function _handleWithdrawErrorInGame(res, data, source) {
    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};

    // 429 — лимит/кулдаун
    if (res.status === 429) {
        const detail = data.detail;
        if (detail && typeof detail === 'object' && detail.error === 'cooldown') {
            const h = detail.hours   ?? 0;
            const m = detail.minutes ?? 0;
            const msg = (t.cooldown_withdraw_wait || 'Подождите {h}ч {m}м')
                .replace('{h}', h).replace('{m}', m);
            showNotify(msg, 'warning');
        } else {
            const msg = typeof detail === 'string' ? detail : (t.limit_reached || 'Лимит достигнут. Попробуйте позже.');
            showNotify(msg, 'warning');
        }
        return true;
    }

    // Ошибки 4xx/5xx
    if (!res.ok) {
        const detail = data.detail;

        // Недостаточно звёзд на комиссию
        if (detail === 'not_enough_stars') {
            _closeGameModal(source);
            showNotify(t.not_enough_stars_alert || 'Недостаточно звёзд для вывода', 'error', () => {
                openModal('topup-stars-modal');
            });
            return true;
        }

        // Любая другая ошибка — показываем читаемый текст
        const msg = typeof detail === 'object'
            ? (detail?.message || detail?.detail || t.err_conn || 'Ошибка')
            : (detail || t.err_conn || 'Ошибка');
        showNotify(msg, 'error');
        return true;
    }

    return false; // ошибок нет, можно продолжать
}

function configureCaseGiftActionsIfNeeded(giftId, source = 'case', isDemo = false) {
    const prefix = source === 'case' ? 'cam' : 'rr';
    const actionsBox        = document.getElementById(`${prefix}-gift-actions`);
    const closeBtn          = document.getElementById(`${prefix}-btn-close`);
    const withdrawBtn       = document.getElementById(`${prefix}-btn-withdraw`);
    const exchangeBtn       = document.getElementById(`${prefix}-btn-exchange`);
    const exchangeDonutsBtn = document.getElementById(`${prefix}-btn-exchange-donuts`);
    const keepBtn           = document.getElementById(`${prefix}-btn-keep`);

    if (!actionsBox || !closeBtn || !withdrawBtn || !exchangeBtn || !keepBtn) return;

    const giftDef  = getGiftDefinitionById(giftId);
    const isTgGift = isRealTgGift(giftId);
    const isBase   = isBaseGift(giftId);

    // Ни TG, ни BASE — просто кнопка «Забрать»
    if (!giftDef || (!isTgGift && !isBase)) {
        actionsBox.classList.add('hidden');
        closeBtn.classList.remove('hidden');
        return;
    }

    actionsBox.classList.remove('hidden');
    closeBtn.classList.add('hidden');
    keepBtn.textContent = i18n[currentLang].btn_tg_keep;
    keepBtn.onclick = () => _closeGameModal(source);

    // ── TG-подарок: вывод в Telegram + обмен на звёзды ────────────────────
    if (isTgGift) {
        const exchangeStars = getTgGiftExchangeStars(giftId);

        withdrawBtn.textContent = i18n[currentLang].btn_tg_withdraw;
        withdrawBtn.classList.remove('hidden');
        exchangeBtn.innerHTML = `<div class="flex items-center justify-center gap-1.5"><span>${i18n[currentLang].btn_tg_exchange} +${exchangeStars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
        exchangeBtn.classList.remove('hidden');
        if (exchangeDonutsBtn) exchangeDonutsBtn.classList.add('hidden');

        withdrawBtn.onclick = async () => {
            if (isDemo) { _closeGameModal(source); return; }
            _setBtnLoading(withdrawBtn, true);
            try {
                const { res, data } = await performGiftAction(giftId, 'withdraw');
                if (_handleWithdrawErrorInGame(res, data, source)) return;
                syncGiftStateFromResponse(data);
                _closeGameModal(source);
                showNotify(i18n[currentLang].tg_withdraw_success || 'Подарок отправлен!', 'success');
            } catch (e) {
                showNotify(i18n[currentLang]?.err_conn || 'Ошибка соединения', 'error');
            } finally {
                _setBtnLoading(withdrawBtn, false);
            }
        };

        exchangeBtn.onclick = async () => {
            if (isDemo) { _closeGameModal(source); return; }
            _setBtnLoading(exchangeBtn, true);
            try {
                const { res, data } = await performGiftAction(giftId, 'exchange');
                if (_handleWithdrawErrorInGame(res, data, source)) return;
                syncGiftStateFromResponse(data);
                _closeGameModal(source);
                showNotify(`${i18n[currentLang].tg_exchange_success || 'Обменяно!'} +${data.exchange_stars || exchangeStars} ⭐`, 'success');
            } catch (e) {
                showNotify(i18n[currentLang]?.err_conn || 'Ошибка соединения', 'error');
            } finally {
                _setBtnLoading(exchangeBtn, false);
            }
        };

    // ── BASE / MAIN-подарок: «Вывести за N ⭐» + «Обменять на ~N ⭐» ────────
    } else {
        const approxStars = calcApproxExchangeStars(giftId);
        withdrawBtn.innerHTML = `<div class="flex items-center justify-center gap-1.5"><span>${i18n[currentLang].withdraw_confirm_btn || 'Вывести за'} ${withdrawFeeAmount}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
        withdrawBtn.classList.remove('hidden');
        // Показываем спиннер, потом запрашиваем точное значение у сервера
        const _setExchangeLabel = (stars, loading) => {
            const prefix = i18n[currentLang].btn_exchange_stars || 'Обменять на';
            exchangeBtn.innerHTML = loading
                ? `<div class="flex items-center justify-center gap-2"><svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg><span>${prefix} ...</span></div>`
                : `<div class="flex items-center justify-center gap-1.5"><span>${prefix} ${stars}</span> <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></div>`;
        };
        _setExchangeLabel(approxStars, true);
        fetch(`/api/exchange-preview?gift_id=${Number(giftId)}`, { headers: getApiHeaders() })
            .then(r => r.json())
            .then(data => { _setExchangeLabel(data.stars_reward ?? approxStars, false); })
            .catch(() => _setExchangeLabel(approxStars, false));
        exchangeBtn.classList.remove('hidden');
        if (exchangeDonutsBtn) exchangeDonutsBtn.classList.add('hidden');

        withdrawBtn.onclick = async () => {
            if (isDemo) { _closeGameModal(source); return; }
            _setBtnLoading(withdrawBtn, true);
            try {
                const { res, data } = await performGiftAction(giftId, 'withdraw');
                if (_handleWithdrawErrorInGame(res, data, source)) return;
                syncGiftStateFromResponse(data);
                _closeGameModal(source);
                showNotify(i18n[currentLang].tg_withdraw_success || 'Подарок выведен!', 'success');
            } catch (e) {
                showNotify(i18n[currentLang]?.err_conn || 'Ошибка соединения', 'error');
            } finally {
                _setBtnLoading(withdrawBtn, false);
            }
        };

        exchangeBtn.onclick = async () => {
            if (isDemo) { _closeGameModal(source); return; }
            _setBtnLoading(exchangeBtn, true);
            try {
                const res = await fetch('/api/exchange-for-stars', {
                    method: 'POST',
                    headers: getApiHeaders(),
                    body: JSON.stringify({ gift_id: giftId })
                });
                const data = await res.json();
                if (_handleWithdrawErrorInGame(res, data, source)) return;
                syncGiftStateFromResponse(data);
                _closeGameModal(source);
                showNotify(`${i18n[currentLang].exchange_stars_success || 'Обменяно!'} +${data.stars_reward} ⭐`, 'success');
            } catch (e) {
                showNotify(i18n[currentLang]?.err_conn || 'Ошибка соединения', 'error');
            } finally {
                _setBtnLoading(exchangeBtn, false);
            }
        };
    }
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
    exchange_gift_donuts: { icon: '🍩', color: 'green',  sign: '+' },
    exchange_gift_stars:  { icon: '⭐', color: 'amber',  sign: '+' },
    task_reward:          { icon: '✅', color: 'green',  sign: '+' },
    task_reward_stars:    { icon: '✅', color: 'green',  sign: '+' },
    referral_bonus:       { icon: '👥', color: 'green',  sign: '+' },
    referral_bonus_stars: { icon: '👥', color: 'green',  sign: '+' },
    case_free_open:       { icon: '🎁', color: 'green',  sign: null },
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
        exchange_gift_donuts: 'Обмен подарка на пончики',
        exchange_gift_stars:  'Обмен подарка на звёзды',
        task_reward:          'Награда за задание',
        task_reward_stars:    'Награда за задание',
        referral_bonus:       'Реферальный бонус',
        referral_bonus_stars: 'Реферальный бонус ⭐',
        case_free_open:       'Бесплатный кейс',
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
        exchange_gift_donuts: 'Gift exchanged for donuts',
        exchange_gift_stars:  'Gift exchanged for stars',
        task_reward:          'Task reward',
        task_reward_stars:    'Task reward',
        referral_bonus:       'Referral bonus',
        referral_bonus_stars: 'Referral bonus ⭐',
        case_free_open:       'Free case',
    }
};

function formatHistoryDate(ts) {
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Функция для поиска фото подарка по gift_id или case_id из описания истории
function getHistoryGiftPhoto(entry) {
    // Бесплатный кейс — всегда показываем его изображение
    if (entry.action_type === 'case_free_open') return '/gifts/freecase.png';

    // Для записей кейса — ищем [case_id:...] и берём фото кейса
    // Только donuts/stars/paid — для gift-выигрышей показываем фото подарка, не кейса
    const caseTypes = new Set([
        'case_win_donuts', 'case_win_stars',
        'case_paid_donuts', 'case_paid_stars'
    ]);
    if (caseTypes.has(entry.action_type) && entry.description) {
        const caseMatch = entry.description.match(/\[case_id:([^\]]+)\]/);
        if (caseMatch) {
            const cid = caseMatch[1];
            // Платный кейс — ищем в casesConfig
            if (casesConfig && casesConfig[cid] && casesConfig[cid].photo) {
                return casesConfig[cid].photo;
            }
            // Бесплатный кейс
            if (cid === 'free') return '/gifts/freecase.png';
        }
    }

    // Только для типов, связанных с подарками
    const giftTypes = new Set([
        'gift_added', 'claim_gift', 'withdraw_gift', 'withdraw_tg_gift',
        'exchange_tg_gift', 'roulette_win_gift', 'roulette_win_tg_gift',
        'case_win_gift', 'case_win_tg_gift', 'exchange_gift_donuts', 'exchange_gift_stars'
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
                let entryTitle = labels[entry.action_type] || entry.action_type;

                // Для кейс-записей donuts/stars/paid — подставляем название кейса
                // case_win_gift / case_win_tg_gift оставляем как есть — там показывается имя подарка
                const caseActionTypes = new Set([
                    'case_win_donuts', 'case_win_stars',
                    'case_paid_donuts', 'case_paid_stars', 'case_free_open'
                ]);
                if (caseActionTypes.has(entry.action_type) && entry.description) {
                    const nameMatch = entry.description.match(/Case '([^']+)'/);
                    if (nameMatch) {
                        const caseName = nameMatch[1];
                        const isWin  = entry.action_type.startsWith('case_win');
                        const isFree = entry.action_type === 'case_free_open';
                        if (isFree) {
                            entryTitle = currentLang === 'ru' ? `Бесплатный кейс` : `Free case`;
                        } else if (isWin) {
                            entryTitle = currentLang === 'ru' ? `Выигрыш: ${caseName}` : `Win: ${caseName}`;
                        } else {
                            entryTitle = currentLang === 'ru' ? `Кейс: ${caseName}` : `Case: ${caseName}`;
                        }
                    }
                }

                let currencyIconUrl = (entry.action_type.includes('stars') || entry.action_type === 'exchange_tg_gift' || entry.action_type === 'exchange_gift_stars') ? '/gifts/stars.png' : '/gifts/dount.png';
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