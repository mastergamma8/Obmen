// =====================================================
// games-cases.js — Логика Игры "Кейсы"
// =====================================================

let currentOpenedCaseId = null;
let isOpeningCase = false;

function openGamesCases() {
    // Используем универсальный роутер из games.js
    if (typeof showGameView === 'function') {
        showGameView('games-cases-list-view');
    } else {
        // Фолбэк, если games.js не загрузился
        if (typeof vibrate === 'function') vibrate('light');
        document.getElementById('games-main-view').classList.add('hidden');
        document.getElementById('games-cases-list-view').classList.remove('hidden');
    }
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
    if (typeof vibrate === 'function') vibrate('light');
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
    
    if (typeof openModal === 'function') openModal('case-details-modal');
}

async function buyAndOpenCase(caseId) {
    if (isOpeningCase) return;
    const c = casesConfig[caseId];
    
    const currentBal = c.currency === 'stars' ? myStars : myBalance;
    if (currentBal < c.price) {
        if(typeof tg !== 'undefined' && tg) tg.showAlert('Недостаточно средств!');
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
            body: JSON.stringify({ tg_id: tgUser.id, gift_id: parseInt(caseId) })
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
            if(typeof tg !== 'undefined' && tg) tg.showAlert(data.detail || 'Error');
        }
    } catch (e) {
        console.error("Open case error:", e);
        if(typeof tg !== 'undefined' && tg) tg.showAlert(i18n[currentLang]?.err_conn || 'Connection error');
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
    
    if (typeof vibrate === 'function') vibrate('medium');
    let shakeInterval = setInterval(() => {
        if (typeof vibrate === 'function') vibrate('light');
    }, 200);

    setTimeout(() => {
        clearInterval(shakeInterval);
        if (typeof vibrate === 'function') vibrate('heavy');
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
    if (typeof vibrate === 'function') vibrate('light');
    document.getElementById('case-animation-modal').classList.add('hidden');
    if (!document.getElementById('games-cases-list-view').classList.contains('hidden')) renderCasesGrid();
}

window.openGamesCases = openGamesCases;
window.closeGamesCases = closeGamesCases;
window.renderCasesGrid = renderCasesGrid;
window.openCaseDetails = openCaseDetails;
window.buyAndOpenCase = buyAndOpenCase;
window.closeCaseAnimation = closeCaseAnimation;