// =====================================================
// games-rocket.js — Логика Игры РАКЕТА (Crash)
// =====================================================

let rocketConfigLocal = null; 
let rocketState = 'idle'; // 'idle', 'starting', 'flying', 'crashed', 'cashed_out'
let rocketBetAmount = 0;
let rocketCrashPoint = 0;
let rocketCurrentMult = 1.00;
let rocketStartTime = 0;
let rocketAnimFrame = null;
let rocketTimeout = null;

function resetRocketToIdle() {
    rocketState = 'idle';
    const statusText = document.getElementById('rocket-status-text');
    if (statusText) {
        statusText.className = "text-sm font-bold bg-black/50 px-3 py-1 rounded-full text-white/70 tracking-widest uppercase";
    }
    updateRocketUI();
}

function openRocketGame() {
    // Используем универсальный роутер из games.js
    if (typeof showGameView === 'function') {
        showGameView('games-rocket-view');
    } else {
        if (typeof vibrate === 'function') vibrate('light');
        document.getElementById('games-main-view').classList.add('hidden');
        document.getElementById('games-rocket-view').classList.remove('hidden');
    }
    
    rocketState = 'idle';
    clearTimeout(rocketTimeout);
    updateRocketUI();
}

function closeRocketGame() {
    if (rocketState === 'starting' || rocketState === 'flying') {
        if(typeof tg !== 'undefined' && tg) tg.showAlert(i18n[currentLang]?.rocket_cant_close || 'Нельзя закрыть во время полета!');
        return;
    }
    
    if (typeof hideGameView === 'function') {
        hideGameView('games-rocket-view');
    } else {
        if (typeof vibrate === 'function') vibrate('light');
        document.getElementById('games-rocket-view').classList.add('hidden');
        document.getElementById('games-main-view').classList.remove('hidden');
    }
}

function updateRocketUI() {
    const inputEl = document.getElementById('rocket-bet-input');
    const btnAction = document.getElementById('btn-rocket-action');
    const txtAction = document.getElementById('rocket-action-text');
    const multText = document.getElementById('rocket-multiplier');
    const rocketImg = document.getElementById('rocket-img');
    const starsBg = document.getElementById('rocket-stars-bg');
    const statusText = document.getElementById('rocket-status-text');
    const btnClose = document.getElementById('btn-close-rocket');
    
    const currencyIcon = rocketConfigLocal?.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';
    const inputIcon = document.getElementById('rocket-currency-icon');
    if (inputIcon) inputIcon.src = currencyIcon;

    if (!btnAction || !multText || !txtAction) return;

    if (rocketState === 'idle') {
        if (inputEl) inputEl.disabled = false;
        if (btnClose) btnClose.classList.remove('opacity-50', 'pointer-events-none');
        btnAction.className = "w-full py-4 rounded-xl font-black text-xl text-white active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg bg-gradient-to-r from-orange-500 to-red-600 shadow-orange-500/40";
        txtAction.innerText = i18n[currentLang]?.place_bet || 'Полететь';
        
        multText.innerText = '1.00x';
        multText.className = "text-5xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-400 drop-shadow-lg transition-transform scale-100";
        
        if (rocketImg) rocketImg.className = "w-20 h-20 object-contain rocket-idle";
        if (starsBg) starsBg.classList.remove('bg-stars-fast');
        if (statusText) statusText.innerText = '';
    } 
    else if (rocketState === 'starting') {
        if (inputEl) inputEl.disabled = true;
        if (btnClose) btnClose.classList.add('opacity-50', 'pointer-events-none');
        btnAction.classList.add('opacity-50', 'pointer-events-none');
        txtAction.innerText = i18n[currentLang]?.processing || 'Подготовка...';
        if (statusText) statusText.innerText = i18n[currentLang]?.rocket_starting || 'Подготовка к взлету...';
        if (rocketImg) rocketImg.className = "w-20 h-20 object-contain rocket-idle"; 
    }
    else if (rocketState === 'flying') {
        if (inputEl) inputEl.disabled = true;
        if (btnClose) btnClose.classList.add('opacity-50', 'pointer-events-none');
        btnAction.className = "w-full py-4 rounded-xl font-black text-xl text-white active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg bg-gradient-to-r from-emerald-500 to-green-600 shadow-green-500/40";
        
        let currentWin = Math.floor(rocketBetAmount * rocketCurrentMult);
        txtAction.innerHTML = `${i18n[currentLang]?.cashout || 'Забрать'} ${currentWin} <img src="${currencyIcon}" class="w-5 h-5 object-contain mb-0.5">`;
        
        multText.innerText = rocketCurrentMult.toFixed(2) + 'x';
        multText.className = "text-6xl font-black text-transparent bg-clip-text bg-gradient-to-b from-orange-300 to-orange-500 drop-shadow-[0_0_15px_rgba(249,115,22,0.8)] scale-110 transition-transform duration-75";
        
        if (rocketImg) rocketImg.className = "w-20 h-20 object-contain rocket-flying";
        if (starsBg) starsBg.classList.add('bg-stars-fast');
        if (statusText) statusText.innerText = '';
    }
    else if (rocketState === 'crashed') {
        if (inputEl) inputEl.disabled = false;
        if (btnClose) btnClose.classList.remove('opacity-50', 'pointer-events-none');
        btnAction.className = "w-full py-4 rounded-xl font-black text-xl text-white transition-all flex items-center justify-center gap-2 shadow-lg bg-gray-600/50 text-gray-400 cursor-not-allowed pointer-events-none";
        txtAction.innerText = i18n[currentLang]?.crashed || 'Улетела!';
        
        multText.className = "text-5xl font-black text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.8)] scale-100 transition-all";
        if (rocketImg) rocketImg.className = "w-20 h-20 object-contain rocket-crashed";
        if (starsBg) starsBg.classList.remove('bg-stars-fast');
        if (statusText) statusText.innerText = '';
    }
    else if (rocketState === 'cashed_out') {
        if (inputEl) inputEl.disabled = false;
        if (btnClose) btnClose.classList.remove('opacity-50', 'pointer-events-none');
        btnAction.className = "w-full py-4 rounded-xl font-black text-xl text-white transition-all flex items-center justify-center gap-2 shadow-lg bg-emerald-500/20 text-emerald-400 pointer-events-none border border-emerald-500/50";
        txtAction.innerText = i18n[currentLang]?.rocket_win_btn || 'Успех!';
        
        multText.className = "text-5xl font-black text-emerald-400 drop-shadow-[0_0_15px_rgba(16,185,129,0.8)] scale-100 transition-all";
        if (rocketImg) rocketImg.className = "w-20 h-20 object-contain rocket-flying opacity-50"; 
        if (starsBg) starsBg.classList.remove('bg-stars-fast');
        
        let winAmount = Math.floor(rocketBetAmount * rocketCurrentMult);
        if (statusText) {
            statusText.innerText = `${i18n[currentLang]?.you_won || 'Вы выиграли'} ${winAmount}!`;
            statusText.className = "text-sm font-bold bg-emerald-500/20 px-3 py-1 rounded-full text-emerald-400 tracking-widest uppercase border border-emerald-500/30";
        }
    }
}

