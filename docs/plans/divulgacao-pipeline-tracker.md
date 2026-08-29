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
- 4 varreduras via TomTom Maps em 2026-08-29 cobrindo Guarulhos, ZN/ZL, zona sul, ABC e
  zona oeste/Osasco. 119 boxes unicos apos deduplicacao por marca e remocao de nao-boxes
  (loja de equipamento, clinica de fisioterapia, fabricante de acessorio).
- a fonte NAO traz e-mail — so telefone e site. Ver "Achado que muda o plano" abaixo.
-->

# Rastreador de pipeline — divulgação OctoBox

## Ferramentas vivas do ciclo (verificadas em 2026-08-29)

| Ferramenta | Estado | Para quê |
|---|---|---|
| TomTom Maps | ativo | enumeração geográfica de boxes-alvo |
| Airtable — base `OctoBox — Pipeline de Divulgação` | **119 de 119 leads sincronizados** (2026-08-29) | espelho deste tracker, legível/editável no celular |
| Calendly — `calendly.com/renanfulas/octobox-conversa-com-dono-de-box` (30 min) | ativo | link de agendamento para colar em toda abordagem |
| Gmail | ativo | rascunhos de cold e-mail |
| Stripe (`Octoboxfit`, livemode) | **caiu de novo, precisa reautorizar** | leitura de conversão real e MRR — bloqueado até reconectar |
| Higgs | ativo | geração de imagem/vídeo para redes |
| Apollo.io | ativo | 199 créditos de lead; créditos de discagem direta esgotados |
| LetsBot (WhatsApp) | pareado, mas sem contatos carregados ainda | canal 2 do plano — pronto para uso morno assim que houver conversa iniciada |

Este arquivo (versionado no repo) continua sendo a fonte de verdade; o Airtable é o espelho
de conveniência. Em divergência, vale o que está aqui.

## Como ler este arquivo

Cada linha é um lead (dono de box). Estágio segue sempre esta ordem:
`pesquisado` → `contatado` → `respondeu` → `aplicou no beta` → `fechado` (ou `descartado`, com motivo).

## Achado que muda o plano (2026-08-29)

A primeira leva real de pesquisa revelou algo que reordena os canais do plano pai:

**A fonte de dados entrega telefone, não e-mail.** Dos 119 boxes levantados, a grande maioria tem telefone
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

## Onde o gargalo está agora

Com 119 leads mapeados e teto de ~19 vagas na Fase 1, **a restrição deixou de ser encontrar box e
passou a ser escolher quem abordar primeiro**. Varrer mais região tem retorno decrescente daqui em
diante; o que move o ponteiro agora é contato, não pesquisa. Próxima varredura só faz sentido se
os tiers abaixo se esgotarem sem converter.

Ordem de ataque: Tier 1 → Tier 2 → Tier 3, e dentro de cada tier começar por quem tem telefone.

## Tier 1 — Guarulhos (7 boxes)

Prioridade máxima: mesma cidade da Endorfina Cross. Sobreposição provável com a rede do Fernando
(indicação natural) e proximidade para visita presencial.

| Box | Cidade | Bairro | Telefone | Qualificação | Estágio | Próxima ação |
|---|---|---|---|---|---|---|
| Arujá Crossfit Guarulhos | Guarulhos | Centro | +55 11 96646-4324 | sem site | pesquisado | primeiro contato |
| CrossFit Forvy | Guarulhos | Centro | +55 11 93394-9736 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit MK-1 | Guarulhos | Picanço | +55 11 98964-7226 | site próprio | pesquisado | primeiro contato |
| CrossFit MK1 Vila Galvão | Guarulhos | Vila Galvão | +55 11 91223-9182 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Saurus Bosque Maia | Guarulhos | Vila Rio | +55 11 98254-0787 | site próprio | pesquisado | primeiro contato |
| CrossFit Vila Augusta | Guarulhos | Vila Augusta | +55 11 93022-9182 | afiliado oficial | pesquisado | primeiro contato |
| Crossfit GRU | Guarulhos | Vila Augusta | +55 11 97246-7271 | site próprio | pesquisado | primeiro contato |

## Tier 2 — Afiliados oficiais CrossFit HQ, fora de Guarulhos (34 boxes)

Pagam taxa de afiliação à CrossFit HQ: negócio estabelecido, com operação e carga administrativa
reais. É o perfil que mais se parece com a Endorfina.

