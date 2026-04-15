<!--
ARQUIVO: origem da fonte Manrope local.

POR QUE ELE EXISTE:
- registra a decisao de hospedar a fonte critica sem dependencia externa em runtime.
- evita que a equipe volte a usar Google Fonts para o heading/body critico sem perceber o custo de LCP.
-->

# Manrope

`manrope-latin-variable.woff2` e o subset latino variavel de Manrope, usado como fonte critica local do shell.

Origem do arquivo:

1. Google Fonts static font host, familia Manrope v20.
2. Peso variavel `400 800`.
3. Subset `latin`.
4. Licenca local registrada em `OFL.txt`.

Contrato de performance:

1. O navegador deve carregar este arquivo por `preload` no `base.html`.
2. O CSS deve consumir o arquivo por `@font-face` em `static/css/design-system/tokens.css`.
3. Nao use `fonts.googleapis.com` ou `fonts.gstatic.com` em runtime.

Observacao:

`Object Sans` continua no token de display como primeira preferencia, mas precisa de um arquivo licenciado local antes de receber `@font-face` ou preload proprio.
