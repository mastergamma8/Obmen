// =====================================================
// app.js — Точка входа
// =====================================================

// ── Экран техобслуживания ─────────────────────────────────────────────────────

async function checkMaintenance() {
    try {
        const res = await fetch('/api/features', {
            headers: getApiHeaders()   // отправляем x-tg-data
        });
        if (!res.ok) return false;
        const data = await res.json();
        if (data.maintenance_mode) {
            showMaintenanceScreen();
            return true;
        }
        return false;
    } catch (e) {
        return false;
    }
}

function showMaintenanceScreen() {
    const screen = document.getElementById('maintenance-screen');
    if (screen) {
        screen.classList.remove('hidden');
        screen.style.display = 'flex';
    }
    // Скрываем лоадер
    hideAppLoader();
}

// ── Применение флагов видимости ────────────────────────────────────────────────

function applyFeatureFlags(flags) {
    if (!flags) return;

    // Рулетка — скрываем/показываем кнопку на главной странице
    const rouletteBtn = document.getElementById('main-roulette-btn');
    if (rouletteBtn) {
        rouletteBtn.style.display = flags.roulette === false ? 'none' : '';
    }

    // Ракета — баннер в разделе Игры
    const rocketBanner = document.getElementById('game-banner-rocket');
    if (rocketBanner) {
        rocketBanner.style.display = flags.rocket === false ? 'none' : '';
    }

    // Кейсы — баннер в разделе Игры
    const casesBanner = document.getElementById('game-banner-cases');
    if (casesBanner) {
        casesBanner.style.display = flags.cases === false ? 'none' : '';
    }

    // TG Подарки / Лимитированные подарки — баннер в разделе Игры
    const limitedBanner = document.getElementById('game-banner-limited');
    if (limitedBanner) {
        limitedBanner.style.display = flags.limited_gifts === false ? 'none' : '';
    }

    // PvP Арена — баннер в разделе Игры
    const pvpBanner = document.getElementById('game-banner-pvp');
    if (pvpBanner) {
        pvpBanner.style.display = flags.pvp === false ? 'none' : '';
    }

    // Отдельные кейсы — прячем конкретные карточки после рендера
    // (вызывается снова после renderCasesList)
    applyCaseFlags(flags);
}

function applyCaseFlags(flags) {
    if (!flags) return;
    // Кейсы рендерятся динамически — выбираем по data-атрибуту
    document.querySelectorAll('[data-case-id]').forEach(el => {
        const cid = el.getAttribute('data-case-id');
        const key = `case_${cid}`;
        if (flags[key] === false) {
            el.style.display = 'none';
        } else {
            el.style.display = '';
        }
    });
}

// Экспортируем для вызова из games-cases.js после рендера
window.applyCaseFlags = applyCaseFlags;

