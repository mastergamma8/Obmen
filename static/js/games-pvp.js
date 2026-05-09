// =============================================================
// games-pvp.js — SPACE DONUT PVP
// =============================================================
'use strict';

// ─── State ────────────────────────────────────────────────────
let pvpState = {
    round_id: 0,
    state: 'waiting',
    time_left: 0,
    players: [],
    winner: null,
    pot: { stars: 0, donuts: 0, gifts: 0 },
    last_game: null,
    best_game: null,
};

let pvpPollTimer     = null;
let pvpBallAnimFrame = null;
let pvpBetTab        = 'stars';   // 'stars' | 'donuts' | 'gift'
let pvpInventory     = [];
let pvpBallPos       = { x: 50, y: 50 };
let pvpBallVel       = { x: 1.4, y: 1.1 };
let pvpBallTrail     = [];
let pvpLastState     = '';
let pvpCountdownInterval = null;
let pvpWinnerRevealed    = false;
let pvpRollingStart      = 0;
const PVP_ROLLING_DURATION = 6500; // ms

// Player avatar cache
const pvpAvatarCache = {};

// ─── Open / Close ─────────────────────────────────────────────

function openPvpGame() {
    if (typeof showGameView === 'function') {
        showGameView('games-pvp-view');
    } else {
        document.getElementById('games-main-view')?.classList.add('hidden');
        document.getElementById('games-pvp-view')?.classList.remove('hidden');
    }
    pvpWinnerRevealed = false;
    startPvpPolling();
    loadPvpInventory();
}

function closePvpGame() {
    stopPvpPolling();
    if (typeof hideGameView === 'function') {
        hideGameView('games-pvp-view');
    } else {
        document.getElementById('games-pvp-view')?.classList.add('hidden');
        document.getElementById('games-main-view')?.classList.remove('hidden');
    }
}

// ─── Polling ──────────────────────────────────────────────────

function startPvpPolling() {
    stopPvpPolling();
    pollPvpState();
}

function stopPvpPolling() {
    if (pvpPollTimer)     { clearTimeout(pvpPollTimer);          pvpPollTimer     = null; }
    if (pvpBallAnimFrame) { cancelAnimationFrame(pvpBallAnimFrame); pvpBallAnimFrame = null; }
    if (pvpCountdownInterval) { clearInterval(pvpCountdownInterval); pvpCountdownInterval = null; }
}

async function pollPvpState() {
    try {
        const res  = await fetch('/api/pvp/state', { headers: getApiHeaders() });
        const data = await res.json();
        applyPvpState(data);
    } catch (_) {}

    const interval = pvpState.state === 'rolling' ? 300 : 600;
    pvpPollTimer = setTimeout(pollPvpState, interval);
}

async function loadPvpInventory() {
    try {
        const res  = await fetch('/api/pvp/inventory', { headers: getApiHeaders() });
        const data = await res.json();
        pvpInventory = data.gifts || [];
        renderPvpInventory();
    } catch (_) {}
}

// ─── State application ────────────────────────────────────────

function applyPvpState(data) {
    const prevState   = pvpState.state;
    const prevRoundId = pvpState.round_id;
    pvpState = data;

    if (data.round_id !== prevRoundId) {
        pvpWinnerRevealed = false;
        pvpBallTrail = [];
    }

    // Transition: enter rolling
    if (prevState !== 'rolling' && data.state === 'rolling') {
        pvpRollingStart = performance.now();
        pvpBallPos = { x: 50, y: 50 };
        pvpBallVel = { x: (Math.random() > 0.5 ? 1 : -1) * (1.2 + Math.random() * 0.8),
                       y: (Math.random() > 0.5 ? 1 : -1) * (0.9 + Math.random() * 0.6) };
        startPvpBallAnimation();
    }

    if (data.state !== 'rolling' && prevState === 'rolling') {
        stopPvpBallAnimation();
    }

    // Countdown timer
    if (data.state === 'countdown') {
        if (prevState !== 'countdown') {
            startPvpCountdown(data.time_left);
        }
    } else {
        if (pvpCountdownInterval) {
            clearInterval(pvpCountdownInterval);
            pvpCountdownInterval = null;
        }
    }

    // Show winner reveal
    if (data.state === 'finished' && !pvpWinnerRevealed && data.winner) {
        pvpWinnerRevealed = true;
        stopPvpBallAnimation();
        showPvpWinnerReveal(data.winner);
    }

    pvpLastState = data.state;
    renderPvpArena();
    renderPvpBetPanel();
    renderPvpParticipants();
    renderPvpTopBar();
    updatePvpStatus();
}

