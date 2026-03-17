// =====================================================
// app.js — Точка входа и глобальные функции
// =====================================================

// Глобальная переменная для демо-режима
let isDemoMode = false;

// Локальный рандомизатор для Демо режима (использует шансы из config)
function simulateRoll(items) {
    let totalChance = items.reduce((sum, item) => sum + (item.chance || 0), 0);
    if (totalChance <= 0) totalChance = 100;
    
    let r = Math.random() * totalChance;
    let cumulative = 0;
    
    for (let i = 0; i < items.length; i++) {
        let chance = items[i].chance || 0;
        if (chance <= 0) continue;
        
        cumulative += chance;
        if (r <= cumulative) {
            return { index: i, item: items[i] };
        }
    }
    return { index: 0, item: items[0] };
}

// Функция переключения Демо-режима
function toggleDemoMode() {
    isDemoMode = document.getElementById('demo-toggle').checked;
    vibrate('light');
    
    // Обновляем UI рулетки если мы там находимся
    if (typeof fetchRouletteInfo === 'function' && !document.getElementById('page-roulette').classList.contains('hidden-tab')) {
        fetchRouletteInfo();
    }
    
    // Обновляем UI кейса если он открыт
    if (typeof openCaseDetails === 'function' && currentOpenedCaseId) {
        if (!document.getElementById('case-details-modal').classList.contains('hidden')) {
            openCaseDetails(currentOpenedCaseId);
        }
    }
}

async function initApp() {
    const savedLang = localStorage.getItem('appLang') || (tgUser?.language_code === 'en' ? 'en' : 'ru');
    setLang(savedLang);
    try {
        const res = await fetch('/api/init', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({
                tg_id:      tgUser.id,
                username:   tgUser.username   || '',
                first_name: tgUser.first_name || '',
                photo_url:  tgUser.photo_url  || ''
            })
        });
        const data = await res.json();
        baseGifts    = data.config.base_gifts;
        mainGifts    = data.config.main_gifts;
        botUsername  = data.config.bot_username;
        if (data.config.roulette) rouletteConfig = data.config.roulette;
        if (data.config.cases) casesConfig = data.config.cases;
        
        myGifts      = data.user_gifts;
        myBalance    = data.balance;
        
        if (rouletteConfig?.items && typeof renderRouletteWheel === 'function') renderRouletteWheel();
        updateUI();
    } catch(e) {
        console.error('initApp error:', e);
        updateUI();
    } finally {
        hideAppLoader();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const pb = document.getElementById('loader-progress');
        if (pb && pb.style.width === '10%') pb.style.width = '60%';
    }, 100);

    if (!tg) {
        console.error('Telegram WebApp не найден');
        hideAppLoader();
        return;
    }

    tg.expand();
    if (tg.requestFullscreen) tg.requestFullscreen();
    if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
    
    tg.setHeaderColor('#0f172a');
    tg.setBackgroundColor('#020617');

    document.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('copy',        e => e.preventDefault());
    document.addEventListener('cut',         e => e.preventDefault());
    document.addEventListener('selectstart', e => e.preventDefault());
    document.addEventListener('dragstart',   e => e.preventDefault());

    initApp();
});

// Экспортируем в window для доступа из HTML и других скриптов
window.isDemoMode = isDemoMode;
window.toggleDemoMode = toggleDemoMode;
window.simulateRoll = simulateRoll;