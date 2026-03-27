// =====================================================
// app.js — Точка входа
// =====================================================

async function initApp() {
    const savedLang = localStorage.getItem('appLang') || (tgUser?.language_code === 'en' ? 'en' : 'ru');
    
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
        if (data.config.rocket) rocketConfigLocal = data.config.rocket; 
        if (data.config.free_case) freeCaseConfig = data.config.free_case;
        
        myGifts      = data.user_gifts;
        myBalance    = data.balance;
        myStars      = data.stars || 0; // <-- Получаем звезды
        
        // ВАЖНО: Устанавливаем язык только после загрузки DOM и конфигов!
        setLang(savedLang); 
        
        if (rouletteConfig?.items && typeof renderRouletteWheel === 'function') renderRouletteWheel();
        updateUI();
    } catch(e) {
        console.error('initApp error:', e);
        setLang(savedLang);
        updateUI();
    } finally {
        hideAppLoader();
    }
}

function startApplication() {
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
}

// ПУЛЕНЕПРОБИВАЕМЫЙ ЗАПУСК:
if (window.partialsAreLoaded) {
    startApplication();
} else {
    document.addEventListener('partialsLoaded', startApplication);
}