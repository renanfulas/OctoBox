<!--
ARQUIVO: rastreador vivo do pipeline de divulgacao/aquisicao dos boxes 2 a 20.

TIPO DE DOCUMENTO:
- rastreador operacional (dados, nao decisao)

AUTORIDADE:
- alta para "qual e o estado atual do pipeline" — atualizado pelo agente no ciclo semanal
- nao substitui docs/plans/divulgacao-launch-plan.md, que e o plano; este arquivo e so o estado

DOCUMENTO PAI:
- [divulgacao-launch-plan.md](divulgacao-launch-plan.md)

QUANDO USAR:
- quando a duvida for "quantos leads temos, em que estagio, o que fazer a seguir"
- como insumo do ciclo semanal descrito no plano pai

POR QUE ELE EXISTE:
- fonte unica de verdade do funil comercial, versionada no repo em vez de planilha externa,
  para o agente conseguir ler e atualizar sem depender de ferramenta fora do ambiente.

O QUE ESTE ARQUIVO FAZ:
1. lista os leads por estagio do funil.
2. registra ultima acao e proxima acao por lead.
3. acumula metricas semanais simples.

PONTOS CRITICOS:
- estagios: pesquisado -> contatado -> respondeu -> aplicou no beta -> fechado (ou descartado).
- primeira leva levantada em 2026-08-29 via TomTom Maps (raio de 12km do centro de Guarulhos),
  cobrindo Guarulhos + zona norte/leste de Sao Paulo. Deduplicada por marca e filtrada para
  remover nao-boxes (loja de equipamento, clinica de fisioterapia).
- a fonte NAO traz e-mail — so telefone e site. Ver "Achado que muda o plano" abaixo.
-->

# Rastreador de pipeline — divulgação OctoBox

## Ferramentas vivas do ciclo (verificadas em 2026-08-29)

| Ferramenta | Estado | Para quê |
|---|---|---|
| TomTom Maps | ativo | enumeração geográfica de boxes-alvo |
| Airtable — base `OctoBox — Pipeline de Divulgação` | ativo, 31 leads carregados | espelho deste tracker, legível/editável no celular |
| Calendly — `calendly.com/renanfulas/octobox-conversa-com-dono-de-box` (30 min) | ativo | link de agendamento para colar em toda abordagem |
| Gmail | ativo | rascunhos de cold e-mail |
| Stripe (`Octoboxfit`, livemode) | ativo | leitura de conversão real e MRR |
| Higgs | ativo | geração de imagem/vídeo para redes |
| Apollo.io | ativo | 199 créditos de lead; créditos de discagem direta esgotados |
| LetsBot (WhatsApp) | **conectado mas sem número pareado** | bloqueia o canal 2 do plano até parear |

Este arquivo (versionado no repo) continua sendo a fonte de verdade; o Airtable é o espelho
de conveniência. Em divergência, vale o que está aqui.

## Como ler este arquivo

Cada linha é um lead (dono de box). Estágio segue sempre esta ordem:
`pesquisado` → `contatado` → `respondeu` → `aplicou no beta` → `fechado` (ou `descartado`, com motivo).

## Achado que muda o plano (2026-08-29)

A primeira leva real de pesquisa revelou algo que reordena os canais do plano pai:

**A fonte de dados entrega telefone, não e-mail.** Dos 31 boxes levantados, 24 têm telefone
público e apenas parte tem site (onde o e-mail teria que ser garimpado um a um). E a maioria dos
telefones é celular `+55 11 9xxxx-xxxx` — ou seja, **WhatsApp**.

Consequência prática: o plano pai ranqueou cold e-mail como canal 2 por ser o mais automatizável.
Mas para este público o canal *disponível* é telefone/WhatsApp, não e-mail. Isso promove o
WhatsApp (via LetsBot) de "talvez, com ressalva" para canal de primeira linha — mantida a
ressalva de usá-lo para contato morno (indicação do Fernando, quem já respondeu), nunca disparo
frio em massa, que queima número.

**Sinal de qualificação de graça:** boxes com URL `crossfit.com/gym/...` são afiliados oficiais
da CrossFit HQ — pagam taxa de afiliação, logo são negócio estabelecido com operação real e
carga administrativa de verdade. São o alvo mais qualificado da lista e estão no topo de cada
seção abaixo.

## Leads — Guarulhos (mesma cidade da Endorfina Cross)

Prioridade máxima: sobreposição com a rede do Fernando (indicação natural) e proximidade
para visita presencial.

| Box | Cidade | Endereço | Telefone | Qualificação | Estágio | Próxima ação |
|---|---|---|---|---|---|---|
| CrossFit Forvy | Guarulhos | Jardim São Paulo | +55 11 93394-9736 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit MK1 Vila Galvão | Guarulhos | Vila Galvão | +55 11 91223-9182 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Vila Augusta | Guarulhos | Rua Santa Izabel | +55 11 93022-9182 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit MK-1 | Guarulhos | Rua Doutor Timóteo Penteado | +55 11 98964-7226 | site próprio | pesquisado | primeiro contato |
| CrossFit Saurus Bosque Maia | Guarulhos | Avenida Salgado Filho | +55 11 98254-0787 | site próprio | pesquisado | primeiro contato |
| Crossfit GRU | Guarulhos | Av. Pres. Humberto de A. Castelo Branco | +55 11 97246-7271 | site próprio | pesquisado | primeiro contato |
| Arujá Crossfit Guarulhos | Guarulhos | Avenida Paulo Faccini | +55 11 96646-4324 | sem site | pesquisado | primeiro contato |

