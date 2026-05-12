// =====================================================
// shop.js — Страница Магазин
// =====================================================

let shopConfig = null;          // { limited_section, sections[] }
let shopBuyPending = null;      // { item, sectionId }
let shopAvailableReferrals = 0; // кэш доступных рефералов

// ── Инициализация ─────────────────────────────────────────

async function initShopPage() {
    if (shopConfig) {
        renderShop();
        return;
    }
    try {
        const [cfgRes, refRes] = await Promise.all([
            fetch('/api/shop/config'),
            fetch('/api/shop/referrals', { headers: getApiHeaders() })
        ]);
        shopConfig = await cfgRes.json();
        const refData = await refRes.json();
        shopAvailableReferrals = refData.available ?? 0;
    } catch (e) {
        console.error('Shop init error:', e);
    }
    renderShop();
}

// ── Рендер страницы ───────────────────────────────────────

function renderShop() {
    if (!shopConfig) return;
    renderCustomSections();
}

// ── Кастомные разделы ─────────────────────────────────────

function renderCustomSections() {
    const container = document.getElementById('shop-custom-sections');
    if (!container) return;

    const sections = shopConfig.sections || [];
    if (!sections.length) {
        container.innerHTML = '';
        return;
    }

    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'ru';
    container.innerHTML = '';

    sections.forEach(section => {
        const title = (section.title && section.title[lang]) || section.title?.ru || '';

        const sectionEl = document.createElement('div');
        sectionEl.className = 'mb-7';
        sectionEl.innerHTML = `
            <h3 class="text-base font-bold text-white/80 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span class="w-1 h-4 rounded-full bg-purple-500 inline-block"></span>
                <span>${title}</span>
            </h3>
            <div class="grid grid-cols-2 gap-3" id="shop-section-${section.id}"></div>
        `;
        container.appendChild(sectionEl);

        const grid = document.getElementById(`shop-section-${section.id}`);
        (section.items || []).forEach(item => {
            grid.appendChild(_buildItemCard(item, section.id, lang));
        });
    });
}

function _buildItemCard(item, sectionId, lang) {
    const title   = (item.title && item.title[lang]) || item.title?.ru || '';
    const imgSrc  = _getItemImage(item);
    const priceLabel = _getPriceLabel(item, lang);

    const card = document.createElement('div');
    card.className = [
        'glass rounded-2xl p-3 flex flex-col items-center gap-2',
        'border border-purple-500/20 cursor-pointer',
        'active:scale-95 transition-all',
        'hover:border-purple-400/50 hover:bg-white/5',
        'shadow-[0_4px_15px_rgba(0,0,0,0.3)]'
    ].join(' ');
    card.onclick = () => openShopBuyModal(item, sectionId);

    card.innerHTML = `
        <div class="w-full aspect-square rounded-xl bg-purple-500/10 border border-purple-400/15
                    flex items-center justify-center overflow-hidden">
            <img src="${imgSrc}"
                 class="w-full h-full object-contain p-2 drop-shadow-[0_0_8px_rgba(168,85,247,0.4)]"
                 onerror="this.src='https://via.placeholder.com/80?text=🎁'">
        </div>
        <p class="text-xs font-bold text-white text-center leading-tight">${title}</p>
        <div class="flex items-center gap-1">
            ${priceLabel}
        </div>
    `;
    return card;
}

function _getItemImage(item) {
    if (item.image) return item.image;
    if (item.gift_id) {
        const giftDef = (typeof tgGifts !== 'undefined') ? tgGifts[item.gift_id] : null;
        if (giftDef && giftDef.photo) return giftDef.photo;
    }
    if (item.type === 'stars')  return '/gifts/stars.png';
    if (item.type === 'donuts') return '/gifts/dount.png';
    return '/gifts/limitedgifts.png';
}