// ─── Countdown ────────────────────────────────────────────────

let pvpLocalCountdown = 0;

function startPvpCountdown(timeLeft) {
    pvpLocalCountdown = timeLeft;
    if (pvpCountdownInterval) clearInterval(pvpCountdownInterval);
    pvpCountdownInterval = setInterval(() => {
        pvpLocalCountdown = Math.max(0, pvpLocalCountdown - 0.1);
        const el = document.getElementById('pvp-countdown-val');
        if (el) el.textContent = Math.ceil(pvpLocalCountdown);
        if (pvpLocalCountdown <= 0) {
            clearInterval(pvpCountdownInterval);
            pvpCountdownInterval = null;
        }
    }, 100);
}

// ─── Ball animation ───────────────────────────────────────────

function startPvpBallAnimation() {
    stopPvpBallAnimation();
    animatePvpBall();
}

function stopPvpBallAnimation() {
    if (pvpBallAnimFrame) {
        cancelAnimationFrame(pvpBallAnimFrame);
        pvpBallAnimFrame = null;
    }
}

function animatePvpBall() {
    const elapsed  = performance.now() - pvpRollingStart;
    const progress = Math.min(elapsed / PVP_ROLLING_DURATION, 1);

    // Slow down as we approach end
    const speedFactor = 1 - Math.pow(progress, 2) * 0.85;
    pvpBallPos.x += pvpBallVel.x * speedFactor;
    pvpBallPos.y += pvpBallVel.y * speedFactor;

    // Bounce off walls (0–100 range)
    if (pvpBallPos.x < 5)  { pvpBallPos.x = 5;  pvpBallVel.x =  Math.abs(pvpBallVel.x); }
    if (pvpBallPos.x > 95) { pvpBallPos.x = 95; pvpBallVel.x = -Math.abs(pvpBallVel.x); }
    if (pvpBallPos.y < 8)  { pvpBallPos.y = 8;  pvpBallVel.y =  Math.abs(pvpBallVel.y); }
    if (pvpBallPos.y > 88) { pvpBallPos.y = 88; pvpBallVel.y = -Math.abs(pvpBallVel.y); }

    // Trail
    pvpBallTrail.push({ x: pvpBallPos.x, y: pvpBallPos.y, a: 1 });
    if (pvpBallTrail.length > 18) pvpBallTrail.shift();

    const ball = document.getElementById('pvp-ball');
    if (ball) {
        ball.style.left = pvpBallPos.x + '%';
        ball.style.top  = pvpBallPos.y + '%';
        ball.style.opacity = '1';
    }

    renderPvpTrail();

    if (progress < 1) {
        pvpBallAnimFrame = requestAnimationFrame(animatePvpBall);
    } else {
        pvpBallAnimFrame = null;
    }
}

function renderPvpTrail() {
    const container = document.getElementById('pvp-ball-trail');
    if (!container) return;
    container.innerHTML = '';
    pvpBallTrail.forEach((pt, i) => {
        const alpha = (i / pvpBallTrail.length) * 0.5;
        const size  = 6 + (i / pvpBallTrail.length) * 8;
        const dot = document.createElement('div');
        dot.style.cssText = `
            position:absolute;
            left:${pt.x}%;top:${pt.y}%;
            width:${size}px;height:${size}px;
            border-radius:50%;
            background:rgba(255,255,255,${alpha});
            transform:translate(-50%,-50%);
            pointer-events:none;
        `;
        container.appendChild(dot);
    });
}

// ─── Arena render ─────────────────────────────────────────────

