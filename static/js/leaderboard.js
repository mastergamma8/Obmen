// =====================================================
// ТАБЛИЦА ЛИДЕРОВ — три вкладки + 3D-подиум для топ-3
// =====================================================

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

let currentLeaderboardTab = 'rich';

// ─── Таймер до сброса ────────────────────────────────
let _resetCountdownInterval = null;

function startResetCountdown(resetTs) {
    const el = document.getElementById('lb-reset-countdown');
    const wrapper = document.getElementById('lb-reset-timer');
    if (!el || !wrapper) return;
    if (_resetCountdownInterval) clearInterval(_resetCountdownInterval);

    function update() {
        const now = Math.floor(Date.now() / 1000);
        const diff = resetTs - now;
        const lang = i18n[currentLang] || i18n['ru'];
        if (diff <= 0) {
            el.textContent = `0${lang.time_d} 0${lang.time_h} 0${lang.time_m}`;
            clearInterval(_resetCountdownInterval);
            return;
        }
        const d = Math.floor(diff / 86400);
        const h = Math.floor((diff % 86400) / 3600);
        const m = Math.floor((diff % 3600) / 60);
        el.textContent = d > 0
            ? `${d}${lang.time_d} ${h}${lang.time_h} ${m}${lang.time_m}`
            : `${h}${lang.time_h} ${m}${lang.time_m}`;
    }
    wrapper.classList.remove('hidden');
    update();
    _resetCountdownInterval = setInterval(update, 1000);
}

// ─── Переключение вкладок ────────────────────────────
function switchLeaderboardTab(tab) {
    currentLeaderboardTab = tab;
    document.querySelectorAll('.leaderboard-tab').forEach(btn => btn.classList.remove('active-tab'));
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
        if (currentLeaderboardTab === 'rich')    await loadRichLeaderboard(list, stickyRank);
        if (currentLeaderboardTab === 'alltime') await loadAlltimeLeaderboard(list, stickyRank);
    } catch(e) {
        list.innerHTML = `<div class="text-center text-red-400 mt-10 glass p-4 rounded-2xl">${i18n[currentLang].err_network || 'Ошибка сети'}</div>`;
    }
}

// ─── Иконка приза для компактного вида ────────────────
function buildPrizeBadgeSmall(prize) {
    if (!prize) return '';
    const t = prize.type;
    const amount = prize.amount || 0;
    if (t === 'donuts') {
        return `<div class="flex items-center justify-center gap-1 mt-2 bg-gradient-to-r from-yellow-500/20 to-yellow-600/10 border border-yellow-500/30 text-yellow-300 px-2 py-0.5 rounded-full text-[9px] font-bold backdrop-blur-md shadow-[0_0_10px_rgba(234,179,8,0.15)] w-max mx-auto">
            <span class="mr-0.5 text-[10px]">🎁</span> ${formatBalance(amount)} <img src="/gifts/dount.png" class="w-2.5 h-2.5 object-contain">
        </div>`;
    }
    if (t === 'stars') {
        return `<div class="flex items-center justify-center gap-1 mt-2 bg-gradient-to-r from-purple-500/20 to-purple-600/10 border border-purple-500/30 text-purple-200 px-2 py-0.5 rounded-full text-[9px] font-bold backdrop-blur-md shadow-[0_0_10px_rgba(168,85,247,0.15)] w-max mx-auto">
            <span class="mr-0.5 text-[10px]">🎁</span> ${formatBalance(amount)} <img src="/gifts/stars.png" class="w-2.5 h-2.5 object-contain">
        </div>`;
    }
    if ((t === 'base_gift' || t === 'tg_gift') && prize.gift_photo) {
        return `<div class="flex items-center justify-center gap-1 mt-2 bg-white/10 border border-white/15 px-2 py-0.5 rounded-full backdrop-blur-md w-max mx-auto shadow-sm">
            <span class="text-[10px] mr-0.5">🎁</span> <img src="${escapeHtml(prize.gift_photo)}" class="w-3.5 h-3.5 object-contain rounded-sm">
        </div>`;
    }
    return '';
}

