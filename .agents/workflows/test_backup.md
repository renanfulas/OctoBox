---
description: Testar a saúde do sistema e realizar o backup do banco de dados principal.
---

Este workflow automatiza a validação da saúde do sistema rodando os testes integrados e, se tudo passar, ele copia o seu banco de dados atual (`db.sqlite3`) para uma pasta segura, adicionando um registro de data e hora para você não perder histórico.

// turbo-all

1. Executar os testes automatizados para garantir que nenhuma tela quebrou.
```powershell
.\.venv\Scripts\python manage.py test
```

2. Criar a pasta de backups se ela não existir.
```powershell
New-Item -ItemType Directory -Force -Path backups
```

3. Obter a data atual formatada para usar como sufixo.
```powershell
$date = Get-Date -Format "yyyyMMdd_HHmmss"
```

4. Copiar o banco de dados principal de forma segura.
```powershell
Copy-Item db.sqlite3 "backups\db_$date.sqlite3" -Force
```

5. Reportar ao usuário que o Workflow foi um sucesso, garantindo uma rotina tranquila de desenvolvimento.
