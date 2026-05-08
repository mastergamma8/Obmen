// =====================================================
// games-mines.js — Игра «Мины» (5×5)
// =====================================================

// ─── СОСТОЯНИЕ ───────────────────────────────────────
const MinesGame = {
    active:       false,
    isProcessing: false, // Флаг для блокировки спам-кликов
    bet:          100,
    mines:        3,
    revealed:     [],
    multiplier:   1.00,
    winAmount:    0,
    nextMult:     null,
    status:       'idle',   // idle | active | won | lost
    // Demo state
    _demoMinePos: [],
};

const MINES_MIN_BET  = 50;
const MINES_MAX_BET  = 5000;
const MINES_VALID    = [1, 3, 5, 10];
const MINES_GRID     = 25;
const MINES_HOUSE    = 0.10;

// ─── МУЛЬТИПЛИКАТОР (дублируется на клиенте для демо) ─
function _minesCalcMult(mines, revealed) {
    if (revealed === 0) return 1.00;
    const safe = MINES_GRID - mines;
    if (revealed > safe) return 1.00;
    let num = 1, den = 1;
    for (let i = 0; i < revealed; i++) {
        num *= (MINES_GRID - i);
        den *= (safe - i);
    }
    return Math.round(num / den * (1 - MINES_HOUSE) * 10000) / 10000;
}
function _minesNextMult(mines, revealed) {
    return _minesCalcMult(mines, revealed + 1);
}

// ─── ДЕМО-РЕЖИМ ──────────────────────────────────────
function _minesIsDemo() {
    return typeof isDemoMode !== 'undefined' && isDemoMode;
}

function _minesDemoStart(bet, mines) {
    const positions = [];
    const all = Array.from({length: MINES_GRID}, (_, i) => i);
    for (let i = all.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [all[i], all[j]] = [all[j], all[i]];
    }
    MinesGame._demoMinePos = all.slice(0, mines);

    MinesGame.active     = true;
    MinesGame.bet        = bet;
    MinesGame.mines      = mines;
    MinesGame.revealed   = [];
    MinesGame.multiplier = 1.00;
    MinesGame.winAmount  = bet;
    MinesGame.nextMult   = _minesNextMult(mines, 0);
    MinesGame.status     = 'active';
    MinesGame.isProcessing = false;

    if (typeof vibrate === 'function') vibrate('medium');
    _minesRenderField([], []);
    _minesUpdatePanel();
    _minesSetGameActive(true);
}

function _minesDemoReveal(cellIdx) {
    if (MinesGame.status !== 'active') return;
    if (MinesGame.revealed.includes(cellIdx)) return;
    if (MinesGame.isProcessing) return;

    MinesGame.isProcessing = true;
    const cellEl = document.querySelector(`.mines-cell[data-cell="${cellIdx}"]`);
    if (cellEl) cellEl.classList.add('mines-cell--loading');

    setTimeout(() => {
        MinesGame.isProcessing = false;
        if (cellEl) cellEl.classList.remove('mines-cell--loading');

        const isMine = MinesGame._demoMinePos.includes(cellIdx);

        if (isMine) {
            MinesGame.status = 'lost';
            if (typeof vibrate === 'function') vibrate('heavy');
            _minesRevealAll(cellIdx, MinesGame._demoMinePos, MinesGame.revealed);
            _minesUpdatePanel();
            _minesSetGameActive(false, 'lost');
            setTimeout(() => _minesShowToast(t('mines_status_lost'), 'error'), 300);
            return;
        }

        MinesGame.revealed.push(cellIdx);
        const safe_left = (MINES_GRID - MinesGame.mines) - MinesGame.revealed.length;
        MinesGame.multiplier = _minesCalcMult(MinesGame.mines, MinesGame.revealed.length);
        MinesGame.winAmount  = Math.floor(MinesGame.bet * MinesGame.multiplier);
        MinesGame.nextMult   = safe_left > 0 ? _minesNextMult(MinesGame.mines, MinesGame.revealed.length) : null;
        MinesGame.status     = safe_left === 0 ? 'won' : 'active';

        if (typeof vibrate === 'function') vibrate('light');
        _minesCellSafe(cellIdx);
        _minesUpdatePanel();

        if (MinesGame.status === 'won') {
            _minesSetGameActive(false, 'won');
            _minesShowToast(`🎉 DEMO +${MinesGame.winAmount} ⭐`, 'success');
        }
    }, 150); // Имитация задержки сети для 3D эффекта
}

