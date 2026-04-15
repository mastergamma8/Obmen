// =====================================================
// games-cases.js — Логика Игры "Кейсы"
// =====================================================

let currentOpenedCaseId = null;
let isOpeningCase = false;
let freeCaseTimerInterval = null;

function openGamesCases() {
    if (typeof showGameView === 'function') {
        showGameView('games-cases-list-view');
    } else {
        if (typeof vibrate === 'function') vibrate('light');
        document.getElementById('games-main-view').classList.add('hidden');
        document.getElementById('games-cases-list-view').classList.remove('hidden');
    }
    if (typeof syncDemoToggles === 'function') syncDemoToggles();
    renderCasesGrid();
}

function closeGamesCases() {
    if (typeof hideGameView === 'function') {
        hideGameView('games-cases-list-view');
    } else {
        if (typeof vibrate === 'function') vibrate('light');
        document.getElementById('games-cases-list-view').classList.add('hidden');
        document.getElementById('games-main-view').classList.remove('hidden');
    }
    // Stop timer when leaving the view
    if (freeCaseTimerInterval) {
        clearInterval(freeCaseTimerInterval);
        freeCaseTimerInterval = null;
    }
}

// ── Free Case Banner ─────────────────────────────────────────────────────────

async function fetchFreeCaseStatus() {
    try {
        const res = await fetch(`/api/cases/free_status`, {
            headers: getApiHeaders()
        });
        const data = await res.json();
        return data; // { remaining_seconds, available }
    } catch (e) {
        return { remaining_seconds: 0, available: true };
    }
}

function formatCountdown(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

async function renderFreeCaseBanner() {
    const banner = document.getElementById('free-case-banner');
    if (!banner) return;

    const status = await fetchFreeCaseStatus();

    if (status.available) {
        _renderFreeCaseBannerAvailable(banner);
    } else {
        _renderFreeCaseBannerCooldown(banner, status.remaining_seconds);
    }
}

function _renderFreeCaseBannerAvailable(banner) {
    if (freeCaseTimerInterval) {
        clearInterval(freeCaseTimerInterval);
        freeCaseTimerInterval = null;
    }
    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};
    banner.innerHTML = `
        <div class="relative overflow-hidden rounded-3xl border border-green-400/40 bg-gradient-to-r from-green-500/20 via-emerald-500/10 to-teal-500/20 shadow-[0_0_30px_rgba(52,211,153,0.2)] p-4 flex items-center gap-4 cursor-pointer active:scale-[0.98] transition-transform"
             onclick="openFreeCaseDetails()">
            <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-10 pointer-events-none"></div>
            <div class="w-16 h-16 flex-shrink-0 relative z-10 animate-bounce-slow">
                <img src="/gifts/freecase.png" class="w-full h-full object-contain drop-shadow-[0_0_12px_rgba(52,211,153,0.7)]"
                     onerror="this.src='https://via.placeholder.com/64?text=🎁'">
            </div>
            <div class="flex-1 relative z-10">
                <div class="text-green-300 font-black text-base tracking-wide">${t.free_case_title || 'Free Case'}</div>
                <div class="text-white/70 text-xs mt-0.5">${t.free_case_desc || 'Open once every 24 hours!'}</div>
            </div>
            <div class="relative z-10 bg-green-400/20 border border-green-400/50 rounded-xl px-3 py-1.5 text-green-300 font-black text-sm shadow-inner">
                ${t.free_case_open_btn || 'Open!'}
            </div>
        </div>
    `;
}