function _getPriceLabel(item, lang) {
    const currency = item.currency;
    const price    = item.price;

    if (currency === 'free') {
        const txt = (i18n[lang] || i18n['ru'])['shop_price_free'] || 'Бесплатно';
        return `<span class="text-sm font-black text-green-400">${txt}</span>`;
    }
    if (currency === 'stars') {
        return `<span class="text-sm font-black text-yellow-300">${price}</span>
                <img src="/gifts/stars.png" class="w-3.5 h-3.5 object-contain" alt="⭐">`;
    }
    if (currency === 'donuts') {
        return `<span class="text-sm font-black text-orange-300">${price}</span>
                <img src="/gifts/dount.png" class="w-3.5 h-3.5 object-contain" alt="🍩">`;
    }
    if (currency === 'referral') {
        const txt = (i18n[lang] || i18n['ru'])['shop_price_referral'] || 'реф.';
        return `<span class="text-sm font-black text-blue-300">${price} ${txt}</span>`;
    }
    return `<span class="text-sm font-black text-white">${price}</span>`;
}

// ── Лимитированные подарки (отдельный вид) ────────────────

function openShopLimitedGifts() {
    if (typeof vibrate === 'function') vibrate('light');
    const mainContent = document.getElementById('page-shop');
    const fullView    = document.getElementById('shop-limited-full');
    if (!mainContent || !fullView) return;

    // Скрываем основное содержимое
    document.getElementById('shop-section-limited').style.display = 'none';
    document.getElementById('shop-custom-sections').style.display = 'none';
    document.querySelector('#page-shop > h2').style.display = 'none';
    fullView.classList.remove('hidden');

    renderShopLimitedGrid();
}

function closeShopLimitedGifts() {
    if (typeof vibrate === 'function') vibrate('light');
    document.getElementById('shop-section-limited').style.display = '';
    document.getElementById('shop-custom-sections').style.display = '';
    document.querySelector('#page-shop > h2').style.display = '';
    document.getElementById('shop-limited-full').classList.add('hidden');
}

