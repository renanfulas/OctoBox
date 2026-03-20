/* 
   ARQUIVO: Lógica do Menu de Perfil.
   POR QUE ELE EXISTE: Controla a abertura, fechamento e interações do menu suspenso.
*/

document.addEventListener('DOMContentLoaded', function() {
    const profileTrigger = document.querySelector('.topbar-profile');
    const profileMenu = document.querySelector('.profile-dropdown');
    
    if (!profileTrigger || !profileMenu) return;

    // Toggle menu
    profileTrigger.addEventListener('click', function(e) {
        e.stopPropagation();
        profileMenu.classList.toggle('is-open');
    });

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!profileMenu.contains(e.target) && !profileTrigger.contains(e.target)) {
            profileMenu.classList.remove('is-open');
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            profileMenu.classList.remove('is-open');
        }
    });
});