function _renderFreeCaseBannerCooldown(banner, remainingSeconds) {
    if (freeCaseTimerInterval) clearInterval(freeCaseTimerInterval);
    let seconds = remainingSeconds;

    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};

    const draw = () => {
        if (seconds <= 0) {
            clearInterval(freeCaseTimerInterval);
            freeCaseTimerInterval = null;
            _renderFreeCaseBannerAvailable(banner);
            return;
        }
        banner.innerHTML = `
            <div class="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-r from-white/5 to-white/5 p-4 flex items-center gap-4">
                <div class="w-16 h-16 flex-shrink-0 opacity-40">
                    <img src="/gifts/freecase.png" class="w-full h-full object-contain grayscale"
                         onerror="this.src='https://via.placeholder.com/64?text=🎁'">
                </div>
                <div class="flex-1">
                    <div class="text-white/50 font-black text-base">${t.free_case_title || 'Free Case'}</div>
                    <div class="text-white/30 text-xs mt-0.5">${t.free_case_cooldown || 'Next free case in:'}</div>
                    <div class="text-white/70 font-mono font-black text-lg mt-1 tabular-nums">${formatCountdown(seconds)}</div>
                </div>
                <div class="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-white/30 font-black text-sm">
                    ${t.free_case_wait || 'Wait'}
                </div>
            </div>
        `;
        seconds--;
    };

    draw();
    freeCaseTimerInterval = setInterval(draw, 1000);
}

// ── Free Case Details Modal ───────────────────────────────────────────────────

async function openFreeCaseDetails() {
    if (typeof vibrate === 'function') vibrate('light');

    // В демо-режиме пропускаем проверку cooldown
    if (!isDemoMode) {
        const status = await fetchFreeCaseStatus();
        if (!status.available) {
            const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};
            const h = Math.floor(status.remaining_seconds / 3600);
            const m = Math.floor((status.remaining_seconds % 3600) / 60);
            const msg = (t.free_case_not_yet || 'Free case available in {h}h {m}m.')
                .replace('{h}', h).replace('{m}', m);
            showNotify(msg, 'warning');
            return;
        }
    }

    // Populate modal with FREE_CASE_CONFIG data sent from server via casesConfig
    // We identify the free case as the entry with id === 'free' or use freeCaseConfig global
    const c = typeof freeCaseConfig !== 'undefined' ? freeCaseConfig : null;
    if (!c) return;

    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};

    document.getElementById('cd-photo').src = getImgSrc(c.photo);
    document.getElementById('cd-title').innerText = c.name;

    const btn = document.getElementById('btn-open-case');
    btn.classList.remove('opacity-50', 'pointer-events-none');
    if (isDemoMode) {
        btn.innerHTML = `<span>${t.free_case_open_btn || 'Open for Free!'} <span class="text-orange-300/80 text-xs">(Демо)</span></span>`;
    } else {
        btn.innerHTML = `<span>${t.free_case_open_btn || 'Open for Free!'} </span>`;
    }
    btn.onclick = () => buyAndOpenFreeCase();

    // Items list
    const itemsContainer = document.getElementById('cd-items');
    itemsContainer.innerHTML = '';
    const sortedItems = [...c.items].sort((a, b) => (b.chance || 0) - (a.chance || 0));

    sortedItems.forEach(item => {
        const info = getItemInfoForCase(item);
        const chance = item.chance || 0;
        let rarityColor, rarityBorder, rarityGlow, rarityBg;
        if (chance <= 5) {
            rarityColor = '#facc15'; rarityBorder = 'rgba(250,204,21,0.45)';
            rarityGlow  = 'rgba(250,204,21,0.25)'; rarityBg = 'rgba(250,204,21,0.08)';
        } else if (chance <= 15) {
            rarityColor = '#c084fc'; rarityBorder = 'rgba(192,132,252,0.45)';
            rarityGlow  = 'rgba(192,132,252,0.22)'; rarityBg = 'rgba(192,132,252,0.07)';
        } else {
            rarityColor = '#60a5fa'; rarityBorder = 'rgba(96,165,250,0.35)';
            rarityGlow  = 'rgba(96,165,250,0.18)'; rarityBg = 'rgba(96,165,250,0.06)';
        }

        const card = document.createElement('div');
        card.style.cssText = `
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            gap:6px; padding:10px 6px 8px;
            border-radius:16px;
            background:${rarityBg};
            border:1.5px solid ${rarityBorder};
            box-shadow:0 4px 18px ${rarityGlow}, inset 0 1px 0 rgba(255,255,255,0.06);
            cursor:default; position:relative; overflow:hidden;
        `;
        card.innerHTML = `
            <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0%,${rarityGlow} 0%,transparent 70%);pointer-events:none;"></div>
            <div style="width:52px;height:52px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.25);border-radius:12px;padding:6px;position:relative;z-index:1;">
                <img src="${escapeHtml(info.photo)}" style="width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 2px 6px ${rarityGlow});"
                     onerror="this.src='https://via.placeholder.com/40'">
            </div>
            <span style="font-size:10px;font-weight:800;color:${rarityColor};text-align:center;line-height:1.25;max-width:72px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;position:relative;z-index:1;">${escapeHtml(info.name)}</span>
        `;
        itemsContainer.appendChild(card);
    });

    if (typeof openModal === 'function') openModal('case-details-modal');
}