| Box | Cidade | Bairro | Telefone | Qualificação | Estágio | Próxima ação |
|---|---|---|---|---|---|---|
| CrossFit Barueri | Barueri | Alphaville | +55 11 97503-7921 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Rudge Ramos | São Bernardo do Campo | Anchieta | — | afiliado oficial | pesquisado | achar contato |
| Soren CrossFit | São Bernardo do Campo | Anchieta | +55 11 95941-3662 | afiliado oficial | pesquisado | primeiro contato |
| B4thor CrossFit | São Paulo | Campo Belo | +55 11 98244-0880 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit | São Paulo | Pinheiros | +55 11 97358-5345 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Azteca | São Paulo | Santo Amaro | +55 11 97205-9595 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Batalha | São Paulo | Jacana | +55 11 94037-4949 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Beco | São Paulo | Vila Leopoldina | +55 11 95240-4007 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Betta | São Paulo | Mandaqui | +55 11 2281-9110 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Bronx | São Paulo | Itaim Bibi | +55 11 99292-6136 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Campo Bacharel | São Paulo | Campo Belo | +55 11 2397-0779 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit City Wolves | São Paulo | Saúde | +55 11 99358-0631 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Conceição | São Paulo | Jabaquara | +55 11 5017-7283 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Fire Hawks | São Paulo | Vila Mariana | +55 11 96609-2246 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Four Heads | São Paulo | Saúde | +55 11 99170-7922 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Higienópolis | São Paulo | Consolação | +55 11 96336-6412 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Juntos | São Paulo | Itaim Bibi | +55 11 99947-5785 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Rutilo | São Paulo | Lapa | +55 11 94390-7851 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Saga | São Paulo | Vila Mariana | +55 11 97349-2008 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Saurus | São Paulo | Vila Guilherme | +55 11 98254-0787 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit São Francisco | São Paulo | Jaguaré | +55 11 97306-6942 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Tupis | São Paulo | Lapa | +55 11 3641-8649 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Vila Carrão | São Paulo | Vila Formosa | +55 11 99162-2452 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Vila Mascote | São Paulo | Jabaquara | +55 11 94988-8889 | afiliado oficial | pesquisado | primeiro contato |
| CrossFit Ximbó | São Paulo | Liberdade | +55 11 94233-0687 | afiliado oficial | pesquisado | primeiro contato |
| KAZA CrossFit | São Paulo | Jardim Paulista | +55 11 99783-6688 | afiliado oficial | pesquisado | primeiro contato |
| Kranio CrossFit | São Paulo | Cidade Ademar | +55 11 96305-4358 | afiliado oficial | pesquisado | primeiro contato |
| Maddock CrossFit | São Paulo | Santo Amaro | +55 11 97059-4689 | afiliado oficial | pesquisado | primeiro contato |
| Made4 CrossFit | São Paulo | Vila Andrade | +55 11 98359-9220 | afiliado oficial | pesquisado | primeiro contato |
| Mega B4thor CrossFit | São Paulo | Rio Pequeno | +55 11 97306-6942 | afiliado oficial | pesquisado | primeiro contato |
| Metalrack CrossFit | São Paulo | Tatuapé | +55 11 94049-9371 | afiliado oficial | pesquisado | primeiro contato |
| Morumbi CrossFit | São Paulo | Vila Sônia | +55 11 3368-2787 | afiliado oficial | pesquisado | primeiro contato |
| Urus CrossFit | São Paulo | Penha | +55 11 94520-8330 | afiliado oficial | pesquisado | primeiro contato |
| Taboão da Serra CrossFit | Taboão da Serra | Rod. Régis Bittencourt | +55 11 4701-0023 | afiliado oficial | pesquisado | primeiro contato |

## Tier 3 — Demais boxes (78 boxes)

Sem selo de afiliação oficial. Não significa box ruim — significa menos sinal público. Atacar
depois dos tiers acima, ou antes se houver indicação.

