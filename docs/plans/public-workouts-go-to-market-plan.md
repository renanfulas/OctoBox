# Go-to-market — consultoria online de treino (`/renan/` → `/treinos/`)

**Plano de produto (o "porquê" técnico):** [public-workouts-produtizacao-plan.md](public-workouts-produtizacao-plan.md)
**Execução técnica:** [public-workouts-produtizacao-corda.md](public-workouts-produtizacao-corda.md)
**Como construir o que este plano pede:** [public-workouts-escala-e-nutricao-corda.md](public-workouts-escala-e-nutricao-corda.md)
**Este documento:** branding, público, oferta, preço, aquisição e a landing page que vende isso.

**Status:** rascunho v3 · **Data:** 2026-09-17 · **Dono:** Renan · **Revisão:** 3

> **O que mudou na Revisão 2:** a esposa do Renan é nutricionista com **CRN ativo** e vai
> assumir a frente de nutrição — o risco legal do R1 (prescrever dieta sem ser
> nutricionista) deixa de existir. Isso reabre a oferta "treino + nutrição" desde o
> lançamento, mas troca o risco legal por um risco operacional novo: agora são **duas**
> agendas humanas limitando o volume, não uma. Ver R1, §3 e §6 atualizados.

> **O que mudou na Revisão 3:** as seis decisões do §7 (antigo "só você pode tomar")
> foram respondidas. Resumo: **já existe audiência** e **já existe orçamento de tráfego
> pago** (isso muda a ordem do funil no §4 — ver nota nova); a nutricionista é **sócia da
> oferta combinada**, não prestadora à parte; o atendimento dela é **assíncrono**
> (formulário → plano), igual ao espírito do treino v1; e a nutrição **nasce estruturada**
> no produto, não como texto livre — decisão que muda o desenho técnico do §6 e da
> Entrega 6 (ver `public-workouts-escala-e-nutricao-corda.md`, D.6 revisado). A única
> pergunta que **continua sem resposta** é o valor real cobrado hoje dos 10 legados — não
> é por falta de pergunta, é porque ninguém mediu ainda; ver nota no §3.

> Regra herdada do GTM B2B do OctoBox ([docs/gtm/README.md](../gtm/README.md)): **nenhuma
> peça de venda pode prometer o que a operação ainda não sustenta.** Este documento segue
> a mesma regra — cada promessa abaixo está ancorada em algo que já existe em produção
> (ver §0), não em algo que "seria legal ter".

---

## Antes de tudo — três riscos que mudam o plano inteiro

Isto não é o plano em si. É o que precisa ser decidido **antes** de escrever uma linha de
copy, porque muda a oferta inteira.

### R1 — "Dieta" na oferta: risco legal resolvido, mas troca de problema

**Atualizado na Revisão 2.** Eu tinha sinalizado que "consultoria de treino + dieta" era
risco legal, porque prescrever plano alimentar individualizado é ato privativo de
nutricionista (Lei 8.234/1991) — e o único precedente no produto era o "plano alimentar
do Rafael", texto solto dentro do HTML dele (achado durante a migração do parser, ver
`docs/plans/public-workouts-produtizacao-corda.md:1916`), sem nenhum profissional
habilitado por trás.

