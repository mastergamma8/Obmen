// =====================================================
// games.js — Логика Игр и Кейсов
// =====================================================

let currentOpenedCaseId = null;
let isOpeningCase = false;

// Открыть список кейсов
function openGamesCases() {
    vibrate('light');
    document.getElementById('games-main-view').classList.add('hidden');
    document.getElementById('games-cases-list-view').classList.remove('hidden');
    renderCasesGrid();
}

// Вернуться на главную страницу Игр
function closeGamesCases() {
    vibrate('light');
    document.getElementById('games-cases-list-view').classList.add('hidden');
    document.getElementById('games-main-view').classList.remove('hidden');
}

// Рендеринг сетки 2 в ряд с улучшенным дизайном
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
        
        const card = document.createElement('div');
        // Улучшенная карточка кейса с градиентами, group-hover эффектами и бОльшими тенями
        card.className = "glass rounded-3xl p-4 flex flex-col items-center justify-between text-center cursor-pointer active:scale-95 transition-transform border border-indigo-400/30 shadow-[0_10px_20px_rgba(0,0,0,0.4)] hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] bg-gradient-to-b from-indigo-500/20 to-black/40 relative overflow-hidden group";
        card.onclick = () => openCaseDetails(id);
        
        card.innerHTML = `
            <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-20 pointer-events-none"></div>
            <!-- Свечение сверху, которое загорается ярче при наведении -->
            <div class="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-24 bg-indigo-500/30 blur-[30px] rounded-full pointer-events-none group-hover:bg-indigo-400/40 transition-colors"></div>
            
            <!-- Увеличенная картинка кейса (с w-16 h-16 на w-24 h-24) с эффектом подскока при наведении -->
            <div class="w-24 h-24 mb-3 relative z-10">
                <img src="${photoUrl}" class="w-full h-full object-contain drop-shadow-[0_10px_15px_rgba(0,0,0,0.6)] group-hover:scale-110 group-hover:-translate-y-1 transition-all duration-300" onerror="this.src='https://via.placeholder.com/96?text=📦'">
            </div>
            
            <h4 class="text-white font-extrabold text-sm mb-3 glow-text w-full truncate relative z-10 tracking-wide">${c.name}</h4>
            
            <!-- Улучшенная плашка с ценой -->
            <div class="bg-black/60 rounded-xl px-3 py-1.5 flex items-center justify-center gap-1.5 border border-white/10 relative z-10 w-full backdrop-blur-sm shadow-inner">
                <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-indigo-300 font-black text-sm">${c.price}</span>
                <img src="/gifts/dount.png" class="w-4 h-4 object-contain drop-shadow-[0_0_5px_rgba(59,130,246,0.6)]" onerror="this.src='https://via.placeholder.com/16?text=🍩'">
            </div>
        `;
        grid.appendChild(card);
    });
}

// Получить визуальное представление предмета (иконка и название)
function getItemInfoForCase(item) {
    if (item.type === 'donuts') {
        return {
            name: `${item.amount} 🍩`,
            photo: '/gifts/dount.png'
        };
    } else if (item.type === 'gift') {
        // --- ИСПРАВЛЕНИЕ: Ищем подарок в ОБОИХ словарях ---
        const gift = mainGifts[item.gift_id] || baseGifts[item.gift_id];
        if (gift) {
            return {
                name: gift.name,
                photo: getImgSrc(gift.photo)
            };
        }
    }
    return { name: "???", photo: "https://via.placeholder.com/32" };
}

