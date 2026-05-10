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

let pvpPollTimer          = null;
let pvpBallAnimFrame      = null;
let pvpBetTab             = 'stars';   // 'stars' | 'donuts' | 'gift'
let pvpInventory          = [];
let pvpBallPos            = { x: 50, y: 50 };
let pvpBallTrail          = [];
let pvpLastState          = '';
let pvpCountdownInterval  = null;
let pvpWinnerRevealed     = false;
let pvpRollingStart       = 0;
let pvpTrajectorySegments = [];   // Precomputed path segments for bouncy ricochets
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
    if (pvpPollTimer)         { clearTimeout(pvpPollTimer);          pvpPollTimer     = null; }
    if (pvpBallAnimFrame)     { cancelAnimationFrame(pvpBallAnimFrame); pvpBallAnimFrame = null; }
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
        pvpBallTrail      = [];
        pvpTrajectorySegments = [];
    }

    // Transition: enter rolling
    if (prevState !== 'rolling' && data.state === 'rolling') {
        const serverNow      = Date.now() / 1000;
        const elapsedSeconds = data.rolling_start_ts > 0
            ? Math.max(0, serverNow - data.rolling_start_ts)
            : 0;
        // Offset pvpRollingStart so trajectory index is already correct for late-joiners
        pvpRollingStart = performance.now() - elapsedSeconds * 1000;
        
        // Pass the winner ID immediately to calculate natural stopping point
        const wId = data.winner ? data.winner.user_id : null;
        pvpInitBallFromSeed(data.ball_seed || 1, wId);
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
        showPvpWinnerReveal(data.winner);
    }

    pvpLastState = data.state;
    renderPvpArena(); // Перерисовываем круговую арену
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
    // Always reset inner zoom when animation stops
    const arenaInner = document.getElementById('pvp-arena-inner');
    if (arenaInner) {
        arenaInner.style.transition = 'transform 0.6s cubic-bezier(0.22, 1, 0.36, 1)';
        arenaInner.style.transform  = '';
    }
    pvpBallTrail = [];
    renderPvpTrail();
}

let _pvpRng = () => Math.random();

function getPvpWinnerSectorTarget(winnerId) {
    const players = pvpState.players || [];
    const totalChance = players.reduce((sum, p) => sum + p.win_chance, 0);
    let currentPercent = 0;

    for (const p of players) {
        const normalizedChance = totalChance > 0
            ? (p.win_chance / totalChance) * 100
            : (100 / players.length);

        if (String(p.user_id) === String(winnerId)) {
            // Вычисляем случайную точку внутри сектора (избегая самых краев)
            const padding = Math.max(2, normalizedChance * 0.1); // отступ от границ цвета
            const safeChance = Math.max(1, normalizedChance - padding * 2);
            const randomPercent = currentPercent + padding + (_pvpRng() * safeChance);

            const angleDeg = (randomPercent * 3.6) - 90;
            const angleRad = angleDeg * (Math.PI / 180);

            // Радиус от центра: от 12% до 28% (не доходя до аватарки, просто на фоне сектора)
            const r = 12 + _pvpRng() * 16;

            const x = 50 + r * Math.cos(angleRad);
            const y = 50 + r * Math.sin(angleRad);
            return { x, y };
        }
        currentPercent += normalizedChance;
    }
    return { x: 50, y: 50 };
}