Você confirmou que sua esposa é **nutricionista com CRN ativo** e vai assumir essa frente
sozinha, com você e o time cuidando só da parte de produto/tecnologia ("só iremos
programar"). Isso muda a decisão:

1. **O risco legal do parágrafo original deixa de existir.** Quem prescreve passa a ser
   uma profissional registrada, sob o próprio CRN dela — não é mais o personal
   "acumulando função". A oferta pode legitimamente virar **"treino + nutrição" desde o
   lançamento**, não precisa nascer só treino.
2. **O CRN dela precisa aparecer na landing page**, em qualquer seção que fale de
   orientação nutricional — não é opcional nem rodapé discreto. É exigência do próprio
   conselho (Resolução CFN sobre publicidade profissional): quem orienta nutrição se
   identifica publicamente, com número de registro, do mesmo jeito que um CREF
   identificaria um profissional de educação física. Trate como campo obrigatório do
   copy, não como detalhe jurídico chato — na verdade é **prova social forte**: a maioria
   dos concorrentes do seu nicho não tem isso.
3. **A parte técnica continua sendo um gap real — só que agora sem pressa que force
   gambiarra.** "Dieta" ainda é, hoje, **um único caso manual**: texto solto num HTML, sem
   estrutura, sem versionamento, sem revisão no app. Como agora existe dona legítima para
   essa frente, a pergunta deixa de ser *"isso pode existir?"* e vira *"como construímos
   isso direito?"* — ver §6.
4. **Ela vira um segundo gargalo de revisão humana, do mesmo jeito que você é hoje para o
   treino.** Escalar "treino" e escalar "treino + nutrição de verdade, com humano
   revisando" não têm o mesmo teto — agora são **duas agendas** limitando o volume, não
   uma. Isso muda a matemática de preço/volume do §3.

Decisões novas que isso abre (divisão de receita, formato de atendimento dela, se v1 é
manual ou já estruturada) foram para §7 — não dá pra assumir isso por vocês dois.

### R2 — a meta de R$ 10 mil/mês em 3–4 meses exige escolher entre preço e volume, e o volume esbarra num gargalo que já existe hoje

Você mesmo notou que existe uma calibragem entre oferta, demanda, público e preço — está
certo, e ela é mais apertada do que parece porque **o onboarding de aluno novo ainda não
é self-service.** O próprio plano técnico lista isso como parte da Entrega 5 ("Escala"),
ainda não iniciada pelas PRs mais recentes (#252–#263, que são refino de periodização,
não onboarding). Hoje, aceitar um cliente novo ainda passa pela sua revisão manual.

Isso importa porque a matemática de "quantos alunos preciso" muda o tamanho do problema
operacional, não só o de marketing — ver §3.

### R3 — "não importa o meio, contanto que bata a meta" é a parte mais perigosa do seu próprio brief

Aviso de prompt, porque isso vale a pena aprender: **um objetivo sem restrição não é uma
meta, é um convite para o otimizador cortar caminho pelo lugar errado.** Pensa assim —
se você pedir para uma criança "chega em casa o mais rápido possível, não importa como",
ela pode atravessar a rua sem olhar. Ela bateu a meta ("chegou rápido") e criou um
problema maior que o que resolveu. Com IA/otimização, isso tem nome: **reward hacking**
— o sistema (ou o freelancer de marketing, ou até eu) encontra o caminho mais curto pro
número, que no nicho de saúde/estética costuma ser: promessa de resultado exagerada
("perca 8kg em 21 dias"), antes/depois editado, escassez falsa ("só restam 2 vagas!" que
na real são infinitas. No seu caso, "vagas limitadas pela sua agenda de revisão" é
**verdade** — ótimo, é a única escassez que vamos usar).

O problema de deixar isso sem trava: propaganda enganosa em saúde é infração do CDC (Código
de Defesa do Consumidor) e, na prática, gera reembolso/chargeback em massa — o que
**destrói a própria meta de MRR mais rápido do que qualquer tráfego pago consegue
construir**. Um prompt mais forte teria vindo com a restrição explícita ("...sem usar
prova social falsa, sem prometer resultado que o produto não entrega, dentro da
capacidade real de atendimento"). É isso que estou assumindo como restrição implícita
daqui pra frente — me avise se quiser abrir mão de alguma.

---

## 0. Estado real do produto (fonte: histórico de commits, não o brief)

Regra do projeto (`documentation-authority-map.md`): runtime e código vencem qualquer
plano escrito. Conferido no `git log`, isto **já está em produção**:

| Já pronto | Onde (commit) |
|---|---|
| Vazamentos de dado pessoal corrigidos (A1/A4) | `0ce4d29` |
| Login sem senha (token de e-mail) + posse do slug | `7990983`, `f5001ca`-adjacentes |
| Cobrança recorrente própria (Stripe checkout + webhook) | `103c3ea` |
| Portal do cliente Stripe (cancelamento self-service) | `c61e92e` |
| Avaliação física (US Navy, JP3, **JP7**) + gráfico de silhueta | `d7dc6bd`, `b4fd7ff` |
| 1RM estimado, detecção de platô, review semanal | `d26c91f` |
| Histórico de carga com gráfico de evolução | `25a51a5` |
| Exportação do treino em PDF | `f5001ca` |
| Migração dos 10 programas legados para dado estruturado | `26bdb81` |
| Exportação de dados do titular (LGPD) | `04df401` |

**Isso muda o discurso de venda:** você não está vendendo "uma promessa de app que vai
existir". Você já tem prova de resultado real (gráfico de evolução de carga, avaliação
física com números reais, PDF do treino) rodando em produção, com 10 clientes reais. Essa
é a arma mais forte da landing page — ver §5.

| Ainda não pronto (não prometer na landing) | Por quê importa |
|---|---|
| Onboarding self-service (assina → responde anamnese → cai na fila sozinho) | Entrega 5, não iniciada. Sem isso, cada venda ainda consome seu tempo manual |
| Fila/painel de revisão para volume | idem |
| Dieta estruturada no produto (versionada, revisável, não é mais só texto em HTML) | ver R1 — agora tem dona legítima (nutricionista com CRN), mas ainda não foi construída; hoje é 1 caso manual |
| Multi-personal / marca própria por profissional | roda hoje só para você (`/renan/`) |

---

## 1. Público-alvo (ICP — Ideal Customer Profile: o retrato de quem compra bem e fica)

Baseado nos 10 alunos legados já documentados na migração (perfis reais: Juliana,
Franciele, Giovanna, Bruno, Henrique, Milene, Rafael e outros — objetivos de
hipertrofia/estética, periodização por fase, restrições articulares registradas), o
padrão que emerge:

**Persona primária — "Já treino, quero parar de treinar no escuro"**
- Já frequenta academia (não é iniciante absoluto), mas treina com plano genérico ou
  written by nobody.
- Motivação estética + saúde (a maioria dos exemplos do repo são objetivo de
  hipertrofia/definição, não performance esportiva).
- Já tentou "treino de internet" ou personal presencial caro e quer algo entre os dois:
  acompanhamento de verdade, preço de assinatura.
- Dor real (dos próprios campos da anamnese do plano técnico): "não sei se estou
  evoluindo", "meu treino não muda nunca", "não aguento ficar 1h na academia".

**Persona secundária — "Treino com restrição física e preciso de adaptação real"**
- Casos como "Posterior Dominante · Joelho-Friendly" no histórico real de programas —
  pessoas com histórico de lesão que precisam de troca de exercício segura, não de
  treino genérico de blog.

A landing page fala primeiro com a Persona 1 (mercado maior) e usa a Persona 2 como
prova de que o produto lida com gente de verdade, não só com corpo perfeito de
estoque de imagem.

---

## 2. Posicionamento e branding

**O diferencial real (não inventado, é o que o código garante):**
1. **O gráfico de evolução é de dado real**, não de photoshop — 1RM calculado, histórico
   de carga que atravessa os 5–12 programas do ano.
2. **Revisão humana + IA**, não treino 100% genérico de robô nem 100% manual e caro.
3. **App instalável (PWA)** — abre como app, funciona offline, sem precisar baixar nada
   de loja.
4. **Avaliação física de verdade** (dobras, %gordura, silhueta) — não "diário
   emocional de balança".
5. **Dupla profissional formalizada — personal + nutricionista com CRN** (Revisão 2).
   Isso é diferencial de verdade, não frase de marketing: a maioria dos concorrentes do
   nicho é "personal que também manda umas dicas de dieta", sem nenhum registro
   profissional por trás da parte nutricional. Vocês dois assinando com CREF/CRN reais é
   prova de credibilidade que se constrói uma vez e vale para sempre — use isso no hero
   da página, não só numa seção "sobre nós".

**Nome da marca — decidido na Revisão 3 (com sua entrada: "meu nome sozinho ainda é
genérico, quero algo mais elaborado").**

O produto **não pode usar a cara do OctoBox** (é o SaaS B2B para donos de academia — o
aluno de consultoria nunca deveria ver essa marca, conforme já decidido no plano
técnico). Você confirmou que hoje só quem já é próximo sabe que você vende consultoria —
ou seja, o nome próprio ainda não carrega reconhecimento de marca por si só (ao contrário
do que a Revisão 2 supunha ao listar "Renan Personal" como aposta óbvia). Isso descarta a
opção 1 (nome próprio) e pede algo que se sustente sozinho, sem depender de fama pessoal
prévia.

O diferencial real (§0/§2 acima) não é "personal simpático" — é **prova mensurável**: o
gráfico de evolução de carga é dado real, não promessa. É esse fio que amarra as opções
abaixo, em vez de nomes genéricos de nicho fitness ("Evolua", "Foco", "Shape"):

| Nome | Por que funciona | Ponto de atenção |
|---|---|---|
| **Curva** (ex.: *Curva Treino & Nutrição*) | Nome mais forte da lista: aponta direto para o ativo de marketing mais concreto que vocês têm — o gráfico de evolução de carga é literalmente uma curva. Curto, fácil de falar, funciona em Instagram (@curva.treino) e não soa "fitness genérico" | Precisa de uma linha de apoio no hero explicando a curva na primeira frase, senão o nome sozinho não entrega o significado |
| **Vetor** (ex.: *Vetor Performance*) | Vetor tem direção **e** magnitude — combina com "treino com direção certa, não giro no lugar", e soa técnico/confiável sem ser frio | Mais abstrato que "Curva"; exige mais copy de apoio para o público não-técnico entender a referência |
| **Cerne** (ex.: *Cerne Treino & Nutrição*) | Cerne = núcleo, essência — soa premium, funciona bem para a marca de dupla (duas frentes, um núcleo comum) | Não referencia o diferencial de dado real tão diretamente quanto "Curva" |

**Recomendação: "Curva".** É o único nome da lista que já nasce contando a história do
produto (dado real, progresso medido) antes de qualquer linha de copy — e funciona tanto
como marca de dupla ("Curva Treino & Nutrição") quanto, se um dia vocês decidirem
escalar para outros profissionais (fora de escopo por ora, ver C5 do plano técnico), como
guarda-chuva neutro que não fica preso ao nome de uma pessoa só.

Se nenhum dos três "bater", a via de saída é gerar uma segunda rodada com você me dando
2–3 palavras/sensações que você quer que a marca transmita (ex.: "científico", "sério",
"acessível") — nomes de marca funcionam melhor com um ponto de partida emocional seu do
que com uma lista genérica.

---

## 3. Arquitetura da oferta — calibrando preço × demanda × prazo

**A fórmula que você já intuiu, agora explícita:**

```
MRR (receita recorrente mensal) = preço da assinatura × alunos ativos pagantes
```

Analogia da banheira, porque isso é o conceito mais importante do documento inteiro:
pense em MRR como o nível de água numa banheira. **Preço** é o tamanho do balde a cada
vez que você enche. **Novas vendas** é quantas vezes por mês você enche o balde.
**Cancelamento (churn)** é o ralo aberto. Se o ralo escoa mais rápido do que você
enche, a banheira nunca sobe — não importa quantos anúncios você rode. Por isso todo
plano abaixo tem uma linha de cancelamento embutida, não só de venda.

### Cenários de preço (para bater R$ 10.000/mês)

| Cenário | Preço | Alunos ativos necessários | Comentário |
|---|---|---|---|
| A — preço já decidido no plano técnico | R$ 89,90 único | **~112** | Metade de mil reais por aluno vira R$10k só com muita gente — e cada aluno hoje ainda passa pela sua revisão manual. Inviável em 90–120 dias sem a Entrega 5 pronta |
| B — ticket médio | R$ 147 único | **~69** | Ainda concentra risco de revisão manual, mas quase metade do volume de A |
| C — ticket mais alto | R$ 197 único | **~51** | Exige oferta mais robusta na página (review semanal explícito, prioridade) para justificar |
| D — dois níveis, só treino | Essencial R$ 97 (template adaptado) + Premium R$ 247 (review semanal, prioridade) | ~70 no total (~50 Essencial + ~20 Premium) | Era a recomendação da Revisão 1, quando "dieta" ainda estava fora da oferta por risco legal |
| **E — três níveis, com nutrição (recomendado agora)** | **Essencial R$ 97** (só treino, template) + **Completo R$ 267** (treino revisado + acompanhamento nutricional real da sua esposa) + **Premium R$ 397** (review semanal dos dois profissionais + prioridade) | **~54 no total** (~30 Essencial + ~19 Completo + ~5 Premium) | O nível com nutrição custa mais **porque soma duas agendas humanas**, não porque "dieta vale mais" no vácuo — ver R1.4. Precisa de **menos alunos no total** que o Cenário D para bater a mesma meta, porque o ticket médio sobe |

**Por que o Cenário E é a recomendação agora:** ele incorpora a mesma lógica do Cenário
D (nível barato escala via template, nível caro financia com menos gente) e soma a
frente de nutrição no nível do meio, onde o preço já reflete que **duas pessoas**, não
uma, gastam tempo de revisão por cliente. Resista à tentação de colocar nutrição no
nível Essencial "de graça para competir" — isso reintroduz o mesmo erro do R3 (prometer
mais do que a operação sustenta), só que agora com duas agendas em vez de uma.

### Recalibração pós-Revisão 3 — o que muda quando audiência e orçamento já existem

Você me pediu para fazer a aferição entre público, demanda, preço e volume em vez de
só confirmar um número — então é isso: com **audiência já existente** (§7.1) e
**orçamento de tráfego pago já definido** (§7.2), o gargalo de topo de funil que a
Revisão 1/2 assumia ("sem base própria, depende só de orgânico crescer devagar")
**deixa de existir**. Isso muda o §4 (ver nota abaixo), mas **não muda o teto real do
negócio**, que continua sendo a agenda de revisão humana — na verdade, essa
recalibração aponta um risco novo: se demanda deixar de ser o fator limitante, leads
vão chegar mais rápido do que antes, e a fila sem SLA do RT2 (plano técnico) fica mais
provável de estourar mais cedo, não menos. Trate isso como motivo para **priorizar a
Entrega 5 (onboarding self-service) e medir a capacidade real da nutricionista antes de
acelerar o tráfego pago**, não como licença para acelerar tudo de uma vez.

O que essa recalibração **não** resolve: o valor real cobrado hoje dos 10 alunos
legados. Perguntei diretamente (§7.3) e a resposta foi pedir esta aferição em vez de um
número — o que é uma resposta válida sobre a *lógica* do funil, mas não substitui o
dado que falta. **Isso continua sendo medido, não estimado** — a linha "Base hoje" da
tabela abaixo segue com o valor do plano técnico original (R$ 89,90) como placeholder
explícito, não como fato confirmado.

### Projeção mês a mês (ilustrativa — não é previsão, é hipótese a validar em 2–3 semanas de dados reais)

Recalculada para o mix E (ticket médio maior, menos alunos necessários que a Revisão 1).
Mês 1 sobe em relação à Revisão 2 porque audiência+orçamento já existentes encurtam o
tempo até a primeira onda de conversão — o teto dos meses 3–4 **não muda**, porque
continua sendo a agenda de revisão dos dois, não a velocidade de geração de leads:

| Mês | Ativos no fim do mês | MRR aproximado (mix E) | O que precisa ser verdade |
|---|---|---|---|
| Base hoje | 10 (legados) | ~R$ 900 (placeholder a R$ 89,90/aluno — **valor real ainda não medido**, ver nota acima) | — |
| Mês 1 | ~22 | ~R$ 4.000 | Audiência existente + orçamento pago já testando anúncio desde a semana 1 (não precisa esperar orgânico converter primeiro) |
| Mês 2 | ~34 | ~R$ 6.200 | Conteúdo orgânico + pago rodando juntos; capacidade real da nutricionista já medida (§6.3) |
| Mês 3 | ~44 | ~R$ 8.200 | A agenda de revisão **dos dois** é o teto agora, não a demanda — Entrega 5 (onboarding self-service) precisa estar no ar, senão a fila (RT2) cresce mais rápido do que antes por ter mais leads chegando |
| Mês 4 | ~54 | **~R$ 9.900–10.300** | Meta batida — assumindo churn ~10%/mês, não confirmado, e as duas agendas seguindo sem sobrecarga |

**O número que decide tudo e ninguém mede antes de vender: taxa de cancelamento
mensal.** Se o churn for 20% em vez de 10%, a mesma quantidade de vendas novas produz
metade do crescimento líquido. Trate isso como a primeira métrica a acompanhar, não a
última.

---

## 4. Funil e canais de aquisição

Ordem por **confiança/custo**, não por "o que é mais chamativo". Revisão 3: como você já
tem audiência **e** orçamento de tráfego pago (§7.1/§7.2), o canal 5 deixa de ser
"depois que os outros provarem" e passa a rodar **em paralelo desde a semana 1** — mas
como teste pequeno, não como aposta principal, pelos motivos abaixo.

1. **Indicação dos 10 alunos atuais (primeiro, grátis, mais alta conversão).** Eles já
   confiam no resultado. Um programa simples de indicação (ex.: 1 mês grátis por
   indicado que assina) converte muito melhor que tráfego frio, porque a prova social já
   está feita.
2. **Sua audiência já existente (Instagram/WhatsApp/indicação ativa, Revisão 3).**
   Diferente de tráfego frio, aqui já existe algum nível de confiança construída — é o
   canal mais barato depois da indicação, e o primeiro lugar para anunciar a landing
   quando ela ficar pronta.
3. **Conteúdo orgânico usando a prova real que o app já gera.** O gráfico de evolução de
   carga e a avaliação física (silhueta, %gordura) são ativos de marketing que a maioria
   dos personal trainers **não tem** — a maioria mostra print de planilha ou treino
   escrito à mão. Isso é diferencial de verdade, use nos Reels.
4. **A base de pacientes já atendidos pela sua esposa (Revisão 2) — canal quente que já
   existe, sem precisar negociar parceria.** Paciente dela que já confia no trabalho
   nutricional e não tem treino estruturado é lead qualificado de graça — some isso ao
   passo 1, é o mesmo princípio (confiança já construída) por outra porta.
5. **Parcerias locais** (fisioterapeutas, academias sem treino estruturado) — tráfego já
   qualificado, custo baixo, mas mais lento de negociar.
6. **Tráfego pago — testado em paralelo desde a semana 1, com verba pequena, nunca como
   aposta principal antes da Entrega 5.** Como você já tem orçamento, não faz sentido
   esperar; mas o motivo original da Revisão 2 para ir por último **ainda vale em
   parte**: gastar para acelerar a entrada de leads não resolve nada se a fila de
   revisão manual (RT2 do plano técnico) já está no teto — nesse cenário, tráfego pago
   só faz a fila crescer mais rápido, não o MRR. Use as primeiras semanas de verba para
   **testar criativo/mensagem** (custo baixo, aprendizado alto), e só escale o valor
   depois que a Entrega 5 e a capacidade da nutricionista estiverem medidas (§6).

---

## 5. Estrutura da landing page — "bateu o olho, era isso que eu queria comprar"

Framework seção a seção, amarrado ao que dá pra provar hoje (regra do §0 — nunca
prometer o que ainda não existe):

| Seção | O que faz | Prova a usar |
|---|---|---|
| **Hero** | Promessa clara + para quem é, em uma frase | Print real do gráfico de evolução de carga (não estoque de imagem) |
| **Dor / agitação** | Nomeia o problema que o público já vive ("treino que nunca muda", "não sei se estou evoluindo") | Linguagem literal dos campos de anamnese (motivação, maior dificuldade) — é a mesma pesquisa de público que o produto já faz por dentro |
| **Como funciona / diferencial** | Revisão humana + IA, periodização de verdade, avaliação física, **e agora acompanhamento nutricional real** | Explicação simples: "seu treino muda a cada 4–6 semanas, baseado no que você registrou de carga, não em achismo" + "sua alimentação é acompanhada por nutricionista registrada, não por um plano genérico de internet" |
| **Credenciais** *(nova, Revisão 2)* | Nome, CREF (você) e **CRN** (sua esposa) visíveis, não escondidos em rodapé | Exigência da Resolução CFN de publicidade profissional — e também a prova de credibilidade mais forte da página |
| **Prova social** | Depoimento dos alunos reais + antes/depois honesto (com consentimento explícito, LGPD) | Os 10 alunos legados são a prova, não atores |
| **Oferta e preço** | Os três níveis (Essencial / Completo com nutrição / Premium) claros, sem letra miúda | — |
| **Garantia** | Ex.: primeiros 7 dias, se não fizer sentido, cancela sem custo | Reduz risco percebido sem prometer resultado de corpo |
| **FAQ / objeção** | "Preciso de equipamento?", "E se eu me machucar?", "Funciona pra iniciante?", **"a dieta é individual ou um PDF genérico?"** | Respostas ancoradas nos 7 campos de anamnese já existentes + no formato assíncrono (formulário → plano) da sua esposa, decidido no §7.5 |
| **CTA final** | Escassez **real**: vagas limitadas pela sua capacidade de revisão | Nunca inventar contador regressivo falso — é o tipo de mentira que o R3 acima descreve |

---

## 6. Débito técnico e dependências que a meta comercial vai expor

Se a campanha funcionar bem antes desses pontos estarem prontos, eles viram o gargalo —
avisando com antecedência, como pedido:

1. **Onboarding manual não escala para ~54 alunos em 4 meses.** Hoje aceitar aluno novo
   ainda passa por você. Se a Entrega 5 (self-service) não acompanhar o ritmo de vendas,
   o risco não é "faltar cliente" — é **sobrecarregar sua agenda de revisão e a
   experiência do aluno cair**, o que aumenta o churn bem no momento em que você mais
   precisa dele baixo.
2. **A nutrição precisa de um módulo próprio no produto — hoje não existe nenhum.**
   *(Reescrito na Revisão 2 — o risco deixou de ser legal e virou puramente de escopo;
   reescrito de novo na Revisão 3 — §7.6 decidiu que nasce estruturada, não texto
   livre, o que aumenta um pouco o escopo desta entrega.)* O que existe é um caso
   manual (texto solto em HTML). Construir isso direito, seguindo o mesmo padrão que o
   CORDA já usa para o resto do produto (D.00: modelo próprio, nunca estender tabela do
   box; ver `public-workouts-escala-e-nutricao-corda.md`, D.6), significa pelo menos:
   uma **anamnese nutricional própria** (comorbidades, alergias, rotina alimentar —
   diferente dos 7 campos da anamnese de treino, que não cobrem isso), um **schema
   explícito para o plano alimentar** (refeições, itens, macros, substituições —
   validado, não um blob livre), um jeito de **sua esposa entregar e revisar** o plano
   por um formulário estruturado (a decisão de v1 continua manual — sem parser/IA — só
   a forma dos dados mudou), e o versionamento que o `PublicWorkoutProgram` já usa para
   o treino, reaproveitado. Ainda não está dimensionado em dias — é trabalho novo de
   verdade, agora com forma mais clara do que antes da Revisão 3.
3. **A agenda da nutricionista é um gargalo tão real quanto a sua.** Cenário E (§3) já
   assume isso no preço, mas vale dizer sem rodeio: se ela também revisa cada plano à
   mão, o teto de alunos do nível Completo/Premium é o tempo dela, não o seu. Meça a
   capacidade real dela (quantos planos/mês ela sustenta com qualidade) antes de vender
   a oferta combinada em volume.
4. **Preço fixo único (Cenário A) empurra volume para cima do que a revisão manual
   aguenta.** Se decidir manter R$ 89,90 único mesmo assim, o Mês 3 acima precisa da
   Entrega 5 pronta, não é opcional.

---

## 7. Decisões — cinco de seis resolvidas na Revisão 3

1. **✅ Audiência: você já tem (Instagram, WhatsApp de leads, indicação ativa).** Muda o
   mix de canais do §4 — audiência própria entrou como canal 2, antes de orgânico do
   zero.
2. **✅ Orçamento de tráfego pago: existe.** Entra em paralelo desde a semana 1 (canal 6
   do §4), mas com verba pequena de teste até a Entrega 5 e a capacidade da
   nutricionista estarem medidas — gastar mais cedo do que isso só acelera a fila, não
   o MRR (ver recalibração no §3).
3. **⏳ Ainda em aberto — valor real cobrado hoje dos 10 alunos legados.** Perguntado
   direto nesta revisão; a resposta foi pedir a aferição de público×demanda×preço×volume
   (feita no §3) em vez do número. Isso resolve a *lógica* do funil, mas a linha "Base
   hoje" da projeção continua com um placeholder (R$ 89,90, valor do plano técnico), não
   um dado medido. Precisa do número real para a projeção deixar de ser estimativa.
4. **✅ Divisão de receita: sócia da oferta combinada.** Ela participa da receita dos
   níveis Completo/Premium, não presta serviço à parte. Consequência a observar: isso
   dá a ela incentivo para **volume**, mas o teto real continua sendo a agenda dela
   (tempo, não dinheiro) — o incentivo de sócia não resolve o RT2/item 3 do §6, só muda
   quem sente o efeito financeiro se a fila crescer demais.
5. **✅ Atendimento nutricional: assíncrono (formulário → plano entregue).** Mesmo
   espírito do treino v1 — sem agenda de chamada para modelar. Isso simplifica o
   trabalho técnico do §6/Entrega 6: a `PublicWorkoutNutritionProfile` (anamnese) já
   cobre o "formulário", e o plano entregue é o `PublicWorkoutMealPlan` — não precisa de
   nenhum sistema de agendamento novo.
6. **✅ Nutrição v1: nasce estruturada, não texto livre.** Reverte a recomendação
   original deste documento ("manual primeiro, sem estrutura"). O preenchimento
   continua manual (sua esposa digita, sem parser/IA) — o que muda é que o
   `payload` segue um schema validado (refeições, itens, macros, substituições) em vez
   de um blob livre. Ver `public-workouts-escala-e-nutricao-corda.md` D.6/ADR-6 para o
   desenho técnico completo — o efeito colateral é que a Entrega 6 fica um pouco maior
   (schema + validação + formulário de admin estruturado), não é mais "ajuste pequeno".

---

## 8. Definição de sucesso e o que medir a partir da semana 1

- **MRR** (receita recorrente mensal) — a métrica-alvo em si.
- **Churn mensal** (% de assinantes que cancelam) — decide se o balde da banheira
  enche ou escoa; medir a partir do primeiro mês, não esperar o quarto.
- **Taxa de conversão lead → assinante** por canal (indicação vs. orgânico vs. pago) —
  decide onde investir tempo/dinheiro no Mês 2 em diante.
- **CAC** (custo de aquisição por cliente, se houver tráfego pago) vs. **ticket médio** —
  se o CAC de um mês superar o ticket, esse canal está queimando dinheiro, não
  construindo negócio.