// Открытие модалки с описанием кейса
function openCaseDetails(caseId) {
    vibrate('light');
    const c = casesConfig[caseId];
    if (!c) return;
    
    currentOpenedCaseId = caseId;
    
    document.getElementById('cd-photo').src = getImgSrc(c.photo);
    document.getElementById('cd-title').innerText = c.name;
    
    // Кнопка
    const btn = document.getElementById('btn-open-case');
    if (myBalance < c.price) {
        btn.classList.add('opacity-50', 'pointer-events-none');
        const txt = (i18n[currentLang] && i18n[currentLang].not_enough_donuts) ? i18n[currentLang].not_enough_donuts : 'Недостаточно пончиков!';
        btn.innerHTML = `<span data-i18n="not_enough_donuts">${txt}</span>`;
    } else {
        btn.classList.remove('opacity-50', 'pointer-events-none');
        const txt = (i18n[currentLang] && i18n[currentLang].open_for) ? i18n[currentLang].open_for : 'Открыть за';
        btn.innerHTML = `<span data-i18n="open_for">${txt}</span> <span class="flex items-center gap-1 text-yellow-300">${c.price} <img src="/gifts/dount.png" class="w-5 h-5 object-contain"></span>`;
        btn.onclick = () => buyAndOpenCase(caseId);
    }
    
    // Список предметов
    const itemsContainer = document.getElementById('cd-items');
    itemsContainer.innerHTML = '';
    
    // Сортировка предметов по шансу (убывание)
    const sortedItems = [...c.items].sort((a, b) => (b.chance || 0) - (a.chance || 0));
    
    sortedItems.forEach(item => {
        const info = getItemInfoForCase(item);
        const chance = item.chance || 0;
        
        let colorClass = "text-white";
        if(chance <= 5) colorClass = "text-yellow-400"; // Редкий
        else if(chance <= 15) colorClass = "text-purple-400"; // Эпик
        else if(chance <= 30) colorClass = "text-blue-400"; // Синий
        
        const row = document.createElement('div');
        row.className = "flex items-center justify-between bg-black/40 border border-white/5 rounded-xl p-2.5";
        row.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center p-1">
                    <img src="${info.photo}" class="w-full h-full object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/32'">
                </div>
                <span class="font-bold text-sm ${colorClass}">${info.name}</span>
            </div>
            <span class="text-xs font-bold text-white/40 bg-white/10 px-2 py-1 rounded-md">${chance}%</span>
        `;
        itemsContainer.appendChild(row);
    });
    
    openModal('case-details-modal');
}

// Покупка и открытие
async function buyAndOpenCase(caseId) {
    if (isOpeningCase) return;
    
    const c = casesConfig[caseId];
    if (myBalance < c.price) {
        if(tg) tg.showAlert((i18n[currentLang] && i18n[currentLang].not_enough_donuts) ? i18n[currentLang].not_enough_donuts : 'Недостаточно пончиков!');
        return;
    }
    
    isOpeningCase = true;
    const btn = document.getElementById('btn-open-case');
    const originalBtnHTML = btn.innerHTML;
    btn.classList.add('btn-disabled');
    const txt = (i18n[currentLang] && i18n[currentLang].case_opening) ? i18n[currentLang].case_opening : 'Открываем...';
    btn.innerHTML = `<span data-i18n="case_opening">${txt}</span>`;
    vibrate('heavy');

    try {
        const res = await fetch('/api/cases/open', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ tg_id: tgUser.id, gift_id: parseInt(caseId) })
        });
        
        const data = await res.json();
        
        if (data.status === 'ok') {
            myBalance = data.balance;
            myGifts = data.user_gifts;
            updateUI();
            
            closeModal('case-details-modal');
            playCaseAnimation(c, data.win_item);
        } else {
            if(tg) tg.showAlert(data.detail || 'Error');
        }
    } catch (e) {
        console.error("Open case error:", e);
        if(tg) tg.showAlert((i18n[currentLang] && i18n[currentLang].err_conn) ? i18n[currentLang].err_conn : 'Connection error');
    } finally {
        isOpeningCase = false;
        btn.classList.remove('btn-disabled');
        btn.innerHTML = originalBtnHTML;
    }
}

// Проигрывание анимации
function playCaseAnimation(caseConfig, winItem) {
    const modal = document.getElementById('case-animation-modal');
    const caseImg = document.getElementById('cam-case-img');
    const wrapper = document.getElementById('cam-case-wrapper');
    const flash = document.getElementById('cam-flash');
    const resultBox = document.getElementById('cam-result');
    const itemImg = document.getElementById('cam-item-img');
    const itemName = document.getElementById('cam-item-name');
    
    // Сброс состояния
    wrapper.style.display = 'flex';
    resultBox.style.display = 'none';
    resultBox.classList.remove('scale-up-active');
    flash.style.opacity = '0';
    flash.style.transitionDuration = '0.3s'; // Возвращаем исходную скорость для вспышки
    caseImg.src = getImgSrc(caseConfig.photo);
    
    // Подготовка предмета (функция корректно вытащит картинку и имя для обоих типов подарков)
    const info = getItemInfoForCase(winItem);
    itemImg.src = info.photo;
    itemName.innerText = info.name;
    
    modal.classList.remove('hidden');
    
    // Старт анимации тряски
    wrapper.classList.add('animate-case-shake');
    vibrate('medium');
    
    let shakeInterval = setInterval(() => vibrate('light'), 200);

    // Через 1.5 секунды - вспышка и результат
    setTimeout(() => {
        clearInterval(shakeInterval);
        vibrate('heavy');
        
        // Вспышка
        flash.style.opacity = '1';
        
        setTimeout(() => {
            wrapper.classList.remove('animate-case-shake');
            wrapper.style.display = 'none'; // Прячем кейс
            resultBox.style.display = 'flex'; // Показываем результат
            resultBox.classList.add('scale-up-active'); // Анимация увеличения
            
            flash.style.transitionDuration = '1s';
            flash.style.opacity = '0'; // Затухание вспышки
        }, 150);
        
    }, 1500);
}

// Закрыть окно результата
function closeCaseAnimation() {
    vibrate('light');
    document.getElementById('case-animation-modal').classList.add('hidden');
    // Если нужно, можно вернуть пользователя к списку кейсов
    if (document.getElementById('games-cases-list-view').classList.contains('hidden') === false) {
        renderCasesGrid(); // Обновляем грид, вдруг цена теперь красная
    }
}

window.openGamesCases = openGamesCases;
window.closeGamesCases = closeGamesCases;
window.renderCasesGrid = renderCasesGrid;
window.openCaseDetails = openCaseDetails;
window.buyAndOpenCase = buyAndOpenCase;
window.closeCaseAnimation = closeCaseAnimation;