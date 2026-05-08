// =====================================================
// games-mines.js — Игра «Мины» (5×5)
// =====================================================

// ─── СОСТОЯНИЕ ───────────────────────────────────────
const MinesGame = {
    active:     false,
    bet:        100,
    mines:      3,
    revealed:   [],
    multiplier: 1.00,
    winAmount:  0,
    nextMult:   null,
    status:     'idle',   // idle | active | won | lost
};

const MINES_MIN_BET  = 50;
const MINES_MAX_BET  = 5000;
const MINES_VALID    = [1, 3, 5, 10];

// ─── ОТКРЫТЬ ЭКРАН ────────────────────────────────────
function openMinesGame() {
    if (typeof vibrate === 'function') vibrate('light');
    const mainView  = document.getElementById('games-main-view');
    const minesView = document.getElementById('games-mines-view');
    if (mainView)  mainView.classList.add('hidden');
    if (minesView) minesView.classList.remove('hidden');
    _minesCheckState();
}

function closeMinesGame() {
    if (MinesGame.status === 'active' && MinesGame.revealed.length > 0) {
        // Предупреждаем если есть активная игра с ходами
        _minesShowToast(t('mines_reveal_first'), 'warn');
        return;
    }
    if (typeof vibrate === 'function') vibrate('light');
    const mainView  = document.getElementById('games-main-view');
    const minesView = document.getElementById('games-mines-view');
    if (minesView) minesView.classList.add('hidden');
    if (mainView)  mainView.classList.remove('hidden');
}

// ─── ПРОВЕРКА АКТИВНОЙ ИГРЫ НА СЕРВЕРЕ ───────────────
async function _minesCheckState() {
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
        btn.classList.toggle('bg-green-500/30',   active);
        btn.classList.toggle('border-green-500/60', active);
        btn.classList.toggle('text-green-300',    active);
        btn.classList.toggle('bg-white/5',        !active);
        btn.classList.toggle('border-white/10',   !active);
        btn.classList.toggle('text-white/70',     !active);
    });
}

// ─── СТАРТ ИГРЫ ───────────────────────────────────────
async function minesStart() {
    const inp = document.getElementById('mines-bet-input');
    const bet = parseInt(inp?.value) || 0;

    if (bet < MINES_MIN_BET || bet > MINES_MAX_BET) {
        _minesShowToast(
            t('mines_err_limits').replace('{min}', MINES_MIN_BET).replace('{max}', MINES_MAX_BET),
            'error'
        );
        return;
    }

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

        // Обновляем баланс звёзд
        if (typeof loadUserData === 'function') loadUserData();
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        _minesSetLoading(false);
    }
}

// ─── ОТКРЫТИЕ ЯЧЕЙКИ ──────────────────────────────────
async function minesReveal(cellIdx) {
    if (MinesGame.status !== 'active') return;
    if (MinesGame.revealed.includes(cellIdx)) return;

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
            // ВЗРЫВ
            MinesGame.status   = 'lost';
            MinesGame.revealed = data.revealed || [];
            if (typeof vibrate === 'function') vibrate('heavy');
            _minesRevealAll(cellIdx, data.mine_pos || [], data.revealed || []);
            _minesUpdatePanel();
            _minesSetGameActive(false, 'lost');
            setTimeout(() => _minesShowToast(t('mines_status_lost'), 'error'), 300);
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
                // Все безопасные ячейки открыты — автовыигрыш
                _minesSetGameActive(false, 'won');
                _minesShowToast(`🎉 +${data.win_amount} ⭐`, 'success');
                if (typeof loadUserData === 'function') loadUserData();
            }
        }
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        if (cellEl) cellEl.classList.remove('mines-cell--loading');
    }
}

// ─── ВЫВОД ВЫИГРЫША ───────────────────────────────────
async function minesCashout() {
    if (MinesGame.status !== 'active' || MinesGame.revealed.length === 0) {
        _minesShowToast(t('mines_reveal_first'), 'warn');
        return;
    }
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

        if (typeof vibrate === 'function') vibrate('medium');
        _minesUpdatePanel();
        _minesSetGameActive(false, 'won');
        _minesShowToast(`🎉 +${data.win_amount} ⭐`, 'success');
        if (typeof loadUserData === 'function') loadUserData();
    } catch(e) {
        _minesShowToast(t('err_conn'), 'error');
    } finally {
        _minesSetLoading(false);
    }
}

// ─── ОТМЕНА ИГРЫ (ДО ПЕРВОГО ХОДА) ───────────────────
async function minesCancel() {
    if (MinesGame.status !== 'active' || MinesGame.revealed.length > 0) return;
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
    }
}

// ─── НОВАЯ ИГРА ───────────────────────────────────────
function minesNewGame() {
    MinesGame.status   = 'idle';
    MinesGame.active   = false;
    MinesGame.revealed = [];
    _minesSetGameIdle();
}