// ─── 3D-подиум (УЛУЧШЕННЫЙ ДИЗАЙН) ─────────────────────
function buildPodium(top3, prizes, myTgId) {
    const empty = { first_name: '—', photo_url: '', username: '', donuts_spent: 0, stars_spent: 0 };
    const p1 = top3[0] || empty;
    const p2 = top3[1] || empty;
    const p3 = top3[2] || empty;

    function isMe(u) {
        return u && u.tg_id != null && (
            u.tg_id == myTgId ||
            (u.username && tgUser.username && u.username === tgUser.username)
        );
    }

    function podiumSlot(user, place) {
        const me = isMe(user);
        const isAnon = me && localStorage.getItem('isAnonymous') === 'true';
        const name = isAnon ? 'Anonim' : escapeHtml(user.first_name || '—');
        const avatar = (user.photo_url && user.photo_url !== '')
            ? (isAnon ? (window.ANON_AVATAR || '') : escapeHtml(user.photo_url))
            : 'https://via.placeholder.com/80';

        const prize = prizes ? prizes[String(place)] : null;
        const lang = i18n[currentLang] || i18n['ru'];

        // Компактный блок приза (без лишнего текста)
        const prizeSectionHtml = prize ? buildPrizeBadgeSmall(prize) : '';

        // Бейдж "Вы"
        const youBadge = me
            ? `<div class="absolute -bottom-2 left-1/2 -translate-x-1/2 text-[8px] font-black text-white bg-blue-500 border border-blue-400/50 px-2 py-0.5 rounded-full uppercase tracking-widest shadow-lg z-20">${lang.you || 'Вы'}</div>`
            : '';

        // Расходы без текста, только красивые плашки
        const spent = buildSpendBadgeSmall(user.donuts_spent || 0, user.stars_spent || 0);

        // Индивидуальные стили для каждого места
        const cfg = {
            1: {
                avatarContainer: 'w-20 h-20 p-1 bg-gradient-to-b from-yellow-300 via-yellow-500 to-yellow-700',
                crown: '<div class="absolute -top-7 text-3xl drop-shadow-[0_0_15px_rgba(234,179,8,0.8)] z-20 animate-custom-bounce">👑</div>',
                rankBadge: '<div class="absolute -bottom-2.5 left-1/2 -translate-x-1/2 w-6 h-6 bg-gradient-to-br from-yellow-300 to-yellow-600 rounded-full flex items-center justify-center text-white font-black text-xs border-2 border-[#0f172a] shadow-[0_0_10px_rgba(234,179,8,0.6)] z-20">1</div>',
                nameColor: 'text-yellow-100 drop-shadow-md',
                nameSize: 'text-[13px]',
                glow: 'bg-yellow-500/40',
                pedestal: 'h-[110px] bg-gradient-to-t from-yellow-500/20 to-transparent border-t border-yellow-500/40'
            },
            2: {
                avatarContainer: 'w-[60px] h-[60px] p-[3px] bg-gradient-to-b from-gray-200 via-gray-400 to-gray-600',
                crown: '<div class="absolute -top-5 text-xl drop-shadow-[0_0_10px_rgba(209,213,219,0.8)] z-20">🥈</div>',
                rankBadge: '<div class="absolute -bottom-2 left-1/2 -translate-x-1/2 w-5 h-5 bg-gradient-to-br from-gray-300 to-gray-500 rounded-full flex items-center justify-center text-white font-black text-[10px] border-2 border-[#0f172a] shadow-[0_0_10px_rgba(209,213,219,0.5)] z-20">2</div>',
                nameColor: 'text-gray-100',
                nameSize: 'text-[11px]',
                glow: 'bg-gray-400/30',
                pedestal: 'h-[80px] bg-gradient-to-t from-gray-400/15 to-transparent border-t border-gray-400/30'
            },
            3: {
                avatarContainer: 'w-[60px] h-[60px] p-[3px] bg-gradient-to-b from-orange-300 via-orange-500 to-orange-700',
                crown: '<div class="absolute -top-5 text-xl drop-shadow-[0_0_10px_rgba(249,115,22,0.8)] z-20">🥉</div>',
                rankBadge: '<div class="absolute -bottom-2 left-1/2 -translate-x-1/2 w-5 h-5 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center text-white font-black text-[10px] border-2 border-[#0f172a] shadow-[0_0_10px_rgba(249,115,22,0.5)] z-20">3</div>',
                nameColor: 'text-orange-100',
                nameSize: 'text-[11px]',
                glow: 'bg-orange-500/30',
                pedestal: 'h-[65px] bg-gradient-to-t from-orange-500/15 to-transparent border-t border-orange-500/30'
            },
        }[place];

        return `
        <div class="flex flex-col items-center justify-end relative flex-1">
            <div class="relative flex flex-col items-center w-full pb-2">
                <!-- Корона -->
                ${cfg.crown}

                <!-- Аватар с градиентной обводкой -->
                <div class="relative rounded-full ${cfg.avatarContainer} shadow-lg mb-2">
                    <img src="${avatar}" class="w-full h-full rounded-full object-cover border-[2px] border-[#0f172a] relative z-10" onerror="this.src='https://via.placeholder.com/80'">
                    ${me ? youBadge : cfg.rankBadge}
                    <!-- Фоновое свечение -->
                    <div class="absolute inset-0 rounded-full blur-xl ${cfg.glow} -z-10 scale-150"></div>
                </div>

                <!-- Информация (Имя, Траты, Приз) -->
                <div class="flex flex-col items-center w-full px-1 z-10">
                    <div class="font-black ${cfg.nameColor} ${cfg.nameSize} truncate w-full text-center tracking-tight max-w-[85px] mx-auto">${name}</div>
                    ${spent}
                    ${prizeSectionHtml}
                </div>
            </div>

            <!-- Glassmorphism Пьедестал -->
            <div class="w-full rounded-t-2xl ${cfg.pedestal} relative overflow-hidden backdrop-blur-md mt-1 shadow-[0_-5px_15px_rgba(0,0,0,0.2)]">
                <!-- Блики на гранях -->
                <div class="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent"></div>
                <div class="absolute top-0 left-0 right-0 h-px bg-white/20"></div>
                <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[60%] h-[2px] bg-white/40 blur-[2px]"></div>
            </div>
        </div>`;
    }

    const hasPrizes = prizes && Object.keys(prizes).length > 0;

    return `
    <div class="w-full mb-2 mt-6 px-1">
        <div class="flex items-end justify-center gap-1.5 sm:gap-2">
            ${podiumSlot(p2, 2)}
            ${podiumSlot(p1, 1)}
            ${podiumSlot(p3, 3)}
        </div>
        ${hasPrizes
            ? `<div class="flex justify-center mt-3">
                <div class="text-center text-[9px] text-white/50 font-medium bg-white/5 py-1 px-3 rounded-full border border-white/10 backdrop-blur-sm shadow-sm inline-flex items-center gap-1.5">
                    <span class="opacity-80">🎁</span> ${(i18n[currentLang] || i18n['ru']).lb_prize_auto || 'Призы раздаются автоматически каждый понедельник'}
                </div>
               </div>`
            : ''}
    </div>`;
}

