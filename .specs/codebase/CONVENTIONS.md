# Coding Conventions - OctoBOX

Este documento estabelece as regras de estilo e padrÃµes de engenharia seguidos no projeto para garantir consistÃªncia e rastreabilidade.

## 1. CabeÃ§Ã¡rios de Arquivos (Self-Documentation)

Todo arquivo importante (especialmente em `model_definitions.py` ou `services.py`) deve comeÃ§ar com um bloco de comentÃ¡rios estruturado:

```python
"""
ARQUIVO: [descriÃ§Ã£o curta]
POR QUE ELE EXISTE: [contexto de negÃ³cio ou arquitetura]
O QUE ESTE ARQUIVO FAZ: [lista enumerada de responsabilidades]
PONTOS CRÃTICOS: [avisos sobre seguranÃ§a, performance ou migraÃ§Ãµes]
"""
```

## 2. Nomenclatura e Idioma

*   **CÃ³digo (LÃ³gica):** InglÃªs para Classes, FunÃ§Ãµes, VariÃ¡veis e Tabelas.
    *   Ex: `Student`, `Enrollment`, `generate_blind_index`.
*   **Interface e Enums:** PortuguÃªs do Brasil para strings visÃ­veis ao usuÃ¡rio e labels de enums.
    *   Ex: `MALE = 'male', 'Masculino'`.
*   **ComentÃ¡rios de Arquivo:** PortuguÃªs do Brasil (seguindo o padrÃ£o do cabeÃ§Ã¡rio).

## 3. PadrÃµes de Django e Modelos

*   **App Labels:** Modelos devem usar `app_label = HISTORICAL_BOXCORE_APP_LABEL` para preservar o schema legado em `boxcore`.
*   **Base Models:** Estender preferencialmente `TimeStampedModel` do app `model_support`.
*   **Enums:** Utilizar `models.TextChoices` para clareza e semÃ¢ntica.
*   **Metadados:** Todo modelo deve ter `class Meta` e `__str__` bem definidos.

## 4. SeguranÃ§a (PII - Personally Identifiable Information)

*   **Dados SensÃ­veis:** CPF, Telefone e outros dados pessoais devem usar `EncryptedCharField` ou similar.
*   **Busca:** Nunca buscar diretamente por campos criptografados. Usar o `phone_lookup_index` ou campos de Ã­ndice determinÃ­stico equivalentes.
*   **Blind Index:** Seguir o padrÃ£o `v1:<hash>` para facilitar upgrades futuros de algoritmo de hash.

## 5. Front-end (Vanilla First)

*   **JavaScript:** Preferir Vanilla JS moderno acessando elementos via IDs Ãºnicos e descritivos.
*   **CSS:** Utilizar CSS puro. VariÃ¡veis CSS (`--color-primary`) devem ser definidas no nÃ­vel do app ou globalmente.
*   **HTML:** Usar semÃ¢ntica HTML5 e garantir que elementos interativos tenham IDs para testes automatizados.

## 6. Qualidade de CÃ³digo

*   **Linting:** Seguir as regras de `.eslintrc.json`, `.stylelintrc.json` e Prettier.
*   **AtÃ´mico:** Commits devem ser atÃ´micos e seguir o propÃ³sito da tarefa.
*   **Traceabilidade:** ComentÃ¡rios devem explicar o "porquÃª" (decisÃ£o) e nÃ£o o "como" (que o cÃ³digo jÃ¡ mostra).

## 7. Contratos de Snapshot e Page Payload (JSON-First)

*   **Snapshot/Page Payload:** Todo dado que entra em `snapshot`, `cache` compartilhado ou `page payload` deve ser serializÃ¡vel em JSON.
*   **Nunca inserir ORM cru:** NÃ£o colocar `QuerySet`, instÃ¢ncias de `Model` do Django ou objetos complexos nesses contratos.
*   **Formato esperado:** Preferir `dict`, `list`, `str`, `int`, `float`, `bool`, `null`, datas e decimais compatÃ­veis com `DjangoJSONEncoder`.
*   **Ownership:** A camada de query pode falar com o ORM; a borda do snapshot deve devolver apenas dado pronto para cache, transporte e renderizaÃ§Ã£o.

## 8. Metodologia C.O.R.D.A. (DiagnÃ³stico EstratÃ©gico)

Para toda evoluÃ§Ã£o de produto ou fechamento de fase (ex: Beta), utilizar o framework C.O.R.D.A. para alinhar expectativas e aÃ§Ãµes:

*   **C - Contexto:** Onde estamos e o que acaba de mudar.
*   **O - Objetivo:** Onde queremos chegar e o que define o sucesso desta fase.
*   **R - Riscos:** O que pode quebrar a confianÃ§a ou a operaÃ§Ã£o no caminho.
*   **D - DireÃ§Ã£o:** Qual o rumo prioritÃ¡rio (ex: tirar pedras vs passar verniz).
*   **A - AÃ§Ãµes:** Plano enxuto de execuÃ§Ã£o (Ondas).
