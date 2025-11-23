/**
 * Модуль для управления действиями команд (изменение статуса).
 * Обрабатывает клики по кнопкам изменения статуса команды.
 */

(function() {
    'use strict';

    /**
     * Получает CSRF токен (использует глобальную функцию из csrf.js)
     */
    function getCsrfToken() {
        if (typeof window.getCSRFToken === 'function') {
            return window.getCSRFToken();
        }
        
        // Fallback если csrf.js не загружен
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return decodeURIComponent(value);
        }
        
        const input = document.querySelector('[name="csrfmiddlewaretoken"]');
        return input ? input.value : null;
    }

    /**
     * Отправляет запрос на изменение статуса команды
     */
    async function changeTeamStatus(teamId, action) {
        const statusMap = {
            'deactivate': 'inactive',
            'reactivate': 'active',
            'disband': 'disbanded'
        };

        const newStatus = statusMap[action];
        if (!newStatus) {
            console.error('Unknown action:', action);
            return;
        }

        try {
            const response = await fetch(`/teams/${teamId}/status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    status: newStatus,
                    reason: ''
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.message || 'Ошибка при изменении статуса команды');
                }
            } else if (response.status === 403) {
                alert('Недостаточно прав для изменения статуса команды');
            } else {
                const text = await response.text();
                console.error('Server response:', text);
                alert('Ошибка при изменении статуса команды');
            }
        } catch (error) {
            console.error('Error changing team status:', error);
            alert('Произошла ошибка при изменении статуса команды');
        }
    }

    /**
     * Показывает подтверждение перед изменением статуса
     */
    function confirmAction(teamName, action) {
        const messages = {
            'deactivate': `Вы уверены, что хотите приостановить команду "${teamName}"?`,
            'reactivate': `Вы уверены, что хотите возобновить команду "${teamName}"?`,
            'disband': `Вы уверены, что хотите распустить команду "${teamName}"? Это действие нельзя отменить!`
        };

        return confirm(messages[action] || 'Вы уверены?');
    }

    /**
     * Инициализация обработчиков событий
     */
    function init() {
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('.team-action-btn');
            if (!btn) return;

            e.preventDefault();

            const teamId = btn.dataset.teamId;
            const teamName = btn.dataset.teamName;
            const action = btn.dataset.action;

            if (!teamId || !action) {
                console.error('Missing team ID or action');
                return;
            }

            if (confirmAction(teamName, action)) {
                changeTeamStatus(teamId, action);
            }
        });
    }

    // Инициализация при загрузке DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