async function buyAndOpenFreeCase() {
    if (isOpeningCase) return;
    isOpeningCase = true;

    const btn = document.getElementById('btn-open-case');
    const originalBtnHTML = btn.innerHTML;
    btn.classList.add('btn-disabled');
    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};
    btn.innerHTML = `<span>${t.case_opening || 'Opening...'}</span>`;
    if (typeof vibrate === 'function') vibrate('heavy');

    // ── ДЕМО-РЕЖИМ ──────────────────────────────────────────────────────────
    if (isDemoMode) {
        const c = typeof freeCaseConfig !== 'undefined' ? freeCaseConfig : null;
        if (c) {
            const items = c.items || [];
            const total = items.reduce((s, it) => s + (it.chance || 0), 0);
            let rand = Math.random() * total;
            let demoWin = items[0];
            for (const it of items) { rand -= (it.chance || 0); if (rand <= 0) { demoWin = it; break; } }
            setTimeout(() => {
                isOpeningCase = false;
                btn.classList.remove('btn-disabled');
                btn.innerHTML = originalBtnHTML;
                if (typeof closeModal === 'function') closeModal('case-details-modal');
                playCaseAnimation(c, demoWin, true);
            }, 300);
        } else {
            isOpeningCase = false;
            btn.classList.remove('btn-disabled');
            btn.innerHTML = originalBtnHTML;
        }
        return;
    }
    // ────────────────────────────────────────────────────────────────────────

    try {
        const res = await fetch('/api/cases/open_free', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({})
        });
        const data = await res.json();

        if (data.status === 'ok') {
            if (data.balance !== undefined) myBalance = data.balance;
            if (data.stars !== undefined) myStars = data.stars;
            myGifts = data.user_gifts;
            if (typeof updateUI === 'function') updateUI();

            if (typeof closeModal === 'function') closeModal('case-details-modal');
            const c = typeof freeCaseConfig !== 'undefined' ? freeCaseConfig : null;
            if (c) playCaseAnimation(c, data.win_item);

            // Refresh banner to start cooldown countdown
            if (data.next_free_in) {
                const banner = document.getElementById('free-case-banner');
                if (banner) _renderFreeCaseBannerCooldown(banner, data.next_free_in);
            }
        } else {
            showNotify(data.detail || 'Error', 'error');
        }
    } catch (e) {
        console.error("Open free case error:", e);
        showNotify(t.err_conn || 'Connection error', 'error');
    } finally {
        isOpeningCase = false;
        btn.classList.remove('btn-disabled');
        btn.innerHTML = originalBtnHTML;
    }
}


function getPromoCaseCount(caseId) {
    const key = String(caseId);
    return parseInt((myPromoCases && (myPromoCases[key] ?? myPromoCases[caseId])) || 0, 10) || 0;
}

