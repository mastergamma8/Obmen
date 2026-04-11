// =====================================================
// РУЛЕТКА (Поддержка Звезд)
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
        
        if (isGift) {
            const giftDef = mainGifts[item.gift_id] || tgGifts[item.gift_id] || baseGifts[item.gift_id];
            if (giftDef) {
                photoSrc = getImgSrc(giftDef.photo);
                text = giftDef.name;
            }
        } else if (item.type === 'stars') {
            photoSrc = getImgSrc(item.photo || '/gifts/stars.png');
            text = `+${item.amount}`;
        } else if (item.type === 'donuts') {
            photoSrc = getImgSrc(item.photo || '/gifts/dount.png');
            text = `+${item.amount}`;
        }
        
        const labelHtml = isGift
            ? ''
            : `<span class="text-[11px] sm:text-[13px] font-black text-white drop-shadow-[0_2px_5px_rgba(0,0,0,1)] text-center leading-tight tracking-wider" style="text-shadow:0px 2px 4px black,0px 0px 10px rgba(168,85,247,0.8);">${text}</span>`;
        html += `<div class="absolute top-0 left-1/2 w-20 h-[50%] -ml-10 origin-bottom flex flex-col items-center pt-5 sm:pt-6" style="transform:rotate(${contentRot}deg);z-index:5;">
            <img src="${photoSrc}" class="w-10 h-10 sm:w-12 sm:h-12 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.4)] mb-1 sm:mb-2" onerror="this.src='https://via.placeholder.com/48'">
            ${labelHtml}
        </div>`;
    });
    wheel.innerHTML = html;
}