| Box | Cidade | Bairro | Telefone | Qualificação | Estágio | Próxima ação |
|---|---|---|---|---|---|---|
| Crossfit Betha Strong | Barueri | Jd dos Camargos | +55 11 93350-7636 | site próprio | pesquisado | primeiro contato |
| Crossfit Puaimana | Barueri | Jd dos Camargos | +55 11 4198-2143 | site próprio | pesquisado | primeiro contato |
| Templo CrossFit | Barueri | Alphaville | +55 11 4688-0370 | site próprio | pesquisado | primeiro contato |
| Crossfit Saúde Granja Viana | Carapicuíba | Av. Paraguaçu Paulista | +55 11 95084-0505 | site próprio | pesquisado | primeiro contato |
| 131 CrossFit | Diadema | Conceição | +55 11 94700-2160 | site próprio | pesquisado | primeiro contato |
| CrossFit Dp Mauá | Mauá | Jardim Pilar | +55 11 2375-7615 | site próprio | pesquisado | primeiro contato |
| CrossFit Saúde Mauá | Mauá | Parque São Vicente | +55 11 97554-1160 | site próprio | pesquisado | primeiro contato |
| Essencial Cross - Academia de Crossfit | Mauá | Vila Mercedes | +55 11 97548-6902 | site próprio | pesquisado | primeiro contato |
| CrossFit Osasco | Osasco | Umuarama | +55 11 4384-9699 | site próprio | pesquisado | primeiro contato |
| Barba Negra Crossfit | Santo André | Vila Curuçá | +55 11 4012-6265 | sem site | pesquisado | primeiro contato |
| Box Utinga Crossfit | Santo André | Vila Metalúrgica | +55 11 4997-3228 | site próprio | pesquisado | primeiro contato |
| Crossfit 198 | Santo André | Bairro Jardim | — | sem site | pesquisado | achar contato |
| Crossfit Badak | Santo André | Centro | +55 11 4432-2332 | site próprio | pesquisado | primeiro contato |
| Juscelino Kubitschek Crossfit | Santo André | Bairro Jardim | +55 11 2896-0253 | sem site | pesquisado | primeiro contato |
| Cross Planalto | São Bernardo do Campo | Independência | +55 11 4509-9888 | site próprio | pesquisado | primeiro contato |
| CrossFit Range | São Bernardo do Campo | Baeta Neves | — | site próprio | pesquisado | achar contato |
| CrossFit Titânio | São Bernardo do Campo | Centro | +55 11 3380-6506 | site próprio | pesquisado | primeiro contato |
| Crossfit Capitão | São Bernardo do Campo | Casa | +55 11 4509-5333 | sem site | pesquisado | primeiro contato |
| Crossfit Tamoko | São Bernardo do Campo | Rudge Ramos | +55 11 99664-7999 | sem site | pesquisado | primeiro contato |
| Crossfit Voraz | São Bernardo do Campo | Centro | +55 11 97698-1669 | site próprio | pesquisado | primeiro contato |
| Arena Crossfit III | São Caetano do Sul | Ceramica | +55 11 96747-7124 | sem site | pesquisado | primeiro contato |
| CrossFit Barcelona Park | São Caetano do Sul | Santa Maria | +55 11 93055-4440 | site próprio | pesquisado | primeiro contato |
| Crossfit Espaço Cerâmica | São Caetano do Sul | São José | +55 11 94453-0999 | site próprio | pesquisado | primeiro contato |
| Crossfit Visconde | São Caetano do Sul | Oswaldo Cruz | +55 11 95279-6110 | site próprio | pesquisado | primeiro contato |
| Triple CrossFit | São Caetano do Sul | Santa Paula | +55 11 91069-4634 | site próprio | pesquisado | primeiro contato |
| 3050 CrossFit | São Paulo | Jardim Paulista | +55 11 99272-0789 | site próprio | pesquisado | primeiro contato |
| Atrium CrossFit | São Paulo | Vila Andrade | +55 11 91689-9090 | site próprio | pesquisado | primeiro contato |
| Blindado CrossFit | São Paulo | Santo Amaro | +55 11 2533-2894 | site próprio | pesquisado | primeiro contato |
| CrossFit 2Hands | São Paulo | Água Rasa | +55 11 94736-3563 | site próprio | pesquisado | primeiro contato |
| CrossFit Aclimação | São Paulo | Liberdade | +55 11 94069-8807 | site próprio | pesquisado | primeiro contato |
| CrossFit Anália Franco | São Paulo | Vila Formosa | +55 11 99884-4540 | site próprio | pesquisado | primeiro contato |
| CrossFit Butantã | São Paulo | Rio Pequeno | +55 11 2386-5766 | site próprio | pesquisado | primeiro contato |
| CrossFit Chácara | São Paulo | Santo Amaro | +55 11 3467-9077 | site próprio | pesquisado | primeiro contato |
| CrossFit Cobra | São Paulo | Saúde | — | sem site | pesquisado | achar contato |
| CrossFit ERM | São Paulo | Ermelino Matarazzo | +55 11 94796-5748 | site próprio | pesquisado | primeiro contato |
| CrossFit Great Bear | São Paulo | Sacomã | +55 11 2307-3273 | sem site | pesquisado | primeiro contato |
| CrossFit Ipiranga | São Paulo | Ipiranga | +55 11 98329-6279 | site próprio | pesquisado | primeiro contato |
| CrossFit Ironhead | São Paulo | Vila Andrade | +55 11 97700-0085 | site próprio | pesquisado | primeiro contato |
| CrossFit Jaceru | São Paulo | Itaim Bibi | — | site próprio | pesquisado | achar contato |
| CrossFit Lion Shield | São Paulo | Vila Matilde | +55 11 2653-5800 | site próprio | pesquisado | primeiro contato |
| CrossFit Mansion | São Paulo | Perdizes | +55 11 2364-2741 | site próprio | pesquisado | primeiro contato |
| CrossFit Moema | São Paulo | Moema | +55 11 99359-3910 | site próprio | pesquisado | primeiro contato |
| CrossFit Perdizes | São Paulo | Perdizes | +55 11 97050-4359 | site próprio | pesquisado | primeiro contato |
| CrossFit Pinheiros | São Paulo | Pinheiros | +55 11 98244-3068 | site próprio | pesquisado | primeiro contato |
| CrossFit SP | São Paulo | Itaim Bibi | +55 11 99229-6469 | site próprio | pesquisado | primeiro contato |
| CrossFit Santa Romana | São Paulo | Pirituba | +55 11 98915-9013 | site próprio | pesquisado | primeiro contato |
| CrossFit Saúde Anchieta | São Paulo | Sacomã | +55 11 94451-9790 | site próprio | pesquisado | primeiro contato |
| CrossFit Tatuapé | São Paulo | Tatuapé | +55 11 96260-1047 | site próprio | pesquisado | primeiro contato |
| CrossFit Teina | São Paulo | Ipiranga | +55 11 99887-1523 | site próprio | pesquisado | primeiro contato |
| CrossFit Volk | São Paulo | Vila Mariana | +55 11 2619-1038 | site próprio | pesquisado | primeiro contato |
| CrossFit ZN 2 | São Paulo | Tucuruvi | +55 11 99906-2601 | site próprio | pesquisado | primeiro contato |
| Crossfit 79 | São Paulo | Pinheiros | +55 11 3853-5042 | site próprio | pesquisado | primeiro contato |
| Crossfit Academia para Mulheres | São Paulo | Sapopemba | +55 14 99153-0682 | sem site | pesquisado | primeiro contato |
| Crossfit Bizarro | São Paulo | Mandaqui | — | sem site | pesquisado | achar contato |
| Crossfit Caveira | São Paulo | Butantã | +55 11 3213-4611 | site próprio | pesquisado | primeiro contato |
| Crossfit Ki | São Paulo | Vila Mariana | +55 11 96574-6947 | site próprio | pesquisado | primeiro contato |
| Crossfit Mazzei | São Paulo | Tremembe | — | sem site | pesquisado | achar contato |
| Crossfit Mister | São Paulo | Vila Formosa | +55 11 91089-2010 | site próprio | pesquisado | primeiro contato |
| Crossfit Mitra | São Paulo | Campo Belo | +55 11 98781-8553 | site próprio | pesquisado | primeiro contato |
| Crossfit Norte | São Paulo | Mandaqui | — | sem site | pesquisado | achar contato |
| Crossfit Revolut!on | São Paulo | Belém | +55 11 4741-2986 | sem site | pesquisado | primeiro contato |
| Crossfit Saúde | São Paulo | Butantã | — | site próprio | pesquisado | achar contato |
| Crossfit Scorpios | São Paulo | Ipiranga | +55 11 2645-2444 | sem site | pesquisado | primeiro contato |
| Crossfit Seleção | São Paulo | Santo Amaro | — | sem site | pesquisado | achar contato |
| Crossfit Sergipe | São Paulo | Consolação | +55 11 2679-2758 | site próprio | pesquisado | primeiro contato |
| Crossfit Simio | São Paulo | Ipiranga | +55 11 94519-3173 | site próprio | pesquisado | primeiro contato |
| Crossfit São Lucas | São Paulo | São Lucas | +55 11 2877-1377 | site próprio | pesquisado | primeiro contato |
| Crossfit Tucuruvi | São Paulo | Tucuruvi | +55 11 99845-4445 | sem site | pesquisado | primeiro contato |
| Crossfit Zl | São Paulo | Penha | +55 11 98076-1578 | site próprio | pesquisado | primeiro contato |
| Crossfit Zn | São Paulo | Santana | +55 11 3567-4884 | sem site | pesquisado | primeiro contato |
| Dobermann Crossfit | São Paulo | Moema | +55 11 99795-4171 | site próprio | pesquisado | primeiro contato |
| Flexus Crossfit | São Paulo | Santana | — | sem site | pesquisado | achar contato |
| Hangar 193 Crossfit | São Paulo | Vila Leopoldina | +55 11 3473-8400 | site próprio | pesquisado | primeiro contato |
| Irmãos Crossfit | São Paulo | Lapa | +55 11 4117-1921 | site próprio | pesquisado | primeiro contato |
| Kampu CrossFit | São Paulo | Itaim Bibi | +55 11 5041-4338 | site próprio | pesquisado | primeiro contato |
| Muralha CrossFit | São Paulo | Saúde | +55 11 2384-2878 | site próprio | pesquisado | primeiro contato |
| Studio Funcional & Crossfit | São Paulo | Tucuruvi | +55 11 99276-5033 | site próprio | pesquisado | primeiro contato |
| Vigor Crossfit | São Paulo | Jaguaré | — | sem site | pesquisado | achar contato |