function setRocketBet(type) {
    if(rocketState !== 'idle') return;
    if (typeof vibrate === 'function') vibrate('light');
    const input = document.getElementById('rocket-bet-input');
    const min = rocketConfigLocal?.min_bet || 50;
    const max = rocketConfigLocal?.max_bet || 10000;
    const currentBal = rocketConfigLocal?.currency === 'stars' ? myStars : myBalance;

    let val = parseInt(input.value) || min;

    if (type === 'min') val = min;
    else if (type === 'x2') val = val * 2;
    else if (type === 'max') val = Math.min(currentBal, max);
    
    val = Math.max(min, Math.min(val, max));
    if (input) input.value = val;
}

async function handleRocketAction() {
    if (typeof vibrate === 'function') vibrate('light');
    if (rocketState === 'idle') {
        const input = document.getElementById('rocket-bet-input');
        rocketBetAmount = parseInt(input?.value || 0) || 0;
        
        const min = rocketConfigLocal?.min_bet || 50;
        const max = rocketConfigLocal?.max_bet || 10000;
        const currentBal = rocketConfigLocal?.currency === 'stars' ? myStars : myBalance;
        
        if (rocketBetAmount < min || rocketBetAmount > max) {
            if(typeof tg !== 'undefined' && tg) tg.showAlert((i18n[currentLang]?.rocket_err_limits || 'Неверная сумма') + ` (${min} - ${max})`);
            return;
        }
        if (rocketBetAmount > currentBal) {
            if(typeof tg !== 'undefined' && tg) tg.showAlert('Недостаточно средств!');
            return;
        }

        rocketState = 'starting';
        updateRocketUI();

        try {
            const res = await fetch('/api/rocket/start', {
                method: 'POST',
                headers: getApiHeaders(),
                body: JSON.stringify({ tg_id: tgUser.id, bet: rocketBetAmount })
            });
            const data = await res.json();
            
            if (data.status === 'ok') {
                if (data.balance !== undefined) myBalance = data.balance;
                if (data.stars !== undefined) myStars = data.stars;
                
                rocketCrashPoint = data.crash_point;
                if (typeof updateUI === 'function') updateUI(); 
                startRocketFlight();
            } else {
                if(typeof tg !== 'undefined' && tg) tg.showAlert(data.detail || 'Error');
                resetRocketToIdle();
            }
        } catch (e) {
            if(typeof tg !== 'undefined' && tg) tg.showAlert(i18n[currentLang]?.err_conn || 'Connection error');
            resetRocketToIdle();
        }

    } else if (rocketState === 'flying') {
        cashoutRocket();
    }
}

