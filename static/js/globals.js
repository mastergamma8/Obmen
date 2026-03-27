// =====================================================
// globals.js — Глобальное состояние и утилиты
// =====================================================

const ALL_TABS = ['main', 'leaderboard', 'games', 'earn', 'profile', 'roulette'];

// Глобальное состояние
let baseGifts = {};
let mainGifts = {};
let rouletteConfig = {};
let casesConfig = {}; 
let myGifts = {};
let myBalance = 0;
let myStars = 0; // <-- НОВЫЙ БАЛАНС ЗВЕЗД
let freeCaseConfig = null;
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

    const stEl = document.getElementById('stars-amount');
    if (stEl) stEl.innerText = myStars;

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

// =====================================================
// ЛОГИКА ПОПОЛНЕНИЯ ЗВЕЗД
// =====================================================

function openTopupModal() {
    vibrate('medium');
    document.getElementById('custom-topup-amount').value = '';
    openModal('topup-stars-modal');
}

function setTopupAmount(amount) {
    vibrate('light');
    document.getElementById('custom-topup-amount').value = amount;
}

function validateTopupAmount(input) {
    if (input.value < 0) input.value = 0;
    if (input.value > 100000) input.value = 100000;
}

async function buyStars() {
    const input = document.getElementById('custom-topup-amount');
    const amount = parseInt(input.value);
    
    if (!amount || amount <= 0) {
        tg?.showAlert(i18n[currentLang]?.err_invalid_amount || 'Неверная сумма');
        return;
    }

    const btn = document.getElementById('btn-buy-stars');
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = '⏳...';

    try {
        const response = await fetch('/api/topup/stars', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({ tg_id: tgUser.id, stars_amount: amount })
        });
        
        const result = await response.json();
        
        if (result.status === 'ok') {
            // Открываем платежное окно Telegram
            if (window.Telegram?.WebApp?.openInvoice) {
                window.Telegram.WebApp.openInvoice(result.invoice_url, (payment_status) => {
                    if (payment_status === 'paid') {
                        closeModal('topup-stars-modal');
                        myStars += amount; // Локальное зачисление для мгновенного отображения
                        updateUI();
                        tg.showAlert(i18n[currentLang]?.topup_success || 'Звезды успешно зачислены!');
                    } else if (payment_status === 'cancelled') {
                        console.log('Оплата отменена пользователем');
                    } else {
                        tg.showAlert('Ошибка оплаты (failed)');
                    }
                });
            } else {
                // Если клиент не поддерживает openInvoice напрямую
                tg.openTelegramLink(result.invoice_url);
            }
        } else {
            tg.showAlert(result.detail || 'Ошибка создания инвойса');
        }
    } catch (e) {
        tg.showAlert(i18n[currentLang]?.err_conn || 'Ошибка соединения');
    } finally {
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

window.openModal = openModal;
window.closeModal = closeModal;
window.openTopupModal = openTopupModal;
window.setTopupAmount = setTopupAmount;
window.validateTopupAmount = validateTopupAmount;
window.buyStars = buyStars;