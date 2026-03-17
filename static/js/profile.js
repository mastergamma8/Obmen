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
        // Проверяем: это Главный подарок или Базовый подарок?
        const giftDef = mainGifts[id] || baseGifts[id];
        
        if (amount > 0 && giftDef) {
            hasGifts = true;
            grid.innerHTML += `
                <div onclick="openWithdrawModal(${id})" class="glass rounded-2xl p-4 flex flex-col items-center relative transition-transform active:scale-95 cursor-pointer border border-green-500/20 bg-green-500/5">
                    <div class="absolute -top-2 -right-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold w-7 h-7 rounded-full flex items-center justify-center border-2 border-[#0f172a] shadow-lg z-10">${amount}</div>
                    <div class="bg-black/20 w-16 h-16 rounded-xl flex items-center justify-center mb-3 border border-white/5 shadow-inner">
                        <img src="${getImgSrc(giftDef.photo)}" class="w-12 h-12 object-contain drop-shadow-md" onerror="this.src='https://via.placeholder.com/48'">
                    </div>
                    <span class="text-xs text-center font-bold text-white mb-1 leading-tight">${giftDef.name}</span>
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
    // Ищем подарок в обоих массивах
    const gift = mainGifts[giftId] || baseGifts[giftId];
    if (!gift) return;
    
    document.getElementById('wd-photo').src = getImgSrc(gift.photo);
    document.getElementById('wd-title').innerText = gift.name;
    document.getElementById('btn-confirm-withdraw').onclick = () => withdrawGift(giftId);
    openModal('withdraw-modal');
}

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
// ИСТОРИЯ ОПЕРАЦИЙ
// =====================================================
const HISTORY_ICONS = {
    gift_added:          { icon: '🎁', color: 'green',  sign: '+' },
    roulette_win_donuts: { icon: '🎰', color: 'green',  sign: '+' },
    roulette_win_gift:   { icon: '🎰', color: 'green',  sign: null },
    roulette_free:       { icon: '🎰', color: 'green',  sign: '+' },
    roulette_free_gift:  { icon: '🎰', color: 'green',  sign: null },
    case_open:           { icon: '📦', color: 'red',    sign: '-' },
    case_win_donuts:     { icon: '📦', color: 'green',  sign: '+' },
    case_win_gift:       { icon: '📦', color: 'green',  sign: null },
    roulette_paid:       { icon: '🎰', color: 'red',    sign: '-' },
    claim_gift:          { icon: '🛍️', color: 'red',    sign: '-' },
    withdraw_gift:       { icon: '📤', color: 'gray',   sign: null },
    task_reward:         { icon: '✅', color: 'green',  sign: '+' },
    referral_bonus:      { icon: '👥', color: 'green',  sign: '+' },
};

function formatHistoryDate(ts) {
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function openHistoryModal() {
    vibrate('light');
    openModal('history-modal');
    const list = document.getElementById('history-list');
    list.innerHTML = `<div class="text-center text-blue-300/50 py-10 animate-pulse font-bold tracking-widest uppercase text-sm">${i18n[currentLang].loading}</div>`;
    try {
        const res = await fetch(`/api/history?tg_id=${tgUser.id}`, { headers: getApiHeaders() });
        const data = await res.json();
        if (!data.history || data.history.length === 0) {
            list.innerHTML = `<div class="text-center text-blue-200/40 text-sm py-10 border border-white/5 border-dashed rounded-2xl px-4">${i18n[currentLang].history_empty}</div>`;
            return;
        }
        list.innerHTML = data.history.map(entry => {
            const meta = HISTORY_ICONS[entry.action_type] || { icon: '📋', color: 'gray', sign: null };
            let amountHtml = '';
            if (meta.sign === '+' && entry.amount > 0) {
                amountHtml = `<span class="text-green-400 font-extrabold text-base flex items-center gap-1">+${entry.amount} <img src="/gifts/dount.png" class="w-4 h-4 object-contain"></span>`;
            } else if (meta.sign === '-' && entry.amount !== 0) {
                amountHtml = `<span class="text-red-400 font-extrabold text-base flex items-center gap-1">−${Math.abs(entry.amount)} <img src="/gifts/dount.png" class="w-4 h-4 object-contain"></span>`;
            } else if (meta.color === 'green' && entry.amount === 0) {
                amountHtml = `<span class="text-green-400 font-extrabold text-lg">🎁</span>`;
            } else if (meta.color === 'gray') {
                amountHtml = `<span class="text-gray-400 font-extrabold text-lg">📤</span>`;
            } else {
                amountHtml = `<span class="text-gray-400 font-bold text-sm">—</span>`;
            }
            const borderColor = meta.color === 'green' ? 'border-green-500/20 bg-green-500/5'
                              : meta.color === 'red'   ? 'border-red-500/20 bg-red-500/5'
                              : 'border-white/5 bg-black/20';
            const iconBg = meta.color === 'green' ? 'bg-green-500/20 border-green-400/30'
                         : meta.color === 'red'   ? 'bg-red-500/20 border-red-400/30'
                         : 'bg-white/5 border-white/10';
            return `
                <div class="glass rounded-2xl px-4 py-3 flex items-center justify-between border ${borderColor} gap-3">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center text-xl border ${iconBg}">
                            ${meta.icon}
                        </div>
                        <div class="min-w-0">
                            <div class="font-semibold text-white text-sm leading-tight truncate">${entry.description}</div>
                            <div class="text-[11px] text-blue-200/40 mt-0.5">${formatHistoryDate(entry.created_at)}</div>
                        </div>
                    </div>
                    <div class="flex-shrink-0 ml-2">${amountHtml}</div>
                </div>`;
        }).join('');
    } catch(e) {
        list.innerHTML = `<div class="text-center text-red-400/70 text-sm py-10">${i18n[currentLang].err_network}</div>`;
    }
}

window.renderProfile = renderProfile; 
window.openWithdrawModal = openWithdrawModal;
window.openHistoryModal = openHistoryModal;