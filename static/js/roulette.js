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
        
        if (isGift) {
            // Ищем и в главных, и в базовых
            const giftDef = mainGifts[item.gift_id] || baseGifts[item.gift_id];
            if (giftDef) {
                photoSrc = getImgSrc(giftDef.photo);
                text = giftDef.name;
            }
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
    
    if (isGift) {
        // Ищем в обоих массивах
        const giftDef = mainGifts[item.gift_id] || baseGifts[item.gift_id];
        if (giftDef) {
            photoSrc = getImgSrc(giftDef.photo);
            text = giftDef.name;
        }
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

window.renderRouletteWheel = renderRouletteWheel;
window.openRoulette = openRoulette;
window.spinRoulette = spinRoulette;
window.fetchRouletteInfo = fetchRouletteInfo;