// =====================================================
// nav.js — Навигация
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

function onTabSwitch(tabId) {
    if (tabId === 'leaderboard' && typeof loadLeaderboard === 'function') loadLeaderboard();
    if (tabId === 'earn' && typeof loadEarnData === 'function') loadEarnData();
    if (tabId === 'roulette' && typeof fetchRouletteInfo === 'function') fetchRouletteInfo();
}

window.switchTab = switchTab;