async function initApp() {
    const savedLang = localStorage.getItem('appLang') || (tgUser?.language_code === 'en' ? 'en' : 'ru');

    // Проверяем тех. перерыв до любого другого запроса
    const isMaintenance = await checkMaintenance();
    if (isMaintenance) {
        setLang(savedLang);
        return;
    }
    
    try {
        const res = await fetch('/api/init', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({
                username:   tgUser.username   || '',
                first_name: tgUser.first_name || '',
                photo_url:  tgUser.photo_url  || ''
            })
        });
        const data = await res.json();
        baseGifts    = data.config.base_gifts;
        mainGifts    = data.config.main_gifts;
        tgGifts      = data.config.tg_gifts || {};
        window.appConfig = {
    withdraw_fee:              data.config.withdraw_fee,
    donuts_to_stars_rate:      data.config.donuts_to_stars_rate,
    gift_exchange_stars_rate:  data.config.gift_exchange_stars_rate,
};
        botUsername  = data.config.bot_username;
        if (data.config.roulette) rouletteConfig = data.config.roulette;
        if (data.config.cases) casesConfig = data.config.cases;
        if (data.config.rocket) rocketConfigLocal = data.config.rocket; 
        if (data.config.free_case) freeCaseConfig = data.config.free_case;
        
        myGifts      = data.user_gifts;
        myBalance    = data.balance;
        myStars      = data.stars || 0;

        // Загружаем настройки с сервера — они имеют приоритет над localStorage
        if (data.user_settings) {
            localStorage.setItem('isAnonymous',  data.user_settings.is_anonymous  ? 'true' : 'false');
            localStorage.setItem('hideUsername', data.user_settings.hide_username ? 'true' : 'false');
        }

        // Ещё раз проверяем тех. перерыв из /init (на случай гонки)
        if (data.maintenance_mode) {
            showMaintenanceScreen();
            return;
        }

        // Применяем флаги видимости разделов
        if (data.feature_flags) {
            window._featureFlags = data.feature_flags;
            applyFeatureFlags(data.feature_flags);
        }
        
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

// ─── Настройки пользователя ───────────────────────────────────────────────────

const USER_SETTINGS = ['hideUsername', 'isAnonymous'];

function openSettingsModal() {
    syncSettingToggles();
    openModal('settings-modal');
}

function syncSettingToggles() {
    USER_SETTINGS.forEach(key => {
        const isOn   = localStorage.getItem(key) === 'true';
        const knobId = key === 'hideUsername' ? 'knob-hide-username' : 'knob-anonymity';
        const btnId  = key === 'hideUsername' ? 'toggle-hide-username' : 'toggle-anonymity';
        const knob   = document.getElementById(knobId);
        const btn    = document.getElementById(btnId);
        if (!knob || !btn) return;
        if (isOn) {
            btn.classList.remove('bg-white/10');
            btn.classList.add('bg-blue-500');
            knob.style.transform = 'translateX(24px)';
        } else {
            btn.classList.add('bg-white/10');
            btn.classList.remove('bg-blue-500');
            knob.style.transform = 'translateX(0px)';
        }
    });
}

function toggleUserSetting(key) {
    vibrate('light');
    const current = localStorage.getItem(key) === 'true';
    localStorage.setItem(key, (!current).toString());
    syncSettingToggles();

    // Сохраняем на сервер — чтобы настройки видели все (особенно анонимность)
    const isAnonymous  = localStorage.getItem('isAnonymous')  === 'true';
    const hideUsername = localStorage.getItem('hideUsername') === 'true';
    fetch('/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Tg-Data': tg?.initData || '',
        },
        body: JSON.stringify({ is_anonymous: isAnonymous, hide_username: hideUsername }),
    }).catch(err => console.warn('Settings save failed:', err));

    // Обновляем профиль и лидерборд
    if (typeof renderProfile   === 'function') renderProfile();
    if (typeof loadLeaderboard === 'function') {
        const lb = document.getElementById('page-leaderboard');
        if (lb && !lb.classList.contains('hidden-tab')) loadLeaderboard();
    }
}

window.openSettingsModal  = openSettingsModal;
window.syncSettingToggles = syncSettingToggles;
window.toggleUserSetting  = toggleUserSetting;

// ─── Поддержка: открыть бот @SpaceDonutSupportBot ────────────────────────────
function openSupportBot() {
    try {
        const tg = window.Telegram && window.Telegram.WebApp;
        if (tg && tg.openTelegramLink) {
            tg.openTelegramLink('https://t.me/SpaceDonutSupportBot');
        } else {
            window.open('https://t.me/SpaceDonutSupportBot', '_blank');
        }
    } catch (e) {
        window.open('https://t.me/SpaceDonutSupportBot', '_blank');
    }
}

// ПУЛЕНЕПРОБИВАЕМЫЙ ЗАПУСК:
if (window.partialsAreLoaded) {
    startApplication();
} else {
    document.addEventListener('partialsLoaded', startApplication);
}