function renderShopLimitedGrid() {
    const grid = document.getElementById('shop-limited-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (!shopConfig || !shopConfig.limited_section) return;

    const items = shopConfig.limited_section.items || [];
    const lang  = (typeof currentLang !== 'undefined') ? currentLang : 'ru';

    items.forEach(item => {
        const giftId  = item.gift_id;
        const giftDef = (typeof tgGifts !== 'undefined') ? tgGifts[giftId] : null;
        const photo   = giftDef ? giftDef.photo : (item.image || '');
        const price   = item.price || 0;

        const card = document.createElement('div');
        card.className = [
            'glass rounded-2xl p-3 flex flex-col items-center gap-2',
            'border border-orange-500/20 cursor-pointer',
            'active:scale-95 transition-all',
            'hover:border-orange-400/50 hover:bg-white/5',
            'shadow-[0_4px_15px_rgba(0,0,0,0.3)]'
        ].join(' ');
        card.onclick = () => {
            // Переиспользуем старый модал из tg-shop.js
            if (typeof openTgBuyModal === 'function') openTgBuyModal(giftId);
        };

        card.innerHTML = `
            <div class="w-full aspect-square rounded-xl bg-orange-500/10 border border-orange-400/15
                        flex items-center justify-center overflow-hidden">
                <img src="${photo}"
                     class="w-full h-full object-contain p-1 drop-shadow-[0_0_8px_rgba(249,115,22,0.5)]"
                     onerror="this.src='https://via.placeholder.com/80?text=🎁'">
            </div>
            <div class="flex items-center gap-1 mt-0.5">
                <span class="text-sm font-black text-yellow-300">${price}</span>
                <img src="/gifts/stars.png" class="w-3.5 h-3.5 object-contain" alt="⭐">
            </div>
        `;
        grid.appendChild(card);
    });
}

// ── Модал покупки кастомного товара ──────────────────────

async function openShopBuyModal(item, sectionId) {
    if (typeof vibrate === 'function') vibrate('medium');
    shopBuyPending = { item, sectionId };

    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'ru';
    const t    = i18n[lang] || i18n['ru'];

    // Изображение
    const imgEl = document.getElementById('shop-buy-modal-img');
    if (imgEl) imgEl.src = _getItemImage(item);

    // Название
    const titleEl = document.getElementById('shop-buy-modal-title');
    if (titleEl) titleEl.textContent = (item.title && item.title[lang]) || item.title?.ru || '';

    // Стоимость
    const costEl = document.getElementById('shop-buy-modal-cost');
    if (costEl) {
        if (item.currency === 'free')    costEl.textContent = t['shop_price_free'] || 'Бесплатно';
        else if (item.currency === 'stars')   costEl.textContent = `${item.price} ⭐`;
        else if (item.currency === 'donuts')  costEl.textContent = `${item.price} 🍩`;
        else if (item.currency === 'referral')costEl.textContent = `${item.price} ${t['shop_price_referral'] || 'реф.'}`;
    }

    // Награда
    const rewardEl = document.getElementById('shop-buy-modal-reward');
    if (rewardEl) {
        if (item.type === 'stars')          rewardEl.textContent = `${item.amount} ⭐`;
        else if (item.type === 'donuts')    rewardEl.textContent = `${item.amount} 🍩`;
        else if (item.type === 'limited_gift' || item.type === 'base_gift') {
            rewardEl.textContent = t['shop_reward_gift'] || '🎁 Telegram-подарок';
        }
    }

    // Строка рефералов
    const refRow   = document.getElementById('shop-buy-modal-referral-row');
    const refCount = document.getElementById('shop-buy-modal-refs-count');
    if (item.currency === 'referral') {
        // Обновляем счётчик рефералов
        try {
            const res = await fetch('/api/shop/referrals', { headers: getApiHeaders() });
            const data = await res.json();
            shopAvailableReferrals = data.available ?? 0;
        } catch (_) {}
        if (refRow)   refRow.classList.remove('hidden');
        if (refCount) refCount.textContent = shopAvailableReferrals;
    } else {
        if (refRow) refRow.classList.add('hidden');
    }

    // Кнопка подтверждения
    const labelEl = document.getElementById('shop-buy-confirm-label');
    if (labelEl) labelEl.textContent = t['shop_modal_confirm_btn'] || 'Купить';

    document.getElementById('shop-buy-modal')?.classList.remove('hidden');
}

function closeShopBuyModal() {
    if (typeof vibrate === 'function') vibrate('light');
    shopBuyPending = null;
    document.getElementById('shop-buy-modal')?.classList.add('hidden');
}

async function confirmShopBuy() {
    if (!shopBuyPending) return;
    const { item, sectionId } = shopBuyPending;
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'ru';
    const t    = i18n[lang] || i18n['ru'];

    const btn = document.getElementById('shop-buy-confirm-btn');
    const originalHTML = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = `<span class="opacity-70">${t['processing'] || '⏳...'}</span>`; }

    try {
        const res = await fetch('/api/shop/buy', {
            method:  'POST',
            headers: getApiHeaders(),
            body:    JSON.stringify({ item_id: item.id, section_id: sectionId }),
        });
        const data = await res.json();

        if (res.ok && data.status === 'ok') {
            // Обновляем баланс
            if (typeof myBalance !== 'undefined' && data.balance !== undefined) myBalance = data.balance;
            if (typeof myStars   !== 'undefined' && data.stars   !== undefined) myStars   = data.stars;
            if (typeof updateUI === 'function') updateUI();

            closeShopBuyModal();

            // Сбрасываем кэш рефералов
            shopAvailableReferrals = Math.max(0, shopAvailableReferrals - (item.currency === 'referral' ? item.price : 0));

            showNotify(t['shop_buy_success'] || '✅ Куплено!', 'success');
        } else {
            const detail = data.detail || '';
            let msg = t['shop_buy_error'] || 'Ошибка покупки';
            if (detail === 'not_enough_donuts') msg = t['not_enough_donuts'] || 'Недостаточно пончиков!';
            if (detail === 'not_enough_stars')  msg = t['not_enough_stars']  || 'Недостаточно звёзд!';
            if (detail === 'not_enough_referrals') msg = t['shop_not_enough_referrals'] || 'Недостаточно приглашённых друзей!';
            if (detail === 'send_gift_failed')  msg = t['tg_buy_error'] || 'Не удалось отправить подарок';
            showNotify(msg, 'error');
        }
    } catch (e) {
        console.error('Shop buy error:', e);
        showNotify(t['err_conn'] || 'Ошибка соединения', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = originalHTML; }
    }
}

// ── Экспорт ───────────────────────────────────────────────

window.initShopPage              = initShopPage;
window.openShopLimitedGifts      = openShopLimitedGifts;
window.closeShopLimitedGifts     = closeShopLimitedGifts;
window.openShopBuyModal          = openShopBuyModal;
window.closeShopBuyModal         = closeShopBuyModal;
window.confirmShopBuy            = confirmShopBuy;