// ─── РЕНДЕР ПОЛЯ ──────────────────────────────────────
function _minesRenderField(mineCells, safeCells) {
    const grid = document.getElementById('mines-grid');
    if (!grid) return;
    grid.innerHTML = '';
    for (let i = 0; i < 25; i++) {
        const cell = document.createElement('button');
        cell.className = 'mines-cell';
        cell.dataset.cell = i;
        cell.innerHTML = `<span class="mines-cell-inner"></span>`;
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
    cell.classList.add('mines-cell--safe');
    cell.innerHTML = `<span class="mines-cell-inner">💎</span>`;
    cell.disabled = true;
}

function _minesRevealAll(explodedIdx, minePos, safeRevealed) {
    for (let i = 0; i < 25; i++) {
        const cell = document.querySelector(`.mines-cell[data-cell="${i}"]`);
        if (!cell) continue;
        if (minePos.includes(i)) {
            cell.classList.add(i === explodedIdx ? 'mines-cell--exploded' : 'mines-cell--mine');
            cell.innerHTML = `<span class="mines-cell-inner">💣</span>`;
            cell.disabled = true;
        } else if (safeRevealed.includes(i)) {
            _applySafeStyle(cell);
        }
        cell.disabled = true;
    }
}

// ─── ОБНОВЛЕНИЕ ПАНЕЛИ СТАТИСТИКИ ─────────────────────
function _minesUpdatePanel() {
    const multEl   = document.getElementById('mines-multiplier');
    const winEl    = document.getElementById('mines-win-amount');
    const nextEl   = document.getElementById('mines-next-mult');
    const statusEl = document.getElementById('mines-status-text');

    if (multEl)   multEl.textContent  = `${MinesGame.multiplier.toFixed(2)}x`;
    if (winEl)    winEl.textContent   = `${MinesGame.winAmount} ⭐`;
    if (nextEl)   nextEl.textContent  = MinesGame.nextMult
        ? `${MinesGame.nextMult.toFixed(2)}x` : '—';

    if (statusEl) {
        const map = {
            idle:   t('mines_status_idle'),
            active: t('mines_status_active'),
            won:    t('mines_status_won'),
            lost:   t('mines_status_lost'),
        };
        statusEl.textContent = map[MinesGame.status] || '';
        statusEl.className = 'text-xs font-bold px-3 py-1 rounded-full ' +
            (MinesGame.status === 'won'  ? 'bg-green-500/20 text-green-300' :
             MinesGame.status === 'lost' ? 'bg-red-500/20 text-red-300' :
             MinesGame.status === 'active' ? 'bg-blue-500/20 text-blue-300' :
             'bg-white/10 text-white/50');
    }
}

// ─── ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ ЭКРАНА ─────────────────────
function _minesSetGameActive(active, endStatus) {
    const setup    = document.getElementById('mines-setup-panel');
    const gameArea = document.getElementById('mines-game-area');
    const cashBtn  = document.getElementById('mines-btn-cashout');
    const cancelBtn = document.getElementById('mines-btn-cancel');
    const newBtn   = document.getElementById('mines-btn-new');
    const gridEl   = document.getElementById('mines-grid');

    if (active) {
        setup?.classList.add('hidden');
        gameArea?.classList.remove('hidden');
        cashBtn?.classList.remove('hidden');
        cancelBtn?.classList.remove('hidden');
        newBtn?.classList.add('hidden');
        if (gridEl) gridEl.classList.remove('pointer-events-none', 'opacity-60');
    } else {
        // Game ended
        cashBtn?.classList.add('hidden');
        cancelBtn?.classList.add('hidden');
        newBtn?.classList.remove('hidden');
        if (gridEl) gridEl.classList.add('pointer-events-none');
        // Show overlay on grid
        if (endStatus === 'won') {
            _minesShowOverlay('won');
        } else if (endStatus === 'lost') {
            _minesShowOverlay('lost');
        }
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
    const ov = document.createElement('div');
    ov.id = 'mines-grid-overlay';
    ov.className = 'absolute inset-0 flex flex-col items-center justify-center rounded-2xl z-20 ' +
        (type === 'won' ? 'bg-green-900/60 backdrop-blur-sm' : 'bg-red-900/60 backdrop-blur-sm');
    ov.innerHTML = type === 'won'
        ? `<div class="text-4xl mb-1">🎉</div>
           <div class="text-lg font-black text-green-300">${MinesGame.winAmount} ⭐</div>`
        : `<div class="text-4xl mb-1">💥</div>
           <div class="text-sm font-bold text-red-300">${t('mines_game_over')}</div>`;
    grid.parentElement.style.position = 'relative';
    grid.parentElement.appendChild(ov);
}

function _minesSetLoading(on) {
    const btn = document.getElementById('mines-btn-start');
    if (btn) btn.disabled = on;
}

// ─── TOAST ────────────────────────────────────────────
function _minesShowToast(msg, type = 'info') {
    const colors = {
        success: 'bg-green-500/90 text-white',
        error:   'bg-red-500/90 text-white',
        warn:    'bg-yellow-500/90 text-black',
        info:    'bg-blue-500/90 text-white',
    };
    const el = document.createElement('div');
    el.className = `fixed top-6 left-1/2 -translate-x-1/2 z-[9999] px-5 py-2.5 rounded-2xl
        text-sm font-bold shadow-xl transition-all duration-300 ${colors[type] || colors.info}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 2200);
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
window.openMinesGame   = openMinesGame;
window.closeMinesGame  = closeMinesGame;
window.minesStart      = minesStart;
window.minesReveal     = minesReveal;
window.minesCashout    = minesCashout;
window.minesCancel     = minesCancel;
window.minesNewGame    = minesNewGame;
window.minesSetBet     = minesSetBet;
window.minesSelectMines = minesSelectMines;
