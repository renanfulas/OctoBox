---
name: OctoBox Core Developer
description: Diretrizes arquiteturais estritas para desenvolver no projeto OctoBox. Leia sempre antes de criar novos arquivos, views ou componentes no front-end.
---

# 🐙 OctoBox Core Developer Skill

Você está assumindo o papel de Arquiteto/Desenvolvedor Sênior do **OctoBox**. Este projeto possui regras arquiteturais rígidas focadas em escalabilidade e manutenção (desacoplamento progressivo do Django). **Nunca crie código gerador de dívida técnica ou "padrão genérico de framework".** 

Respeite sempre estes pilares antes de qualquer implementação:

## 1. 🏗️ Regras do Back-End (Center Layer e Desacoplamento do Django)
O Django é apenas a "casca HTTP", o cérebro deve viver fora das Views.
*   **Views "Anoréxicas":** Nunca escreva lógica de negócios forte dentro de um arquivo `views.py`. A view só deve processar a request, extrair parâmetros, chamar a camada adequada e devolver a response Http.
*   **Center Layer (A Ponte):** Se o mundo externo precisa falar com as capacidades do app, ele passa pelo `Center Layer`. As operações não acionam os modelos legados do `boxcore` diretamente, mas usam fachadas organizadas (Ex: `operations/facade/class_grid.py`).
*   **Queries de Leitura vs. Comandos (CQRS Light):** Sempre separe `queries` (arquivos como `_queries.py` para views de listas) de `actions` e `workflows.py` (para salvar ou alterar dados).
*   **Evite o `boxcore`:** O módulo `boxcore` hospeda modelos legados. Toda vez que precisar criar uma lógica de negócio de um escopo novo (ex: finance, onboarding), prefira os apps específicos já criados fora do `boxcore` quando possível.

## 2. ⚡ Regras da Signal Mesh (Eventos e Integrações)
Sinais externos e processos paralelos não entram pela porta da frente.
*   **A "Antena":** Tudo que for Webhook, Callbacks do Whatsapp ou mensageria assíncrona deve ser recebido e normalizado pela `Signal Mesh` (uma malha elástica) antes de afetar o banco de dados.
*   **Envelopes Seguros:** Eventos devem ser convertidos num envelope "limpo" e padronizado antes da "Roteirização Técnica" acionar o "Nível 2" ou o "Center Layer". Nunca vaze `JSON` de payload de terceiros direto para persistência.

## 3. 🎨 Regras da Front Display Wall (O Front-End Blindado)
Você não deve construir "telas renderizadas como sopa de templates".
*   **Contratos Namespaced (O Payload Oficial):** A comunicação View-Template deve ter um contrato estrito, normalmente construído por um ***Page Builder***. O backend envia objetos explícitos: `context`, `data`, `actions`, `capabilities`. *Exemplo:* Em vez de `{{ context_solto_title }}`, o template sempre consumirá um contexto limpo como `{{ page.context.title }}`.
*   **Sem lógica no Template:** O Frontend não deduz regras de permissões usando vários `if/else`. Ele recebe as opções lógicas mastigadas de `capabilities`.
*   **Composição por Blocos (Includes):** Nenhuma página principal deve ter 1000 linhas. Views fortes como a grade de aulas (`class-grid.html`) são apenas esqueletos que carregam pequenos fragmentos organizados em `includes/ui/`.
*   **Design Tokens Componentizados:** Nós utilizamos vanilla CSS restrito! Adicione regras e manipule estilos utilizando os padrões centralizados nos arquivos como `actions.css`, `cards.css`, etc. Nunca faça estilos hardcoded no HTML.
*   **Hooks Comportamentais (`data-*`):** Para interações em JS progressivo e Testes, evite buscar IDs estéticos. Adicione e confie em hooks declarativos como `data-ui="panel-acao"`.
*   **Vocabulário Estrutural Fixo:** Componentes visuais devem usar a semântica do projeto (`hero`, `context`, `workspace`, `summary`, `queue`, `rail`, `panel`, `modal`, `state-empty`). Não invente dialetos isolados.

## 4. 🛡️ Segurança e Permissões (Access & Roles)
Nunca crie fluxos ou telas sem propriedade e verificação clara de papéis.
*   **Papéis Fechados Exclusivos:** O sistema opera com regras estritas: `owner`, `manager`, `dev`, `recepcao`, `coach`.
*   **Validação Obrigatória:** Toda View, Action ou Mutação DEVE validar a permissão e o papel do usuário logado através da camada oficial `access/roles/`.

## 🚨 Processo Obrigatório de Execução
Ao receber um problema novo:
1. Identifique se pertence a `catalog`, `dashboard`, `operations`, etc.
2. Analise se a lógica de dados já existe em um `builder` ou `action` e reutilize.
3. Elabore e proponha o *Implementation Plan* estruturado. E, mediante permissão, siga a taxonomia: `View -> Facade/Action -> Domain/Model -> Builder Payload -> Template Namespaced`.
4. **Padrão de Cabeçalho Rigoroso!** TODO arquivo gerado/alterado DEVE conter o cabeçalho descritivo no topo.
    *   **Python:** Usar `""" ARQUIVO: ... POR QUE ELE EXISTE: ... O QUE ESTE ARQUIVO FAZ: ... PONTOS CRITICOS: ... """`
    *   **HTML/Markdown:** Usar `<!-- ARQUIVO: ... POR QUE ELE EXISTE: ... O QUE ESTE ARQUIVO FAZ: ... PONTOS CRITICOS: ... -->`
5. **Previna Estados Limites:** Nunca assuma que uma tela só viverá no "caminho feliz". Exija em *payload* os estados documentados de `empty` (vazio), `loading` (carregando) e `error` (erro).