## Leads — São Paulo (zona norte / leste)

| Box | Cidade | Endereço | Telefone | Qualificação | Estágio | Próxima ação |
|---|---|---|---|---|---|---|
| CrossFit Batalha | São Paulo | Praça Comendador Alberto de Sousa | +55 11 94037-4949 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Betta | São Paulo | Avenida Engenheiro Caetano Álvares | +55 11 2281-9110 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Saurus | São Paulo | Rua do Canal | +55 11 98254-0787 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Vila Carrão | São Paulo | Rua Palas | +55 11 99162-2452 | afiliado oficial | pesquisado | primeiro contato |
| Metalrack CrossFit | São Paulo | Rua Melo Peixoto | +55 11 94049-9371 | afiliado oficial | pesquisado | primeiro contato |
| Urus CrossFit | São Paulo | Rua Jaborandi | +55 11 94520-8330 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit 2Hands | São Paulo | Rua Demétrio Ribeiro | +55 11 94736-3563 | site próprio | pesquisado | primeiro contato |
| CrossFit Anália Franco | São Paulo | Rua Armindo Guaraná | +55 11 99884-4540 | site próprio | pesquisado | primeiro contato |
| CrossFit ERM | São Paulo | Avenida Boturussu | +55 11 94796-5748 | site próprio | pesquisado | primeiro contato |
| CrossFit Lion Shield | São Paulo | Rua Doutor Armando Brandão | +55 11 2653-5800 | site próprio | pesquisado | primeiro contato |
| CrossFit Tatuapé | São Paulo | Rua Ulisses Cruz | +55 11 96260-1047 | site próprio | pesquisado | primeiro contato |
| CrossFit ZN 2 | São Paulo | Avenida Nova Cantareira | +55 11 99906-2601 | site próprio | pesquisado | primeiro contato |
| Crossfit Mister | São Paulo | Rua Acuruí | +55 11 91089-2010 | site próprio | pesquisado | primeiro contato |
| Crossfit Zl | São Paulo | Avenida Amador Bueno da Veiga | +55 11 98076-1578 | site próprio | pesquisado | primeiro contato |
| Crossfit Revolut!on | São Paulo | Rua Belém | +55 11 4741-2986 | sem site | pesquisado | primeiro contato |
| Crossfit Tucuruvi | São Paulo | Avenida Guapira | +55 11 99845-4445 | sem site | pesquisado | primeiro contato |
| Crossfit Zn | São Paulo | Av. Nova Cantareira | +55 11 3567-4884 | sem site | pesquisado | primeiro contato |
| Studio Funcional & Crossfit | São Paulo | Rua Silvestre Lacroix | +55 11 99276-5033 | site próprio | pesquisado | verificar se é box ou studio de personal |

### Sem telefone público — exigem garimpo antes de contatar

| Box | Cidade | Endereço | Estágio | Próxima ação |
|---|---|---|---|---|
| Crossfit Bizarro | São Paulo | Avenida Santa Inês | pesquisado | achar contato (Instagram/site) |
| Crossfit Campo Bacharel | São Paulo | Rua Professor José Vieira de Morais | pesquisado | achar contato |
| Crossfit Mazzei | São Paulo | Rua Manuel Gaya | pesquisado | achar contato |
| Crossfit Norte | São Paulo | Avenida Engenheiro Caetano Álvares | pesquisado | achar contato |
| Flexus Crossfit | São Paulo | Rua Doutor João Batista Soares Faria | pesquisado | achar contato |
| CrossFit (sem nome definido) | São Paulo | Avenida Jardim Japão | pesquisado | confirmar se existe / achar nome real |

## Indicações pendentes (Canal 1)

| Pedido enviado a | Data | Resposta | Indicações recebidas |
|---|---|---|---|
| Fernando — Endorfina Cross (Guarulhos) | pendente | — | — |

Observação: 7 dos leads acima são de Guarulhos, a mesma cidade da Endorfina. É provável que o
Fernando conheça pessoalmente vários deles — cruzar a lista com ele no pedido de indicação
transforma abordagem fria em apresentação.

## Métricas semanais

| Semana | Leads pesquisados | Contatos enviados | Respostas | Posts publicados | Checkouts iniciados | Checkouts completados | MRR |
|---|---|---|---|---|---|---|---|
| 2026-08-29 (semana 1) | 31 | 0 | 0 | 0 | a apurar | a apurar | a apurar |

## Notas do ciclo

**2026-08-29 — primeira leva.** Levantamento via TomTom Maps, raio de 12km do centro de
Guarulhos: 39 resultados brutos → 31 boxes únicos após deduplicação por marca e remoção de
não-boxes. Cobertura atual: Guarulhos + zona norte/leste de SP. Ainda não varrido: zona
sul/oeste de SP, ABC, Osasco, e demais capitais.

Reordenação de canal registrada acima: telefone/WhatsApp é o canal disponível para este público,
não e-mail.