// Компактные плашки трат для подиума (без текстового ярлыка)
function buildSpendBadgeSmall(donuts, stars) {
    const hasDonuts = donuts > 0;
    const hasStars  = stars  > 0;

    if (!hasDonuts && !hasStars) {
        return '<div class="text-[10px] text-white/30 font-medium mt-1">—</div>';
    }

    let html = '<div class="flex flex-col items-center gap-1 mt-1.5 w-full px-1">';
    if (hasDonuts) {
        html += `<div class="flex items-center justify-center gap-1 bg-[#020617]/60 w-full max-w-[65px] py-[3px] rounded-md border border-white/5 backdrop-blur-sm shadow-inner">
            <span class="text-[10px] font-bold text-white/90 leading-none tracking-tight">${formatBalance(donuts)}</span>
            <img src="/gifts/dount.png" class="w-3 h-3 object-contain shrink-0 drop-shadow-md">
        </div>`;
    }
    if (hasStars) {
        html += `<div class="flex items-center justify-center gap-1 bg-[#020617]/60 w-full max-w-[65px] py-[3px] rounded-md border border-white/5 backdrop-blur-sm shadow-inner">
            <span class="text-[10px] font-bold text-white/90 leading-none tracking-tight">${formatBalance(stars)}</span>
            <img src="/gifts/stars.png" class="w-3 h-3 object-contain shrink-0 drop-shadow-md">
        </div>`;
    }
    html += '</div>';
    return html;
}