## Indicações pendentes (Canal 1)

| Pedido enviado a | Data | Resposta | Indicações recebidas |
|---|---|---|---|
| Fernando — Endorfina Cross (Guarulhos) | pendente | — | — |

Observação: os 7 boxes do Tier 1 são de Guarulhos, mesma cidade da Endorfina. É provável que o
Fernando conheça pessoalmente vários deles — cruzar a lista com ele no pedido de indicação
transforma abordagem fria em apresentação.

## Métricas semanais

| Semana | Leads pesquisados | Contatos enviados | Respostas | Posts publicados | Checkouts iniciados | Checkouts completados | MRR |
|---|---|---|---|---|---|---|---|
| 2026-08-29 (semana 1) | 119 | 0 | 0 | 0 | a apurar | a apurar | a apurar |

## Notas do ciclo

**2026-08-29 — 4 varreduras.** Guarulhos + ZN/ZL (39 brutos), zona sul, ABC e zona oeste/Osasco.
Consolidado: **119 boxes únicos** após deduplicação por marca e remoção de não-boxes. Cobertura:
Guarulhos, São Paulo capital (todas as zonas), Santo André, São Bernardo, São Caetano, Diadema,
Mauá, Osasco, Barueri, Carapicuíba, Taboão da Serra.

Reordenação de canal registrada acima: telefone/WhatsApp é o canal disponível para este público,
não e-mail.

