// =============================================================
// games-pvp.js — SPACE DONUT PVP (Обновленная Радиальная Арена)
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
let pvpTrajectory        = [];   // Precomputed fixed-step trajectory (frame-rate independent)
let pvpWinnerTarget      = null; // Winner sector coords
const PVP_ROLLING_DURATION = 6500; // ms
const PVP_TRAJ_STEP_MS     = 16;   // Fixed step for trajectory precomputation (≈60 fps)

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
        pvpBallTrail    = [];
        pvpTrajectory   = [];
        pvpWinnerTarget = null;
    }

    // Transition: enter rolling
    if (prevState !== 'rolling' && data.state === 'rolling') {
        const serverNow      = Date.now() / 1000;
        const elapsedSeconds = data.rolling_start_ts > 0
            ? Math.max(0, serverNow - data.rolling_start_ts)
            : 0;
        
        pvpRollingStart = performance.now() - elapsedSeconds * 1000;
        
        // Заранее находим целевую точку, куда должен приехать шарик
        let target = null;
        if (data.winner) {
            target = getPvpWinnerSectorTarget(data.winner.user_id);
        }
        
        pvpInitBallFromSeed(data.ball_seed || 1, target);
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

    // Finished: fallback reveal if animation already ended or state arrived before animation
    if (data.state === 'finished' && !pvpWinnerRevealed && data.winner) {
        pvpWinnerRevealed = true;
        stopPvpBallAnimation();
        if (pvpWinnerTarget) {
            showPvpWinnerReveal(data.winner);
        } else {
            const target = getPvpWinnerSectorTarget(data.winner.user_id);
            animatePvpBallToTarget(target, () => showPvpWinnerReveal(data.winner));
        }
    }

    pvpLastState = data.state;
    renderPvpArena(); 
    renderPvpBetPanel();
    renderPvpParticipants();
    renderPvpTopBar();
    updatePvpStatus();

    const badge = document.getElementById('pvp-round-badge');
    if (badge) badge.textContent = `Round #${data.round_id}`;

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

// ─── Ball / Diamond animation ─────────────────────────────────

function startPvpBallAnimation() {
    stopPvpBallAnimation();
    animatePvpBall();
}

function stopPvpBallAnimation() {
    if (pvpBallAnimFrame) {
        cancelAnimationFrame(pvpBallAnimFrame);
        pvpBallAnimFrame = null;
    }
    const arenaInner = document.getElementById('pvp-arena-inner');
    if (arenaInner) {
        arenaInner.style.transition = 'transform 0.4s ease-in-out';
        arenaInner.style.transform  = '';
    }
}

let _pvpRng = () => Math.random();

function pvpInitBallFromSeed(seed, winnerTarget) {
    // Mulberry32 PRNG — identical seed → identical sequence on every client
    let s = seed >>> 0;
    _pvpRng = () => {
        s += 0x6D2B79F5;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    let px = 50, py = 50;
    // Значительно увеличиваем скорость, чтобы шарик активно рикошетил
    let vx = (_pvpRng() > 0.5 ? 1 : -1) * (3.0 + _pvpRng() * 2.5);
    let vy = (_pvpRng() > 0.5 ? 1 : -1) * (3.0 + _pvpRng() * 2.5);

    pvpBallPos  = { x: px, y: py };
    pvpBallVel  = { x: vx, y: vy };
    pvpWinnerTarget = winnerTarget || null;

    pvpTrajectory = [];
    const totalSteps = Math.ceil(PVP_ROLLING_DURATION / PVP_TRAJ_STEP_MS) + 4;
    
    // Начинаем плавно "притягивать" шарик к цели после 40% времени анимации
    const BLEND_START_STEP = Math.floor(totalSteps * 0.40); 

    for (let i = 0; i < totalSteps; i++) {
        // 1. Физический шаг
        px += vx;
        py += vy;

        // 2. Круговая коллизия (отскок от краев рулетки)
        // Центр (50,50), радиус арены примерно 45% (чтобы шарик не вылезал за границы визуального кольца)
        let dx = px - 50;
        let dy = py - 50;
        let dist = Math.sqrt(dx * dx + dy * dy);
        
        if (dist > 45) {
            // Нормаль вектора отскока
            let nx = dx / dist;
            let ny = dy / dist;
            
            // Отражение скорости по формуле: V = V - 2*(V.N)*N
            let dot = vx * nx + vy * ny;
            vx = vx - 2 * dot * nx;
            vy = vy - 2 * dot * ny;
            
            // Выталкиваем обратно внутрь круга
            px = 50 + nx * 45;
            py = 50 + ny * 45;
            
            // Добавляем немного хаоса при отскоке
            vx += (_pvpRng() - 0.5);
            vy += (_pvpRng() - 0.5);
        }

        // 3. Имитация трения: шарик постепенно теряет скорость
        vx *= 0.992;
        vy *= 0.992;

        let finalX = px;
        let finalY = py;

        // 4. Плавное доведение до сектора победителя
        if (pvpWinnerTarget && i > BLEND_START_STEP) {
            let blendProgress = (i - BLEND_START_STEP) / (totalSteps - BLEND_START_STEP);
            
            // Quartic ease-out: Начинает плавно и оооочень медленно останавливается в самом конце
            let ease = 1 - Math.pow(1 - Math.min(blendProgress, 1), 4);

            finalX = px * (1 - ease) + pvpWinnerTarget.x * ease;
            finalY = py * (1 - ease) + pvpWinnerTarget.y * ease;

            // Гасим "физическую" скорость сильнее, чтобы базовые скачки не мешали плавной остановке
            vx *= 0.85;
            vy *= 0.85;
        }

        pvpTrajectory.push({ x: finalX, y: finalY });
    }
}

function animatePvpBall() {
    const elapsed  = performance.now() - pvpRollingStart;
    const progress = Math.min(elapsed / PVP_ROLLING_DURATION, 1);

    // Просто берем готовую предрассчитанную позицию. 
    // Это гарантирует одинаковую анимацию у всех при любой частоте кадров.
    const stepIdx = Math.min(Math.floor(elapsed / PVP_TRAJ_STEP_MS), pvpTrajectory.length - 1);
    const pos = pvpTrajectory[stepIdx] || { x: 50, y: 50 };

    pvpBallPos.x = pos.x;
    pvpBallPos.y = pos.y;

    const ball = document.getElementById('pvp-ball');
    if (ball) {
        ball.style.left    = pvpBallPos.x + '%';
        ball.style.top     = pvpBallPos.y + '%';
        ball.style.opacity = '1';
    }

    // Легкий зум в конце на выигрышный сектор
    const arenaInner = document.getElementById('pvp-arena-inner');
    if (arenaInner) {
        if (progress > 0.70) {
            const zoomT = (progress - 0.70) / 0.30;
            const smoothZoom = 1 - Math.pow(1 - zoomT, 3); // ease-out
            const scale = 1 + smoothZoom * 0.35;
            
            arenaInner.style.transform       = `scale(${scale.toFixed(3)})`;
            arenaInner.style.transformOrigin = `${pvpBallPos.x}% ${pvpBallPos.y}%`;
            arenaInner.style.transition      = 'none'; // Управляем через requestAnimationFrame
        } else {
            arenaInner.style.transform  = '';
            arenaInner.style.transition = '';
        }
    }

    renderPvpTrail();

    if (progress < 1) {
        pvpBallAnimFrame = requestAnimationFrame(animatePvpBall);
    } else {
        pvpBallAnimFrame = null;
        const arenaInner = document.getElementById('pvp-arena-inner');
        if (arenaInner) {
            arenaInner.style.transition = 'transform 0.5s ease-in-out';
            arenaInner.style.transform  = '';
        }
        if (pvpState.winner && !pvpWinnerRevealed) {
            pvpWinnerRevealed = true;
            showPvpWinnerReveal(pvpState.winner);
        }
    }
}

function renderPvpTrail() {
    const container = document.getElementById('pvp-ball-trail');
    if (!container) return;
    container.innerHTML = '';
    pvpBallTrail.push({x: pvpBallPos.x, y: pvpBallPos.y});
    if (pvpBallTrail.length > 15) pvpBallTrail.shift();
    
    pvpBallTrail.forEach((pt, i) => {
        const alpha = (i / pvpBallTrail.length) * 0.4;
        const size  = 4 + (i / pvpBallTrail.length) * 6;
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

// ─── Arena render — РАДИАЛЬНАЯ АРЕНА КАК НА ФОТО ──────────────

function renderPvpArena() {
    const container = document.getElementById('pvp-arena-players');
    const bg = document.getElementById('pvp-dynamic-bg');
    if (!container || !bg) return;
    container.innerHTML = '';

    const players = pvpState.players || [];
    
    if (players.length === 0) {
        bg.style.background = 'radial-gradient(ellipse at center, rgba(244,63,94,0.08) 0%, #020617 70%)';
        return;
    }

    let gradientParts = [];
    let currentPercent = 0;
    let totalChance = players.reduce((sum, p) => sum + p.win_chance, 0);

    players.forEach((p) => {
        let normalizedChance = totalChance > 0 ? (p.win_chance / totalChance) * 100 : (100 / players.length);
        
        let start = currentPercent;
        let end = currentPercent + normalizedChance;
        
        gradientParts.push(`${p.color} ${start}% ${end}%`);

        let midPercent = start + (normalizedChance / 2);
        let angleDeg = (midPercent * 3.6) - 90; 
        let angleRad = angleDeg * (Math.PI / 180);

        let radius = 33; 
        let x = 50 + radius * Math.cos(angleRad);
        let y = 50 + radius * Math.sin(angleRad);

        const isWinner = pvpState.state === 'finished' && pvpState.winner?.user_id === p.user_id;

        const avatarWrap = document.createElement('div');
        avatarWrap.id = `pvp-player-avatar-${p.user_id}`;
        avatarWrap.className = `absolute z-10 rounded-full flex flex-col items-center justify-center border-[3px] shadow-2xl transition-all duration-300 ${isWinner ? 'z-20 pvp-winner-pulse' : ''}`;
        avatarWrap.style.cssText = `
            left: ${x}%; top: ${y}%;
            transform: translate(-50%, -50%) ${isWinner ? 'scale(1.2)' : 'scale(1)'};
            width: 50px; height: 50px;
            border-color: rgba(255,255,255,0.9);
            background: ${p.color};
        `;

        if (p.avatar) {
            avatarWrap.innerHTML = `<img src="${p.avatar}" class="w-full h-full object-cover rounded-full" onerror="this.innerHTML='<div class=\\'w-full h-full flex items-center justify-center font-black text-white\\'>${(p.name||'?')[0]}</div>'">`;
        } else {
            avatarWrap.innerHTML = `<div class="w-full h-full flex items-center justify-center font-black text-white">${(p.name||'?')[0]}</div>`;
        }

        const infoLabel = document.createElement('div');
        infoLabel.className = "absolute -bottom-6 left-1/2 -translate-x-1/2 bg-black/70 px-2 py-0.5 rounded-lg text-[9px] font-black text-white whitespace-nowrap backdrop-blur-md border border-white/20 flex flex-col items-center leading-tight shadow-lg";
        infoLabel.innerHTML = `<span>${p.win_chance.toFixed(1)}%</span>`;
        avatarWrap.appendChild(infoLabel);

        container.appendChild(avatarWrap);
        
        currentPercent = end;
    });

    bg.style.background = `conic-gradient(${gradientParts.join(', ')})`;
}

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
        else if (s === 'countdown') statusEl.textContent = '🔥 Прием ставок...';
        else if (s === 'rolling')   statusEl.textContent = '💎 Выбираем победителя...';
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

// ─── Center target logic ───────────────────────────────────────────

function getPvpWinnerSectorTarget(winnerId) {
    const players    = pvpState.players || [];
    const totalChance = players.reduce((sum, p) => sum + p.win_chance, 0);
    let currentPercent = 0;

    for (const p of players) {
        const normalizedChance = totalChance > 0
            ? (p.win_chance / totalChance) * 100
            : (100 / players.length);

        if (String(p.user_id) === String(winnerId)) {
            const midPercent = currentPercent + normalizedChance / 2;
            const angleDeg   = (midPercent * 3.6) - 90;
            const angleRad   = angleDeg * (Math.PI / 180);
            
            // Радиус 18 - это ровно середина фонового цвета, не доезжая до аватарки (она на 33)
            const radius     = 18; 
            const x = 50 + radius * Math.cos(angleRad);
            const y = 50 + radius * Math.sin(angleRad);
            return { x, y };
        }
        currentPercent += normalizedChance;
    }
    return { x: 50, y: 50 };
}

// Fallback, если вдруг стейт пришел сразу готовый, а анимация не крутилась
function animatePvpBallToTarget(target, callback) {
    const ball = document.getElementById('pvp-ball');
    if (!ball) { if (callback) callback(); return; }

    ball.style.opacity = '1';

    // Делаем плавный ease-out к нужной точке (имитация завершения анимации)
    ball.style.transition = 'left 1.2s cubic-bezier(0.1, 1, 0.2, 1), top 1.2s cubic-bezier(0.1, 1, 0.2, 1), transform 1s ease';
    ball.style.left       = target.x + '%';
    ball.style.top        = target.y + '%';
    pvpBallPos = { x: target.x, y: target.y };

    setTimeout(() => {
        if (callback) callback();
    }, 1250);
}

// ─── Winner reveal ────────────────────────────────────────────

function showPvpWinnerReveal(winner) {
    const overlay = document.getElementById('pvp-winner-overlay');
    if (!overlay) return;

    const pot = pvpState.pot;
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
            <div class="text-sm text-white/60">забирает весь банк!</div>
            <div class="flex gap-2 flex-wrap justify-center mt-1">
                ${potStr.map(s => `<span class="px-3 py-1 rounded-full text-sm font-black border border-white/20 bg-white/10 text-white">${s}</span>`).join('')}
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
