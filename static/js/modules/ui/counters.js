/**
 * Counters - Teams
 */

async function updateTeams() {
    try {
        const response = await fetch(window.URLS.teamsTeamCounts);
        const data = await response.json();
        const totalCount = data.active + data.inactive + data.disbanded;
        
        const badges = {
            total: document.getElementById('teams-total-badge'),
            all: document.getElementById('teams-all-badge'),
            active: document.getElementById('teams-active-badge'),
            inactive: document.getElementById('teams-inactive-badge'),
            disbanded: document.getElementById('teams-disbanded-badge')
        };
        
        if (badges.total) {
            badges.total.textContent = totalCount > 99 ? '99+' : totalCount;
            badges.total.style.display = totalCount > 0 ? 'inline-block' : 'none';
        }
        if (badges.all) badges.all.textContent = totalCount;
        if (badges.active) badges.active.textContent = data.active;
        if (badges.inactive) badges.inactive.textContent = data.inactive;
        if (badges.disbanded) badges.disbanded.textContent = data.disbanded;
    } catch (error) {
        console.error('Ошибка при получении счетчиков команд:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('teams-total-badge')) {
        updateTeams();
        setInterval(updateTeams, 30000);
    }
});