// ─── Стили для карточек 4-50 мест ───────────────────
function getRankStyle(index) {
    if (index === 0) return {
        card: 'border-yellow-400/50 bg-gradient-to-r from-yellow-500/30 via-yellow-500/10 to-transparent shadow-[0_0_20px_rgba(234,179,8,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-yellow-300 to-yellow-600 shadow-[0_0_15px_rgba(234,179,8,1)]"></div>',
        rankStyle: 'background: linear-gradient(to bottom, #fef08a, #eab308, #92400e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; filter: drop-shadow(0 0 10px rgba(234,179,8,0.9));',
        text: 'text-yellow-400',
        avatarBorder: 'border-yellow-400', glowColor: 'bg-yellow-500', rankNum: '1'
    };
    if (index === 1) return {
        card: 'border-gray-300/50 bg-gradient-to-r from-gray-400/30 via-gray-400/10 to-transparent shadow-[0_0_20px_rgba(209,213,219,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-gray-100 to-gray-400 shadow-[0_0_15px_rgba(209,213,219,1)]"></div>',
        rankStyle: 'background: linear-gradient(to bottom, #f9fafb, #9ca3af, #4b5563); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; filter: drop-shadow(0 0 10px rgba(209,213,219,0.9));',
        text: 'text-gray-300',
        avatarBorder: 'border-gray-300', glowColor: 'bg-gray-300', rankNum: '2'
    };
    if (index === 2) return {
        card: 'border-orange-500/50 bg-gradient-to-r from-orange-500/30 via-orange-500/10 to-transparent shadow-[0_0_20px_rgba(249,115,22,0.15)]',
        accent: '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-orange-300 to-orange-600 shadow-[0_0_15px_rgba(249,115,22,1)]"></div>',
        rankStyle: 'background: linear-gradient(to bottom, #fed7aa, #f97316, #c2410c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; filter: drop-shadow(0 0 10px rgba(249,115,22,0.9));',
        text: 'text-orange-400',
        avatarBorder: 'border-orange-400', glowColor: 'bg-orange-500', rankNum: '3'
    };
    return {
        card: '', accent: '',
        rankStyle: '',
        text: 'text-white/50 font-medium',
        avatarBorder: 'border-white/10', glowColor: '',
        rankNum: (index + 1).toString()
    };
}