async function openPromoCase(caseId) {
    if (isOpeningCase) return;
    isOpeningCase = true;

    const btn = document.getElementById('btn-open-case');
    const originalBtnHTML = btn ? btn.innerHTML : '';
    if (btn) {
        btn.classList.add('btn-disabled');
        btn.innerHTML = `<span>${(i18n[currentLang] && i18n[currentLang].processing) ? i18n[currentLang].processing : '⏳ Обработка...'}</span>`;
    }

    try {
        const res = await fetch('/api/cases/open_promo', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ gift_id: caseId })
        });
        const data = await res.json();

        if (!res.ok || data.status !== 'ok') {
            showNotify(data.detail || 'Error', 'error');
            return;
        }

        if (data.balance !== undefined) myBalance = data.balance;
        if (data.stars !== undefined) myStars = data.stars;
        if (data.user_gifts) myGifts = data.user_gifts;
        if (data.promo_case_credits) myPromoCases = data.promo_case_credits;
        if (typeof updateUI === 'function') updateUI();

        if (typeof closeModal === 'function') closeModal('case-details-modal');
        const c = casesConfig[String(caseId)] || casesConfig[caseId];
        if (c) playCaseAnimation(c, data.win_item);

        showNotify((i18n[currentLang] && i18n[currentLang].promo_case_opened) ? i18n[currentLang].promo_case_opened : 'Кейс открыт бесплатно!', 'success');
        if (typeof renderCasesGrid === 'function') renderCasesGrid();
    } catch (e) {
        console.error('openPromoCase error:', e);
        showNotify((i18n[currentLang] && i18n[currentLang].err_conn) ? i18n[currentLang].err_conn : 'Ошибка соединения', 'error');
    } finally {
        isOpeningCase = false;
        if (btn) {
            btn.classList.remove('btn-disabled');
            btn.innerHTML = originalBtnHTML;
        }
    }
}

// ── Cases Grid ────────────────────────────────────────────────────────────────

function renderCasesGrid() {
    const grid = document.getElementById('cases-grid');
    if (!grid) return;
    grid.innerHTML = '';

    // Render free case banner first
    renderFreeCaseBanner();

    if (!casesConfig || Object.keys(casesConfig).length === 0) {
        grid.innerHTML = `<div class="col-span-2 text-center text-white/50 text-sm py-10" data-i18n="not_found">Кейсы пока не добавлены</div>`;
        return;
    }

    Object.keys(casesConfig).forEach(id => {
        const c = casesConfig[id];
        const photoUrl = getImgSrc(c.photo);
        const currencyIcon = c.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';

        const card = document.createElement('div');
        card.className = "glass rounded-3xl p-4 flex flex-col items-center justify-between text-center cursor-pointer transition-transform border border-indigo-400/30 shadow-[0_10px_20px_rgba(0,0,0,0.4)] hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] bg-gradient-to-b from-indigo-500/20 to-black/40 relative overflow-hidden group";
        card.onclick = () => openCaseDetails(id);

        const promoCount = getPromoCaseCount(id);
        card.innerHTML = `
            <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-20 pointer-events-none"></div>
            <div class="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-24 bg-indigo-500/30 blur-[30px] rounded-full pointer-events-none group-hover:bg-indigo-400/40 transition-colors"></div>
            ${promoCount > 0 ? `<div class="absolute top-3 right-3 bg-emerald-500 text-white text-[10px] font-black px-2 py-1 rounded-full shadow-lg z-20">FREE ×${promoCount}</div>` : ''}

            <div class="w-24 h-24 mb-3 relative z-10">
                <img src="${escapeHtml(photoUrl)}" class="w-full h-full object-contain drop-shadow-[0_10px_15px_rgba(0,0,0,0.6)] transition-all duration-300" onerror="this.src='https://via.placeholder.com/96?text=📦'">
            </div>

            <h4 class="text-white font-extrabold text-sm mb-3 glow-text w-full truncate relative z-10 tracking-wide">${escapeHtml(c.name)}</h4>

            <div class="bg-black/60 rounded-xl px-3 py-1.5 flex items-center justify-center gap-1.5 border border-white/10 relative z-10 w-full backdrop-blur-sm shadow-inner">
                <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-indigo-300 font-black text-sm">${c.price}</span>
                <img src="${currencyIcon}" class="w-4 h-4 object-contain drop-shadow-[0_0_5px_rgba(59,130,246,0.6)]" onerror="this.src='https://via.placeholder.com/16'">
            </div>
        `;
        grid.appendChild(card);
    });
}