function _minesDemoCashout() {
    if (MinesGame.status !== 'active' || MinesGame.revealed.length === 0) {
        _minesShowToast(t('mines_reveal_first'), 'warn');
        return;
    }
    MinesGame.status = 'won';
    _minesSetGameActive(false, 'won');
    _minesShowToast(`🎉 DEMO +${MinesGame.winAmount} ⭐`, 'success');
    _minesUpdatePanel();
}

// ─── ОТКРЫТЬ ЭКРАН ────────────────────────────────────
function openMinesGame() {
    if (typeof vibrate === 'function') vibrate('light');
    const mainView  = document.getElementById('games-main-view');
    const minesView = document.getElementById('games-mines-view');
    if (mainView)  mainView.classList.add('hidden');
    if (minesView) minesView.classList.remove('hidden');
    if (typeof syncDemoToggles === 'function') syncDemoToggles();
    _minesUpdateDemoRibbon();
    _minesCheckState();
}

function closeMinesGame() {
    if (MinesGame.status === 'active' && MinesGame.revealed.length > 0 && !_minesIsDemo()) {
        _minesShowToast(t('mines_reveal_first'), 'warn');
        return;
    }
    if (typeof vibrate === 'function') vibrate('light');
    const mainView  = document.getElementById('games-main-view');
    const minesView = document.getElementById('games-mines-view');
    if (minesView) minesView.classList.add('hidden');
    if (mainView)  mainView.classList.remove('hidden');
}

// ─── ДЕМО-ЛЕНТА ──────────────────────────────────────
function _minesUpdateDemoRibbon() {
    const ribbon = document.getElementById('mines-demo-ribbon');
    if (ribbon) ribbon.classList.toggle('hidden', !_minesIsDemo());
}

// ─── ПРОВЕРКА АКТИВНОЙ ИГРЫ НА СЕРВЕРЕ ───────────────
async function _minesCheckState() {
    _minesUpdateDemoRibbon();
    if (_minesIsDemo()) {
        _minesSetGameIdle();
        return;
    }
    MinesGame.isProcessing = true;
    try {
        const res = await fetch('/api/mines/state', { headers: getApiHeaders() });
        const data = await res.json();
        if (data.active) {
            MinesGame.active     = true;
            MinesGame.bet        = data.bet;
            MinesGame.mines      = data.mines;
            MinesGame.revealed   = data.revealed || [];
            MinesGame.multiplier = data.multiplier;
            MinesGame.winAmount  = data.win_amount;
            MinesGame.nextMult   = data.next_mult;
            MinesGame.status     = data.status;
            _minesRenderField([], []);
            _minesUpdatePanel();
            _minesSetGameActive(true);
        } else {
            _minesSetGameIdle();
        }
    } catch (e) {
        _minesSetGameIdle();
    } finally {
        MinesGame.isProcessing = false;
    }
}

// ─── УСТАНОВКА СТАВКИ ─────────────────────────────────
function minesSetBet(action) {
    const inp = document.getElementById('mines-bet-input');
    if (!inp) return;
    let val = parseInt(inp.value) || MINES_MIN_BET;
    if (action === 'min')      val = MINES_MIN_BET;
    else if (action === 'max') val = MINES_MAX_BET;
    else if (action === 'x2')  val = Math.min(val * 2, MINES_MAX_BET);
    inp.value = val;
    MinesGame.bet = val;
}

