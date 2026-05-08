// =====================================================
// games-mines.js  —  Мины (Minesweeper Casino)
// Валюта: только ⭐ Stars
// =====================================================
'use strict';

const MINES_GRID = 25;   // 5×5
const MINES_HE   = 0.03; // house edge (для клиентского предпросмотра/демо)

// ─── Состояние ────────────────────────────────────────────────────────────────
let minesS = {
    phase:    'idle',  // 'idle' | 'playing' | 'exploded' | 'won'
    bet:      50,
    count:    3,       // количество мин
    revealed: [],
    mult:     1.0,
    nextMult: null,
    safeLeft: 0,
    locked:   false,
    isDemo:   false,
    _dm:      [],      // демо-мины (генерируются локально)
};

// ─── Утилиты ──────────────────────────────────────────────────────────────────

function _mt(key, vars = {}) {
    let s = (i18n[currentLang] || i18n['ru'] || {})[key] || key;
    Object.entries(vars).forEach(([k, v]) => { s = s.replace(`{${k}}`, v); });
    return s;
}

function _mCalc(total, mines, k, he = MINES_HE) {
    if (k <= 0) return 1.0;
    const safe = total - mines;
    if (safe <= 0 || k > safe) return 1.0;
    let p = 1.0;
    for (let i = 0; i < k; i++) p *= (safe - i) / (total - i);
    return p > 0 ? Math.round((1 - he) / p * 10000) / 10000 : 1.0;
}

function _el(id) { return document.getElementById(id); }

// ─── Открытие / Закрытие ──────────────────────────────────────────────────────

function openMinesGame() {
    showGameView('games-mines-view');
    minesS.isDemo = typeof isDemoMode !== 'undefined' ? isDemoMode : false;
    _minesRestoreOrReset();
}

function closeMinesGame() {
    if (minesS.phase === 'playing' && !minesS.isDemo) {
        showNotify(_mt('mines_cashout_before_exit'), 'warning');
        return;
    }
    hideGameView('games-mines-view');
}

// ─── Восстановление сессии ────────────────────────────────────────────────────

async function _minesRestoreOrReset() {
    if (minesS.isDemo) { _minesReset(); return; }
    try {
        const r = await fetch('/api/mines/state', { headers: getApiHeaders() });
        const d = await r.json();
        if (d.active) {
            minesS.phase    = 'playing';
            minesS.bet      = d.bet;
            minesS.count    = d.mines_count;
            minesS.revealed = d.revealed;
            minesS.mult     = d.multiplier;
            minesS.nextMult = d.next_multiplier;
            minesS.safeLeft = d.safe_left;
            _minesApplyPlaying();
        } else { _minesReset(); }
    } catch (_) { _minesReset(); }
}

// ─── Рендер сетки ─────────────────────────────────────────────────────────────

function _minesRenderGrid() {
    const grid = _el('mines-grid');
    if (!grid) return;
    grid.innerHTML = '';
    for (let i = 0; i < MINES_GRID; i++) {
        const btn = document.createElement('button');
        btn.id             = `mc${i}`;
        btn.className      = 'mc mc--hidden';
        btn.dataset.i      = i;
        btn.innerHTML      = `
            <span class="mc-dot"></span>
            <span class="mc-gem hidden">💎</span>
            <span class="mc-bomb hidden">💣</span>`;
        btn.addEventListener('click', () => minesReveal(i));
        grid.appendChild(btn);
    }
}

function _mcSet(i, state) {
    const c = _el(`mc${i}`);
    if (!c) return;
    c.className = `mc mc--${state}`;
    c.querySelector('.mc-dot') ?.classList.toggle('hidden', state !== 'hidden');
    c.querySelector('.mc-gem') ?.classList.toggle('hidden', state !== 'safe');
    c.querySelector('.mc-bomb')?.classList.toggle('hidden', state !== 'mine' && state !== 'mine-dim');
}

// ─── Обновление статистики ────────────────────────────────────────────────────