function getItemInfoForCase(item) {
    if (item.type === 'donuts') {
        return { name: `${item.amount}`, photo: '/gifts/dount.png' };
    } else if (item.type === 'stars') {
        return { name: `${item.amount}`, photo: '/gifts/stars.png' };
    } else if (item.type === 'gift') {
        const gift = mainGifts[item.gift_id] || tgGifts[item.gift_id] || baseGifts[item.gift_id];
        if (gift) return { name: gift.name, photo: getImgSrc(gift.photo) };
    }
    return { name: "???", photo: "https://via.placeholder.com/32" };
}

// ── Paid Case Details Modal ───────────────────────────────────────────────────

function openCaseDetails(caseId) {
    if (typeof vibrate === 'function') vibrate('light');
    const c = casesConfig[caseId];
    if (!c) return;
    currentOpenedCaseId = caseId;

    document.getElementById('cd-photo').src = getImgSrc(c.photo);
    document.getElementById('cd-title').innerText = c.name;

    const currencyIcon = c.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';
    const currentBal = c.currency === 'stars' ? myStars : myBalance;

    const btn = document.getElementById('btn-open-case');
    const promoCount = getPromoCaseCount(caseId);
    if (promoCount > 0) {
        btn.classList.remove('opacity-50', 'pointer-events-none');
        btn.innerHTML = `<span>${(i18n[currentLang] && i18n[currentLang].promo_open_free) ? i18n[currentLang].promo_open_free : 'Открыть бесплатно'}</span> <span class="flex items-center gap-1 text-emerald-300">×${promoCount} <img src="/gifts/stars.png" class="w-5 h-5 object-contain"></span>`;
        btn.onclick = () => openPromoCase(caseId);
    } else if (!isDemoMode && currentBal < c.price) {
        btn.classList.add('opacity-50', 'pointer-events-none');
        const notEnoughKey = c.currency === 'stars' ? 'not_enough_stars' : 'not_enough_donuts';
        const txt = (i18n[currentLang] && i18n[currentLang][notEnoughKey]) ? i18n[currentLang][notEnoughKey] : 'Недостаточно средств!';
        btn.innerHTML = `<span>${txt}</span>`;
    } else {
        btn.classList.remove('opacity-50', 'pointer-events-none');
        if (isDemoMode) {
            const txt = (i18n[currentLang] && i18n[currentLang].open_for) ? i18n[currentLang].open_for : 'Открыть за';
            btn.innerHTML = `<span>${txt}</span> <span class="flex items-center gap-1 text-orange-300">${c.price} <img src="${currencyIcon}" class="w-5 h-5 object-contain"> <span class="text-orange-300/70 text-xs">(Демо)</span></span>`;
        } else {
            const txt = (i18n[currentLang] && i18n[currentLang].open_for) ? i18n[currentLang].open_for : 'Открыть за';
            btn.innerHTML = `<span data-i18n="open_for">${txt}</span> <span class="flex items-center gap-1 text-yellow-300">${c.price} <img src="${currencyIcon}" class="w-5 h-5 object-contain"></span>`;
        }
        btn.onclick = () => buyAndOpenCase(caseId);
    }

    const itemsContainer = document.getElementById('cd-items');
    itemsContainer.innerHTML = '';
    const sortedItems = [...c.items].sort((a, b) => (b.chance || 0) - (a.chance || 0));

    sortedItems.forEach(item => {
        const info = getItemInfoForCase(item);
        const chance = item.chance || 0;
        let rarityColor, rarityBorder, rarityGlow, rarityBg;
        if (chance <= 5) {
            rarityColor = '#facc15'; rarityBorder = 'rgba(250,204,21,0.45)';
            rarityGlow  = 'rgba(250,204,21,0.25)'; rarityBg = 'rgba(250,204,21,0.08)';
        } else if (chance <= 15) {
            rarityColor = '#c084fc'; rarityBorder = 'rgba(192,132,252,0.45)';
            rarityGlow  = 'rgba(192,132,252,0.22)'; rarityBg = 'rgba(192,132,252,0.07)';
        } else {
            rarityColor = '#60a5fa'; rarityBorder = 'rgba(96,165,250,0.35)';
            rarityGlow  = 'rgba(96,165,250,0.18)'; rarityBg = 'rgba(96,165,250,0.06)';
        }

        const card = document.createElement('div');
        card.style.cssText = `
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            gap:6px; padding:10px 6px 8px;
            border-radius:16px;
            background:${rarityBg};
            border:1.5px solid ${rarityBorder};
            box-shadow:0 4px 18px ${rarityGlow}, inset 0 1px 0 rgba(255,255,255,0.06);
            cursor:default; position:relative; overflow:hidden;
        `;
        card.innerHTML = `
            <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0%,${rarityGlow} 0%,transparent 70%);pointer-events:none;"></div>
            <div style="width:52px;height:52px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.25);border-radius:12px;padding:6px;position:relative;z-index:1;">
                <img src="${info.photo}" style="width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 2px 6px ${rarityGlow});"
                     onerror="this.src='https://via.placeholder.com/40'">
            </div>
            <span style="font-size:10px;font-weight:800;color:${rarityColor};text-align:center;line-height:1.25;max-width:72px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;position:relative;z-index:1;">${escapeHtml(info.name)}</span>
        `;
        itemsContainer.appendChild(card);
    });

    if (typeof openModal === 'function') openModal('case-details-modal');
}