function pvpInitBallFromSeed(seed, winnerId) {
    // Mulberry32 PRNG — identical seed → identical sequence on every client
    let s = seed >>> 0;
    _pvpRng = () => {
        s += 0x6D2B79F5;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    let targetP = { x: 50, y: 50 };
    if (winnerId) {
        targetP = getPvpWinnerSectorTarget(winnerId);
    }

    // Генерируем точки рикошетов по стенам арены (от 7 до 10 отскоков)
    let wpts = [{ x: 50, y: 50 }];
    let lastWall = -1;
    let numBounces = 7 + Math.floor(_pvpRng() * 4); 

    for(let i = 0; i < numBounces; i++) {
        let wallIdx;
        do {
            wallIdx = Math.floor(_pvpRng() * 4); // 0:top, 1:right, 2:bottom, 3:left
        } while (wallIdx === lastWall);
        lastWall = wallIdx;

        let px, py;
        if (wallIdx === 0) { px = 10 + _pvpRng()*80; py = 10; } 
        else if (wallIdx === 1) { px = 90; py = 10 + _pvpRng()*80; } 
        else if (wallIdx === 2) { px = 10 + _pvpRng()*80; py = 90; } 
        else { px = 10; py = 10 + _pvpRng()*80; } 

        wpts.push({x: px, y: py});
    }
    
    // Финальная точка - вычисленная позиция цвета победителя
    wpts.push(targetP);

    // Вычисляем расстояния отрезков пути
    let totalDist = 0;
    pvpTrajectorySegments = [];
    for(let i = 0; i < wpts.length - 1; i++) {
        let p1 = wpts[i];
        let p2 = wpts[i+1];
        let dx = p2.x - p1.x;
        let dy = p2.y - p1.y;
        let dist = Math.sqrt(dx*dx + dy*dy);
        pvpTrajectorySegments.push({ p1, p2, dist, accDist: totalDist });
        totalDist += dist;
    }

    // Проставляем процентные отметки по расстоянию
    for(let seg of pvpTrajectorySegments) {
        seg.startT = seg.accDist / totalDist;
        seg.endT = (seg.accDist + seg.dist) / totalDist;
    }

    pvpBallPos = { x: 50, y: 50 };
}

function animatePvpBall() {
    const elapsed  = performance.now() - pvpRollingStart;
    const timeProgress = Math.min(elapsed / PVP_ROLLING_DURATION, 1);

    // Плавное кубическое замедление (Cubic Ease-Out). 
    // В начале скорость максимальна (рикошеты), в конце плавно спадает до нуля на финальной точке.
    const distProgress = 1 - Math.pow(1 - timeProgress, 3);

    // Находим текущий отрезок пути
    let currentPos = pvpTrajectorySegments[pvpTrajectorySegments.length - 1].p2;
    for(let seg of pvpTrajectorySegments) {
        if (distProgress >= seg.startT && distProgress <= seg.endT) {
            let range = seg.endT - seg.startT;
            let segProg = range > 0 ? (distProgress - seg.startT) / range : 1;
            currentPos = {
                x: seg.p1.x + (seg.p2.x - seg.p1.x) * segProg,
                y: seg.p1.y + (seg.p2.y - seg.p1.y) * segProg
            };
            break;
        }
    }

    pvpBallPos = currentPos;
    const ball = document.getElementById('pvp-ball');

    if (ball) {
        ball.style.left    = pvpBallPos.x + '%';
        ball.style.top     = pvpBallPos.y + '%';
        ball.style.opacity = '1';
    }

    // Зум арены, показывающий где останавливается шарик (последние 35% времени)
    const arenaInner = document.getElementById('pvp-arena-inner');
    if (arenaInner) {
        if (timeProgress > 0.65) {
            let zoomProgress = Math.max(0, (timeProgress - 0.65) / 0.35);
            // Smooth step для зума
            zoomProgress = zoomProgress * zoomProgress * (3 - 2 * zoomProgress);
            const scale = 1 + zoomProgress * 0.9; // Scale до 1.9x
            arenaInner.style.transform       = `scale(${scale.toFixed(3)})`;
            arenaInner.style.transformOrigin = `${pvpBallPos.x}% ${pvpBallPos.y}%`;
            arenaInner.style.transition      = 'none'; // обновляем кадр за кадром без задержек
        } else {
            arenaInner.style.transform  = '';
            arenaInner.style.transition = '';
        }
    }

    // Хвост за шариком
    if (Math.random() > 0.3) {
        pvpBallTrail.push({x: pvpBallPos.x, y: pvpBallPos.y});
        if (pvpBallTrail.length > 15) pvpBallTrail.shift();
    }
    renderPvpTrail();

    if (timeProgress < 1) {
        pvpBallAnimFrame = requestAnimationFrame(animatePvpBall);
    } else {
        pvpBallAnimFrame = null;
        stopPvpBallAnimation();
        
        // Шарик остановился в секторе победителя — вызываем показ карточки
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

    // Собираем данные для градиента (Сектора зависят от win_chance)
    let gradientParts = [];
    let currentPercent = 0;
    
    // Суммируем шансы на всякий случай (должно быть ~100)
    let totalChance = players.reduce((sum, p) => sum + p.win_chance, 0);

    players.forEach((p) => {
        let normalizedChance = totalChance > 0 ? (p.win_chance / totalChance) * 100 : (100 / players.length);
        
        let start = currentPercent;
        let end = currentPercent + normalizedChance;
        
        // Добавляем жесткий переход цвета для стиля "кусочков пирога"
        gradientParts.push(`${p.color} ${start}% ${end}%`);

        // Вычисляем угол, где должна стоять аватарка (середина сектора)
        let midPercent = start + (normalizedChance / 2);
        // В CSS conic-gradient 0% начинается сверху (12 часов), что математически = -90 градусов
        let angleDeg = (midPercent * 3.6) - 90; 
        let angleRad = angleDeg * (Math.PI / 180);

        // Радиус отдаления аватарок от центра (33% от контейнера)
        let radius = 33; 
        let x = 50 + radius * Math.cos(angleRad);
        let y = 50 + radius * Math.sin(angleRad);

        const isWinner = pvpState.state === 'finished' && pvpState.winner?.user_id === p.user_id;

        // Создаем контейнер аватарки
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

        // Плашка с именем и процентами под аватаркой
        const infoLabel = document.createElement('div');
        infoLabel.className = "absolute -bottom-6 left-1/2 -translate-x-1/2 bg-black/70 px-2 py-0.5 rounded-lg text-[9px] font-black text-white whitespace-nowrap backdrop-blur-md border border-white/20 flex flex-col items-center leading-tight shadow-lg";
        infoLabel.innerHTML = `
            <span>${p.win_chance.toFixed(1)}%</span>
        `;
        avatarWrap.appendChild(infoLabel);

        container.appendChild(avatarWrap);
        
        currentPercent = end;
    });

    // Применяем фон
    bg.style.background = `conic-gradient(${gradientParts.join(', ')})`;
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
    const ball      = document.getElementById('pvp-ball');

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

    if (ball) {
        // Гарантируем, что шарик исчезает по завершению игры
        ball.style.opacity = pvpState.state === 'rolling' && !pvpWinnerRevealed ? '1' : '0';
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

// ─── Winner reveal ────────────────────────────────────────────

function showPvpWinnerReveal(winner) {
    const overlay = document.getElementById('pvp-winner-overlay');
    const ball    = document.getElementById('pvp-ball');
    if (!overlay) return;

    // Скрываем шарик как только появляется плашка победителя
    if (ball) ball.style.opacity = '0';

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
