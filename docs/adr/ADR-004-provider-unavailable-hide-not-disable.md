# ADR-004 — Provider indisponível: esconder, não desabilitar

**Status:** Aceito  
**Data:** 2026-04-21  
**Contexto:** Student OAuth onboarding polish

## Decisão

Botão de provider não configurado **some** da tela. Se nenhum provider estiver disponível, aparece o partial `provider_unavailable_block.html` com copy: "O login social está em manutenção. Fale com a recepção do seu box."

Nunca renderizar botão desabilitado (cinza/cursor-not-allowed).

## Por quê

- Botão cinza gera dúvida ("está quebrado? sou eu?")
- Sumir sem contexto gera confusão ("cadê o botão do Google?")
- Sumir com fallback informativo preserva confiança e direciona o usuário para uma ação concreta

## Consequências

- Template usa `{% if google_available %}` / `{% if apple_available %}` para renderizar botões
- Bloco de fallback extraído como partial reutilizável — um ponto de manutenção
- Contexto `google_available` e `apple_available` são booleanos computados na view a partir de settings
