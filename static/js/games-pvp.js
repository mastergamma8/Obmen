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

    // Transition: enter rolling — use server-provided seed + timestamp for sync
    if (prevState !== 'rolling' && data.state === 'rolling') {
        // Server timestamp lets us compute how much of the animation has already elapsed,
        // so a user who joins mid-round sees the ball in the correct position.
        const serverNow      = Date.now() / 1000;
        const elapsedSeconds = data.rolling_start_ts > 0
            ? Math.max(0, serverNow - data.rolling_start_ts)
            : 0;
        pvpRollingStart = performance.now() - elapsedSeconds * 1000;

        // Seeded PRNG so every client gets the same initial velocity
        pvpInitBallFromSeed(data.ball_seed || 1);
        startPvpBallAnimation();
    }

    // Re-joining during rolling: keep animation in sync even without state transition
    if (data.state === 'rolling' && prevState === 'rolling' && data.rolling_start_ts > 0) {
        // No-op: animation frame loop already tracks elapsed from pvpRollingStart
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
        // Guide ball to winner's segment, then show reveal
        const target = getPvpWinnerSegmentCenter(data.winner.user_id);
        animatePvpBallToTarget(target, () => showPvpWinnerReveal(data.winner));
    }

    pvpLastState = data.state;
    renderPvpArena();
    renderPvpBetPanel();
    renderPvpParticipants();
    renderPvpTopBar();
    updatePvpStatus();

    // Update round badge
    const badge = document.getElementById('pvp-round-badge');
    if (badge) badge.textContent = `Round #${data.round_id}`;

    // Sync balance + inventory when game ends and after new round starts
    if ((data.state === 'finished' && prevState === 'rolling') ||
        (data.state === 'waiting' && prevState === 'finished')) {
        setTimeout(pvpRefreshUserData, 1200);
    }
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

// ─── Seeded PRNG (Mulberry32) ────────────────────────────────
// Identical seed → identical sequence on every client.
let _pvpRng = () => Math.random();

