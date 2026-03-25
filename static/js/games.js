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