function _minesStats() {
    const pot   = minesS.bet * minesS.mult;
    const multEl = _el('mines-mult-val');
    const potEl  = _el('mines-pot-val');
    const nextEl = _el('mines-next-val');
    const nextW  = _el('mines-next-wrap');
    const cbLbl  = _el('mines-cb-label');

    if (multEl) multEl.textContent = `×${minesS.mult.toFixed(2)}`;
    if (potEl)  potEl.textContent  = `${Math.round(pot)} ⭐`;

    if (nextEl && nextW) {
        if (minesS.nextMult && minesS.phase === 'playing') {
            nextW.classList.remove('hidden');
            nextEl.textContent = `→ ×${minesS.nextMult.toFixed(2)}`;
        } else {
            nextW.classList.add('hidden');
        }
    }
    if (cbLbl && minesS.phase === 'playing') {
        cbLbl.textContent = `${_mt('mines_cashout_btn')} ${Math.round(pot)} ⭐`;
    }
}

// ─── Переходы UI ─────────────────────────────────────────────────────────────

function _minesReset() {
    Object.assign(minesS, {
        phase: 'idle', revealed: [], mult: 1.0,
        nextMult: null, locked: false, _dm: [],
    });
    _minesRenderGrid();
    _minesPreview();
    _minesToggle(false);
    _minesHideResult();
}

function _minesApplyPlaying() {
    _minesRenderGrid();
    minesS.revealed.forEach(i => _mcSet(i, 'safe'));
    _minesStats();
    _minesToggle(true);
}

/** playing=true → cashout visible, controls hidden */
function _minesToggle(playing) {
    _el('mines-ctrl-wrap')?.classList.toggle('hidden', playing);
    _el('mines-cb-wrap')  ?.classList.toggle('hidden', !playing);
    ['mines-mines-sel', 'mines-bet-wrap'].forEach(id => {
        _el(id)?.classList.toggle('pointer-events-none', playing);
        _el(id)?.classList.toggle('opacity-40', playing);
    });
}

// ─── Результат ────────────────────────────────────────────────────────────────

function _minesResult(win, data) {
    const w = _el('mines-result');
    if (!w) return;
    w.classList.remove('hidden', 'mr--win', 'mr--lose');
    if (win) {
        w.classList.add('mr--win');
        w.innerHTML = `
            <div class="mr-emoji">💰</div>
            <div class="mr-title">${_mt('mines_win_title')}</div>
            <div class="mr-amount">${Math.round(data.win_amount)} ⭐</div>
            <div class="mr-sub">×${data.multiplier.toFixed(2)}</div>`;
    } else {
        w.classList.add('mr--lose');
        w.innerHTML = `
            <div class="mr-emoji">💥</div>
            <div class="mr-title">${_mt('mines_lose_title')}</div>
            <div class="mr-sub">${_mt('mines_lose_msg', { amount: `${data.bet} ⭐` })}</div>`;
    }
    setTimeout(_minesHideResult, 3200);
}

function _minesHideResult() {
    _el('mines-result')?.classList.add('hidden');
}

// ─── Предпросмотр (idle) ──────────────────────────────────────────────────────

function _minesPreview() {
    const bet  = parseInt(_el('mines-bet-input')?.value || 0) || 0;
    const mult = _mCalc(MINES_GRID, minesS.count, 1);
    const multEl = _el('mines-mult-val');
    const potEl  = _el('mines-pot-val');
    if (multEl) multEl.textContent = `×${mult.toFixed(2)}`;
    if (potEl)  potEl.textContent  = `${Math.round(bet * mult)} ⭐`;
}

// ─── Баланс ───────────────────────────────────────────────────────────────────

function _mApplyBal(bal) {
    if (typeof myStars !== 'undefined') myStars = bal;
    if (typeof updateUI === 'function') updateUI();
}

// ─── СТАРТ ИГРЫ ───────────────────────────────────────────────────────────────

