// =====================================================
// globals.js — Глобальное состояние и утилиты
// =====================================================

// ДОБАВЛЕНА НОВАЯ ВКЛАДКА 'games'
const ALL_TABS = ['main', 'leaderboard', 'games', 'earn', 'profile', 'roulette'];

// Глобальное состояние
let baseGifts = {};
let mainGifts = {};
let rouletteConfig = {};
let casesConfig = {}; // Добавлена конфигурация кейсов
let myGifts = {};
let myBalance = 0;
let botUsername = '';
let openTasksState = {};
let rouletteSpinning = false;
let rouletteCurrentRotation = 0;
let currentSortMethod = 'value_desc';
let currentLang = '';

// Telegram SDK
const tg = window.Telegram?.WebApp;
window.tg = tg;

const tgUser = (tg?.initDataUnsafe?.user) ? tg.initDataUnsafe.user : {
    id: 123456789, first_name: 'Тест', username: 'test_user', photo_url: ''
};

function vibrate(style = 'light') {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred(style);
}

function getImgSrc(path) {
    if (!path) return 'https://via.placeholder.com/64';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    return path.startsWith('/') ? path : '/' + path;
}

function getApiHeaders() {
    return {
        'Content-Type': 'application/json',
        'x-tg-data': tg?.initData || ''
    };
}

function hideAppLoader() {
    const pb = document.getElementById('loader-progress');
    if (pb) pb.style.width = '100%';
    setTimeout(() => {
        const loader = document.getElementById('app-loader');
        if (loader) {
            loader.classList.add('opacity-0', 'pointer-events-none');
            setTimeout(() => loader.style.display = 'none', 500);
        }
    }, 500);
}

function updateUI() {
    const el = document.getElementById('balance-amount');
    if (el) el.innerText = myBalance;
    if (typeof renderMainPage === 'function') renderMainPage();
    if (typeof renderProfile === 'function') renderProfile();
}

function openModal(id) {
    vibrate('light');
    document.getElementById(id)?.classList.remove('hidden');
}

function closeModal(id) {
    vibrate('light');
    document.getElementById(id)?.classList.add('hidden');
}

window.openModal = openModal;
window.closeModal = closeModal;