function buildCard(u, index, isMe, valueBadge) {
    const s = getRankStyle(index);
    const isAnonymous = isMe && localStorage.getItem('isAnonymous') === 'true';
    const displayName = isAnonymous ? 'Anonim' : (u.first_name || 'Без имени');
    const avatar = isAnonymous ? (window.ANON_AVATAR || '') : escapeHtml(u.photo_url || 'https://via.placeholder.com/40');
    const cardClass = s.card || (isMe ? 'border-blue-400/60 bg-gradient-to-r from-blue-600/20 to-transparent shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-white/5 bg-black/30');
    const accentLine = s.accent || (isMe ? '<div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-blue-300 to-blue-600 shadow-[0_0_10px_rgba(96,165,250,0.8)]"></div>' : '');
    const avatarBorder = isMe && index > 2 ? 'border-blue-400' : s.avatarBorder;
    const activeGlowColor = isMe && index > 2 ? 'bg-blue-500' : s.glowColor;
    let rankDisplay;
    if (index < 3) {
        rankDisplay = `<div class="w-8 sm:w-10 shrink-0 text-center text-2xl sm:text-3xl font-black italic tracking-tighter pr-1 sm:pr-2" style="${s.rankStyle}">${s.rankNum}</div>`;
    } else {
        rankDisplay = `<div class="w-8 sm:w-10 shrink-0 text-center text-base sm:text-lg ${s.text} pr-1 sm:pr-2">${s.rankNum}</div>`;
    }
    const badgeClass = isMe ? 'bg-blue-500/30 border-blue-400/50 text-blue-100' : 'bg-black/30 border-white/5 text-blue-300';
    return `
        <div class="glass rounded-2xl p-2.5 sm:p-3 flex items-center justify-between relative overflow-hidden border ${cardClass} transition-all duration-300 hover:scale-[1.02] gap-2 mt-2">
            ${accentLine}
            <div class="flex items-center gap-1.5 sm:gap-2 pl-1 sm:pl-2 flex-1 min-w-0">
                ${rankDisplay}
                <div class="relative shrink-0">
                    <img src="${avatar}" class="w-10 h-10 sm:w-12 sm:h-12 rounded-full object-cover border-2 ${avatarBorder} shadow-lg relative z-10 bg-black/50 shrink-0">
                    ${activeGlowColor ? `<div class="absolute inset-0 rounded-full blur-md ${activeGlowColor} opacity-50 z-0 scale-110"></div>` : ''}
                </div>
                <div class="font-bold text-white text-[14px] sm:text-[15px] ml-1.5 sm:ml-2 flex flex-col justify-center flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 min-w-0">
                        <span class="truncate">${escapeHtml(displayName)}</span>
                        ${isMe ? `<span class="shrink-0 text-[10px] leading-none text-blue-200 bg-blue-500/40 border border-blue-400/50 px-1.5 py-0.5 rounded-md uppercase tracking-wider">${i18n[currentLang].you || 'Вы'}</span>` : ''}
                    </div>
                </div>
            </div>
            <div class="${badgeClass} border font-bold px-2 py-1 sm:px-3 sm:py-1.5 rounded-xl shadow-inner flex flex-wrap justify-end items-center gap-x-1 gap-y-0.5 text-xs sm:text-sm backdrop-blur-md shrink-0 max-w-[45%] sm:max-w-none text-right">
                ${valueBadge}
            </div>
        </div>`;
}

function buildStickyRankHTML(rankText, avatar, name, badgeHtml, badgeTextColorClass) {
    const safeAvatar = escapeHtml(avatar || 'https://via.placeholder.com/40');
    const safeName   = escapeHtml(name   || 'Вы');
    return `
        <div class="glass rounded-2xl p-2.5 sm:p-3 flex items-center justify-between relative overflow-hidden border-blue-400/60 bg-gradient-to-r from-blue-600/30 via-blue-500/10 to-black/40 shadow-[0_0_25px_rgba(59,130,246,0.4)] backdrop-blur-3xl gap-2">
            <div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-blue-300 to-blue-600 shadow-[0_0_15px_rgba(96,165,250,1)]"></div>
            <div class="flex items-center gap-1.5 sm:gap-2 pl-1 sm:pl-2 flex-1 min-w-0">
                <div class="w-8 sm:w-10 shrink-0 text-center text-lg sm:text-xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-blue-100 to-blue-400 drop-shadow-[0_0_8px_rgba(96,165,250,0.8)] pr-1 sm:pr-2">${rankText}</div>
                <div class="relative shrink-0">
                    <img src="${safeAvatar}" class="w-10 h-10 sm:w-12 sm:h-12 rounded-full object-cover border-2 border-blue-400 shadow-lg relative z-10 bg-black/50 shrink-0">
                    <div class="absolute inset-0 rounded-full blur-md bg-blue-500 opacity-60 z-0 scale-110"></div>
                </div>
                <div class="font-bold text-white text-[14px] sm:text-[15px] ml-1.5 sm:ml-2 flex flex-col justify-center flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 min-w-0">
                        <span class="truncate">${safeName}</span>
                        <span class="shrink-0 text-[10px] leading-none text-blue-200 bg-blue-500/40 border border-blue-400/50 px-1.5 py-0.5 rounded-md uppercase tracking-wider">${i18n[currentLang].you || 'Вы'}</span>
                    </div>
                </div>
            </div>
            <div class="bg-black/40 border border-blue-400/50 ${badgeTextColorClass} font-bold px-2 py-1 sm:px-3 sm:py-1.5 rounded-xl shadow-inner flex flex-wrap justify-end items-center gap-x-1 gap-y-0.5 text-xs sm:text-sm backdrop-blur-md shrink-0 max-w-[45%] sm:max-w-none text-right">
                ${badgeHtml}
            </div>
        </div>`;
}

