// =====================================================
// SPACE DONUT — app.js
// =====================================================
//
// КАК ДОБАВИТЬ НОВУЮ СТРАНИЦУ:
// 1. В index.html добавь блок:
//    <div id="page-MYPAGE" class="px-5 pb-5 hidden-tab fade-in"> ... </div>
//
// 2. В навигации (nav) добавь кнопку:
//    <button onclick="switchTab('MYPAGE')" id="nav-MYPAGE" class="nav-item ..."> ... </button>
//
// 3. Здесь, в массиве ALL_TABS, добавь 'MYPAGE':
//    const ALL_TABS = ['main','leaderboard','earn','profile','roulette','MYPAGE'];
//
// 4. Если страница требует загрузки данных при открытии — добавь обработчик
//    в функцию onTabSwitch() ниже (ищи комментарий "ХУКИ ВКЛАДОК").
//
// =====================================================

// Все id страниц — добавляй сюда новые
const ALL_TABS = ['main', 'leaderboard', 'earn', 'profile', 'roulette'];

// =====================================================
// ИНИЦИАЛИЗАЦИЯ (ждём загрузку DOM, затем Telegram SDK)
// =====================================================
document.addEventListener('DOMContentLoaded', () => {

    // Анимация прогресс-бара до 60% пока грузимся
    setTimeout(() => {
        const pb = document.getElementById('loader-progress');
        if (pb && pb.style.width === '10%') pb.style.width = '60%';
    }, 100);

    // Ждём Telegram WebApp SDK
    const tg = window.Telegram?.WebApp;
    if (!tg) {
        console.error('Telegram WebApp не найден');
        hideAppLoader();
        return;
    }

    // Делаем tg глобальным объектом, чтобы inline-обработчики (например в локализации) могли его вызывать
    window.tg = tg;

    tg.expand();
    if (tg.requestFullscreen) tg.requestFullscreen();
    
    // ВАЖНО: Отключаем вертикальные свайпы для закрытия мини-приложения (доступно в новых версиях API)
    if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
    
    tg.setHeaderColor('#0f172a');
    tg.setBackgroundColor('#020617');

    // ===== ЗАЩИТА ОТ КОПИРОВАНИЯ =====
    document.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('copy',        e => e.preventDefault());
    document.addEventListener('cut',         e => e.preventDefault());
    document.addEventListener('selectstart', e => e.preventDefault());
    document.addEventListener('dragstart',   e => e.preventDefault());

    // ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
    function vibrate(style = 'light') {
        if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred(style);
    }

    function getImgSrc(path) {
        if (!path) return 'https://via.placeholder.com/64';
        if (path.startsWith('http://') || path.startsWith('https://')) return path;
        return path.startsWith('/') ? path : '/' + path;
    }

    function getApiHeaders() {
        return {
            'Content-Type': 'application/json',
            'x-tg-data': tg.initData || ''
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

    // ===== ДАННЫЕ ПОЛЬЗОВАТЕЛЯ =====
    const tgUser = (tg.initDataUnsafe?.user) ? tg.initDataUnsafe.user : {
        id: 123456789, first_name: 'Тест', username: 'test_user', photo_url: ''
    };

    // ===== ГЛОБАЛЬНОЕ СОСТОЯНИЕ =====
    let baseGifts    = {};
    let mainGifts    = {};
    let rouletteConfig = {};
    let myGifts      = {};
    let myBalance    = 0;
    let botUsername  = '';
    let openTasksState = {};
    let rouletteSpinning = false;
    let rouletteCurrentRotation = 0;
    let currentSortMethod = 'value_desc';

    // =====================================================
    // НАВИГАЦИЯ
    // =====================================================
    function switchTab(tabId) {
        vibrate('light');
        ALL_TABS.forEach(id => {
            const page = document.getElementById(`page-${id}`);
            const nav  = document.getElementById(`nav-${id}`);
            if (page) page.classList.add('hidden-tab');
            if (nav)  nav.classList.remove('active');
        });
        const activePage = document.getElementById(`page-${tabId}`);
        const activeNav  = document.getElementById(`nav-${tabId}`);
        if (activePage) activePage.classList.remove('hidden-tab');
        if (activeNav)  activeNav.classList.add('active');

        onTabSwitch(tabId);
    }

    // =====================================================
    // ХУКИ ВКЛАДОК — что загружать при открытии страницы
    // Добавь сюда свою вкладку если нужно:
    // if (tabId === 'MYPAGE') loadMyPageData();
    // =====================================================
    function onTabSwitch(tabId) {
        if (tabId === 'leaderboard') loadLeaderboard();
        if (tabId === 'earn')        loadEarnData();
        if (tabId === 'roulette')    fetchRouletteInfo();
    }

    // Делаем switchTab глобальной для onclick в HTML
    window.switchTab = switchTab;

    function switchEarnSubtab(subTabId) {
        vibrate('light');
        ['referrals', 'tasks'].forEach(id => {
            document.getElementById(`earn-${id}`)?.classList.add('hidden-tab');
            document.getElementById(`subtab-${id}`)?.classList.remove('active');
        });
        document.getElementById(`earn-${subTabId}`)?.classList.remove('hidden-tab');
        document.getElementById(`subtab-${subTabId}`)?.classList.add('active');
    }
    window.switchEarnSubtab = switchEarnSubtab;

    function openModal(id)  { vibrate('light'); document.getElementById(id)?.classList.remove('hidden'); }
    function closeModal(id) { vibrate('light'); document.getElementById(id)?.classList.add('hidden'); }
    window.openModal  = openModal;
    window.closeModal = closeModal;

    // =====================================================
    // ЛОКАЛИЗАЦИЯ (RU / EN)
    // =====================================================
    const i18n = {
        ru: {
            nav_main: 'Главная', nav_top: 'Топ', nav_earn: 'Заработок', nav_profile: 'Профиль',
            roulette_daily: 'Ежедневная Рулетка', roulette_desc: 'Крути и выигрывай призы!',
            avail_gifts: 'Доступные подарки',
            collect_desc: 'Соберите <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> для разблокировки подарков',
            leaderboard: 'Таблица лидеров', earn_title: 'Заработок',
            tab_refs: 'Рефералы', tab_tasks: 'Задания',
            invite_friends: 'Приглашайте друзей',
            ref_desc: 'Вы будете получать <strong class="text-blue-400 glow-text">10%</strong> пончиков с каждого добавленного вашим другом подарка! <br><span class="text-xs opacity-70">(Например: добавили подарок за 4 <img src="/gifts/dount.png" class="w-3 h-3 inline-block align-middle object-contain"> — вы получите 1 <img src="/gifts/dount.png" class="w-3 h-3 inline-block align-middle object-contain"> бонус)</span>',
            btn_invite: 'Пригласить друзей', your_refs: 'Ваши приглашенные',
            tasks_desc: 'Выполняйте задания, чтобы получать больше пончиков <img src="/gifts/dount.png" class="w-4 h-4 inline object-contain">',
            add_gift: '+ Добавить подарок', my_gifts: 'Мои подарки', for_withdraw: 'на вывод',
            wheel_fortune: 'Колесо Фортуны', spin_free: 'Крутить бесплатно',
            loading: 'Загрузка...',
            no_refs: 'У вас пока нет приглашенных друзей.', no_tasks: 'Нет доступных заданий.',
            completed: 'Выполнено', check: 'Проверить', go: 'Перейти',
            available: 'ДОСТУПНО', progress: 'ПРОГРЕСС',
            claim_gift: 'Забрать подарок', close: 'Закрыть',
            withdraw_q: 'Вы хотите вывести этот подарок? Он исчезнет из вашего профиля.',
            btn_withdraw: 'Вывести подарок', cancel: 'Отмена',
            withdraw_success: 'Подарок выведен!',
            withdraw_msg: 'Пожалуйста, напишите любое сообщение <br><span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-green-400 text-lg font-bold cursor-pointer underline decoration-green-400/50 underline-offset-4">@SpaceDonutGifts</span><br> для получения вашего подарка.',
            excellent: 'Отлично', how_to_get: 'Как получить',
            how_to_desc: 'Отправьте NFT-подарок на аккаунт <span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-blue-400 cursor-pointer underline font-bold decoration-blue-400/50 underline-offset-4">@SpaceDonutGifts</span>. После проверки он появится у вас. Подарки автоматически конвертируются в <img src="/gifts/dount.png" class="w-4 h-4 inline-block align-middle object-contain"> для открытия главных подарков!',
            understood: 'Понятно', you: '(Вы)',
            no_gifts_yet: 'У вас пока нет подарков.<br><span class="inline-flex items-center gap-1 mt-1">Копите <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> чтобы получить подарок!</span>',
            click: 'Нажми', win: 'Победа!', take_prize: 'Забрать приз!',
            accumulated: 'Накоплено:', what_gifts_give: 'Какие подарки дают',
            spin_for: 'Крутить за', until_free: 'До бесплатной прокрутки:',
            h: 'ч.', free_24h: 'Раз в 24 часа бесплатно!', ref_copied: 'Реферальная ссылка скопирована!',
            task_done: 'Задание выполнено! Награда начислена.', err_check: 'Ошибка проверки.',
            err_conn: 'Ошибка соединения', err_conn_srv: 'Ошибка соединения с сервером.',
            processing: '⏳ Обработка...', gift_added: 'Подарок успешно добавлен в ваш профиль!',
            withdrawing: '⏳ Выводим...', err_network: 'Ошибка сети. Попробуйте позже.',
            share_text: 'Заходи в Space Donut и забирай крутые подарки! 🎁',
            donuts_text: 'пончиков!',
            search_ph: 'Поиск...', sort_title: 'Сортировка',
            sort_val_desc: 'Сначала дорогие', sort_val_asc: 'Сначала дешевые',
            sort_name_asc: 'По имени (А-Я)', sort_name_desc: 'По имени (Я-А)', not_found: 'Ничего не найдено'
        },
        en: {
            nav_main: 'Main', nav_top: 'Top', nav_earn: 'Earn', nav_profile: 'Profile',
            roulette_daily: 'Daily Roulette', roulette_desc: 'Spin and win prizes!',
            avail_gifts: 'Available gifts',
            collect_desc: 'Collect <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> to unlock gifts',
            leaderboard: 'Leaderboard', earn_title: 'Earn',
            tab_refs: 'Referrals', tab_tasks: 'Tasks',
            invite_friends: 'Invite friends',
            ref_desc: 'You will receive <strong class="text-blue-400 glow-text">10%</strong> of donuts from each gift added by your friend! <br><span class="text-xs opacity-70">(Example: added a gift for 4 <img src="/gifts/dount.png" class="w-3 h-3 inline-block align-middle object-contain"> — you get 1 <img src="/gifts/dount.png" class="w-3 h-3 inline-block align-middle object-contain"> bonus)</span>',
            btn_invite: 'Invite friends', your_refs: 'Your referrals',
            tasks_desc: 'Complete tasks to get more donuts <img src="/gifts/dount.png" class="w-4 h-4 inline object-contain">',
            add_gift: '+ Add gift', my_gifts: 'My gifts', for_withdraw: 'for withdraw',
            wheel_fortune: 'Wheel of Fortune', spin_free: 'Spin for free',
            loading: 'Loading...',
            no_refs: 'You have no invited friends yet.', no_tasks: 'No available tasks.',
            completed: 'Completed', check: 'Check', go: 'Go',
            available: 'AVAILABLE', progress: 'PROGRESS',
            claim_gift: 'Claim gift', close: 'Close',
            withdraw_q: 'Do you want to withdraw this gift? It will disappear from your profile.',
            btn_withdraw: 'Withdraw gift', cancel: 'Cancel',
            withdraw_success: 'Gift withdrawn!',
            withdraw_msg: 'Please write any message to <br><span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-green-400 text-lg font-bold cursor-pointer underline decoration-green-400/50 underline-offset-4">@SpaceDonutGifts</span><br> to receive your gift.',
            excellent: 'Excellent', how_to_get: 'How to get',
            how_to_desc: 'Send an NFT gift to the account <span onclick="tg.openTelegramLink(\'https://t.me/SpaceDonutGifts\')" class="text-blue-400 cursor-pointer underline font-bold decoration-blue-400/50 underline-offset-4">@SpaceDonutGifts</span>. After verification, it will appear here. Gifts are automatically converted to <img src="/gifts/dount.png" class="w-4 h-4 inline-block align-middle object-contain"> to unlock main gifts!',
            understood: 'Understood', you: '(You)',
            no_gifts_yet: 'You have no gifts yet.<br><span class="inline-flex items-center gap-1 mt-1">Collect <img src="/gifts/dount.png" class="w-4 h-4 object-contain"> to get a gift!</span>',
            click: 'Click', win: 'Victory!', take_prize: 'Take prize!',
            accumulated: 'Accumulated:', what_gifts_give: 'What gifts give',
            spin_for: 'Spin for', until_free: 'Until free spin:',
            h: 'h.', free_24h: 'Once per 24 hours free!', ref_copied: 'Referral link copied!',
            task_done: 'Task completed! Reward credited.', err_check: 'Verification error.',
            err_conn: 'Connection error', err_conn_srv: 'Server connection error.',
            processing: '⏳ Processing...', gift_added: 'Gift successfully added to your profile!',
            withdrawing: '⏳ Withdrawing...', err_network: 'Network error. Try again later.',
            share_text: 'Join Space Donut and claim cool gifts! 🎁',
            donuts_text: 'donuts!',
            search_ph: 'Search...', sort_title: 'Sort by',
            sort_val_desc: 'Highest value', sort_val_asc: 'Lowest value',
            sort_name_asc: 'By name (A-Z)', sort_name_desc: 'By name (Z-A)', not_found: 'Nothing found'
        }
    };

    let currentLang = '';

    function setLang(lang) {
        vibrate('light');
        currentLang = lang;
        try { localStorage.setItem('appLang', lang); } catch(e) {}

        const btnRu = document.getElementById('lang-ru');
        const btnEn = document.getElementById('lang-en');
        const activeClass   = 'px-3 py-1 rounded-full text-[10px] font-extrabold transition-all bg-blue-500 text-white shadow-[0_0_10px_rgba(59,130,246,0.5)]';
        const inactiveClass = 'px-3 py-1 rounded-full text-[10px] font-extrabold transition-all text-white/50 hover:text-white';
        if (btnRu) btnRu.className = lang === 'ru' ? activeClass : inactiveClass;
        if (btnEn) btnEn.className = lang === 'en' ? activeClass : inactiveClass;

        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (i18n[lang][key] !== undefined) el.innerHTML = i18n[lang][key];
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (i18n[lang][key] !== undefined) el.placeholder = i18n[lang][key];
        });

        const el = (id) => document.getElementById(id);
        if (el('collect-text'))  el('collect-text').innerHTML  = i18n[lang].collect_desc;
        if (el('ref-desc'))      el('ref-desc').innerHTML      = i18n[lang].ref_desc;
        if (el('tasks-desc'))    el('tasks-desc').innerHTML    = i18n[lang].tasks_desc;
        if (el('how-to-desc'))   el('how-to-desc').innerHTML   = i18n[lang].how_to_desc;
        if (el('withdraw-msg'))  el('withdraw-msg').innerHTML  = i18n[lang].withdraw_msg;

        updateUI();
        if (el('page-leaderboard') && !el('page-leaderboard').classList.contains('hidden-tab')) loadLeaderboard();
        if (el('page-earn')        && !el('page-earn').classList.contains('hidden-tab'))        loadEarnData();
        if (el('page-roulette')    && !el('page-roulette').classList.contains('hidden-tab'))    fetchRouletteInfo();
        if (rouletteConfig?.items  && el('page-roulette') && !el('page-roulette').classList.contains('hidden-tab')) renderRouletteWheel();
        if (el('main-gift-modal')  && !el('main-gift-modal').classList.contains('hidden'))      renderBaseGiftsList();
    }
    window.setLang = setLang;

    // =====================================================
    // ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
    // =====================================================
    async function initApp() {
        const savedLang = localStorage.getItem('appLang') || (tg.initDataUnsafe?.user?.language_code === 'en' ? 'en' : 'ru');
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
            myGifts      = data.user_gifts;
            myBalance    = data.balance;
            if (rouletteConfig?.items) renderRouletteWheel();
            updateUI();
        } catch(e) {
            console.error('initApp error:', e);
            updateUI();
        } finally {
            hideAppLoader();
        }
    }

    function updateUI() {
        const el = document.getElementById('balance-amount');
        if (el) el.innerText = myBalance;
        renderMainPage();
        renderProfile();
    }

    // =====================================================
    // РУЛЕТКА
    // =====================================================
    function renderRouletteWheel() {
        const wheel = document.getElementById('roulette-wheel-container');
        const items = rouletteConfig.items;
        if (!wheel || !items) return;

        const numSegments = items.length;
        const angle = 360 / numSegments;
        const colors = numSegments % 2 === 0
            ? ['#1e1b4b','#0f172a']
            : numSegments % 3 === 0
                ? ['#1e1b4b','#0f172a','#2e1065']
                : ['#1e1b4b','#0f172a','#2e1065','#172554'];

        const gradients = items.map((_, i) =>
            `${colors[i % colors.length]} ${i*angle}deg ${(i+1)*angle}deg`
        );
        wheel.style.background = `conic-gradient(${gradients.join(', ')})`;

        let html = '';
        items.forEach((item, index) => {
            const rot = index * angle;
            const contentRot = rot + angle / 2;
            html += `<div class="absolute top-0 left-1/2 w-[2px] h-[50%] bg-gradient-to-b from-purple-400/60 via-blue-500/20 to-transparent origin-bottom -ml-[1px]" style="transform:rotate(${rot}deg);z-index:10;"></div>`;
            const isGift = item.type === 'gift';
            let photoSrc = 'https://via.placeholder.com/48';
            let text = 'Приз';
            if (isGift && mainGifts[item.gift_id]) {
                photoSrc = getImgSrc(mainGifts[item.gift_id].photo);
                text = mainGifts[item.gift_id].name;
            } else if (!isGift) {
                photoSrc = getImgSrc(item.photo);
                text = `+${item.amount}`;
            }
            html += `<div class="absolute top-0 left-1/2 w-20 h-[50%] -ml-10 origin-bottom flex flex-col items-center pt-5 sm:pt-6" style="transform:rotate(${contentRot}deg);z-index:5;">
                <img src="${photoSrc}" class="w-10 h-10 sm:w-12 sm:h-12 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.4)] mb-1 sm:mb-2" onerror="this.src='https://via.placeholder.com/48'">
                <span class="text-[11px] sm:text-[13px] font-black text-white drop-shadow-[0_2px_5px_rgba(0,0,0,1)] text-center leading-tight tracking-wider" style="text-shadow:0px 2px 4px black,0px 0px 10px rgba(168,85,247,0.8);">${text}</span>
            </div>`;
        });
        wheel.innerHTML = html;
    }
    window.renderRouletteWheel = renderRouletteWheel;

    async function fetchRouletteInfo() {
        const btn = document.getElementById('btn-spin');
        const costText = document.getElementById('spin-cost-text');
        if (!btn) return;
        const btnSpan = btn.querySelector('span');
        btnSpan.innerText = i18n[currentLang].loading;
        btn.disabled = true;
        try {
            const res = await fetch(`/api/roulette/info?tg_id=${tgUser.id}`, { headers: getApiHeaders() });
            const data = await res.json();
            if (data.can_free) {
                btnSpan.innerText = i18n[currentLang].spin_free;
                costText.innerText = i18n[currentLang].free_24h;
            } else {
                btnSpan.innerHTML = `${i18n[currentLang].spin_for} ${data.cost} <img src="/gifts/dount.png" class="w-5 h-5 inline object-contain align-text-bottom">`;
                costText.innerText = `${i18n[currentLang].until_free} ${Math.ceil(data.time_left / 3600)} ${i18n[currentLang].h}`;
            }
            btn.disabled = false;
        } catch(e) {
            btnSpan.innerText = 'Error';
        }
    }

    async function openRoulette() {
        if (!rouletteConfig.items) return;
        vibrate('medium');
        switchTab('roulette');
        await fetchRouletteInfo();
    }
    window.openRoulette = openRoulette;

    async function spinRoulette() {
        if (rouletteSpinning) return;
        vibrate('heavy');
        const btn = document.getElementById('btn-spin');
        btn.disabled = true;
        try {
            const res = await fetch('/api/roulette/spin', {
                method: 'POST',
                headers: getApiHeaders(),
                body: JSON.stringify({ tg_id: tgUser.id })
            });
            const data = await res.json();
            if (data.status !== 'ok') { tg.showAlert(data.detail || 'Error!'); btn.disabled = false; return; }

            rouletteSpinning = true;
            const numSegments = rouletteConfig.items.length;
            const angle = 360 / numSegments;
            const winAngle = (data.win_index + 0.5) * angle;
            const currentMod = rouletteCurrentRotation % 360;
            let targetRotation = rouletteCurrentRotation + 6*360 + (360 - winAngle - currentMod);
            targetRotation += (Math.random() - 0.5) * (angle * 0.7);

            animateRouletteWheel(targetRotation, 6500, () => {
                rouletteSpinning = false;
                myBalance = data.balance;
                myGifts   = data.user_gifts;
                updateUI();
                showRouletteResultModal(data.win_item);
                fetchRouletteInfo();
            });
        } catch(e) {
            tg.showAlert(i18n[currentLang].err_conn);
            btn.disabled = false;
        }
    }
    window.spinRoulette = spinRoulette;

    function animateRouletteWheel(targetRotation, duration, callback) {
        let startRotation = rouletteCurrentRotation;
        let startTime = performance.now();
        const segmentAngle = 360 / rouletteConfig.items.length;
        let lastSegment = Math.floor(startRotation / segmentAngle);
        function easeOutQuint(x) { return 1 - Math.pow(1-x, 5); }
        function step(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = easeOutQuint(progress);
            rouletteCurrentRotation = startRotation + (targetRotation - startRotation) * eased;
            document.getElementById('roulette-wheel-container').style.transform = `rotate(${rouletteCurrentRotation}deg) translateZ(0)`;
            const seg = Math.floor(rouletteCurrentRotation / segmentAngle);
            if (seg > lastSegment) {
                if      (progress < 0.6)  vibrate('heavy');
                else if (progress < 0.85) vibrate('medium');
                else                       vibrate('light');
                lastSegment = seg;
            }
            if (progress < 1) requestAnimationFrame(step);
            else if (callback) callback();
        }
        requestAnimationFrame(step);
    }

    function showRouletteResultModal(item) {
        vibrate('heavy');
        const isGift = item.type === 'gift';
        let photoSrc = 'https://via.placeholder.com/48', text = 'Приз';
        if (isGift && mainGifts[item.gift_id]) {
            photoSrc = getImgSrc(mainGifts[item.gift_id].photo);
            text = mainGifts[item.gift_id].name;
        } else if (!isGift) {
            photoSrc = getImgSrc(item.photo);
            text = `+${item.amount} ${i18n[currentLang].donuts_text}`;
        }
        document.getElementById('rr-photo').src = photoSrc;
        document.getElementById('rr-text').innerHTML = text;
        const content = document.getElementById('rrm-content');
        if (content) { content.classList.remove('scale-95'); content.classList.add('scale-100'); }
        openModal('roulette-result-modal');
    }

    // =====================================================
    // ЗАРАБОТОК И РЕФЕРАЛЫ
    // =====================================================
    function getRefLink() { return `https://t.me/${botUsername}?start=${tgUser.id}`; }

    function copyRefLink() {
        vibrate('medium');
        const tmp = document.createElement('input');
        tmp.value = getRefLink();
        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand('copy');
        document.body.removeChild(tmp);
        tg.showAlert(i18n[currentLang].ref_copied);
    }
    window.copyRefLink = copyRefLink;

    function shareRefLink() {
        vibrate('medium');
        const link = getRefLink();
        tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(i18n[currentLang].share_text)}`);
    }
    window.shareRefLink = shareRefLink;

    async function loadEarnData() {
        try {
            const res = await fetch(`/api/earn_data?tg_id=${tgUser.id}`, { headers: getApiHeaders() });
            const data = await res.json();
            const refList = document.getElementById('referrals-list');
            if (data.referrals.length === 0) {
                refList.innerHTML = `<div class="text-center text-sm text-gray-500 py-4 glass rounded-2xl border border-white/5 border-dashed">${i18n[currentLang].no_refs}</div>`;
            } else {
                refList.innerHTML = '';
                data.referrals.forEach(user => {
                    const avatar = user.photo_url || 'https://via.placeholder.com/40';
                    refList.innerHTML += `<div class="glass rounded-2xl p-3 flex items-center gap-3"><img src="${avatar}" class="w-10 h-10 rounded-full border border-white/10"><div class="font-bold text-white text-sm">${user.first_name}</div></div>`;
                });
            }
            const taskList = document.getElementById('tasks-list');
            taskList.innerHTML = '';
            if (data.tasks.length === 0) {
                taskList.innerHTML = `<div class="text-center text-sm text-gray-500 py-4 glass rounded-2xl border border-white/5 border-dashed">${i18n[currentLang].no_tasks}</div>`;
            } else {
                data.tasks.forEach(task => {
                    if (task.completed) {
                        taskList.innerHTML += `<div class="glass rounded-2xl p-4 flex items-center justify-between opacity-50"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center text-xl">✅</div><div><div class="font-bold text-white text-sm line-through">${task.title}</div><div class="text-xs text-green-400">${i18n[currentLang].completed}</div></div></div></div>`;
                    } else {
                        const isChecking = openTasksState[task.id];
                        const btn = isChecking
                            ? `<button onclick="checkTask(${task.id})" id="btn-task-${task.id}" class="bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-bold active:scale-95 transition-transform shadow-[0_0_10px_rgba(59,130,246,0.5)]">${i18n[currentLang].check}</button>`
                            : `<button onclick="openTaskUrl(${task.id},'${task.url}')" class="glass px-4 py-2 rounded-xl text-sm font-bold text-white active:scale-95 transition-transform border border-blue-400/30">${i18n[currentLang].go}</button>`;
                        taskList.innerHTML += `<div class="glass rounded-2xl p-4 flex items-center justify-between border border-blue-500/20 bg-blue-500/5"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-xl border border-blue-400/30">📢</div><div><div class="font-bold text-white text-sm">${task.title}</div><div class="text-xs text-blue-300 flex items-center gap-1">+${task.reward} <img src="/gifts/dount.png" class="w-3 h-3 inline object-contain"></div></div></div>${btn}</div>`;
                    }
                });
            }
        } catch(e) { console.error('loadEarnData:', e); }
    }

    function openTaskUrl(taskId, url) {
        vibrate('light');
        openTasksState[taskId] = true;
        tg.openTelegramLink(url);
        setTimeout(loadEarnData, 1000);
    }
    window.openTaskUrl = openTaskUrl;

    async function checkTask(taskId) {
        vibrate('medium');
        const btn = document.getElementById(`btn-task-${taskId}`);
        if (btn) { btn.innerText = '⏳...'; btn.disabled = true; }
        try {
            const res = await fetch('/api/check_task', {
                method: 'POST',
                headers: getApiHeaders(),
                body: JSON.stringify({ tg_id: tgUser.id, task_id: taskId })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                vibrate('heavy');
                tg.showAlert(i18n[currentLang].task_done);
                myBalance = data.balance;
                updateUI();
                loadEarnData();
            } else {
                tg.showAlert(data.detail || i18n[currentLang].err_check);
                if (btn) { btn.innerText = i18n[currentLang].check; btn.disabled = false; }
            }
        } catch(e) {
            tg.showAlert(i18n[currentLang].err_conn_srv);
            if (btn) { btn.innerText = i18n[currentLang].check; btn.disabled = false; }
        }
    }
    window.checkTask = checkTask;

    // =====================================================
    // ГЛАВНАЯ — СЕТКА ПОДАРКОВ
    // =====================================================
    function renderMainPage() {
        const grid = document.getElementById('main-gifts-grid');
        if (!grid) return;
        grid.innerHTML = '';
        for (const [id, gift] of Object.entries(mainGifts)) {
            const req = gift.required_value;
            const unlocked = myBalance >= req;
            const pct = Math.min(100, Math.round(myBalance / req * 100));
            const statusColor = unlocked ? 'text-green-400' : 'text-blue-300';
            const statusText  = unlocked ? i18n[currentLang].available : i18n[currentLang].progress;
            grid.innerHTML += `
                <div onclick="showMainGiftDetails(${id})" class="glass rounded-3xl p-5 flex items-center gap-5 cursor-pointer relative overflow-hidden active:scale-[0.98] transition-transform">
                    ${unlocked ? '<div class="absolute inset-0 bg-green-500/10 pointer-events-none"></div>' : ''}
                    <div class="relative w-20 h-20 flex-shrink-0 flex items-center justify-center bg-black/20 rounded-2xl border border-white/5">
                        <img src="${getImgSrc(gift.photo)}" class="w-14 h-14 object-contain drop-shadow-xl" onerror="this.src='https://via.placeholder.com/64'">
                    </div>
                    <div class="flex-1">
                        <h4 class="font-bold text-lg mb-2 text-white ${unlocked ? 'glow-text' : ''}">${gift.name}</h4>
                        <div class="w-full bg-black/40 rounded-full h-2 mb-2 border border-white/5 shadow-inner">
                            <div class="progress-bar-fill h-full rounded-full ${unlocked ? 'from-green-400 to-emerald-500' : ''}" style="width:${pct}%"></div>
                        </div>
                        <div class="flex justify-between items-center text-xs font-bold">
                            <span class="${statusColor}">${statusText}</span>
                            <span class="text-gray-300 flex items-center gap-1">${myBalance} <span class="text-blue-400/70 flex items-center gap-1">/ ${req} <img src="/gifts/dount.png" class="w-3 h-3 object-contain"></span></span>
                        </div>
                    </div>
                </div>`;
        }
    }

    // =====================================================
    // СОРТИРОВКА
    // =====================================================
    function openSortModal() {
        vibrate('light');
        document.querySelectorAll('.sort-option').forEach(btn => {
            btn.classList.remove('border-blue-400/50','bg-blue-500/10');
            btn.classList.add('border-white/5','bg-black/40');
            btn.querySelector('.check-icon')?.classList.add('hidden');
        });
        const activeBtn = document.getElementById(`btn-sort-${currentSortMethod}`);
        if (activeBtn) {
            activeBtn.classList.remove('border-white/5','bg-black/40');
            activeBtn.classList.add('border-blue-400/50','bg-blue-500/10');
            activeBtn.querySelector('.check-icon')?.classList.remove('hidden');
        }
        openModal('sort-modal');
    }
    window.openSortModal = openSortModal;

    function selectSort(method) {
        vibrate('light');
        currentSortMethod = method;
        const labelEl = document.getElementById('current-sort-label');
        const key = `sort_${method.replace('value','val')}`;
        if (labelEl) { labelEl.setAttribute('data-i18n', key); labelEl.innerText = i18n[currentLang][key]; }
        closeModal('sort-modal');
        renderBaseGiftsList();
    }
    window.selectSort = selectSort;

    function renderBaseGiftsList() {
        const searchQ = (document.getElementById('mg-search')?.value || '').toLowerCase();
        const container = document.getElementById('mg-sources');
        if (!container) return;
        let arr = Object.entries(baseGifts).map(([id, g]) => ({ id, ...g }));
        if (searchQ) arr = arr.filter(g => g.name.toLowerCase().includes(searchQ));
        arr.sort((a, b) => {
            if (currentSortMethod === 'name_asc')  return a.name.localeCompare(b.name);
            if (currentSortMethod === 'name_desc') return b.name.localeCompare(a.name);
            if (currentSortMethod === 'value_asc') return a.value - b.value;
            return b.value - a.value;
        });
        if (arr.length === 0) {
            container.innerHTML = `<div class="text-center text-blue-200/50 text-xs py-4">${i18n[currentLang].not_found}</div>`;
            return;
        }
        container.innerHTML = arr.map(gift => `
            <div class="flex justify-between items-center bg-black/20 p-2 rounded-xl border border-white/5">
                <div class="flex items-center gap-3">
                    <img src="${getImgSrc(gift.photo)}" class="w-8 h-8 object-contain" onerror="this.src='https://via.placeholder.com/32'">
                    <span class="text-white font-medium">${gift.name}</span>
                </div>
                <span class="text-blue-300 font-bold bg-blue-500/10 px-2 py-1 rounded-lg border border-blue-500/20 flex items-center gap-1">+${gift.value} <img src="/gifts/dount.png" class="w-3 h-3 object-contain"></span>
            </div>`).join('');
    }
    window.renderBaseGiftsList = renderBaseGiftsList;

    function showMainGiftDetails(id) {
        vibrate('light');
        const gift = mainGifts[id];
        document.getElementById('mg-photo').src = getImgSrc(gift.photo);
        document.getElementById('mg-title').innerText = gift.name;
        const req = gift.required_value;
        const unlocked = myBalance >= req;
        document.getElementById('mg-progress-text').innerHTML = `${myBalance} / ${req} <img src="/gifts/dount.png" class="w-4 h-4 object-contain">`;
        const pBar = document.getElementById('mg-progress-bar');
        pBar.style.width = `${Math.min(100, myBalance/req*100)}%`;
        pBar.style.background = unlocked ? 'linear-gradient(90deg,#34d399,#10b981)' : 'linear-gradient(90deg,#3b82f6,#8b5cf6)';
        document.getElementById('mg-search').value = '';
        currentSortMethod = 'value_desc';
        const labelEl = document.getElementById('current-sort-label');
        if (labelEl) { labelEl.setAttribute('data-i18n','sort_val_desc'); labelEl.innerText = i18n[currentLang].sort_val_desc; }
        renderBaseGiftsList();
        const btnClaim = document.getElementById('btn-claim');
        if (unlocked) { btnClaim.classList.remove('hidden'); btnClaim.onclick = () => claimGift(id); }
        else           { btnClaim.classList.add('hidden'); }
        openModal('main-gift-modal');
    }
    window.showMainGiftDetails = showMainGiftDetails;

    async function claimGift(giftId) {
        vibrate('heavy');
        const btn = document.getElementById('btn-claim');
        btn.innerText = i18n[currentLang].processing; btn.disabled = true;
        try {
            const res = await fetch('/api/claim', { method:'POST', headers:getApiHeaders(), body:JSON.stringify({ tg_id:tgUser.id, gift_id:giftId }) });
            const data = await res.json();
            if (data.status === 'ok') {
                myBalance = data.balance; myGifts = data.user_gifts;
                closeModal('main-gift-modal'); updateUI(); switchTab('profile');
                setTimeout(() => tg.showAlert(i18n[currentLang].gift_added), 300);
            } else { tg.showAlert(data.detail || 'Error'); }
        } finally { btn.innerText = i18n[currentLang].claim_gift; btn.disabled = false; }
    }

    // =====================================================
    // ПРОФИЛЬ И ВЫВОД
    // =====================================================
    function renderProfile() {
        const el = (id) => document.getElementById(id);
        if (tgUser.first_name) el('profile-name').innerText = tgUser.first_name;
        if (tgUser.username)   el('profile-username').innerText = `@${tgUser.username}`;
        if (tgUser.photo_url)  el('profile-avatar').src = tgUser.photo_url;
        const grid = el('profile-gifts-grid');
        if (!grid) return;
        grid.innerHTML = '';
        let hasGifts = false;
        for (const [id, amount] of Object.entries(myGifts)) {
            if (amount > 0 && mainGifts[id]) {
                hasGifts = true;
                const gift = mainGifts[id];
                grid.innerHTML += `
                    <div onclick="openWithdrawModal(${id})" class="glass rounded-2xl p-4 flex flex-col items-center relative transition-transform active:scale-95 cursor-pointer border border-green-500/20 bg-green-500/5">
                        <div class="absolute -top-2 -right-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold w-7 h-7 rounded-full flex items-center justify-center border-2 border-[#0f172a] shadow-lg z-10">${amount}</div>
                        <div class="bg-black/20 w-16 h-16 rounded-xl flex items-center justify-center mb-3 border border-white/5 shadow-inner">
                            <img src="${getImgSrc(gift.photo)}" class="w-12 h-12 object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/48'">
                        </div>
                        <span class="text-xs text-center font-bold text-white mb-1 leading-tight">${gift.name}</span>
                        <span class="text-[10px] font-bold text-gray-400 bg-black/30 px-2 py-0.5 rounded-full mt-auto">${i18n[currentLang].click}</span>
                    </div>`;
            }
        }
        if (!hasGifts) {
            grid.innerHTML = `<div class="col-span-3 text-center text-blue-200/40 text-sm mt-6 border border-white/5 border-dashed rounded-2xl p-6">${i18n[currentLang].no_gifts_yet}</div>`;
        }
    }

    function openWithdrawModal(giftId) {
        vibrate('medium');
        const gift = mainGifts[giftId];
        document.getElementById('wd-photo').src = getImgSrc(gift.photo);
        document.getElementById('wd-title').innerText = gift.name;
        document.getElementById('btn-confirm-withdraw').onclick = () => withdrawGift(giftId);
        openModal('withdraw-modal');
    }
    window.openWithdrawModal = openWithdrawModal;

    async function withdrawGift(giftId) {
        vibrate('heavy');
        const btn = document.getElementById('btn-confirm-withdraw');
        btn.innerText = i18n[currentLang].withdrawing; btn.disabled = true;
        try {
            const res = await fetch('/api/withdraw', { method:'POST', headers:getApiHeaders(), body:JSON.stringify({ tg_id:tgUser.id, gift_id:giftId }) });
            const data = await res.json();
            if (data.status === 'ok') {
                myGifts = data.user_gifts; closeModal('withdraw-modal'); updateUI();
                setTimeout(() => openModal('success-withdraw-modal'), 300);
            } else { tg.showAlert(data.detail || 'Error'); }
        } catch(e) { tg.showAlert(i18n[currentLang].err_conn); }
        finally { btn.innerText = i18n[currentLang].btn_withdraw; btn.disabled = false; }
    }

    // =====================================================
    // ТАБЛИЦА ЛИДЕРОВ
    // =====================================================
    async function loadLeaderboard() {
        const list = document.getElementById('leaderboard-list');
        const stickyRank = document.getElementById('user-sticky-rank');
        if (!list) return;
        list.innerHTML = `<div class="text-center text-blue-300/50 mt-10 animate-pulse font-bold tracking-widest uppercase">${i18n[currentLang].loading}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        try {
            const res = await fetch(`/api/leaderboard?tg_id=${tgUser.id}`, { headers: getApiHeaders() });
            const data = await res.json();
            list.innerHTML = '';
            let currentUserRankData = null;
            data.leaderboard.forEach((u, index) => {
                const rank = index + 1;
                const avatar = u.photo_url || 'https://via.placeholder.com/40';
                const isMe = (u.tg_id == tgUser.id || u.id == tgUser.id || (u.username && tgUser.username && u.username === tgUser.username));
                if (isMe) currentUserRankData = { rank, total_gifts: u.total_gifts };
                let rankClass, accentLine, rankTextStyle;
                if (index === 0) {
                    rankClass = 'border-yellow-500/50 bg-gradient-to-r from-yellow-500/20 to-yellow-500/5';
                    accentLine = '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-yellow-300 to-yellow-600 shadow-[0_0_10px_rgba(234,179,8,0.8)]"></div>';
                    rankTextStyle = 'text-yellow-400 drop-shadow-[0_0_8px_rgba(234,179,8,0.8)]';
                } else if (index === 1) {
                    rankClass = 'border-gray-300/50 bg-gradient-to-r from-gray-300/20 to-gray-300/5';
                    accentLine = '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-gray-100 to-gray-400 shadow-[0_0_10px_rgba(209,213,219,0.8)]"></div>';
                    rankTextStyle = 'text-gray-300 drop-shadow-[0_0_8px_rgba(209,213,219,0.8)]';
                } else if (index === 2) {
                    rankClass = 'border-orange-500/50 bg-gradient-to-r from-orange-500/20 to-orange-500/5';
                    accentLine = '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-orange-300 to-orange-600 shadow-[0_0_10px_rgba(249,115,22,0.8)]"></div>';
                    rankTextStyle = 'text-orange-400 drop-shadow-[0_0_8px_rgba(249,115,22,0.8)]';
                } else {
                    rankClass = isMe ? 'border-blue-400/60 bg-blue-500/20' : 'border-white/5 bg-black/30';
                    accentLine = isMe ? '<div class="absolute left-0 top-0 bottom-0 w-1 bg-blue-400"></div>' : '';
                    rankTextStyle = 'text-gray-400/80';
                }
                const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `<span class="font-bold text-lg ${rankTextStyle}">${rank}</span>`;
                list.innerHTML += `
                    <div class="glass rounded-2xl p-3 flex items-center justify-between relative overflow-hidden border ${rankClass}">
                        ${accentLine}
                        <div class="flex items-center gap-4 pl-2">
                            <div class="w-8 text-center text-2xl drop-shadow-md">${medal}</div>
                            <img src="${avatar}" class="w-12 h-12 rounded-full object-cover border ${isMe ? 'border-blue-400' : 'border-white/10'} shadow-sm">
                            <div class="font-bold text-white text-[15px]">${u.first_name} ${isMe ? `<span class="text-xs text-blue-300 ml-1">${i18n[currentLang].you}</span>` : ''}</div>
                        </div>
                        <div class="${isMe ? 'bg-blue-500/30 border-blue-400/50' : 'bg-black/30 border-white/5'} border text-blue-300 font-bold px-4 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5">
                            ${u.total_gifts} <img src="/gifts/dount.png" class="w-4 h-4 object-contain">
                        </div>
                    </div>`;
            });
            if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;
            let myTotalGifts = 0;
            Object.values(myGifts).forEach(a => { if (typeof a === 'number') myTotalGifts += a; });
            const rankText  = currentUserRankData ? currentUserRankData.rank        : '99+';
            const totalGifts = currentUserRankData ? currentUserRankData.total_gifts : myTotalGifts;
            const myAvatar  = tgUser.photo_url  || 'https://via.placeholder.com/40';
            const myName    = tgUser.first_name || 'Вы';
            if (stickyRank) {
                stickyRank.innerHTML = `
                    <div class="glass rounded-2xl p-3 flex items-center justify-between relative overflow-hidden border-blue-300/80 bg-blue-500/30 shadow-[0_0_25px_rgba(59,130,246,0.4)] backdrop-blur-2xl">
                        <div class="absolute left-0 top-0 bottom-0 w-1.5 bg-blue-400 shadow-[0_0_15px_rgba(96,165,250,1)]"></div>
                        <div class="flex items-center gap-4 pl-2">
                            <div class="w-8 text-center text-xl drop-shadow-md text-blue-50 font-extrabold">${rankText}</div>
                            <img src="${myAvatar}" class="w-12 h-12 rounded-full object-cover border-2 border-blue-300 shadow-lg">
                            <div class="font-bold text-white text-[15px]">${myName} <span class="text-xs text-blue-200 ml-1">${i18n[currentLang].you}</span></div>
                        </div>
                        <div class="bg-black/40 border border-blue-300/50 text-blue-100 font-bold px-4 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5">
                            ${totalGifts} <img src="/gifts/dount.png" class="w-4 h-4 object-contain">
                        </div>
                    </div>`;
                stickyRank.classList.remove('hidden');
            }
        } catch(e) {
            list.innerHTML = `<div class="text-center text-red-400 mt-10 glass p-4 rounded-2xl">${i18n[currentLang].err_network}</div>`;
        }
    }

    // =====================================================
    // СТАРТ
    // =====================================================
    initApp();

}); // end DOMContentLoaded