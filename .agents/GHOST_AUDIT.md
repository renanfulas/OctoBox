# 👻 Ghost Audit: Protocolo de Excelência 175 QI

Este workflow executa uma auditoria automática focada em:

- Estilos inline que ignoram o Design System.
- Heurísticas de N+1 (loops com `.count()`/`.exists()` ou acesso a atributos relacionados dentro de loops).
- Uso de `aggregate()` sem cache aparente.
- Checagens básicas de acessibilidade (IDs duplicados, elementos interativos sem `aria-`/`title`).

Como rodar:

```powershell
python .agents\scripts\ghost_audit.py --base-path . --report .agents/ghost_audit_report.json
```

Saída:
- Um arquivo JSON em `.agents/ghost_audit_report.json` com detalhes.
- Resumo impresso no console com classificação: 🟢 Limpo / 🟡 Alerta / 🔴 Crítico.

Critérios rápidos:
- Todo `style=` que defina `margin`, `padding`, `color`, `font-size` ou `display` deverá ser sinalizado para migração para `tokens.css`.
- Loops que contenham `.count()` ou `.exists()` próximos são candidatos a N+1.
- `aggregate()` sem cache identificado será listado para avaliação.

Notas:
- O scanner é heurístico e não substitui uma revisão manual aprofundada.
- Ajuste `IGNORED_DIRS` no topo do script se precisar pular outros diretórios.
