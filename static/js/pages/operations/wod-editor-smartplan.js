/*
ARQUIVO: interacoes leves do card SmartPlan e do popup de gating no editor de WOD.

POR QUE ELE EXISTE:
- desacopla DOM do template Django para que o popup possa fechar sem reload e o
  botao "Como funciona?" possa explicar o fluxo BYOLLM.

O QUE ESTE ARQUIVO FAZ:
1. fecha o popup quando overlay ou botao primario "Voltar e formatar" e clicado.
2. devolve o foco ao textarea apos fechar o popup.
3. mostra um modal nativo (alert) explicando o fluxo no clique de "Como funciona?".

PONTOS CRITICOS:
- nao toca em estado server-side; popup e renderizado pelo Django via flag de contexto.
- "Publicar mesmo assim" e form POST (server-side); JS nao precisa interceptar.
- mantem-se vanilla JS, sem framework, alinhado ao restante do projeto.
*/

(function () {
    'use strict';

    function onReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback, { once: true });
        } else {
            callback();
        }
    }

    function closePopup() {
        var popup = document.querySelector('[data-panel="wod-smartplan-popup"]');
        if (!popup) {
            return;
        }
        popup.remove();
        var textarea = document.querySelector('[data-field="smartplan-paste"]');
        if (textarea) {
            textarea.focus();
            // posiciona cursor no final para edicao rapida
            var len = textarea.value.length;
            try {
                textarea.setSelectionRange(len, len);
            } catch (err) {
                // textarea pode estar fora do DOM em casos raros; ignorar.
            }
        }
    }

    function showHelp() {
        var lines = [
            'Como funciona o SmartPlan:',
            '',
            '1. Clique em "Abrir SmartPlan no ChatGPT" para abrir o GPT customizado em uma nova aba.',
            '2. Cole o WOD bruto no GPT e envie.',
            '3. Copie a resposta inteira (com os marcadores === WOD NORMALIZADO === e === JSON ESTRUTURADO ===).',
            '4. Cole aqui no textarea e clique "Publicar com SmartPlan".',
            '5. Se o formato bater, o WOD vira tier rico para o aluno: videos, RM, deteccao de PR.',
            '6. Se nao bater, o sistema avisa antes de publicar.',
        ];
        window.alert(lines.join('\n'));
    }

    function bindEvents() {
        document.addEventListener('click', function (event) {
            var target = event.target;
            if (!target || !target.closest) {
                return;
            }

            var closeTrigger = target.closest('[data-action="wod-smartplan-popup-close"]');
            if (closeTrigger) {
                event.preventDefault();
                closePopup();
                return;
            }

            var helpTrigger = target.closest('[data-action="wod-smartplan-help"]');
            if (helpTrigger) {
                event.preventDefault();
                showHelp();
                return;
            }
        });

        // Esc fecha o popup quando aberto.
        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') {
                return;
            }
            var popup = document.querySelector('[data-panel="wod-smartplan-popup"]');
            if (popup) {
                event.preventDefault();
                closePopup();
            }
        });

        // Auto-foco no textarea quando o popup acabou de aparecer (recem-renderizado pelo server).
        var popup = document.querySelector('[data-panel="wod-smartplan-popup"]');
        if (popup) {
            var primary = popup.querySelector('.wod-smartplan-popup__primary');
            if (primary) {
                primary.focus();
            }
        }
    }

    onReady(bindEvents);
})();