async function buyAndOpenCase(caseId) {
    if (isOpeningCase) return;
    const c = casesConfig[caseId];

    // ── ДЕМО-РЕЖИМ ──────────────────────────────────────────────────────────
    if (isDemoMode) {
        isOpeningCase = true;
        const btn = document.getElementById('btn-open-case');
        const originalBtnHTML = btn.innerHTML;
        btn.classList.add('btn-disabled');
        const txt = i18n[currentLang]?.case_opening || 'Открываем...';
        btn.innerHTML = `<span>${txt}</span>`;
        if (typeof vibrate === 'function') vibrate('heavy');

        // Выбираем случайный предмет на клиенте без запроса к серверу
        const items = c.items || [];
        const total = items.reduce((s, it) => s + (it.chance || 0), 0);
        let rand = Math.random() * total;
        let demoWin = items[0];
        for (const it of items) { rand -= (it.chance || 0); if (rand <= 0) { demoWin = it; break; } }

        setTimeout(() => {
            isOpeningCase = false;
            btn.classList.remove('btn-disabled');
            btn.innerHTML = originalBtnHTML;
            if (typeof closeModal === 'function') closeModal('case-details-modal');
            playCaseAnimation(c, demoWin, true);
        }, 300);
        return;
    }
    // ────────────────────────────────────────────────────────────────────────

    const currentBal = c.currency === 'stars' ? myStars : myBalance;
    if (currentBal < c.price) {
        showNotify('Недостаточно средств!', 'error');
        return;
    }

    isOpeningCase = true;
    const btn = document.getElementById('btn-open-case');
    const originalBtnHTML = btn.innerHTML;
    btn.classList.add('btn-disabled');
    const txt = i18n[currentLang]?.case_opening || 'Открываем...';
    btn.innerHTML = `<span>${txt}</span>`;
    if (typeof vibrate === 'function') vibrate('heavy');

    try {
        const res = await fetch('/api/cases/open', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ gift_id: parseInt(caseId) })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            if (data.balance !== undefined) myBalance = data.balance;
            if (data.stars !== undefined) myStars = data.stars;
            myGifts = data.user_gifts;
            if (typeof updateUI === 'function') updateUI();

            if (typeof closeModal === 'function') closeModal('case-details-modal');
            playCaseAnimation(c, data.win_item);
        } else {
            showNotify(data.detail || 'Error', 'error');
        }
    } catch (e) {
        console.error("Open case error:", e);
        showNotify(i18n[currentLang]?.err_conn || 'Connection error', 'error');
    } finally {
        isOpeningCase = false;
        btn.classList.remove('btn-disabled');
        btn.innerHTML = originalBtnHTML;
    }
}