async function minesStart() {
    if (minesS.phase !== 'idle') return;

    const bet   = parseInt(_el('mines-bet-input')?.value || 0);
    const mines = minesS.count;

    if (!bet || bet <= 0) { showNotify(_mt('err_invalid_amount'), 'error'); return; }

    if (minesS.isDemo) { _mDemoStart(bet, mines); return; }

    const btn = _el('mines-start-btn');
    if (btn) { btn.disabled = true; btn.textContent = _mt('mines_starting'); }

    try {
        const res  = await fetch('/api/mines/start', {
            method: 'POST', headers: getApiHeaders(),
            body: JSON.stringify({ bet, mines_count: mines }),
        });
        const data = await res.json();

        if (!res.ok) {
            const d = data.detail || '';
            if (d === 'insufficient_balance' || res.status === 402)
                showNotify(_mt('not_enough_stars'), 'error');
            else if (d.startsWith('bet_out_of_range:')) {
                const [, mn, mx] = d.split(':');
                showNotify(_mt('mines_bet_limits', { min: mn, max: mx }), 'error');
            } else showNotify(d || _mt('err_conn_srv'), 'error');
            return;
        }

        minesS.phase    = 'playing';
        minesS.bet      = bet;
        minesS.count    = mines;
        minesS.revealed = [];
        minesS.mult     = 1.0;
        minesS.nextMult = data.next_multiplier;
        minesS.safeLeft = MINES_GRID - mines;
        minesS.locked   = false;

        _mApplyBal(data.balance);
        _minesApplyPlaying();
        if (typeof vibrate === 'function') vibrate('medium');

    } catch (_) { showNotify(_mt('err_conn_srv'), 'error'); }
    finally {
        if (btn) { btn.disabled = false; btn.textContent = _mt('mines_start'); }
    }
}

// ─── ОТКРЫТИЕ ЯЧЕЙКИ ─────────────────────────────────────────────────────────

async function minesReveal(idx) {
    if (minesS.phase !== 'playing') return;
    if (minesS.locked) return;
    if (minesS.revealed.includes(idx)) return;

    minesS.locked = true;
    if (typeof vibrate === 'function') vibrate('light');

    if (minesS.isDemo) { _mDemoReveal(idx); minesS.locked = false; return; }

    try {
        const res  = await fetch('/api/mines/reveal', {
            method: 'POST', headers: getApiHeaders(),
            body: JSON.stringify({ cell: idx }),
        });
        const data = await res.json();

        if (!res.ok) { showNotify(data.detail || _mt('err_conn_srv'), 'error'); return; }

        if (data.hit_mine) {
            minesS.phase = 'exploded';
            _mcSet(idx, 'mine');
            data.mine_cells.forEach(m => { if (m !== idx) _mcSet(m, 'mine-dim'); });
            if (typeof vibrate === 'function') vibrate('heavy');
            _minesResult(false, { bet: minesS.bet });
            _mApplyBal(data.balance);
            _minesToggle(false);
            setTimeout(_minesReset, 3200);
        } else {
            minesS.revealed = data.revealed;
            minesS.mult     = data.multiplier;
            minesS.nextMult = data.next_multiplier;
            minesS.safeLeft = data.safe_left;
            _mcSet(idx, 'safe');
            _minesStats();
            if (data.safe_left === 0) await minesCashout();
        }
    } catch (_) { showNotify(_mt('err_conn_srv'), 'error'); }
    finally { minesS.locked = false; }
}

// ─── КЭШАУТ ───────────────────────────────────────────────────────────────────

async function minesCashout() {
    if (minesS.phase !== 'playing') return;
    if (!minesS.revealed.length)    return;

    if (minesS.isDemo) { _mDemoCashout(); return; }

    minesS.locked = true;
    const btn = _el('mines-cb-btn');
    if (btn) btn.disabled = true;

    try {
        const res  = await fetch('/api/mines/cashout', {
            method: 'POST', headers: getApiHeaders(),
        });
        const data = await res.json();

        if (!res.ok) { showNotify(data.detail || _mt('err_conn_srv'), 'error'); return; }

        minesS.phase = 'won';
        data.mine_cells.forEach(m => {
            if (!minesS.revealed.includes(m)) _mcSet(m, 'mine-dim');
        });
        _minesResult(true, data);
        _mApplyBal(data.balance);
        if (typeof vibrate === 'function') vibrate('success');
        _minesToggle(false);
        setTimeout(_minesReset, 3200);

    } catch (_) { showNotify(_mt('err_conn_srv'), 'error'); }
    finally {
        minesS.locked = false;
        if (btn) btn.disabled = false;
    }
}