function minesSelectMines(count) {
    if (!MINES_VALID.includes(count)) return;
    MinesGame.mines = count;
    document.querySelectorAll('.mines-count-btn').forEach(btn => {
        const active = parseInt(btn.dataset.mines) === count;
        btn.classList.toggle('mines-count-btn--active', active);
        btn.classList.toggle('bg-white/10', active);
        btn.classList.toggle('text-white', active);
        btn.classList.toggle('text-white/60', !active);
    });
}

// ─── СТАРТ ИГРЫ ───────────────────────────────────────
async function minesStart() {
    if (MinesGame.isProcessing) return;
    const inp = document.getElementById('mines-bet-input');
    const bet = parseInt(inp?.value) || 0;

    if (bet < MINES_MIN_BET || bet > MINES_MAX_BET) {
        _minesShowToast(
            t('mines_err_limits').replace('{min}', MINES_MIN_BET).replace('{max}', MINES_MAX_BET),
            'error'
        );
        return;
    }

    if (_minesIsDemo()) {
        _minesDemoStart(bet, MinesGame.mines);
        return;
    }

    MinesGame.isProcessing = true;
    _minesSetLoading(true);
    try {
        const res = await fetch('/api/mines/start', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ bet, mines: MinesGame.mines }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            _minesShowToast(data.detail || t('mines_err_not_enough'), 'error');
            return;
        }
        MinesGame.active     = true;
        MinesGame.bet        = data.bet;
        MinesGame.mines      = data.mines;
        MinesGame.revealed   = [];
        MinesGame.multiplier = 1.00;
        MinesGame.winAmount  = data.win_amount;
        MinesGame.nextMult   = data.next_mult;
        MinesGame.status     = 'active';

        if (typeof vibrate === 'function') vibrate('medium');
        _minesRenderField([], []);
        _minesUpdatePanel();
        _minesSetGameActive(true);

        if (typeof loadUserData === 'function') loadUserData();
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        _minesSetLoading(false);
        MinesGame.isProcessing = false;
    }
}

// ─── ОТКРЫТИЕ ЯЧЕЙКИ ──────────────────────────────────
async function minesReveal(cellIdx) {
    if (MinesGame.status !== 'active') return;
    if (MinesGame.revealed.includes(cellIdx)) return;
    
    // Блокируем новые клики, пока не придет ответ по текущему
    if (MinesGame.isProcessing) return;

    if (_minesIsDemo()) {
        _minesDemoReveal(cellIdx);
        return;
    }

    MinesGame.isProcessing = true;
    const cellEl = document.querySelector(`.mines-cell[data-cell="${cellIdx}"]`);
    if (cellEl) cellEl.classList.add('mines-cell--loading');

    try {
        const res = await fetch('/api/mines/reveal', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ cell: cellIdx }),
        });
        const data = await res.json();
        
        if (!res.ok) {
            _minesShowToast(data.detail || t('err_conn'), 'error');
            return;
        }

        if (data.hit_mine) {
            MinesGame.status   = 'lost';
            MinesGame.revealed = data.revealed || [];
            if (typeof vibrate === 'function') vibrate('heavy');
            _minesRevealAll(cellIdx, data.mine_pos || [], data.revealed || []);
            _minesUpdatePanel();
            _minesSetGameActive(false, 'lost');
            setTimeout(() => _minesShowToast(t('mines_status_lost'), 'error'), 400);
        } else {
            MinesGame.revealed   = data.revealed || [];
            MinesGame.multiplier = data.multiplier;
            MinesGame.winAmount  = data.win_amount;
            MinesGame.nextMult   = data.next_mult;
            MinesGame.status     = data.status;

            if (typeof vibrate === 'function') vibrate('light');
            _minesCellSafe(cellIdx);
            _minesUpdatePanel();

            if (data.status === 'won') {
                _minesSetGameActive(false, 'won');
                _minesShowToast(`🎉 +${data.win_amount} ⭐`, 'success');
                if (typeof loadUserData === 'function') loadUserData();
            }
        }
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        if (cellEl) cellEl.classList.remove('mines-cell--loading');
        MinesGame.isProcessing = false;
    }
}

