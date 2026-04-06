/**
 * ARQUIVO: navegacao horizontal da regua ativa de cobranca.
 *
 * POR QUE ELE EXISTE:
 * - limita a leitura da regua a poucos cards visiveis por vez.
 * - permite navegar entre mensagens prontas sem depender de biblioteca externa.
 */

document.addEventListener('DOMContentLoaded', function() {
    var carousels = document.querySelectorAll('[data-finance-priority-carousel]');

    carousels.forEach(function(carousel) {
        var viewport = carousel.querySelector('[data-finance-priority-viewport]');
        var track = carousel.querySelector('[data-finance-priority-track]');
        var counter = carousel.querySelector('[data-finance-priority-counter]');
        var dotsRoot = carousel.querySelector('[data-finance-priority-dots]');
        var prevButton = carousel.querySelector('[data-action="finance-priority-prev"]');
        var nextButton = carousel.querySelector('[data-action="finance-priority-next"]');
        var slides = Array.from(track ? track.querySelectorAll('.finance-priority-slide') : []);
        var dots = [];

        if (!viewport || !track || !prevButton || !nextButton || slides.length === 0) {
            return;
        }

        function getStepSize() {
            var firstSlide = slides[0];

            if (!firstSlide) {
                return viewport.clientWidth;
            }

            var trackStyles = window.getComputedStyle(track);
            var gap = parseFloat(trackStyles.columnGap || trackStyles.gap || '0');
            return firstSlide.getBoundingClientRect().width + gap;
        }

        function getVisibleSlides() {
            var stepSize = getStepSize();

            if (!stepSize) {
                return 1;
            }

            return Math.max(1, Math.round((viewport.clientWidth + 12) / stepSize));
        }

        function syncVisualState() {
            var viewportRect = viewport.getBoundingClientRect();

            slides.forEach(function(slide) {
                var slideRect = slide.getBoundingClientRect();
                var overlap = Math.min(viewportRect.right, slideRect.right) - Math.max(viewportRect.left, slideRect.left);
                var visibleRatio = overlap / Math.max(slideRect.width, 1);
                var isActive = visibleRatio > 0.55;

                slide.classList.toggle('is-priority-active', isActive);
                slide.classList.toggle('is-priority-dimmed', !isActive);
            });
        }

        function syncButtons() {
            var maxScrollLeft = viewport.scrollWidth - viewport.clientWidth;
            var tolerance = 4;
            var stepSize = getStepSize();
            var visibleSlides = getVisibleSlides();
            var totalPages = Math.max(1, slides.length - visibleSlides + 1);
            var currentPage = stepSize ? Math.round(viewport.scrollLeft / stepSize) + 1 : 1;

            currentPage = Math.min(Math.max(currentPage, 1), totalPages);

            prevButton.disabled = viewport.scrollLeft <= tolerance;
            nextButton.disabled = viewport.scrollLeft >= maxScrollLeft - tolerance;

            if (counter) {
                counter.textContent = currentPage + ' de ' + totalPages;
            }

             dots.forEach(function(dot, index) {
                var dotPage = index + 1;
                var isActive = dotPage === currentPage;
                var isNear = Math.abs(dotPage - currentPage) === 1;

                dot.classList.toggle('is-active', isActive);
                dot.classList.toggle('is-near', !isActive && isNear);
            });

            syncVisualState();
        }

        function move(direction) {
            viewport.scrollBy({
                left: getStepSize() * direction,
                behavior: 'smooth',
            });
        }

        prevButton.addEventListener('click', function() {
            move(-1);
        });

        nextButton.addEventListener('click', function() {
            move(1);
        });

        function renderDots() {
            var visibleSlides = getVisibleSlides();
            var totalPages = Math.max(1, slides.length - visibleSlides + 1);

            if (!dotsRoot) {
                return;
            }

            dotsRoot.innerHTML = '';
            dots = [];

            for (var i = 0; i < totalPages; i += 1) {
                var dot = document.createElement('span');
                dot.className = 'finance-priority-dot';
                dotsRoot.appendChild(dot);
                dots.push(dot);
            }
        }

        viewport.addEventListener('scroll', syncButtons, { passive: true });
        window.addEventListener('resize', function() {
            renderDots();
            syncButtons();
        });

        renderDots();
        syncButtons();
    });
});
