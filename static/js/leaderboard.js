// =====================================================
// ТАБЛИЦА ЛИДЕРОВ — три вкладки
// =====================================================

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

let currentLeaderboardTab = 'rich'; // 'rich' | 'rocket' | 'lucky'

// ─── Переключение вкладок ────────────────────────────
function switchLeaderboardTab(tab) {
    currentLeaderboardTab = tab;

    document.querySelectorAll('.leaderboard-tab').forEach(btn => {
        btn.classList.remove('active-tab');
    });
    const activeBtn = document.getElementById(`tab-${tab}`);
    if (activeBtn) activeBtn.classList.add('active-tab');

    loadLeaderboard();
}

// ─── Общий загрузчик ────────────────────────────────
async function loadLeaderboard() {
    const list = document.getElementById('leaderboard-list');
    const stickyRank = document.getElementById('user-sticky-rank');
    if (!list) return;

    list.innerHTML = `<div class="text-center text-blue-300/50 mt-10 animate-pulse font-bold tracking-widest uppercase">${i18n[currentLang].loading}</div>`;
    if (stickyRank) stickyRank.classList.add('hidden');

    try {
        if (currentLeaderboardTab === 'rich')   await loadRichLeaderboard(list, stickyRank);
        if (currentLeaderboardTab === 'rocket') await loadRocketLeaderboard(list, stickyRank);
        if (currentLeaderboardTab === 'lucky')  await loadLuckyLeaderboard(list, stickyRank);
    } catch(e) {
        list.innerHTML = `<div class="text-center text-red-400 mt-10 glass p-4 rounded-2xl">${i18n[currentLang].err_network || 'Ошибка сети'}</div>`;
    }
}

// ─── Вспомогательная: стили для топ-3 ───────────────
function getRankStyle(index) {
    if (index === 0) return { // Золото
        card: 'border-yellow-400/50 bg-gradient-to-r from-yellow-500/30 via-yellow-500/10 to-transparent shadow-[0_0_20px_rgba(234,179,8,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-yellow-300 to-yellow-600 shadow-[0_0_15px_rgba(234,179,8,1)]"></div>',
        text: 'text-transparent bg-clip-text bg-gradient-to-b from-yellow-100 via-yellow-400 to-yellow-600 drop-shadow-[0_0_12px_rgba(234,179,8,0.8)]',
        avatarBorder: 'border-yellow-400',
        glowColor: 'bg-yellow-500',
        rankNum: '1'
    };
    if (index === 1) return { // Серебро
        card: 'border-gray-300/50 bg-gradient-to-r from-gray-400/30 via-gray-400/10 to-transparent shadow-[0_0_20px_rgba(209,213,219,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-gray-100 to-gray-400 shadow-[0_0_15px_rgba(209,213,219,1)]"></div>',
        text: 'text-transparent bg-clip-text bg-gradient-to-b from-white via-gray-300 to-gray-500 drop-shadow-[0_0_12px_rgba(209,213,219,0.8)]',
        avatarBorder: 'border-gray-300',
        glowColor: 'bg-gray-300',
        rankNum: '2'
    };
    if (index === 2) return { // Бронза
        card: 'border-orange-500/50 bg-gradient-to-r from-orange-500/30 via-orange-500/10 to-transparent shadow-[0_0_20px_rgba(249,115,22,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-orange-300 to-orange-600 shadow-[0_0_15px_rgba(249,115,22,1)]"></div>',
        text: 'text-transparent bg-clip-text bg-gradient-to-b from-orange-100 via-orange-400 to-orange-600 drop-shadow-[0_0_12px_rgba(249,115,22,0.8)]',
        avatarBorder: 'border-orange-400',
        glowColor: 'bg-orange-500',
        rankNum: '3'
    };
    // Обычные места
    return {
        card: '',
        accent: '',
        text: 'text-white/50 font-medium',
        avatarBorder: 'border-white/10',
        glowColor: '',
        rankNum: (index + 1).toString()
    };
}