**Cuidados antes de abordar** (evitam contato duplicado com a mesma gestão):

1. **Saurus** aparece em Guarulhos e em São Paulo — mesma marca, tratar como uma conversa só.
2. **ZN / ZN 2** dividem a Av. Nova Cantareira — provável mesma gestão.
3. **Crossfit Norte** divide endereço exato com o **CrossFit Betta** — pode ser o mesmo box com
   nome antigo.
4. **B4thor CrossFit** e **Mega B4thor CrossFit** compartilham telefone com **CrossFit São
   Francisco** — as três linhas provavelmente são uma gestão só; confirmar antes do terceiro
   contato.
5. **Crossfit Saúde** aparece 4 vezes (Butantã, Mauá, Anchieta, Granja Viana) — parece rede
   licenciada, não boxes independentes com o mesmo dono; tratar cada endereço como decisor
   diferente até confirmar o contrário.
6. **Studio Funcional & Crossfit** e **Vigor Crossfit** podem não ser boxes de verdade —
   qualificar antes de gastar contato.

Duplicatas exatas de nome/telefone (ex.: as duas entradas de "Irmãos Crossfit" na Lapa, as duas
de "CrossFit Barueri" em Alphaville) já foram fundidas em uma linha só antes de entrar nas
tabelas acima — não é preciso checar essas de novo.