function renderPvpArena() {
    const container = document.getElementById('pvp-arena-players');
    if (!container) return;
    container.innerHTML = '';

    const players  = pvpState.players || [];
    const total    = players.length;
    if (total === 0) return;

    const cx = 50, cy = 48;
    const radius = Math.min(32, 26 + total * 1.5);

    players.forEach((p, i) => {
        const angle  = (i / total) * 2 * Math.PI - Math.PI / 2;
        const px     = cx + radius * Math.cos(angle);
        const py     = cy + radius * Math.sin(angle);
        const pct    = p.win_chance;
        const size   = 36 + (pct / 100) * 28;

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            position:absolute;
            left:${px}%;top:${py}%;
            transform:translate(-50%,-50%);
            display:flex;flex-direction:column;align-items:center;
            z-index:5;
        `;

        const ring = document.createElement('div');
        ring.style.cssText = `
            width:${size}px;height:${size}px;
            border-radius:50%;
            background: radial-gradient(circle, ${p.color}44 0%, ${p.color}22 60%, transparent 100%);
            border:2.5px solid ${p.color};
            box-shadow: 0 0 ${12 + pct * 0.4}px ${p.color}88, inset 0 0 8px ${p.color}33;
            display:flex;align-items:center;justify-content:center;
            transition: all 0.3s ease;
            position:relative;
            overflow:hidden;
        `;

        if (pvpState.state === 'finished' && pvpState.winner?.user_id === p.user_id) {
            ring.style.boxShadow = `0 0 30px ${p.color}, 0 0 60px ${p.color}88`;
            ring.style.border    = `3px solid ${p.color}`;
            ring.classList.add('pvp-winner-pulse');
        }

        const imgSize = size * 0.72;
        if (p.avatar) {
            const img = document.createElement('img');
            img.src    = p.avatar;
            img.style.cssText = `width:${imgSize}px;height:${imgSize}px;border-radius:50%;object-fit:cover;`;
            img.onerror = () => { img.replaceWith(makePvpAvatarFallback(p.name, imgSize, p.color)); };
            ring.appendChild(img);
        } else {
            ring.appendChild(makePvpAvatarFallback(p.name, imgSize, p.color));
        }

        // Win% badge
        const badge = document.createElement('div');
        badge.style.cssText = `
            position:absolute;bottom:-2px;right:-2px;
            background:${p.color};
            color:#000;font-size:8px;font-weight:900;
            padding:1px 4px;border-radius:6px;
            white-space:nowrap;border:1px solid rgba(0,0,0,0.3);
        `;
        badge.textContent = pct.toFixed(1) + '%';
        ring.appendChild(badge);

        // Name label
        const label = document.createElement('div');
        label.style.cssText = `
            margin-top:4px;font-size:9px;color:rgba(255,255,255,0.8);
            font-weight:700;text-align:center;max-width:60px;
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        `;
        label.textContent = p.name;

        wrapper.appendChild(ring);
        wrapper.appendChild(label);
        container.appendChild(wrapper);
    });
}

function makePvpAvatarFallback(name, size, color) {
    const d = document.createElement('div');
    d.style.cssText = `
        width:${size}px;height:${size}px;border-radius:50%;
        background: linear-gradient(135deg, ${color}88, ${color}33);
        display:flex;align-items:center;justify-content:center;
        font-size:${size * 0.45}px;font-weight:900;color:#fff;
    `;
    d.textContent = (name || '?')[0].toUpperCase();
    return d;
}

// ─── Top bar (best/last game) ──────────────────────────────────

function renderPvpTopBar() {
    const last = pvpState.last_game;
    const best = pvpState.best_game;

    const lastEl = document.getElementById('pvp-last-game');
    const bestEl = document.getElementById('pvp-best-game');

    if (lastEl) {
        if (last) {
            lastEl.innerHTML = `
                <div class="flex items-center gap-1.5">
                    <span class="text-white/40 text-[9px] font-bold uppercase tracking-wide">Последняя</span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                    ${last.avatar ? `<img src="${last.avatar}" class="w-5 h-5 rounded-full object-cover" onerror="this.style.display='none'">` : ''}
                    <span class="text-white/80 text-[10px] font-bold truncate max-w-[70px]">${escHtml(last.name)}</span>
                    ${last.total_stars > 0 ? `<span class="text-yellow-300 text-[10px] font-black">+${last.total_stars}⭐</span>` : ''}
                </div>
            `;
        } else {
            lastEl.innerHTML = `<span class="text-white/20 text-[9px]">Нет данных</span>`;
        }
    }

    if (bestEl) {
        if (best) {
            bestEl.innerHTML = `
                <div class="flex items-center gap-1.5">
                    <span class="text-amber-400/60 text-[9px] font-bold uppercase tracking-wide">🏆 Лучшая</span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                    ${best.avatar ? `<img src="${best.avatar}" class="w-5 h-5 rounded-full object-cover" onerror="this.style.display='none'">` : ''}
                    <span class="text-white/80 text-[10px] font-bold truncate max-w-[70px]">${escHtml(best.name)}</span>
                    ${best.total_stars > 0 ? `<span class="text-amber-300 text-[10px] font-black">+${best.total_stars}⭐</span>` : ''}
                </div>
            `;
        } else {
            bestEl.innerHTML = `<span class="text-white/20 text-[9px]">Нет данных</span>`;
        }
    }
}

// ─── Status overlay ───────────────────────────────────────────

function updatePvpStatus() {
    const statusEl  = document.getElementById('pvp-status-text');
    const countEl   = document.getElementById('pvp-countdown-overlay');
    const potEl     = document.getElementById('pvp-pot-display');

    if (statusEl) {
        const s = pvpState.state;
        if      (s === 'waiting')   statusEl.textContent = '⏳ Ожидаем игроков...';
        else if (s === 'countdown') statusEl.textContent = '🔥 Ставки ещё принимаются!';
        else if (s === 'rolling')   statusEl.textContent = '⚪ Шарик катится...';
        else if (s === 'finished')  statusEl.textContent = '🏆 Победитель определён!';
    }

    if (countEl) {
        if (pvpState.state === 'countdown') {
            countEl.classList.remove('hidden');
        } else {
            countEl.classList.add('hidden');
        }
    }

    if (potEl) {
        const p = pvpState.pot;
        const parts = [];
        if (p.stars  > 0)  parts.push(`${p.stars}⭐`);
        if (p.donuts > 0)  parts.push(`${formatDonut ? formatDonut(p.donuts) : p.donuts}🍩`);
        if (p.gifts  > 0)  parts.push(`${p.gifts}🎁`);
        potEl.textContent = parts.length > 0 ? 'Банк: ' + parts.join(' + ') : 'Банк пуст';
    }

    // Ball visibility
    const ball = document.getElementById('pvp-ball');
    if (ball) {
        ball.style.opacity = pvpState.state === 'rolling' ? '1' : '0';
    }
}

// ─── Participants list ────────────────────────────────────────

function renderPvpParticipants() {
    const list = document.getElementById('pvp-participants-list');
    const cnt  = document.getElementById('pvp-players-count');
    if (!list) return;

    const players = pvpState.players || [];
    if (cnt) cnt.textContent = players.length;

    if (players.length === 0) {
        list.innerHTML = `<p class="text-center text-white/30 text-xs py-3">Пока нет участников</p>`;
        return;
    }

    list.innerHTML = players.map(p => {
        const betParts = [];
        if (p.stars_bet  > 0)  betParts.push(`<span class="text-yellow-300 font-bold">${p.stars_bet}⭐</span>`);
        if (p.donuts_bet > 0)  betParts.push(`<span class="text-orange-300 font-bold">${p.donuts_bet}🍩</span>`);
        if (p.gift_bets?.length > 0) betParts.push(`<span class="text-purple-300 font-bold">${p.gift_bets.length}🎁</span>`);

        const isWinner = pvpState.state === 'finished' && pvpState.winner?.user_id === p.user_id;

        return `
            <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all ${isWinner ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/10 border border-amber-500/40' : 'bg-white/3 border border-white/5'}">
                <div class="relative flex-shrink-0">
                    <div class="w-8 h-8 rounded-full overflow-hidden border-2 flex-shrink-0" style="border-color:${p.color}">
                        ${p.avatar
                            ? `<img src="${p.avatar}" class="w-full h-full object-cover" onerror="this.outerHTML='<div class=\\'w-full h-full flex items-center justify-center text-xs font-black\\'>${(p.name||'?')[0].toUpperCase()}</div>'">`
                            : `<div class="w-full h-full flex items-center justify-center text-xs font-black" style="background:${p.color}44">${(p.name||'?')[0].toUpperCase()}</div>`
                        }
                    </div>
                    ${isWinner ? '<div class="absolute -top-1 -right-1 text-sm">👑</div>' : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-bold text-white truncate">${escHtml(p.name)}</div>
                    <div class="flex items-center gap-1.5 mt-0.5">${betParts.join('')}</div>
                </div>
                <div class="text-right flex-shrink-0">
                    <div class="text-xs font-black" style="color:${p.color}">${p.win_chance}%</div>
                    <div class="text-[9px] text-white/40">шанс</div>
                </div>
            </div>
        `;
    }).join('');
}

// ─── Bet panel ────────────────────────────────────────────────

function renderPvpBetPanel() {
    const panel  = document.getElementById('pvp-bet-panel');
    const canBet = pvpState.state === 'waiting' || pvpState.state === 'countdown';
    if (panel) {
        panel.style.opacity     = canBet ? '1' : '0.45';
        panel.style.pointerEvents = canBet ? 'auto' : 'none';
    }
}

function pvpSwitchBetTab(tab) {
    pvpBetTab = tab;
    ['stars', 'donuts', 'gift'].forEach(t => {
        const btn    = document.getElementById(`pvp-tab-${t}`);
        const pane   = document.getElementById(`pvp-pane-${t}`);
        const active = t === tab;
        if (btn) {
            btn.classList.toggle('pvp-tab-active', active);
            btn.classList.toggle('text-white', active);
            btn.classList.toggle('text-white/40', !active);
        }
        if (pane) pane.classList.toggle('hidden', !active);
    });
}

function renderPvpInventory() {
    const grid = document.getElementById('pvp-gift-grid');
    if (!grid) return;

    if (pvpInventory.length === 0) {
        grid.innerHTML = `<p class="col-span-3 text-center text-white/30 text-xs py-4">Инвентарь пуст</p>`;
        return;
    }

    grid.innerHTML = pvpInventory.map(g => `
        <div onclick="placePvpGiftBet(${g.gift_id})"
             class="glass rounded-xl p-2 flex flex-col items-center gap-1 cursor-pointer active:scale-95 transition-transform border border-white/10 hover:border-purple-500/40 relative">
            <img src="${g.photo}" class="w-10 h-10 object-contain drop-shadow-md" onerror="this.src='/gifts/dount.png'">
            <div class="text-[9px] text-white/70 text-center leading-tight max-w-[56px] truncate">${escHtml(g.name || 'Gift')}</div>
            <div class="text-[9px] text-yellow-300 font-bold">${g.value_stars}⭐</div>
            ${g.amount > 1 ? `<div class="absolute top-1 right-1 bg-purple-500 rounded-full w-4 h-4 flex items-center justify-center text-[8px] font-black text-white">${g.amount}</div>` : ''}
        </div>
    `).join('');
}

// ─── Placing bets ─────────────────────────────────────────────

async function placePvpBet() {
    const state = pvpState.state;
    if (state !== 'waiting' && state !== 'countdown') {
        if (typeof showNotify === 'function') showNotify('Ставки сейчас не принимаются', 'warning');
        return;
    }

    if (pvpBetTab === 'stars') {
        const amount = parseInt(document.getElementById('pvp-stars-input')?.value || '0');
        if (!amount || amount < 50) {
            if (typeof showNotify === 'function') showNotify('Минимум 50 ⭐', 'warning');
            return;
        }
        await sendPvpBet('/api/pvp/bet/stars', { amount });

    } else if (pvpBetTab === 'donuts') {
        const amount = parseFloat(document.getElementById('pvp-donuts-input')?.value || '0');
        if (!amount || amount < 0.1) {
            if (typeof showNotify === 'function') showNotify('Минимум 0.1 🍩', 'warning');
            return;
        }
        await sendPvpBet('/api/pvp/bet/donuts', { amount });
    }
}

async function placePvpGiftBet(gift_id) {
    const state = pvpState.state;
    if (state !== 'waiting' && state !== 'countdown') {
        if (typeof showNotify === 'function') showNotify('Ставки сейчас не принимаются', 'warning');
        return;
    }
    if (typeof vibrate === 'function') vibrate('light');
    await sendPvpBet('/api/pvp/bet/gift', { gift_id });
    await loadPvpInventory();
}

async function sendPvpBet(url, body) {
    const btn = document.getElementById('pvp-bet-btn');
    if (btn) { btn.disabled = true; btn.classList.add('opacity-60'); }
    try {
        if (typeof vibrate === 'function') vibrate('light');
        const res  = await fetch(url, {
            method: 'POST',
            headers: { ...getApiHeaders(), 'Content-Type': 'application/json' },
            body:    JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) {
            if (typeof showNotify === 'function') showNotify(data.detail || 'Ошибка', 'error');
            return;
        }
        if (typeof showNotify === 'function') showNotify('Ставка принята! 🎯', 'success');
        // Update balances
        if (typeof updateBalanceDisplay === 'function') updateBalanceDisplay(data);
    } catch (e) {
        if (typeof showNotify === 'function') showNotify('Ошибка сети', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.classList.remove('opacity-60'); }
    }
}

function setPvpStarsBet(preset) {
    const inp = document.getElementById('pvp-stars-input');
    if (!inp) return;
    const userData = window._userData || {};
    const balance  = userData.stars || 0;
    if (preset === 'min')       inp.value = 50;
    else if (preset === 'x2')   inp.value = Math.min(balance, Math.max(50, parseInt(inp.value || 50) * 2));
    else if (preset === 'max')  inp.value = balance;
    else                        inp.value = preset;
}

function setPvpDonutsBet(preset) {
    const inp = document.getElementById('pvp-donuts-input');
    if (!inp) return;
    const userData = window._userData || {};
    const balance  = userData.balance || 0;
    if (preset === 'min')      inp.value = 0.1;
    else if (preset === 'x2')  inp.value = Math.min(balance, Math.max(0.1, parseFloat(inp.value || 0.1) * 2));
    else if (preset === 'max') inp.value = balance;
    else                       inp.value = preset;
}

// ─── Winner reveal ────────────────────────────────────────────

function showPvpWinnerReveal(winner) {
    const overlay = document.getElementById('pvp-winner-overlay');
    if (!overlay) return;

    const player = pvpState.players.find(p => p.user_id === winner.user_id);
    const pot    = pvpState.pot;
    const potStr = [];
    if (pot.stars  > 0) potStr.push(`${Math.floor(pot.stars  * 0.95)}⭐`);
    if (pot.donuts > 0) potStr.push(`${(pot.donuts * 0.95).toFixed(2)}🍩`);
    if (pot.gifts  > 0) potStr.push(`${pot.gifts}🎁`);

    overlay.innerHTML = `
        <div class="pvp-winner-card flex flex-col items-center gap-3 p-6 text-center animate-pvp-winner-pop">
            <div class="text-3xl">🏆</div>
            <div class="pvp-winner-avatar" style="border-color:${winner.color};box-shadow:0 0 30px ${winner.color}88">
                ${winner.avatar
                    ? `<img src="${winner.avatar}" class="w-full h-full object-cover rounded-full" onerror="this.style.display='none'">`
                    : `<div class="w-full h-full flex items-center justify-center text-2xl font-black rounded-full" style="background:${winner.color}33">${(winner.name||'?')[0]}</div>`
                }
            </div>
            <div class="text-xl font-black text-white">${escHtml(winner.name)}</div>
            <div class="text-sm text-white/60">забирает весь банк</div>
            <div class="flex gap-2 flex-wrap justify-center">
                ${potStr.map(s => `<span class="px-3 py-1 rounded-full text-sm font-black bg-white/10 text-white">${s}</span>`).join('')}
            </div>
            <div class="pvp-confetti-emitter" id="pvp-confetti"></div>
        </div>
    `;
    overlay.classList.remove('hidden');
    spawnPvpConfetti();

    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }

    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 6500);
}

function spawnPvpConfetti() {
    const container = document.getElementById('pvp-confetti');
    if (!container) return;
    const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#fff', '#FFEAA7', '#DDA0DD'];
    for (let i = 0; i < 40; i++) {
        const c = document.createElement('div');
        c.className = 'pvp-confetti-piece';
        c.style.cssText = `
            position:absolute;
            width:${4 + Math.random() * 6}px;
            height:${4 + Math.random() * 6}px;
            background:${colors[Math.floor(Math.random() * colors.length)]};
            border-radius:${Math.random() > 0.5 ? '50%' : '2px'};
            left:${Math.random() * 100}%;
            top:0;
            opacity:1;
            animation: pvpConfettiFall ${1.5 + Math.random() * 2}s ease-out forwards;
            animation-delay:${Math.random() * 0.8}s;
        `;
        container.appendChild(c);
    }
}

// ─── Utility ──────────────────────────────────────────────────

function escHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
      }