// ─── ДЕМО-РЕЖИМ ───────────────────────────────────────────────────────────────

function _mDemoStart(bet, mines) {
    const cells = [];
    while (cells.length < mines) {
        const c = Math.floor(Math.random() * MINES_GRID);
        if (!cells.includes(c)) cells.push(c);
    }
    minesS._dm      = cells;
    minesS.phase    = 'playing';
    minesS.bet      = bet;
    minesS.count    = mines;
    minesS.revealed = [];
    minesS.mult     = 1.0;
    minesS.nextMult = _mCalc(MINES_GRID, mines, 1);
    minesS.safeLeft = MINES_GRID - mines;
    minesS.locked   = false;
    _minesApplyPlaying();
    if (typeof vibrate === 'function') vibrate('medium');
}

function _mDemoReveal(idx) {
    if (minesS._dm.includes(idx)) {
        minesS.phase = 'exploded';
        _mcSet(idx, 'mine');
        minesS._dm.forEach(m => { if (m !== idx) _mcSet(m, 'mine-dim'); });
        if (typeof vibrate === 'function') vibrate('heavy');
        _minesResult(false, { bet: minesS.bet });
        _minesToggle(false);
        setTimeout(_minesReset, 3200);
    } else {
        minesS.revealed.push(idx);
        const k = minesS.revealed.length;
        minesS.mult     = _mCalc(MINES_GRID, minesS.count, k);
        minesS.nextMult = _mCalc(MINES_GRID, minesS.count, k + 1);
        minesS.safeLeft = MINES_GRID - minesS.count - k;
        _mcSet(idx, 'safe');
        _minesStats();
        if (typeof vibrate === 'function') vibrate('light');
        if (minesS.safeLeft === 0) _mDemoCashout();
    }
}

function _mDemoCashout() {
    minesS.phase = 'won';
    minesS._dm.forEach(m => { if (!minesS.revealed.includes(m)) _mcSet(m, 'mine-dim'); });
    _minesResult(true, { win_amount: minesS.bet * minesS.mult, multiplier: minesS.mult });
    if (typeof vibrate === 'function') vibrate('success');
    _minesToggle(false);
    setTimeout(_minesReset, 3200);
}

// ─── НАСТРОЙКИ (idle only) ────────────────────────────────────────────────────

function minesSetCount(n) {
    if (minesS.phase !== 'idle') return;
    minesS.count = n;
    document.querySelectorAll('.mc-opt').forEach(b =>
        b.classList.toggle('mc-opt--on', parseInt(b.dataset.n) === n)
    );
    _minesPreview();
}

function minesSetBet(mode) {
    const cfg = window._minesCfg || {};
    const mn  = cfg.min_bet || 10;
    const mx  = cfg.max_bet || 5000;
    const inp = _el('mines-bet-input');
    if (!inp) return;
    let v = parseInt(inp.value) || mn;
    if      (mode === 'min')    v = mn;
    else if (mode === 'max')    v = mx;
    else if (mode === 'half')   v = Math.max(mn, Math.floor(v / 2));
    else if (mode === 'double') v = Math.min(mx, v * 2);
    inp.value = v;
    _minesPreview();
}

// ─── СИНХРОНИЗАЦИЯ ДЕМО ────────────────────────────────────────────────────────

function minesSyncDemo() {
    minesS.isDemo = typeof isDemoMode !== 'undefined' ? isDemoMode : false;
}

// ─── ИНИЦИАЛИЗАЦИЯ ────────────────────────────────────────────────────────────

function minesInit() {
    _minesRenderGrid();
    minesSetCount(3);
    const inp = _el('mines-bet-input');
    if (inp) inp.addEventListener('input', _minesPreview);
    _minesPreview();
}

// ─── ЭКСПОРТ ─────────────────────────────────────────────────────────────────

window.openMinesGame  = openMinesGame;
window.closeMinesGame = closeMinesGame;
window.minesReveal    = minesReveal;
window.minesCashout   = minesCashout;
window.minesStart     = minesStart;
window.minesSetCount  = minesSetCount;
window.minesSetBet    = minesSetBet;
window.minesInit      = minesInit;
window.minesSyncDemo  = minesSyncDemo;
