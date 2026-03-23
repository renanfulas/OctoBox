# Guia de Configuração: Evolution API + OctoBox

Este guia explica como conectar o **Evolution API** (Robô do WhatsApp) ao Webhook de Enquetes que acabamos de criar no OctoBox.

---

## 🛠️ Pré-requisitos

1.  **Instalar o Evolution API**: Ele roda como um servidor separado (geralmente via Docker ou Node.js).
    *   [Documentação Oficial da Evolution API](https://evolution-api.net/)
2.  **Conectar o WhatsApp**: Escanear o QR Code no Evolution API para ativar sua sessão.
3.  **Endereço Público**: O Evolution API precisa conseguir "conversar" com o seu OctoBox. Se você estiver rodando o OctoBox no `localhost`, vai precisar de uma ferramenta como o **ngrok** para criar uma URL pública temporária (ex: `https://meu-octobox.ngrok-free.app`).

---

## 🔌 Passo a Passo da Conexão

Para automatizar a conexão, você pode rodar o script abaixo para **Registrar o Webhook** no Evolution de forma automática.

### 📝 Script de Vinculação (`connect_evolution.py`)

Crie um arquivo chamado `connect_evolution.py` na raiz do projeto e preencha com as suas credenciais reais da Evolution API:

```python
import requests
import json

# 1. Configurações da sua Evolution API
EVOLUTION_URL = "http://localhost:8080" # URL onde o Evolution roda
EVOLUTION_API_KEY = "SUA_API_KEY_AQUI" # Chave secreta do Evolution
INSTANCE_NAME = "Instancia_OctoBox"       # Nome da sua instancia do WhatsApp

# 2. Configurações do seu OctoBox
# (IMPORTANTE: Se for rodar local, use a URL do ngrok para o Evolution conseguir acessar!)
OCTOBOX_WEBHOOK_URL = "https://SEU-NGROK.ngrok-free.app/api/v1/integrations/whatsapp/webhook/poll-vote/"

def cadastrar_webhook():
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY
    }

    # Payload para o Evolution API
    payload = {
        "enabled": True,
        "url": OCTOBOX_WEBHOOK_URL,
        "events": [
            "MESSAGES_UPSERT", # Escuta novas mensagens
            "POLL_VOTES"       # <-- O evento crucial para a enquete! (Se a versao suportar)
        ]
    }

    endpoint = f"{EVOLUTION_URL}/webhook/set/{INSTANCE_NAME}"

    try:
        print(f"🔗 Conectando Webhook no Evolution ({OCTOBOX_WEBHOOK_URL})...")
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        
        if response.status_code in [200, 201]:
             print("✅ Webhook cadastrado com SUCESSO na Evolution API!")
             print("Agora, quando alguém votar na enquete, o Evolution vai avisar o OctoBox.")
        else:
             print(f"❌ Erro ao cadastrar: {response.status_code}")
             print(response.text)
             
    except Exception as e:
        print(f"❌ Erro de Conexão: {e}")

if __name__ == "__main__":
    cadastrar_webhook()
```

---

## 💡 Como Testar no Mundo Real

1.  **Crie uma Enquete no Grupo pelo WhatsApp**: 
    *   Pergunta: `"Check in - Aula de Hoje"`
    *   Opções: `"18h"`, `"19h"`, `"20h"`
2.  **Peça para um Aluno votar** em `"18h"`.
3.  **O Fluxo**:
    *   O WhatsApp avisa o **Evolution API**.
    *   O Evolution dispara o `POST` para o seu **Webhook**.
    *   O OctoBox lê o telefone do aluno, bate com o horário da aula e **Marca a Presença** no Painel do Coach!

> [!NOTE]
> Dependendo da versão da Evolution API, alguns webhooks de poll vote podem ser lidos como `MESSAGES_UPSERT` (com tipo `pollVote`) ou um evento dedicado. O webhook que construímos já está preparado para processar payloads estruturados.