// ── Slot Animation ────────────────────────────────────────────────────────────

function playCaseAnimation(caseConfig, winItem, isDemo = false) {
    const modal = document.getElementById('case-animation-modal');
    const track = document.getElementById('cam-reel-track');
    const slotPhase = document.getElementById('cam-slot-phase');
    const resultPhase = document.getElementById('cam-result-phase');
    const flash = document.getElementById('cam-flash');
    const progressBar = document.getElementById('cam-progress-bar');
    const spinLabel = document.getElementById('cam-spin-label');

    if (!modal || !track) return;

    // Reset phases
    slotPhase.classList.remove('hidden');
    slotPhase.style.display = '';
    resultPhase.classList.add('hidden');
    resultPhase.style.display = 'none';
    flash.style.opacity = '0';
    progressBar.style.transition = 'none';
    progressBar.style.width = '0%';

    modal.classList.remove('hidden');
    modal.style.display = 'flex';

    const winInfo = getItemInfoForCase(winItem);
    document.getElementById('cam-item-img').src = winInfo.photo;
    document.getElementById('cam-item-name').innerText = winInfo.name;
    const t = (i18n && i18n[currentLang]) ? i18n[currentLang] : {};
    const typeLabels = {
        donuts: t.type_donuts || 'Донуты',
        stars:  t.type_stars  || 'Звёзды',
        gift:   t.type_gift   || 'Подарок'
    };
    document.getElementById('cam-item-type-label').innerText = typeLabels[winItem.type] || '';
    if (typeof configureCaseGiftActionsIfNeeded === 'function' && winItem.type === 'gift') {
        configureCaseGiftActionsIfNeeded(winItem.gift_id, 'case', isDemo);
    } else {
        // Не подарок — скрываем кнопки действий и показываем кнопку закрытия
        const actionsBox = document.getElementById('cam-gift-actions');
        const closeBtn = document.getElementById('cam-btn-close');
        if (actionsBox) actionsBox.classList.add('hidden');
        if (closeBtn) closeBtn.classList.remove('hidden');
    }

    const items = caseConfig.items || [];
    const pool = items.length > 0 ? items : [winItem];

    const ITEM_W = 96;
    const GAP    = 10;
    const STEP   = ITEM_W + GAP;
    const TOTAL_ITEMS = 60;
    const WIN_INDEX = 52;

    const reelItems = [];
    for (let i = 0; i < TOTAL_ITEMS; i++) {
        reelItems.push(i === WIN_INDEX ? winItem : pool[Math.floor(Math.random() * pool.length)]);
    }

    track.style.transition = 'none';
    track.style.transform = 'translateX(0px)';
    track.innerHTML = '';

    reelItems.forEach((item, idx) => {
        const info = getItemInfoForCase(item);
        const isWinner = (idx === WIN_INDEX);
        const card = document.createElement('div');
        card.style.cssText = `
            min-width:${ITEM_W}px; height:96px;
            border-radius:14px;
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            padding:8px 4px; gap:4px; flex-shrink:0;
            background:${isWinner ? 'rgba(245,158,11,0.18)' : 'rgba(255,255,255,0.04)'};
            border:1.5px solid ${isWinner ? 'rgba(250,204,21,0.6)' : 'rgba(255,255,255,0.08)'};
            box-shadow:${isWinner ? '0 0 18px rgba(245,158,11,0.35)' : 'none'};
            transition:none;
        `;
        card.innerHTML = `
            <img src="${escapeHtml(info.photo)}" style="width:52px;height:52px;object-fit:contain;pointer-events:none;" onerror="this.src='https://via.placeholder.com/52'">
            <span style="font-size:10px;color:rgba(255,255,255,0.65);font-weight:700;text-align:center;line-height:1.2;max-width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(info.name)}</span>
        `;
        track.appendChild(card);
    });

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            const reelContainer = track.parentElement;
            const visibleW = reelContainer.offsetWidth;
            const centerOffset = Math.floor(visibleW / 2);
            const PADDING = 12;
            const finalX = -(WIN_INDEX * STEP + PADDING - centerOffset + ITEM_W / 2);
            const DURATION = 5200;

            progressBar.style.transition = `width ${DURATION}ms linear`;
            progressBar.style.width = '100%';

            if (typeof vibrate === 'function') vibrate('heavy');

            track.style.transition = `transform ${DURATION}ms cubic-bezier(0.12, 0.8, 0.25, 1.0)`;
            track.style.transform = `translateX(${finalX}px)`;

            const startTime = performance.now();
            let lastItemIndex = -1;
            function vibStep(now) {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / DURATION, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const currentX = (finalX) * eased;
                const currentIdx = Math.floor((-currentX + PADDING + centerOffset - ITEM_W / 2) / STEP);
                if (currentIdx > lastItemIndex && currentIdx >= 0 && currentIdx < TOTAL_ITEMS) {
                    if (typeof vibrate === 'function') {
                        if      (progress < 0.6)  vibrate('heavy');
                        else if (progress < 0.85) vibrate('medium');
                        else                       vibrate('light');
                    }
                    lastItemIndex = currentIdx;
                }
                if (progress < 1) requestAnimationFrame(vibStep);
            }
            requestAnimationFrame(vibStep);

            const midLabel = t.case_almost || 'Почти...';
            setTimeout(() => {
                if (spinLabel) spinLabel.innerText = midLabel;
            }, DURATION * 0.65);

            setTimeout(() => {
                flash.style.transition = 'opacity 0.15s ease';
                flash.style.opacity = '1';
                if (typeof vibrate === 'function') vibrate('heavy');

                setTimeout(() => {
                    flash.style.transition = 'opacity 0.5s ease';
                    flash.style.opacity = '0';

                    slotPhase.style.display = 'none';
                    slotPhase.classList.add('hidden');
                    resultPhase.classList.remove('hidden');
                    resultPhase.style.display = 'flex';

                    // Плашка ДЕМО в результате
                    const camDemoBadge = document.getElementById('cam-demo-badge');
                    if (camDemoBadge) camDemoBadge.style.display = isDemo ? '' : 'none';

                    resultPhase.style.opacity = '0';
                    resultPhase.style.transform = 'scale(0.85)';
                    resultPhase.style.transition = 'opacity 0.4s ease, transform 0.4s cubic-bezier(0.175,0.885,0.32,1.275)';
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            resultPhase.style.opacity = '1';
                            resultPhase.style.transform = 'scale(1)';
                        });
                    });

                    if (typeof vibrate === 'function') vibrate('heavy');
                }, 180);
            }, DURATION + 100);
        });
    });
}

function closeCaseAnimation() {
    if (typeof vibrate === 'function') vibrate('light');
    const modal = document.getElementById('case-animation-modal');
    const resultPhase = document.getElementById('cam-result-phase');
    modal.classList.add('hidden');
    modal.style.display = '';
    if (resultPhase) {
        resultPhase.style.opacity = '';
        resultPhase.style.transform = '';
        resultPhase.style.transition = '';
    }
    if (!document.getElementById('games-cases-list-view').classList.contains('hidden')) renderCasesGrid();
}

window.openGamesCases = openGamesCases;
window.closeGamesCases = closeGamesCases;
window.renderCasesGrid = renderCasesGrid;
window.openCaseDetails = openCaseDetails;
window.openFreeCaseDetails = openFreeCaseDetails;
window.buyAndOpenCase = buyAndOpenCase;
window.buyAndOpenFreeCase = buyAndOpenFreeCase;
window.closeCaseAnimation = closeCaseAnimation;