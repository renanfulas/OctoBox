# Protótipo: Import Preview

Arquivos criados para um protótipo leve de pré-visualização de importação CSV.

- `index.html` — UI principal (seletor de arquivo, preview, validação, import simulado)
- `styles.css` — estilos básicos do protótipo
- `app.js` — parsing CSV simples, validação por linha e simulação de import

Como usar:
1. Abra `prototypes/import_preview/index.html` no navegador.
2. Selecione um arquivo CSV com cabeçalho.
3. Clique em "Pré-visualizar" para ver até 50 linhas e erros detectados.
4. Clique em "Iniciar importação" para simular o processamento e ver progresso.

Observações:
- Parser CSV aqui é simples (protótipo). Para produção, usar uma biblioteca robusta (ex: PapaParse).
- Integração backend: criar endpoint assíncrono que aceite upload, retorne job id e permita polling/websocket para progresso.
