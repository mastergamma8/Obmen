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

// Экспорт для использования в nav.js и i18n.js
window.loadLeaderboard = loadLeaderboard;