// ─── Транжиры ─────────────────────────────────────────
async function loadRichLeaderboard(list, stickyRank) {
    const res = await fetch(`/api/leaderboard`, { headers: getApiHeaders() });
    const data = await res.json();
    list.innerHTML = '';

    if (data.reset_ts) startResetCountdown(data.reset_ts);

    if (!data.leaderboard || data.leaderboard.length === 0) {
        list.innerHTML = `<div class="text-center text-white/40 mt-12 text-sm">${i18n[currentLang].lb_empty_spender || 'Пока никто ничего не потратил на этой неделе 💸'}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        return;
    }

    const myTgId = tgUser.id;
    const prizes = data.prizes || null;

    // 3D-подиум
    list.innerHTML = buildPodium(data.leaderboard.slice(0, 3), prizes, myTgId);

    // Разделитель
    list.innerHTML += `<div class="flex items-center gap-2 mt-6 mb-2 px-1">
        <div class="flex-1 h-px bg-gradient-to-r from-transparent to-white/20"></div>
        <span class="text-white/30 text-[9px] font-bold tracking-widest uppercase shrink-0 px-1">${(i18n[currentLang] || i18n['ru']).lb_others_label || 'Остальные участники'}</span>
        <div class="flex-1 h-px bg-gradient-to-l from-transparent to-white/20"></div>
    </div>`;

    // Карточки 4+
    let currentUserRankData = null;
    data.leaderboard.forEach((u, index) => {
        const isMe = (u.tg_id == myTgId || (u.username && tgUser.username && u.username === tgUser.username));
        if (isMe) currentUserRankData = { rank: index + 1, donuts_spent: u.donuts_spent, stars_spent: u.stars_spent };
        if (index < 3) return;
        list.innerHTML += buildCard(u, index, isMe, buildSpendBadge(u.donuts_spent || 0, u.stars_spent || 0));
    });

    if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;

    const rankText    = currentUserRankData?.rank ?? '—';
    const donutsSpent = currentUserRankData?.donuts_spent ?? 0;
    const starsSpent  = currentUserRankData?.stars_spent  ?? 0;
    const myAvatar    = localStorage.getItem('isAnonymous') === 'true' ? (window.ANON_AVATAR || '') : escapeHtml(tgUser.photo_url || 'https://via.placeholder.com/40');
    const myName      = localStorage.getItem('isAnonymous') === 'true' ? 'Anonim' : escapeHtml(tgUser.first_name || 'Вы');

    if (stickyRank) {
        stickyRank.innerHTML = buildStickyRankHTML(rankText, myAvatar, myName, buildSpendBadge(donutsSpent, starsSpent), 'text-purple-200');
        stickyRank.classList.remove('hidden');
    }
}

function buildSpendBadge(donutsSpent, starsSpent) {
    const hasDonuts = donutsSpent > 0;
    const hasStars  = starsSpent  > 0;

    if (!hasDonuts && !hasStars) {
        return `<div class="flex items-center gap-1 whitespace-nowrap">0 <img src="/gifts/dount.png" class="w-3.5 h-3.5 sm:w-4 sm:h-4 object-contain shrink-0"></div>`;
    }
    if (hasDonuts && hasStars) {
        return `<div class="flex flex-col items-end gap-0.5">
            <div class="flex items-center gap-1 whitespace-nowrap">${formatBalance(donutsSpent)} <img src="/gifts/dount.png" class="w-3.5 h-3.5 sm:w-4 sm:h-4 object-contain shrink-0"></div>
            <div class="flex items-center gap-1 whitespace-nowrap">${formatBalance(starsSpent)} <img src="/gifts/stars.png" class="w-3.5 h-3.5 sm:w-4 sm:h-4 object-contain shrink-0"></div>
        </div>`;
    }
    if (hasDonuts) {
        return `<div class="flex items-center gap-1 whitespace-nowrap">${formatBalance(donutsSpent)} <img src="/gifts/dount.png" class="w-3.5 h-3.5 sm:w-4 sm:h-4 object-contain shrink-0"></div>`;
    }
    return `<div class="flex items-center gap-1 whitespace-nowrap">${formatBalance(starsSpent)} <img src="/gifts/stars.png" class="w-3.5 h-3.5 sm:w-4 sm:h-4 object-contain shrink-0"></div>`;
}

// ─── За всё время ────────────────────────────────────
async function loadAlltimeLeaderboard(list, stickyRank) {
    const res = await fetch(`/api/leaderboard/alltime`, { headers: getApiHeaders() });
    const data = await res.json();
    list.innerHTML = '';

    const timerWrapper = document.getElementById('lb-reset-timer');
    if (timerWrapper) timerWrapper.classList.add('hidden');
    if (_resetCountdownInterval) { clearInterval(_resetCountdownInterval); _resetCountdownInterval = null; }

    if (!data.leaderboard || data.leaderboard.length === 0) {
        list.innerHTML = `<div class="text-center text-white/40 mt-12 text-sm">${i18n[currentLang].lb_empty_alltime || 'Пока никто ничего не потратил 🏆'}</div>`;
        if (stickyRank) stickyRank.classList.add('hidden');
        return;
    }

    const myTgId = tgUser.id;

    // Для «за всё время» призов нет
    list.innerHTML = buildPodium(data.leaderboard.slice(0, 3), null, myTgId);

    list.innerHTML += `<div class="flex items-center gap-2 mt-6 mb-2 px-1">
        <div class="flex-1 h-px bg-gradient-to-r from-transparent to-white/20"></div>
        <span class="text-white/30 text-[9px] font-bold tracking-widest uppercase shrink-0 px-1">${(i18n[currentLang] || i18n['ru']).lb_others_label || 'Остальные участники'}</span>
        <div class="flex-1 h-px bg-gradient-to-l from-transparent to-white/20"></div>
    </div>`;

    let currentUserRankData = null;
    data.leaderboard.forEach((u, index) => {
        const isMe = (u.tg_id == myTgId || (u.username && tgUser.username && u.username === tgUser.username));
        if (isMe) currentUserRankData = { rank: index + 1, donuts_spent: u.donuts_spent, stars_spent: u.stars_spent };
        if (index < 3) return;
        list.innerHTML += buildCard(u, index, isMe, buildSpendBadge(u.donuts_spent || 0, u.stars_spent || 0));
    });

    if (!currentUserRankData && data.user_info) currentUserRankData = data.user_info;

    const rankText    = currentUserRankData?.rank ?? '—';
    const donutsSpent = currentUserRankData?.donuts_spent ?? 0;
    const starsSpent  = currentUserRankData?.stars_spent  ?? 0;
    const myAvatar    = localStorage.getItem('isAnonymous') === 'true' ? (window.ANON_AVATAR || '') : escapeHtml(tgUser.photo_url || 'https://via.placeholder.com/40');
    const myName      = localStorage.getItem('isAnonymous') === 'true' ? 'Anonim' : escapeHtml(tgUser.first_name || 'Вы');

    if (stickyRank) {
        stickyRank.innerHTML = buildStickyRankHTML(rankText, myAvatar, myName, buildSpendBadge(donutsSpent, starsSpent), 'text-yellow-200');
        stickyRank.classList.remove('hidden');
    }
}

window.loadLeaderboard = loadLeaderboard;
window.switchLeaderboardTab = switchLeaderboardTab;
