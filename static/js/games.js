// =====================================================
// games.js — Базовый роутер и логика для раздела Игр
// =====================================================

/**
 * Открывает экран игры и скрывает главное меню игр.
 * Используй эту функцию для добавления новых игр.
 * @param {string} viewId - ID HTML-контейнера новой игры (например, 'games-mines-view')
 */
function showGameView(viewId) {
    if (typeof vibrate === 'function') vibrate('light');
    const mainView = document.getElementById('games-main-view');
    const gameView = document.getElementById(viewId);
    
    if (mainView) mainView.classList.add('hidden');
    if (gameView) gameView.classList.remove('hidden');
}

/**
 * Закрывает экран игры и возвращает в главное меню игр.
 * Используй эту функцию для кнопки "Назад" в новых играх.
 * @param {string} viewId - ID HTML-контейнера текущей игры
 */
function hideGameView(viewId) {
    if (typeof vibrate === 'function') vibrate('light');
    const mainView = document.getElementById('games-main-view');
    const gameView = document.getElementById(viewId);
    
    if (gameView) gameView.classList.add('hidden');
    if (mainView) mainView.classList.remove('hidden');
}

// Экспорт базовых функций в глобальную область видимости
window.showGameView = showGameView;
window.hideGameView = hideGameView;
/**
 * Сбрасывает раздел игр на главный экран со списком игр.
 * Вызывается при повторном нажатии на кнопку "Игры" в навигации.
 * Возвращает true, если какой-то игровой экран был закрыт.
 */
function resetGamesView() {
    if (typeof vibrate === 'function') vibrate('light');

    const gameViews = [
        'games-cases-list-view',
        'games-rocket-view',
        'games-pvp-view',
    ];
    const mainView = document.getElementById('games-main-view');

    let anyOpen = false;
    gameViews.forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.classList.contains('hidden')) {
            el.classList.add('hidden');
            anyOpen = true;
        }
    });

    if (anyOpen && mainView) {
        mainView.classList.remove('hidden');
    }

    return anyOpen;
}

window.resetGamesView = resetGamesView;