function buildCard(u, index, isMe, valueBadge) {
    const s = getRankStyle(index);
    const avatar = escapeHtml(u.photo_url || 'https://via.placeholder.com/40');

    // Классы для карточки
    const cardClass = s.card || (isMe ? 'border-blue-400/60 bg-gradient-to-r from-blue-600/20 to-transparent shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-white/5 bg-black/30');
    const accentLine = s.accent || (isMe ? '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-blue-300 to-blue-600 shadow-[0_0_10px_rgba(96,165,250,0.8)]"></div>' : '');
    const avatarBorder = isMe && index > 2 ? 'border-blue-400' : s.avatarBorder;
    const activeGlowColor = isMe && index > 2 ? 'bg-blue-500' : s.glowColor;

    // Отображение числа
    let rankDisplay;
    if (index < 3) {
        rankDisplay = `<div class="w-10 text-center text-3xl font-black italic tracking-tighter ${s.text} pr-2">${s.rankNum}</div>`;
    } else {
        rankDisplay = `<div class="w-10 text-center text-lg ${s.text} pr-2">${s.rankNum}</div>`;
    }

    const badgeClass = isMe ? 'bg-blue-500/30 border-blue-400/50 text-blue-100' : 'bg-black/30 border-white/5 text-blue-300';

    return `
        <div class="glass rounded-2xl p-3 flex items-center justify-between relative overflow-hidden border ${cardClass} transition-all duration-300 hover:scale-[1.02]">
            ${accentLine}
            <div class="flex items-center gap-2 pl-2">
                ${rankDisplay}
                <div class="relative">
                    <img src="${avatar}" class="w-12 h-12 rounded-full object-cover border-2 ${avatarBorder} shadow-lg relative z-10 bg-black/50">
                    ${activeGlowColor ? `<div class="absolute inset-0 rounded-full blur-md ${activeGlowColor} opacity-50 z-0 scale-110"></div>` : ''}
                </div>
                <div class="font-bold text-white text-[15px] ml-2 flex flex-col justify-center">
                    <div class="flex items-center gap-1.5">
                        ${escapeHtml(u.first_name || 'Без имени')}
                        ${isMe ? `<span class="text-[10px] leading-none text-blue-200 bg-blue-500/40 border border-blue-400/50 px-1.5 py-0.5 rounded-md uppercase tracking-wider">${i18n[currentLang].you || 'Вы'}</span>` : ''}
                    </div>
                </div>
            </div>
            <div class="${badgeClass} border font-bold px-3 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5 text-sm backdrop-blur-md">
                ${valueBadge}
            </div>
        </div>`;
}

// ─── Вспомогательная: генерация плавающей плашки (Sticky Rank) ──
function buildStickyRankHTML(rankText, avatar, name, badgeHtml, badgeTextColorClass) {
    const safeAvatar = escapeHtml(avatar || 'https://via.placeholder.com/40');
    const safeName   = escapeHtml(name   || 'Вы');
    return `
        <div class="glass rounded-2xl p-3 flex items-center justify-between relative overflow-hidden border-blue-400/60 bg-gradient-to-r from-blue-600/30 via-blue-500/10 to-black/40 shadow-[0_0_25px_rgba(59,130,246,0.4)] backdrop-blur-3xl">
            <div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-blue-300 to-blue-600 shadow-[0_0_15px_rgba(96,165,250,1)]"></div>
            <div class="flex items-center gap-2 pl-2">
                <div class="w-10 text-center text-xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-blue-100 to-blue-400 drop-shadow-[0_0_8px_rgba(96,165,250,0.8)] pr-2">${rankText}</div>
                <div class="relative">
                    <img src="${safeAvatar}" class="w-12 h-12 rounded-full object-cover border-2 border-blue-400 shadow-lg relative z-10 bg-black/50">
                    <div class="absolute inset-0 rounded-full blur-md bg-blue-500 opacity-60 z-0 scale-110"></div>
                </div>
                <div class="font-bold text-white text-[15px] ml-2 flex flex-col justify-center">
                    <div class="flex items-center gap-1.5">
                        ${safeName}
                        <span class="text-[10px] leading-none text-blue-200 bg-blue-500/40 border border-blue-400/50 px-1.5 py-0.5 rounded-md uppercase tracking-wider">${i18n[currentLang].you || 'Вы'}</span>
                    </div>
                </div>
            </div>
            <div class="bg-black/40 border border-blue-400/50 ${badgeTextColorClass} font-bold px-3 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5 backdrop-blur-md">
                ${badgeHtml}
            </div>
        </div>`;
}