function startRocketFlight() {
    rocketState = 'flying';
    rocketCurrentMult = 1.00;
    rocketStartTime = Date.now();
    updateRocketUI();
    if (typeof vibrate === 'function') vibrate('medium');

    const growthSpeed = rocketConfigLocal?.growth_speed || 1.00006;
    const currencyIcon = rocketConfigLocal?.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';

    function gameLoop() {
        if (rocketState !== 'flying') return;
        
        let elapsed = Date.now() - rocketStartTime;
        rocketCurrentMult = Math.max(1.00, Math.pow(growthSpeed, elapsed));
        
        if (rocketCurrentMult >= rocketCrashPoint) {
            rocketCurrentMult = rocketCrashPoint; 
            handleRocketCrash();
            return;
        }
        
        const multText = document.getElementById('rocket-multiplier');
        if (multText) multText.innerText = rocketCurrentMult.toFixed(2) + 'x';
        
        const txtAction = document.getElementById('rocket-action-text');
        let currentWin = Math.floor(rocketBetAmount * rocketCurrentMult);
        if (txtAction) txtAction.innerHTML = `${i18n[currentLang]?.cashout || 'Забрать'} ${currentWin} <img src="${currencyIcon}" class="w-5 h-5 object-contain mb-0.5">`;

        rocketAnimFrame = requestAnimationFrame(gameLoop);
    }
    
    rocketAnimFrame = requestAnimationFrame(gameLoop);
}

function handleRocketCrash() {
    cancelAnimationFrame(rocketAnimFrame);
    rocketState = 'crashed';
    if (typeof vibrate === 'function') vibrate('heavy');
    updateRocketUI();

    // Сообщаем бэкенду о краше — записываем проигрыш в историю
    fetch('/api/rocket/crash', {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({ tg_id: tgUser.id, bet: rocketBetAmount })
    })
    .then(r => r.json())
    .then(data => {
        if (data.balance !== undefined) myBalance = data.balance;
        if (data.stars !== undefined) myStars = data.stars;
        if (typeof updateUI === 'function') updateUI();
    })
    .catch(e => console.error('Rocket crash report error:', e));

    clearTimeout(rocketTimeout);
    rocketTimeout = setTimeout(resetRocketToIdle, 2500);
}

async function cashoutRocket() {
    if (rocketState !== 'flying') return;
    
    cancelAnimationFrame(rocketAnimFrame);
    const stoppedMult = rocketCurrentMult;
    
    rocketState = 'cashed_out';
    const txtAction = document.getElementById('rocket-action-text');
    if (txtAction) txtAction.innerText = '...'; 
    if (typeof vibrate === 'function') vibrate('medium');

    try {
        const res = await fetch('/api/rocket/cashout', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ tg_id: tgUser.id, multiplier: parseFloat(stoppedMult.toFixed(2)) })
        });
        const data = await res.json();
        
        if (data.status === 'ok') {
            if (data.balance !== undefined) myBalance = data.balance;
            if (data.stars !== undefined) myStars = data.stars;
            
            rocketCurrentMult = stoppedMult; 
            if (typeof updateUI === 'function') updateUI(); 
            updateRocketUI(); 
        } else {
            if(typeof tg !== 'undefined' && tg) tg.showAlert(data.detail || 'Error');
            rocketState = 'crashed';
            updateRocketUI();
        }
    } catch (e) {
        console.error(e);
        rocketState = 'crashed';
        updateRocketUI();
    } finally {
        clearTimeout(rocketTimeout);
        rocketTimeout = setTimeout(resetRocketToIdle, 2500);
    }
}

window.openRocketGame = openRocketGame;
window.closeRocketGame = closeRocketGame;
window.setRocketBet = setRocketBet;
window.handleRocketAction = handleRocketAction;