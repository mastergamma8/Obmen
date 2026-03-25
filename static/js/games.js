// =====================================================
// games.js — Логика Игр и Кейсов + РАКЕТА (Поддержка Звезд)
// =====================================================

let currentOpenedCaseId = null;
let isOpeningCase = false;
let rocketConfigLocal = null; 

// =================== КЕЙСЫ ===================

function openGamesCases() {
    vibrate('light');
    document.getElementById('games-main-view').classList.add('hidden');
    document.getElementById('games-cases-list-view').classList.remove('hidden');
    renderCasesGrid();
}

function closeGamesCases() {
    vibrate('light');
    document.getElementById('games-cases-list-view').classList.add('hidden');
    document.getElementById('games-main-view').classList.remove('hidden');
}

function renderCasesGrid() {
    const grid = document.getElementById('cases-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    if (!casesConfig || Object.keys(casesConfig).length === 0) {
        grid.innerHTML = `<div class="col-span-2 text-center text-white/50 text-sm py-10" data-i18n="not_found">Кейсы пока не добавлены</div>`;
        return;
    }

    Object.keys(casesConfig).forEach(id => {
        const c = casesConfig[id];
        const photoUrl = getImgSrc(c.photo);
        // Выбираем иконку валюты для кейса
        const currencyIcon = c.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';
        
        const card = document.createElement('div');
        card.className = "glass rounded-3xl p-4 flex flex-col items-center justify-between text-center cursor-pointer active:scale-95 transition-transform border border-indigo-400/30 shadow-[0_10px_20px_rgba(0,0,0,0.4)] hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] bg-gradient-to-b from-indigo-500/20 to-black/40 relative overflow-hidden group";
        card.onclick = () => openCaseDetails(id);
        
        card.innerHTML = `
            <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-20 pointer-events-none"></div>
            <div class="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-24 bg-indigo-500/30 blur-[30px] rounded-full pointer-events-none group-hover:bg-indigo-400/40 transition-colors"></div>
            
            <div class="w-24 h-24 mb-3 relative z-10">
                <img src="${photoUrl}" class="w-full h-full object-contain drop-shadow-[0_10px_15px_rgba(0,0,0,0.6)] group-hover:scale-110 group-hover:-translate-y-1 transition-all duration-300" onerror="this.src='https://via.placeholder.com/96?text=📦'">
            </div>
            
            <h4 class="text-white font-extrabold text-sm mb-3 glow-text w-full truncate relative z-10 tracking-wide">${c.name}</h4>
            
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
        const gift = mainGifts[item.gift_id] || baseGifts[item.gift_id];
        if (gift) return { name: gift.name, photo: getImgSrc(gift.photo) };
    }
    return { name: "???", photo: "https://via.placeholder.com/32" };
}

function openCaseDetails(caseId) {
    vibrate('light');
    const c = casesConfig[caseId];
    if (!c) return;
    currentOpenedCaseId = caseId;
    
    document.getElementById('cd-photo').src = getImgSrc(c.photo);
    document.getElementById('cd-title').innerText = c.name;
    
    const currencyIcon = c.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';
    const currentBal = c.currency === 'stars' ? myStars : myBalance;

    const btn = document.getElementById('btn-open-case');
    if (currentBal < c.price) {
        btn.classList.add('opacity-50', 'pointer-events-none');
        const notEnoughKey = c.currency === 'stars' ? 'not_enough_stars' : 'not_enough_donuts';
        const txt = (i18n[currentLang] && i18n[currentLang][notEnoughKey]) ? i18n[currentLang][notEnoughKey] : 'Недостаточно средств!';
        btn.innerHTML = `<span>${txt}</span>`;
    } else {
        btn.classList.remove('opacity-50', 'pointer-events-none');
        const txt = (i18n[currentLang] && i18n[currentLang].open_for) ? i18n[currentLang].open_for : 'Открыть за';
        btn.innerHTML = `<span data-i18n="open_for">${txt}</span> <span class="flex items-center gap-1 text-yellow-300">${c.price} <img src="${currencyIcon}" class="w-5 h-5 object-contain"></span>`;
        btn.onclick = () => buyAndOpenCase(caseId);
    }
    
    const itemsContainer = document.getElementById('cd-items');
    itemsContainer.innerHTML = '';
    const sortedItems = [...c.items].sort((a, b) => (b.chance || 0) - (a.chance || 0));
    
    sortedItems.forEach(item => {
        const info = getItemInfoForCase(item);
        const chance = item.chance || 0;
        let colorClass = chance <= 5 ? "text-yellow-400" : (chance <= 15 ? "text-purple-400" : "text-blue-400");
        
        const row = document.createElement('div');
        row.className = "flex items-center justify-between bg-black/40 border border-white/5 rounded-xl p-2.5";
        row.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center p-1">
                    <img src="${info.photo}" class="w-full h-full object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/32'">
                </div>
                <span class="font-bold text-sm ${colorClass}">${info.name}</span>
            </div>
        `;
        itemsContainer.appendChild(row);
    });
    
    openModal('case-details-modal');
}