async function fetchRouletteInfo() {
    const btn = document.getElementById('btn-spin');
    const costText = document.getElementById('spin-cost-text');
    if (!btn) return;
    const btnSpan = btn.querySelector('span');

    // В демо-режиме всегда активна кнопка без запроса к серверу
    if (isDemoMode) {
        btnSpan.innerText = (currentLang === 'en' ? 'Spin (Demo)' : 'Крутить (Демо)');
        if (costText) costText.innerText = (currentLang === 'en' ? 'Demo — nothing is credited' : 'Демо — ничего не начисляется');
        btn.disabled = false;
        return;
    }

    btnSpan.innerText = i18n[currentLang].loading;
    btn.disabled = true;
    try {
        const res = await fetch(`/api/roulette/info`, { headers: getApiHeaders() });
        const data = await res.json();
        
        // Определяем иконку валюты (Пончики или Звезды)
        const currencyIcon = data.currency === 'stars' ? '/gifts/stars.png' : '/gifts/dount.png';

        if (data.can_free) {
            btnSpan.innerText = i18n[currentLang].spin_free;
            costText.innerText = i18n[currentLang].free_24h;
        } else {
            btnSpan.innerHTML = `${i18n[currentLang].spin_for} ${data.cost} <img src="${currencyIcon}" class="w-5 h-5 inline object-contain align-text-bottom">`;
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
    syncDemoToggles();
    await fetchRouletteInfo();
}

async function spinRoulette() {
    if (rouletteSpinning) return;
    vibrate('heavy');
    const btn = document.getElementById('btn-spin');
    btn.disabled = true;

    // ── ДЕМО-РЕЖИМ ──────────────────────────────────────────────────────────
    if (isDemoMode) {
        rouletteSpinning = true;
        const items = rouletteConfig.items;
        const numSegments = items.length;
        const angle = 360 / numSegments;
        const demoIndex = Math.floor(Math.random() * numSegments);
        const winAngle = (demoIndex + 0.5) * angle;
        const currentMod = rouletteCurrentRotation % 360;
        let targetRotation = rouletteCurrentRotation + 6*360 + (360 - winAngle - currentMod);
        targetRotation += (Math.random() - 0.5) * (angle * 0.7);

        animateRouletteWheel(targetRotation, 6500, () => {
            rouletteSpinning = false;
            showRouletteResultModal(items[demoIndex], true);
            fetchRouletteInfo();
        });
        return;
    }
    // ────────────────────────────────────────────────────────────────────────
    try {
        const res = await fetch('/api/roulette/spin', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.status !== 'ok') { showNotify(data.detail || 'Error!', 'error'); btn.disabled = false; return; }

        rouletteSpinning = true;
        const numSegments = rouletteConfig.items.length;
        const angle = 360 / numSegments;
        const winAngle = (data.win_index + 0.5) * angle;
        const currentMod = rouletteCurrentRotation % 360;
        let targetRotation = rouletteCurrentRotation + 6*360 + (360 - winAngle - currentMod);
        targetRotation += (Math.random() - 0.5) * (angle * 0.7);

        animateRouletteWheel(targetRotation, 6500, () => {
            rouletteSpinning = false;
            if (data.balance !== undefined) myBalance = data.balance;
            if (data.stars !== undefined) myStars = data.stars;
            myGifts = data.user_gifts;
            updateUI();
            showRouletteResultModal(data.win_item);
            fetchRouletteInfo();
        });
    } catch(e) {
        showNotify(i18n[currentLang].err_conn, 'error');
        btn.disabled = false;
    }
}

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

function showRouletteResultModal(item, isDemo = false) {
    vibrate('heavy');
    const isGift = item.type === 'gift';
    let photoSrc = 'https://via.placeholder.com/48', text = 'Приз';
    
    if (isGift) {
        const giftDef = mainGifts[item.gift_id] || tgGifts[item.gift_id] || baseGifts[item.gift_id];
        if (giftDef) {
            photoSrc = getImgSrc(giftDef.photo);
            text = giftDef.name;
        }
    } else if (item.type === 'stars') {
        photoSrc = getImgSrc(item.photo || '/gifts/stars.png');
        const starsText = currentLang === 'en' ? 'stars!' : 'звезд!';
        text = `+${item.amount} ${starsText}`;
    } else if (item.type === 'donuts') {
        photoSrc = getImgSrc(item.photo || '/gifts/dount.png');
        text = `+${item.amount} ${i18n[currentLang].donuts_text || 'пончиков!'}`;
    }
    
    document.getElementById('rr-photo').src = photoSrc;
    document.getElementById('rr-text').innerHTML = text;
    if (typeof configureCaseGiftActionsIfNeeded === 'function') {
        if (isGift) {
            configureCaseGiftActionsIfNeeded(item.gift_id, 'roulette', isDemo);
        } else {
            // Не подарок — скрываем кнопки действий и показываем кнопку закрытия
            const actionsBox = document.getElementById('rr-gift-actions');
            const closeBtn = document.getElementById('rr-btn-close');
            if (actionsBox) actionsBox.classList.add('hidden');
            if (closeBtn) closeBtn.classList.remove('hidden');
        }
    }
    // Показываем/скрываем плашку ДЕМО в модалке результата
    const demoBadge = document.getElementById('rr-demo-badge');
    if (demoBadge) demoBadge.style.display = isDemo ? '' : 'none';
    const content = document.getElementById('rrm-content');
    if (content) { content.classList.remove('scale-95'); content.classList.add('scale-100'); }
    openModal('roulette-result-modal');
}

window.renderRouletteWheel = renderRouletteWheel;
window.openRoulette = openRoulette;
window.spinRoulette = spinRoulette;
window.fetchRouletteInfo = fetchRouletteInfo;

// =====================================================
// DRAG-TO-SPIN + БЛОКИРОВКА ГОРИЗОНТАЛЬНОГО СВАЙПА
// =====================================================
(function initRouletteDrag() {
    function getWheel() { return document.getElementById('roulette-wheel-container'); }

    // --- вспомогательные ---
    function getCenter(el) {
        const r = el.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }
    function getAngle(cx, cy, px, py) {
        return Math.atan2(py - cy, px - cx) * 180 / Math.PI;
    }

    let dragActive   = false;
    let startAngle   = 0;
    let lastAngle    = 0;
    let prevAngle    = 0;
    let velocity     = 0;
    let lastTime     = 0;
    let animFrame    = null;
    let momentumRunning = false;

    function getEventPoint(e) {
        if (e.touches && e.touches.length > 0) {
            return { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
        return { x: e.clientX, y: e.clientY };
    }

    function onDragStart(e) {
        if (rouletteSpinning || momentumRunning) return;
        const wheel = getWheel();
        if (!wheel) return;
        e.preventDefault();
        e.stopPropagation();

        dragActive = true;
        const pt = getEventPoint(e);
        const c  = getCenter(wheel);
        startAngle = getAngle(c.x, c.y, pt.x, pt.y) - rouletteCurrentRotation;
        lastAngle  = rouletteCurrentRotation;
        prevAngle  = rouletteCurrentRotation;
        lastTime   = performance.now();
        velocity   = 0;
        wheel.style.cursor = 'grabbing';

        if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }
    }

    function onDragMove(e) {
        if (!dragActive) return;
        e.preventDefault();
        e.stopPropagation();

        const wheel = getWheel();
        if (!wheel) return;
        const pt = getEventPoint(e);
        const c  = getCenter(wheel);
        const raw = getAngle(c.x, c.y, pt.x, pt.y);
        let newRot = raw - startAngle;

        // Нормализуем скачок при пересечении 180°
        let delta = newRot - lastAngle;
        if (delta >  180) delta -= 360;
        if (delta < -180) delta += 360;
        newRot = lastAngle + delta;

        // Скорость для momentum
        const now = performance.now();
        const dt  = now - lastTime;
        if (dt > 0) velocity = (newRot - prevAngle) / dt * 16; // °/frame @60fps
        prevAngle = lastAngle;
        lastAngle = newRot;
        lastTime  = now;

        rouletteCurrentRotation = newRot;
        wheel.style.transform = `rotate(${newRot}deg) translateZ(0)`;
    }

    function onDragEnd(e) {
        if (!dragActive) return;
        dragActive = false;
        const wheel = getWheel();
        if (wheel) wheel.style.cursor = 'grab';

        // Запускаем инерцию если есть скорость
        if (Math.abs(velocity) > 0.3) {
            momentumRunning = true;
            runMomentum(velocity);
        }
    }

    function runMomentum(vel) {
        const friction = 0.97; // замедление
        const minVel   = 0.05;

        function step() {
            vel *= friction;
            rouletteCurrentRotation += vel;
            const wheel = getWheel();
            if (wheel) wheel.style.transform = `rotate(${rouletteCurrentRotation}deg) translateZ(0)`;

            if (Math.abs(vel) > minVel) {
                animFrame = requestAnimationFrame(step);
            } else {
                momentumRunning = false;
                animFrame = null;
            }
        }
        animFrame = requestAnimationFrame(step);
    }

    // Вешаем события после загрузки DOM
    function attachDragEvents() {
        const wheel = getWheel();
        if (!wheel) { setTimeout(attachDragEvents, 300); return; }

        // Touch
        wheel.addEventListener('touchstart', onDragStart, { passive: false });
        wheel.addEventListener('touchmove',  onDragMove,  { passive: false });
        wheel.addEventListener('touchend',   onDragEnd,   { passive: false });
        wheel.addEventListener('touchcancel',onDragEnd,   { passive: false });
        // Mouse (для десктопа)
        wheel.addEventListener('mousedown', onDragStart);
        window.addEventListener('mousemove', onDragMove);
        window.addEventListener('mouseup',   onDragEnd);
    }

    // Блокируем горизонтальный свайп на всей странице рулетки
    function blockHorizontalSwipe() {
        const page = document.getElementById('page-roulette');
        if (!page) { setTimeout(blockHorizontalSwipe, 300); return; }
        page.addEventListener('touchstart', function(e) {
            this._touchStartX = e.touches[0].clientX;
            this._touchStartY = e.touches[0].clientY;
        }, { passive: true });
        page.addEventListener('touchmove', function(e) {
            const dx = Math.abs(e.touches[0].clientX - (this._touchStartX || 0));
            const dy = Math.abs(e.touches[0].clientY - (this._touchStartY || 0));
            if (dx > dy && dx > 8) e.preventDefault(); // горизонталь — блокируем
        }, { passive: false });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { attachDragEvents(); blockHorizontalSwipe(); });
    } else {
        attachDragEvents();
        blockHorizontalSwipe();
    }
})();