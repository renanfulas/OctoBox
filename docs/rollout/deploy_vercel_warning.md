# Alertas para Deploy do OctoBox na Vercel ⚠️

Embora o deploy na Vercel seja ótimo para testes rápidos, o OctoBox é um **módulo operacional denso** e o modelo Serverless da Vercel impõe limitações críticas.

---

### 🚨 Impedimentos Imediatos (Para Funcionar)

1.  **Banco de Dados Externo Obrigatório**:
    *   O **SQLite não funciona** na Vercel (os arquivos são apagados a cada clique).
    *   Você **precisa** de um Banco Postgres na nuvem (ex: Supabase, Neon) e colocar a `DATABASE_URL` nas variáveis de ambiente da Vercel.
2.  **Upload de Arquivos (Imagens)**:
    *   Qualquer imagem enviada via sistema será perdida em minutos. É obrigatório plugar um **AWS S3** ou **Cloudinary** para mídias.

---

### 🐢 Limitações de Longo Prazo (Para o SaaS)

*   **Tempo de Execução (Timeout)**: No plano grátis da Vercel, se uma conta ou processamento demorar mais de **10 segundos**, a Vercel derruba a conexão.
*   **Sem Background Workers**: O OctoBox não consegue rodar tarefas agendadas (como ler enquetes no loop, rodar Celery) nativamente o tempo todo. Ele depende de gatilhos externos da própria Vercel.

---
> [!IMPORTANT]
> **Recomendação**: Para o OctoBox + Evolution API rodarem em harmonia de forma **leve, barata e sem dor de cabeça**, o **VPS com Docker** (que discutimos da Hostinger) é **10x superior** arquiteturalmente para o seu modelo de negócio.