// ─── 💸 Транжиры ───────────────────────────────────────
async function loadRichLeaderboard(list, stickyRank) {
    const res = await fetch(`/api/leaderboard`, { headers: getApiHeaders() });
    const data = await res.json();
    list.innerHTML = '';

    if (!data.leaderboard || data.leaderboard.length === 0) {
        list.innerHTML = `<div class="text-center text-white/40 mt-12 text-sm">${i18n[currentLang].lb_empty_spender || 'Пока никто ничего не потратил на этой неделе 💸'}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        return;
    }

    let currentUserRankData = null;

    data.leaderboard.forEach((u, index) => {
        const isMe = (u.tg_id == tgUser.id || (u.username && tgUser.username && u.username === tgUser.username));
        if (isMe) currentUserRankData = { rank: index + 1, donuts_spent: u.donuts_spent, stars_spent: u.stars_spent };

        const badge = buildSpendBadge(u.donuts_spent || 0, u.stars_spent || 0);
        list.innerHTML += buildCard(u, index, isMe, badge);
    });

    if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;

    const rankText     = currentUserRankData?.rank ?? '—';
    const donutsSpent  = currentUserRankData?.donuts_spent ?? 0;
    const starsSpent   = currentUserRankData?.stars_spent  ?? 0;
    const myAvatar     = escapeHtml(tgUser.photo_url  || 'https://via.placeholder.com/40');
    const myName       = escapeHtml(tgUser.first_name || 'Вы');

    if (stickyRank) {
        stickyRank.innerHTML = buildStickyRankHTML(
            rankText, myAvatar, myName,
            buildSpendBadge(donutsSpent, starsSpent),
            'text-purple-200'
        );
        stickyRank.classList.remove('hidden');
    }
}

function buildSpendBadge(donutsSpent, starsSpent) {
    let parts = [];
    if (donutsSpent > 0) parts.push(`${formatBalance(donutsSpent)} <img src="/gifts/dount.png" class="w-4 h-4 object-contain">`);
    if (starsSpent  > 0) parts.push(`${formatBalance(starsSpent)} <img src="/gifts/stars.png" class="w-4 h-4 object-contain">`);
    return parts.length > 0 ? parts.join(' <span class="text-white/30">+</span> ') : `0 <img src="/gifts/dount.png" class="w-4 h-4 object-contain">`;
}

// ─── 🚀 Сорвиголовы ─────────────────────────────────
async function loadRocketLeaderboard(list, stickyRank) {
    const res = await fetch(`/api/leaderboard/rocket`, { headers: getApiHeaders() });
    const data = await res.json();
    list.innerHTML = '';

    if (!data.leaderboard || data.leaderboard.length === 0) {
        list.innerHTML = `<div class="text-center text-white/40 mt-12 text-sm">${i18n[currentLang].lb_empty_rocket || 'Пока нет данных за эту неделю 🚀'}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        return;
    }

    let currentUserRankData = null;

    data.leaderboard.forEach((u, index) => {
        const isMe = (u.tg_id == tgUser.id || (u.username && tgUser.username && u.username === tgUser.username));
        if (isMe) currentUserRankData = { rank: index + 1, max_multiplier: u.max_multiplier };

        const badge = `<span class="text-green-300 font-extrabold">x${parseFloat(u.max_multiplier ?? 0).toFixed(2)}</span> <img src="/gifts/raketa.png" class="w-4 h-4 object-contain">`;
        list.innerHTML += buildCard(u, index, isMe, badge);
    });

    if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;

    const myAvatar = escapeHtml(tgUser.photo_url  || 'https://via.placeholder.com/40');
    const myName   = escapeHtml(tgUser.first_name || 'Вы');
    const rankText = currentUserRankData?.rank ?? '—';
    const multText = currentUserRankData?.max_multiplier != null
        ? `x${parseFloat(currentUserRankData.max_multiplier).toFixed(2)}`
        : '—';

    if (stickyRank) {
        stickyRank.innerHTML = buildStickyRankHTML(
            rankText, myAvatar, myName,
            `${multText} <img src="/gifts/raketa.png" class="w-4 h-4 object-contain">`,
            'text-green-300'
        );
        stickyRank.classList.remove('hidden');
    }
}

// ─── 🍀 Счастливчики ─────────────────────────────────
async function loadLuckyLeaderboard(list, stickyRank) {
    const res = await fetch(`/api/leaderboard/lucky`, { headers: getApiHeaders() });
    const data = await res.json();
    list.innerHTML = '';

    if (!data.leaderboard || data.leaderboard.length === 0) {
        list.innerHTML = `<div class="text-center text-white/40 mt-12 text-sm">${i18n[currentLang].lb_empty_lucky || 'Пока никто не открывал кейсы 🍀'}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        return;
    }

    let currentUserRankData = null;

    data.leaderboard.forEach((u, index) => {
        const isMe = (u.tg_id == tgUser.id || (u.username && tgUser.username && u.username === tgUser.username));
        if (isMe) currentUserRankData = { rank: index + 1, ratio: u.ratio };

        const badge = `<span class="text-emerald-300 font-extrabold">${u.ratio.toFixed(2)}x</span> <img src="/gifts/case.png" class="w-4 h-4 object-contain">`;
        list.innerHTML += buildCard(u, index, isMe, badge);
    });

    if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;

    const myAvatar  = escapeHtml(tgUser.photo_url  || 'https://via.placeholder.com/40');
    const myName    = escapeHtml(tgUser.first_name || 'Вы');
    const rankText  = currentUserRankData?.rank ?? '—';
    const ratioText = currentUserRankData?.ratio != null
        ? `${parseFloat(currentUserRankData.ratio).toFixed(2)}x`
        : '—';

    if (stickyRank) {
        stickyRank.innerHTML = buildStickyRankHTML(
            rankText, myAvatar, myName,
            `${ratioText} <img src="/gifts/case.png" class="w-4 h-4 object-contain">`,
            'text-emerald-300'
        );
        stickyRank.classList.remove('hidden');
    }
}

// Экспорт для использования в nav.js и i18n.js
window.loadLeaderboard = loadLeaderboard;
window.switchLeaderboardTab = switchLeaderboardTab;