# QA da abertura do calendário do WOD — 22/10/2026

## Relato e reprodução

Relato: o calendário às vezes não abre quando a data já está preenchida.

O caminho principal de abertura passou no Chromium. Ao desativar
`HTMLInputElement.prototype.showPicker`, a regressão falhou em celular e desktop:
o clique programático do fallback não abriu corretamente o seletor e as teclas
passaram a editar segmentos da data. Na reprodução, a seleção esperada de
`02/11/2026` terminou em `21/12/2026`.

Os dois seletores do Smart Paste usavam implementações duplicadas que moviam um
input de data oculto para uma área de 1 px, chamavam `showPicker()` ou `click()` e
restauravam os estilos em `change`/`blur`. Cancelar ou confirmar a mesma data pode
não emitir `change`, tornando essa restauração dependente do foco do navegador.

## Correção

- Um include compartilhado mantém o input nativo renderizado sobre a superfície
  visual do calendário. O clique/toque chega diretamente ao input, com ou sem
  a API `showPicker`; a abertura não altera `hidden`, estilos ou temporizadores.
- O controle fica na ordem de Tab, tem nome acessível e foco visível. Enter e
  Espaço abrem o seletor quando `showPicker` está disponível. A digitação manual
  da data continua disponível.
- Semana inicial e semana de destino usam o mesmo componente, inclusive após
  atualização HTMX da prévia. O campo enviado e a data exibida continuam sincronizados.
- O botão da semana inicial usa “Calendário”, reduzindo o truncamento do rótulo.

## Verificação

Regressões exercitam cancelamentos repetidos, confirmação da data existente,
seleção da semana seguinte, mouse, toque emulado, teclado, disponibilidade ou
ausência de `showPicker`, ano completo e ajuste para segunda-feira. O fluxo de
CrossFit/HYROX troca a semana de destino duas vezes, com renovação HTMX entre elas.

Resultado da bateria completa de navegador: **47 cenários passaram**. As
verificações Django, sintaxe dos dois JavaScripts, `git diff --check` e
`check_static_drift --strict` também passaram.

Backend do Smart Paste: **69 testes e 7 subtests passaram**.

Ambiente: PostgreSQL e Redis locais em Docker, Django em schema de teste e
Chromium. Toque emulado não substitui uma verificação em Safari/iPhone físico.
As alterações precisam ser publicadas para chegar ao aplicativo em produção.