async function buyAndOpenCase(caseId) {
    if (isOpeningCase) return;
    const c = casesConfig[caseId];
    
    const currentBal = c.currency === 'stars' ? myStars : myBalance;
    if (currentBal < c.price) {
        if(tg) tg.showAlert('Недостаточно средств!');
        return;
    }
    
    isOpeningCase = true;
    const btn = document.getElementById('btn-open-case');
    const originalBtnHTML = btn.innerHTML;
    btn.classList.add('btn-disabled');
    const txt = i18n[currentLang]?.case_opening || 'Открываем...';
    btn.innerHTML = `<span>${txt}</span>`;
    vibrate('heavy');

    try {
        const res = await fetch('/api/cases/open', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ tg_id: tgUser.id, gift_id: parseInt(caseId) })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            if (data.balance !== undefined) myBalance = data.balance;
            if (data.stars !== undefined) myStars = data.stars;
            myGifts = data.user_gifts;
            if (typeof updateUI === 'function') updateUI();
            
            closeModal('case-details-modal');
            playCaseAnimation(c, data.win_item);
        } else {
            if(tg) tg.showAlert(data.detail || 'Error');
        }
    } catch (e) {
        console.error("Open case error:", e);
        if(tg) tg.showAlert(i18n[currentLang]?.err_conn || 'Connection error');
    } finally {
        isOpeningCase = false;
        btn.classList.remove('btn-disabled');
        btn.innerHTML = originalBtnHTML;
    }
}

function playCaseAnimation(caseConfig, winItem) {
    const modal = document.getElementById('case-animation-modal');
    const wrapper = document.getElementById('cam-case-wrapper');
    const flash = document.getElementById('cam-flash');
    const resultBox = document.getElementById('cam-result');
    
    wrapper.style.display = 'flex';
    resultBox.style.display = 'none';
    resultBox.classList.remove('scale-up-active');
    flash.style.opacity = '0';
    flash.style.transitionDuration = '0.3s';
    document.getElementById('cam-case-img').src = getImgSrc(caseConfig.photo);
    
    const info = getItemInfoForCase(winItem);
    document.getElementById('cam-item-img').src = info.photo;
    document.getElementById('cam-item-name').innerText = info.name;
    
    modal.classList.remove('hidden');
    wrapper.classList.add('animate-case-shake');
    vibrate('medium');
    let shakeInterval = setInterval(() => vibrate('light'), 200);

    setTimeout(() => {
        clearInterval(shakeInterval);
        vibrate('heavy');
        flash.style.opacity = '1';
        setTimeout(() => {
            wrapper.classList.remove('animate-case-shake');
            wrapper.style.display = 'none';
            resultBox.style.display = 'flex';
            resultBox.classList.add('scale-up-active');
            flash.style.transitionDuration = '1s';
            flash.style.opacity = '0';
        }, 150);
    }, 1500);
}

function closeCaseAnimation() {
    vibrate('light');
    document.getElementById('case-animation-modal').classList.add('hidden');
    if (!document.getElementById('games-cases-list-view').classList.contains('hidden')) renderCasesGrid();
}


// =================== РАКЕТА (CRASH) ===================
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
    vibrate('light');
    document.getElementById('games-main-view').classList.add('hidden');
    document.getElementById('games-rocket-view').classList.remove('hidden');
    
    rocketState = 'idle';
    clearTimeout(rocketTimeout);
    updateRocketUI();
}

function closeRocketGame() {
    if (rocketState === 'starting' || rocketState === 'flying') {
        if(tg) tg.showAlert(i18n[currentLang]?.rocket_cant_close || 'Нельзя закрыть во время полета!');
        return;
    }
    vibrate('light');
    document.getElementById('games-rocket-view').classList.add('hidden');
    document.getElementById('games-main-view').classList.remove('hidden');
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
    vibrate('light');
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
    vibrate('light');
    if (rocketState === 'idle') {
        const input = document.getElementById('rocket-bet-input');
        rocketBetAmount = parseInt(input?.value || 0) || 0;
        
        const min = rocketConfigLocal?.min_bet || 50;
        const max = rocketConfigLocal?.max_bet || 10000;
        const currentBal = rocketConfigLocal?.currency === 'stars' ? myStars : myBalance;
        
        if (rocketBetAmount < min || rocketBetAmount > max) {
            if(tg) tg.showAlert((i18n[currentLang]?.rocket_err_limits || 'Неверная сумма') + ` (${min} - ${max})`);
            return;
        }
        if (rocketBetAmount > currentBal) {
            if(tg) tg.showAlert('Недостаточно средств!');
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
                if(tg) tg.showAlert(data.detail || 'Error');
                resetRocketToIdle();
            }
        } catch (e) {
            if(tg) tg.showAlert(i18n[currentLang]?.err_conn || 'Connection error');
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
    vibrate('medium');

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
    vibrate('heavy');
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
    vibrate('medium');

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
            if(tg) tg.showAlert(data.detail || 'Error');
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

window.openGamesCases = openGamesCases;
window.closeGamesCases = closeGamesCases;
window.renderCasesGrid = renderCasesGrid;
window.openCaseDetails = openCaseDetails;
window.buyAndOpenCase = buyAndOpenCase;
window.closeCaseAnimation = closeCaseAnimation;
window.openRocketGame = openRocketGame;
window.closeRocketGame = closeRocketGame;
window.setRocketBet = setRocketBet;
window.handleRocketAction = handleRocketAction;