function pvpInitBallFromSeed(seed) {
    // Mulberry32 — fast, good distribution
    let s = seed >>> 0;
    _pvpRng = () => {
        s += 0x6D2B79F5;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    pvpBallPos = { x: 50, y: 50 };
    pvpBallVel = {
        x: (_pvpRng() > 0.5 ? 1 : -1) * (1.2 + _pvpRng() * 0.8),
        y: (_pvpRng() > 0.5 ? 1 : -1) * (0.9 + _pvpRng() * 0.6),
    };
}

function animatePvpBall() {
    const elapsed  = performance.now() - pvpRollingStart;
    const progress = Math.min(elapsed / PVP_ROLLING_DURATION, 1);

    // Decelerate toward the end
    const speedFactor = 1 - Math.pow(progress, 2) * 0.85;
    pvpBallPos.x += pvpBallVel.x * speedFactor;
    pvpBallPos.y += pvpBallVel.y * speedFactor;

    // Bounce off walls — stays within arena bounds
    if (pvpBallPos.x < 5)  { pvpBallPos.x = 5;  pvpBallVel.x =  Math.abs(pvpBallVel.x); }
    if (pvpBallPos.x > 95) { pvpBallPos.x = 95; pvpBallVel.x = -Math.abs(pvpBallVel.x); }
    if (pvpBallPos.y < 8)  { pvpBallPos.y = 8;  pvpBallVel.y =  Math.abs(pvpBallVel.y); }
    if (pvpBallPos.y > 88) { pvpBallPos.y = 88; pvpBallVel.y = -Math.abs(pvpBallVel.y); }

    // Trail
    pvpBallTrail.push({ x: pvpBallPos.x, y: pvpBallPos.y, a: 1 });
    if (pvpBallTrail.length > 18) pvpBallTrail.shift();

    const ball = document.getElementById('pvp-ball');
    if (ball) {
        ball.style.left    = pvpBallPos.x + '%';
        ball.style.top     = pvpBallPos.y + '%';
        ball.style.opacity = '1';
    }

    // Contained zoom: scale only #pvp-arena-players (clipped by overflow:hidden parent)
    // so the effect never escapes the arena border.
    const arenaPlayers = document.getElementById('pvp-arena-players');
    if (arenaPlayers) {
        if (progress > 0.80) {
            const zoomT = (progress - 0.80) / 0.20;
            const scale = 1 + zoomT * 0.40;
            arenaPlayers.style.transform       = `scale(${scale.toFixed(3)})`;
            arenaPlayers.style.transformOrigin = `${pvpBallPos.x}% ${pvpBallPos.y}%`;
            arenaPlayers.style.transition      = 'transform 0.12s ease-out';
        } else {
            arenaPlayers.style.transform  = '';
            arenaPlayers.style.transition = '';
        }
    }

    renderPvpTrail();

    if (progress < 1) {
        pvpBallAnimFrame = requestAnimationFrame(animatePvpBall);
    } else {
        pvpBallAnimFrame = null;
        // Smoothly reset zoom
        if (arenaPlayers) {
            arenaPlayers.style.transition = 'transform 0.5s ease-in-out';
            arenaPlayers.style.transform  = '';
        }
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

// ─── Arena render — SQUARE GRID ───────────────────────────────

/**
 * Renders players as a responsive square-card grid inside the arena.
 * Each card shows: avatar, name, win%, bet breakdown.
 * Winner card gets a glowing gold highlight.
 */
function renderPvpArena() {
    const container = document.getElementById('pvp-arena-players');
    if (!container) return;
    container.innerHTML = '';

    const players = pvpState.players || [];
    if (players.length === 0) return;

    // Grid layout: auto columns, constrained card width
    const cols  = players.length <= 2 ? players.length : Math.min(players.length, 3);
    container.style.cssText = `
        position:absolute; inset:0; overflow:hidden;
        display:grid;
        grid-template-columns: repeat(${cols}, 1fr);
        gap:4px; padding:8px;
        align-items:stretch;
    `;

    players.forEach((p, idx) => {
        const isWinner = pvpState.state === 'finished' && pvpState.winner?.user_id === p.user_id;

        const card = document.createElement('div');
        card.id    = `pvp-player-card-${p.user_id}`;
        card.style.cssText = `
            border-radius:12px;
            border:2px solid ${isWinner ? p.color : p.color + '55'};
            background:${isWinner
                ? `linear-gradient(160deg, ${p.color}33, ${p.color}11)`
                : `linear-gradient(160deg, rgba(255,255,255,0.05), rgba(0,0,0,0.3))`};
            box-shadow:${isWinner ? `0 0 20px ${p.color}88, 0 0 40px ${p.color}44` : 'none'};
            display:flex; flex-direction:column; align-items:center;
            justify-content:center; gap:4px; padding:8px 4px;
            position:relative; overflow:hidden; cursor:default;
            transition: box-shadow 0.3s ease;
        `;
        if (isWinner) card.classList.add('pvp-winner-pulse');

        // Glow stripe at top matching player colour
        const stripe = document.createElement('div');
        stripe.style.cssText = `
            position:absolute; top:0; left:0; right:0; height:3px;
            background:${p.color};
            border-radius:12px 12px 0 0;
        `;
        card.appendChild(stripe);

        // Avatar
        const avatarWrap = document.createElement('div');
        avatarWrap.style.cssText = `
            width:40px; height:40px; border-radius:50%;
            border:2px solid ${p.color};
            box-shadow:0 0 10px ${p.color}77;
            overflow:hidden; flex-shrink:0;
            background:${p.color}33;
            display:flex; align-items:center; justify-content:center;
        `;
        if (p.avatar) {
            const img = document.createElement('img');
            img.src = p.avatar;
            img.style.cssText = 'width:100%;height:100%;object-fit:cover;';
            img.onerror = () => img.replaceWith(makePvpAvatarFallback(p.name, 40, p.color));
            avatarWrap.appendChild(img);
        } else {
            avatarWrap.appendChild(makePvpAvatarFallback(p.name, 40, p.color));
        }
        card.appendChild(avatarWrap);

        // Winner crown
        if (isWinner) {
            const crown = document.createElement('div');
            crown.style.cssText = 'position:absolute;top:6px;right:6px;font-size:14px;';
            crown.textContent = '👑';
            card.appendChild(crown);
        }

        // Name
        const nameEl = document.createElement('div');
        nameEl.style.cssText = `
            font-size:10px; font-weight:800; color:rgba(255,255,255,0.9);
            text-align:center; max-width:90%; overflow:hidden;
            text-overflow:ellipsis; white-space:nowrap;
            text-shadow:0 1px 4px rgba(0,0,0,0.8);
        `;
        nameEl.textContent = p.name;
        card.appendChild(nameEl);

        // Win % badge
        const badge = document.createElement('div');
        badge.style.cssText = `
            background:${p.color}; color:#000;
            font-size:8px; font-weight:900;
            padding:2px 7px; border-radius:8px;
            border:1px solid rgba(0,0,0,0.25);
            letter-spacing:0.3px;
        `;
        badge.textContent = p.win_chance.toFixed(1) + '%';
        card.appendChild(badge);

        // Bets summary
        const bets = document.createElement('div');
        bets.style.cssText = 'display:flex;flex-wrap:wrap;gap:2px;justify-content:center;max-width:100%;';
        if (p.stars_bet  > 0) bets.innerHTML += `<span style="font-size:8px;color:#fbbf24;font-weight:800;">${p.stars_bet}⭐</span>`;
        if (p.donuts_bet > 0) bets.innerHTML += `<span style="font-size:8px;color:#fb923c;font-weight:800;">${p.donuts_bet}🍩</span>`;
        if (p.gift_bets?.length > 0) {
            p.gift_bets.slice(0, 2).forEach(gb => {
                const gs = document.createElement('span');
                gs.style.cssText = 'font-size:8px;color:#c084fc;font-weight:800;display:flex;align-items:center;gap:1px;';
                if (gb.gift_photo) {
                    gs.innerHTML = `<img src="${gb.gift_photo}" style="width:12px;height:12px;object-fit:contain;" onerror="this.outerHTML='🎁'">`;
                } else {
                    gs.textContent = '🎁';
                }
                bets.appendChild(gs);
            });
            if (p.gift_bets.length > 2) {
                const more = document.createElement('span');
                more.style.cssText = 'font-size:8px;color:#c084fc;font-weight:800;';
                more.textContent = `+${p.gift_bets.length - 2}🎁`;
                bets.appendChild(more);
            }
        }
        if (bets.innerHTML) card.appendChild(bets);

        container.appendChild(card);
    });
}

function makePvpAvatarFallback(name, size, color) {
    const d = document.createElement('div');
    d.style.cssText = `
        width:${size}px;height:${size}px;border-radius:50%;
        background: linear-gradient(135deg, ${color}88, ${color}33);
        display:flex;align-items:center;justify-content:center;
        font-size:${Math.round(size * 0.45)}px;font-weight:900;color:#fff;
    `;
    d.textContent = (name || '?')[0].toUpperCase();
    return d;
}

// Fullscreen removed — zoom is contained within arena border via overflow:hidden

// ─── Top bar (best/last game) ──────────────────────────────────

function _formatGameStars(game) {
    if (!game) return '';
    const val = game.total_value_stars || game.total_stars || 0;
    return val > 0 ? `+${val}⭐` : '';
}

function renderPvpTopBar() {
    const last = pvpState.last_game;
    const best = pvpState.best_game;

    const lastEl = document.getElementById('pvp-last-game');
    const bestEl = document.getElementById('pvp-best-game');

    if (lastEl) {
        if (last) {
            const valStr = _formatGameStars(last);
            lastEl.innerHTML = `
                <div class="flex items-center gap-1.5">
                    <span class="text-white/40 text-[9px] font-bold uppercase tracking-wide">Последняя</span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                    ${last.avatar ? `<img src="${last.avatar}" class="w-5 h-5 rounded-full object-cover" onerror="this.style.display='none'">` : ''}
                    <span class="text-white/80 text-[10px] font-bold truncate max-w-[70px]">${escHtml(last.name)}</span>
                    ${valStr ? `<span class="text-yellow-300 text-[10px] font-black">${valStr}</span>` : ''}
                </div>
            `;
        } else {
            lastEl.innerHTML = `<span class="text-white/20 text-[9px]">Нет данных</span>`;
        }
    }

    if (bestEl) {
        if (best) {
            const valStr = _formatGameStars(best);
            bestEl.innerHTML = `
                <div class="flex items-center gap-1.5">
                    <span class="text-amber-400/60 text-[9px] font-bold uppercase tracking-wide">🏆 Лучшая</span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                    ${best.avatar ? `<img src="${best.avatar}" class="w-5 h-5 rounded-full object-cover" onerror="this.style.display='none'">` : ''}
                    <span class="text-white/80 text-[10px] font-bold truncate max-w-[70px]">${escHtml(best.name)}</span>
                    ${valStr ? `<span class="text-amber-300 text-[10px] font-black">${valStr}</span>` : ''}
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
        // Build rich pot line: stars + donuts as text, gifts as thumbnails
        let html = '';
        if (p.stars  > 0) html += `<span class="font-black text-yellow-300">${p.stars}⭐</span>`;
        if (p.donuts > 0) {
            if (html) html += `<span class="text-white/40 mx-1">+</span>`;
            const dn = typeof formatDonut === 'function' ? formatDonut(p.donuts) : p.donuts;
            html += `<span class="font-black text-orange-300">${dn}🍩</span>`;
        }
        const previews = p.gift_previews || [];
        if (previews.length > 0) {
            if (html) html += `<span class="text-white/40 mx-1">+</span>`;
            previews.slice(0, 3).forEach(g => {
                if (g.photo) {
                    html += `<img src="${g.photo}" title="${escHtml(g.name)}" style="width:16px;height:16px;object-fit:contain;display:inline-block;vertical-align:middle;" onerror="this.outerHTML='🎁'">`;
                } else {
                    html += `<span>🎁</span>`;
                }
            });
            if (p.gifts > 3) html += `<span class="text-purple-300 font-bold text-[9px]">+${p.gifts - 3}</span>`;
        } else if (p.gifts > 0) {
            if (html) html += `<span class="text-white/40 mx-1">+</span>`;
            html += `<span class="font-black text-purple-300">${p.gifts}🎁</span>`;
        }

        if (html) {
            potEl.innerHTML = `<span class="text-white/50 mr-1">Банк:</span>` + html;
        } else {
            potEl.textContent = 'Банк пуст';
        }
    }

    // Ball: visible only while rolling
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

    grid.innerHTML = pvpInventory.map(g => {
        // Live exchange_stars from backend — same calculation as profile's "Обменять на" button
        const exchangeStars = g.exchange_stars > 0 ? g.exchange_stars : g.value_stars;
        return `
        <div onclick="placePvpGiftBet(${g.gift_id})"
             class="glass rounded-xl p-2 flex flex-col items-center gap-1 cursor-pointer active:scale-95 transition-transform border border-white/10 hover:border-purple-500/40 relative">
            <img src="${g.photo}" class="w-10 h-10 object-contain drop-shadow-md" onerror="this.src='/gifts/dount.png'">
            <div class="text-[9px] text-white/70 text-center leading-tight max-w-[56px] truncate">${escHtml(g.name || 'Gift')}</div>
            <div class="flex items-center gap-0.5 text-[9px] text-amber-300 font-bold leading-tight">
                <span>→ ${exchangeStars}</span>
                <img src="/gifts/stars.png" class="w-3 h-3 object-contain inline-block" onerror="this.outerHTML='⭐'">
            </div>
            ${g.amount > 1 ? `<div class="absolute top-1 right-1 bg-purple-500 rounded-full w-4 h-4 flex items-center justify-center text-[8px] font-black text-white">${g.amount}</div>` : ''}
        </div>
    `}).join('');
}

// ─── Balance + inventory sync ─────────────────────────────────

async function pvpRefreshUserData() {
    try {
        const res  = await fetch('/api/pvp/user_balance', { headers: getApiHeaders() });
        const data = await res.json();
        if (data.balance !== undefined) myBalance = data.balance;
        if (data.stars   !== undefined) myStars   = data.stars;
        if (data.gifts   !== undefined) myGifts   = data.gifts;
        if (typeof updateUI      === 'function') updateUI();
        if (typeof renderProfile === 'function') renderProfile();
    } catch (_) {}
    await loadPvpInventory();
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
        // Update balances immediately from response
        if (data.balance !== undefined) myBalance = data.balance;
        if (data.stars   !== undefined) myStars   = data.stars;
        if (data.gifts   !== undefined) myGifts   = data.gifts;
        if (typeof updateUI      === 'function') updateUI();
        if (typeof renderProfile === 'function') renderProfile();
    } catch (e) {
        if (typeof showNotify === 'function') showNotify('Ошибка сети', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.classList.remove('opacity-60'); }
    }
}

function setPvpStarsBet(preset) {
    const inp = document.getElementById('pvp-stars-input');
    if (!inp) return;
    const balance = (typeof myStars !== 'undefined' ? myStars : 0);
    if (preset === 'min')       inp.value = 50;
    else if (preset === 'x2')   inp.value = Math.min(balance, Math.max(50, parseInt(inp.value || '50') * 2));
    else if (preset === 'max')  inp.value = balance;
    else                        inp.value = preset;
}

function setPvpDonutsBet(preset) {
    const inp = document.getElementById('pvp-donuts-input');
    if (!inp) return;
    const balance = (typeof myBalance !== 'undefined' ? myBalance : 0);
    if (preset === 'min')      inp.value = 0.1;
    else if (preset === 'x2')  inp.value = Math.min(balance, Math.max(0.1, parseFloat(inp.value || '0.1') * 2));
    else if (preset === 'max') inp.value = balance;
    else                       inp.value = preset;
}

// ─── Ball guidance to winner card ─────────────────────────────

/**
 * Returns the center of the winner player-card as % coordinates
 * within the arena container, using live getBoundingClientRect().
 * Works for any grid size — no geometry hardcoding needed.
 */
function getPvpWinnerSegmentCenter(winnerId) {
    const arena = document.getElementById('pvp-arena-players');
    const card  = document.getElementById('pvp-player-card-' + winnerId);
    if (!arena || !card) return { x: 50, y: 50 };

    const arenaRect = arena.getBoundingClientRect();
    const cardRect  = card.getBoundingClientRect();

    const x = ((cardRect.left - arenaRect.left) + cardRect.width  / 2) / arenaRect.width  * 100;
    const y = ((cardRect.top  - arenaRect.top)  + cardRect.height / 2) / arenaRect.height * 100;

    return {
        x: Math.max(5,  Math.min(95, x)),
        y: Math.max(8,  Math.min(88, y)),
    };
}

/**
 * Two-phase ball animation: quick arc toward winner, then slow precise landing.
 * Calls callback after the ball settles on the winner card.
 */
function animatePvpBallToTarget(target, callback) {
    const ball = document.getElementById('pvp-ball');
    if (!ball) { if (callback) callback(); return; }

    ball.style.opacity = '1';

    // Phase 1: fast arc to a midpoint near the target
    const midX = (pvpBallPos.x + target.x) / 2 + (Math.random() - 0.5) * 20;
    const midY = (pvpBallPos.y + target.y) / 2 + (Math.random() - 0.5) * 20;

    ball.style.transition = 'left 0.35s ease-in, top 0.35s ease-in, transform 0.35s ease';
    ball.style.transform  = 'translate(-50%,-50%) scale(1.3)';
    ball.style.left       = midX + '%';
    ball.style.top        = midY + '%';

    setTimeout(() => {
        // Phase 2: slow precise landing
        ball.style.transition = 'left 0.55s cubic-bezier(0.22,1,0.36,1), top 0.55s cubic-bezier(0.22,1,0.36,1), transform 0.4s ease';
        ball.style.transform  = 'translate(-50%,-50%) scale(1.6)';
        ball.style.left       = target.x + '%';
        ball.style.top        = target.y + '%';
        pvpBallPos = { x: target.x, y: target.y };

        setTimeout(() => {
            ball.style.transition = 'transform 0.25s ease';
            ball.style.transform  = 'translate(-50%,-50%) scale(1)';
            if (callback) callback();
        }, 620);
    }, 380);
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