// ─── ВЫВОД ВЫИГРЫША ───────────────────────────────────
async function minesCashout() {
    if (MinesGame.status !== 'active' || MinesGame.revealed.length === 0) {
        _minesShowToast(t('mines_reveal_first'), 'warn');
        return;
    }
    if (MinesGame.isProcessing) return;

    if (_minesIsDemo()) {
        _minesDemoCashout();
        return;
    }

    MinesGame.isProcessing = true;
    _minesSetLoading(true);
    try {
        const res = await fetch('/api/mines/cashout', {
            method: 'POST',
            headers: getApiHeaders(),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            _minesShowToast(data.detail || t('err_conn'), 'error');
            return;
        }
        MinesGame.multiplier = data.multiplier;
        MinesGame.winAmount  = data.win_amount;
        MinesGame.status     = 'won';
        _minesUpdatePanel();
        _minesSetGameActive(false, 'won');
        _minesShowToast(`🎉 +${data.win_amount} ⭐`, 'success');
        if (typeof loadUserData === 'function') loadUserData();
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        _minesSetLoading(false);
        MinesGame.isProcessing = false;
    }
}

// ─── ОТМЕНА ИГРЫ (ДО ПЕРВОГО ХОДА) ───────────────────
async function minesCancel() {
    if (MinesGame.status !== 'active' || MinesGame.revealed.length > 0) return;
    if (MinesGame.isProcessing) return;

    if (_minesIsDemo()) {
        MinesGame.status = 'idle';
        MinesGame.active = false;
        _minesSetGameIdle();
        return;
    }

    MinesGame.isProcessing = true;
    _minesSetLoading(true);
    try {
        const res = await fetch('/api/mines/cancel', {
            method: 'POST',
            headers: getApiHeaders(),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            _minesShowToast(data.detail || t('err_conn'), 'error');
            return;
        }
        MinesGame.status = 'idle';
        MinesGame.active = false;
        _minesSetGameIdle();
        if (typeof loadUserData === 'function') loadUserData();
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        _minesSetLoading(false);
        MinesGame.isProcessing = false;
    }
}

// ─── НОВАЯ ИГРА ───────────────────────────────────────
function minesNewGame() {
    MinesGame.status       = 'idle';
    MinesGame.active       = false;
    MinesGame.revealed     = [];
    MinesGame._demoMinePos = [];
    _minesSetGameIdle();
}

// ─── РЕНДЕР ПОЛЯ (НОВЫЙ 3D FLIP) ──────────────────────
function _minesRenderField(mineCells, safeCells) {
    const grid = document.getElementById('mines-grid');
    if (!grid) return;
    grid.innerHTML = '';
    for (let i = 0; i < 25; i++) {
        const cell = document.createElement('button');
        cell.className = 'mines-cell';
        cell.dataset.cell = i;
        // HTML структура для 3D переворота
        cell.innerHTML = `
            <div class="mines-cell-flipper">
                <div class="mines-cell-front"></div>
                <div class="mines-cell-back"></div>
            </div>
        `;
        cell.onclick = () => minesReveal(i);
        if (MinesGame.revealed.includes(i)) {
            _applySafeStyle(cell);
        }
        grid.appendChild(cell);
    }
}

function _minesCellSafe(idx) {
    const cell = document.querySelector(`.mines-cell[data-cell="${idx}"]`);
    if (cell) _applySafeStyle(cell);
}

function _applySafeStyle(cell) {
    cell.classList.add('mines-cell--revealed', 'mines-cell--safe');
    const back = cell.querySelector('.mines-cell-back');
    if (back) back.innerHTML = `💎`;
    cell.disabled = true;
}

function _minesRevealAll(explodedIdx, minePos, safeRevealed) {
    for (let i = 0; i < 25; i++) {
        const cell = document.querySelector(`.mines-cell[data-cell="${i}"]`);
        if (!cell) continue;
        
        if (minePos.includes(i)) {
            cell.classList.add('mines-cell--revealed');
            cell.classList.add(i === explodedIdx ? 'mines-cell--exploded' : 'mines-cell--mine');
            const back = cell.querySelector('.mines-cell-back');
            if (back) back.innerHTML = `💣`;
        } else if (safeRevealed.includes(i)) {
            _applySafeStyle(cell);
        }
        cell.disabled = true;
    }
}

// ─── ОБНОВЛЕНИЕ ПАНЕЛИ СТАТИСТИКИ ─────────────────────
function _minesUpdatePanel() {
    const multEl     = document.getElementById('mines-multiplier');
    const winEl      = document.getElementById('mines-win-amount');
    const nextEl     = document.getElementById('mines-next-mult');
    const statusEl   = document.getElementById('mines-status-text');
    const cashoutVal = document.getElementById('mines-cashout-val');

    if (multEl) multEl.textContent = `${MinesGame.multiplier.toFixed(2)}x`;
    if (winEl)  winEl.innerHTML = `${MinesGame.winAmount} <img src="/gifts/stars.png" class="w-4 h-4 inline-block mb-1">`;
    if (nextEl) nextEl.textContent = MinesGame.nextMult ? `${MinesGame.nextMult.toFixed(2)}x` : '—';
    
    // Обновляем значение внутри кнопки Забрать
    if (cashoutVal) cashoutVal.textContent = MinesGame.winAmount > 0 ? `${MinesGame.winAmount} ⭐` : '';

    if (statusEl) {
        const map = {
            idle:   t('mines_status_idle'),
            active: t('mines_status_active'),
            won:    t('mines_status_won'),
            lost:   t('mines_status_lost'),
        };
        statusEl.textContent = map[MinesGame.status] || '';
        
        // Меняем цвет рамки и текста статуса
        statusEl.className = 'text-[10px] uppercase tracking-wider font-bold px-3 py-1.5 rounded-full border transition-colors ' +
            (MinesGame.status === 'won'    ? 'bg-green-500/20 border-green-500/50 text-green-300 shadow-[0_0_10px_rgba(16,185,129,0.2)]'  :
             MinesGame.status === 'lost'   ? 'bg-red-500/20 border-red-500/50 text-red-300 shadow-[0_0_10px_rgba(239,68,68,0.2)]'      :
             MinesGame.status === 'active' ? 'bg-blue-500/20 border-blue-500/50 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.2)]'    :
             'bg-white/5 border-white/10 text-white/50');
    }
}

// ─── ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ ЭКРАНА ─────────────────────
function _minesSetGameActive(active, endStatus) {
    const setup     = document.getElementById('mines-setup-panel');
    const gameArea  = document.getElementById('mines-game-area');
    const cashBtn   = document.getElementById('mines-btn-cashout');
    const cancelBtn = document.getElementById('mines-btn-cancel');
    const newBtn    = document.getElementById('mines-btn-new');
    const gridEl    = document.getElementById('mines-grid');
    const actionsRow = cashBtn?.parentElement;

    if (active) {
        setup?.classList.add('hidden');
        gameArea?.classList.remove('hidden');
        cashBtn?.classList.remove('hidden');
        cancelBtn?.classList.remove('hidden');
        newBtn?.classList.add('hidden');
        if (actionsRow) actionsRow.classList.remove('hidden');
        if (gridEl) gridEl.classList.remove('pointer-events-none', 'opacity-60');
    } else {
        cashBtn?.classList.add('hidden');
        cancelBtn?.classList.add('hidden');
        newBtn?.classList.remove('hidden');
        if (gridEl) gridEl.classList.add('pointer-events-none');
        if (endStatus === 'won')  _minesShowOverlay('won');
        if (endStatus === 'lost') _minesShowOverlay('lost');
    }
}

function _minesSetGameIdle() {
    const setup    = document.getElementById('mines-setup-panel');
    const gameArea = document.getElementById('mines-game-area');
    const overlay  = document.getElementById('mines-grid-overlay');

    setup?.classList.remove('hidden');
    gameArea?.classList.add('hidden');
    if (overlay) overlay.remove();
    MinesGame.multiplier = 1.00;
    MinesGame.winAmount  = 0;
    MinesGame.nextMult   = null;
    _minesUpdatePanel();
}

function _minesShowOverlay(type) {
    const grid = document.getElementById('mines-grid');
    if (!grid) return;
    const old = document.getElementById('mines-grid-overlay');
    if (old) old.remove();
    
    // Задержка появления оверлея, чтобы игрок успел увидеть взрыв/результат
    setTimeout(() => {
        const ov = document.createElement('div');
        ov.id = 'mines-grid-overlay';
        ov.className = 'absolute inset-0 flex flex-col items-center justify-center rounded-[20px] z-20 transition-opacity duration-500 opacity-0 ' +
            (type === 'won' ? 'bg-green-900/40 backdrop-blur-[2px]' : 'bg-red-900/40 backdrop-blur-[2px]');
            
        const demoTag = _minesIsDemo() ? ' <span class="text-xs opacity-70 bg-white/10 px-2 py-0.5 rounded-full ml-1 align-middle">DEMO</span>' : '';
        
        ov.innerHTML = type === 'won'
            ? `<div class="text-5xl mb-2 drop-shadow-lg">🎉</div>
               <div class="text-2xl font-black text-green-300 drop-shadow-[0_0_10px_rgba(16,185,129,0.8)]">${MinesGame.winAmount} ⭐${demoTag}</div>`
            : `<div class="text-5xl mb-2 drop-shadow-lg">💥</div>
               <div class="text-lg font-bold text-red-300 drop-shadow-[0_0_10px_rgba(239,68,68,0.8)]">${t('mines_game_over')}${demoTag}</div>`;
               
        grid.parentElement.style.position = 'relative';
        grid.parentElement.appendChild(ov);
        
        // Плавное появление
        requestAnimationFrame(() => {
            ov.style.opacity = '1';
        });
    }, 600); // 600ms задержки
}

function _minesSetLoading(on) {
    const btn = document.getElementById('mines-btn-start');
    if (btn) btn.disabled = on;
}

// ─── TOAST ────────────────────────────────────────────
function _minesShowToast(msg, type = 'info') {
    const colors = {
        success: 'bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-emerald-500/50',
        error:   'bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-red-500/50',
        warn:    'bg-gradient-to-r from-yellow-500 to-orange-500 text-black shadow-yellow-500/50',
        info:    'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-blue-500/50',
    };
    const el = document.createElement('div');
    el.className = `fixed top-6 left-1/2 -translate-x-1/2 z-[9999] px-6 py-3 rounded-2xl
        text-sm font-bold shadow-[0_10px_40px_-10px_rgba(0,0,0,0.5)] transition-all duration-300 border border-white/20 ${colors[type] || colors.info}`;
    el.innerHTML = msg; // Разрешаем HTML для иконок
    document.body.appendChild(el);
    
    // Анимация появления
    el.style.transform = 'translate(-50%, -20px)';
    el.style.opacity = '0';
    requestAnimationFrame(() => {
        el.style.transform = 'translate(-50%, 0)';
        el.style.opacity = '1';
    });

    setTimeout(() => { 
        el.style.transform = 'translate(-50%, -20px)';
        el.style.opacity = '0'; 
        setTimeout(() => el.remove(), 300); 
    }, 2500);
}

// ─── ХЕЛПЕР i18n ─────────────────────────────────────
function t(key) {
    if (typeof i18n !== 'undefined' && i18n[currentLang] && i18n[currentLang][key])
        return i18n[currentLang][key];
    if (typeof i18n !== 'undefined' && i18n['ru'] && i18n['ru'][key])
        return i18n['ru'][key];
    return key;
}

// ─── ГЛОБАЛЬНЫЙ ЭКСПОРТ ───────────────────────────────
window.openMinesGame    = openMinesGame;
window.closeMinesGame   = closeMinesGame;
window.minesStart       = minesStart;
window.minesReveal      = minesReveal;
window.minesCashout     = minesCashout;
window.minesCancel      = minesCancel;
window.minesNewGame     = minesNewGame;
window.minesSetBet      = minesSetBet;
window.minesSelectMines = minesSelectMines;
