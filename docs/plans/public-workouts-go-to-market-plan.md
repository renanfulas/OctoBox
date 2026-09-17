# Go-to-market — consultoria online de treino (`/renan/` → `/treinos/`)

**Plano de produto (o "porquê" técnico):** [public-workouts-produtizacao-plan.md](public-workouts-produtizacao-plan.md)
**Execução técnica:** [public-workouts-produtizacao-corda.md](public-workouts-produtizacao-corda.md)
**Este documento:** branding, público, oferta, preço, aquisição e a landing page que vende isso.

**Status:** rascunho v1 · **Data:** 2026-09-17 · **Dono:** Renan

> Regra herdada do GTM B2B do OctoBox ([docs/gtm/README.md](../gtm/README.md)): **nenhuma
> peça de venda pode prometer o que a operação ainda não sustenta.** Este documento segue
> a mesma regra — cada promessa abaixo está ancorada em algo que já existe em produção
> (ver §0), não em algo que "seria legal ter".

---

## Antes de tudo — três riscos que mudam o plano inteiro

Isto não é o plano em si. É o que precisa ser decidido **antes** de escrever uma linha de
copy, porque muda a oferta inteira.

### R1 — "Dieta" na oferta é risco legal, não só técnico

O brief pede "consultoria de treino junto com a dieta". Fui conferir o que existe: há
**um único caso**, o "plano alimentar do Rafael", escrito à mão dentro do HTML dele
(`docs/plans/public-workouts-produtizacao-corda.md:1916`, achado durante a migração do
parser). Não é feature — é texto solto, feito uma vez, para um cliente. O parser
inclusive foi desenhado para **não** tratar isso como dado estruturado.

Mais grave que a parte técnica: **prescrever plano alimentar individualizado (cardápio,
quantidade, "coma X gramas de Y") é ato privativo de nutricionista** no Brasil (Lei
8.234/1991). Se você é personal trainer e não nutricionista, colocar "dieta
personalizada" na oferta é exercício ilegal de profissão regulamentada — não é
"zona cinzenta", é o tipo de coisa que gera notificação do CRN e, pior para o negócio,
motivo de reembolso em massa se alguém reclamar.

**Recomendação (o que assumi no resto deste documento, ajuste se discordar):** a oferta
de lançamento é **treino**, ponto. "Orientação alimentar geral" (não individualizada,
tipo conteúdo educativo) pode entrar como bônus de baixo risco. Uma dieta prescrita de
verdade entra como **upsell futuro com nutricionista parceiro** (comissionado ou em
parceria formal) — não como algo que você assina embaixo.

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
| Dieta como feature de produto | ver R1 — nem deveria virar feature sem nutricionista |
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

**Nome da marca — decisão sua, não invento por você:**
O produto **não pode usar a cara do OctoBox** (é o SaaS B2B para donos de academia —
o aluno de consultoria nunca deveria ver essa marca, conforme já decidido no plano
técnico). Precisa de nome/identidade **pessoal, ligado a você como profissional**, não
ao software. Três direções possíveis, para você escolher ou combinar:
- **Nome próprio + especialidade**: "Renan Personal", "Treino com Renan" — aposta na
  confiança pessoal, funciona bem se você já tem alguma presença (Instagram, indicação).
- **Nome de método/sistema**: algo como "Método [X]" ou "[X] Treino" — funciona melhor
  para escalar depois para outros personais (`/joao/`, `/milene/`...), porque não fica
  preso à sua imagem.
- **Nome do problema resolvido**: foca na dor ("Evolua Real", "Treino que Funciona") —
  mais genérico, mais fácil de testar em anúncio, mais difícil de defender depois.

Pergunta em aberto (ver §8): você já tem um nome/perfil que os 10 alunos atuais
reconhecem? Se sim, é o ponto de partida óbvio — não descarte marca que já tem confiança
construída.

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
| **D — dois níveis (recomendado)** | **Essencial R$ 97** (programa por template adaptado, sem review semanal individual) + **Premium R$ 247** (anamnese completa, review semanal, prioridade) | **~70 no total** (~50 Essencial + ~20 Premium) | Ancorado no que o sistema já resolve: adaptar um `WorkoutTemplate` custa **segundos** do seu tempo (dado do próprio plano técnico); só o nível Premium consome seu tempo de review — e nesse nível você tem só ~20 clientes, não 70 |

**Por que o Cenário D é a recomendação:** ele resolve exatamente a tensão que você
identificou (oferta × demanda × preço) usando uma peça que já existe no código
(`WorkoutTemplate`, a biblioteca de ~15 programas reaproveitáveis) em vez de inventar
capacidade operacional do nada. O nível caro financia o nível barato; o nível barato
financia o volume.

### Projeção mês a mês (ilustrativa — não é previsão, é hipótese a validar em 2–3 semanas de dados reais)

| Mês | Ativos no fim do mês | MRR aproximado (mix D) | O que precisa ser verdade |
|---|---|---|---|
| Base hoje | 10 (legados) | ~R$ 1.400 (estimado — **confirme o valor real cobrado hoje**) | — |
| Mês 1 | ~24 | ~R$ 3.400 | Landing no ar, funil de indicação ativo |
| Mês 2 | ~42 | ~R$ 6.000 | Conteúdo orgânico rodando, primeiras conversões pagas testadas |
| Mês 3 | ~58 | ~R$ 8.200 | Onboarding self-service (Entrega 5) precisa começar aqui, senão sua agenda de revisão vira o teto |
| Mês 4 | ~72 | **~R$ 10.200** | Meta batida — assumindo churn ~10%/mês, não confirmado |

**O número que decide tudo e ninguém mede antes de vender: taxa de cancelamento
mensal.** Se o churn for 20% em vez de 10%, a mesma quantidade de vendas novas produz
metade do crescimento líquido. Trate isso como a primeira métrica a acompanhar, não a
última.

---

## 4. Funil e canais de aquisição

Ordem por **confiança/custo**, não por "o que é mais chamativo":

1. **Indicação dos 10 alunos atuais (primeiro, grátis, mais alta conversão).** Eles já
   confiam no resultado. Um programa simples de indicação (ex.: 1 mês grátis por
   indicado que assina) converte muito melhor que tráfego frio, porque a prova social já
   está feita.
2. **Conteúdo orgânico usando a prova real que o app já gera.** O gráfico de evolução de
   carga e a avaliação física (silhueta, %gordura) são ativos de marketing que a maioria
   dos personal trainers **não tem** — a maioria mostra print de planilha ou treino
   escrito à mão. Isso é diferencial de verdade, use nos Reels.
3. **Parcerias locais** (fisioterapeutas, nutricionistas, academias sem treino
   estruturado) — tráfego já qualificado, custo baixo, mas mais lento de negociar.
4. **Tráfego pago — só depois que a página converter organicamente pelo menos algumas
   vezes.** Pagar para levar gente para um funil não testado é queimar dinheiro para
   descobrir o que o passo 1–3 já teria mostrado de graça.

---

## 5. Estrutura da landing page — "bateu o olho, era isso que eu queria comprar"

Framework seção a seção, amarrado ao que dá pra provar hoje (regra do §0 — nunca
prometer o que ainda não existe):

| Seção | O que faz | Prova a usar |
|---|---|---|
| **Hero** | Promessa clara + para quem é, em uma frase | Print real do gráfico de evolução de carga (não estoque de imagem) |
| **Dor / agitação** | Nomeia o problema que o público já vive ("treino que nunca muda", "não sei se estou evoluindo") | Linguagem literal dos campos de anamnese (motivação, maior dificuldade) — é a mesma pesquisa de público que o produto já faz por dentro |
| **Como funciona / diferencial** | Revisão humana + IA, periodização de verdade, avaliação física | Explicação simples: "seu treino muda a cada 4–6 semanas, baseado no que você registrou de carga, não em achismo" |
| **Prova social** | Depoimento dos alunos reais + antes/depois honesto (com consentimento explícito, LGPD) | Os 10 alunos legados são a prova, não atores |
| **Oferta e preço** | Os dois níveis (Essencial/Premium) claros, sem letra miúda | — |
| **Garantia** | Ex.: primeiros 7 dias, se não fizer sentido, cancela sem custo | Reduz risco percebido sem prometer resultado de corpo |
| **FAQ / objeção** | "Preciso de equipamento?", "E se eu me machucar?", "Funciona pra iniciante?" | Respostas ancoradas nos 7 campos de anamnese já existentes |
| **CTA final** | Escassez **real**: vagas limitadas pela sua capacidade de revisão | Nunca inventar contador regressivo falso — é o tipo de mentira que o R3 acima descreve |

---

## 6. Débito técnico e dependências que a meta comercial vai expor

Se a campanha funcionar bem antes desses pontos estarem prontos, eles viram o gargalo —
avisando com antecedência, como pedido:

1. **Onboarding manual não escala para ~70 alunos em 4 meses.** Hoje aceitar aluno novo
   ainda passa por você. Se a Entrega 5 (self-service) não acompanhar o ritmo de vendas,
   o risco não é "faltar cliente" — é **sobrecarregar sua agenda de revisão e a
   experiência do aluno cair**, o que aumenta o churn bem no momento em que você mais
   precisa dele baixo.
2. **"Dieta" na copy sem nutricionista parceiro é dívida legal, não técnica** — e ao
   contrário de dívida técnica, essa não dá para "pagar depois com juros": uma
   notificação do conselho profissional não se resolve com um refactor.
3. **Preço fixo único (Cenário A) empurra volume para cima do que a revisão manual
   aguenta.** Se decidir manter R$ 89,90 único mesmo assim, o Mês 3 acima precisa da
   Entrega 5 pronta, não é opcional.

---

## 7. Decisões que só você pode tomar

Preenchi o resto do plano com a opção mais segura/razoável em cada uma destas — ajuste
se sua realidade for diferente:

1. **Você já tem audiência (Instagram, WhatsApp de leads, indicação ativa) ou começa do
   zero?** Muda o mix de canais do §4 inteiro.
2. **Tem orçamento definido para tráfego pago, ou o plano dos primeiros 90 dias precisa
   ser 100% orgânico + indicação?**
3. **Confirma a decisão de tirar "dieta prescrita" da oferta de lançamento (R1)?** Ou
   prefere buscar uma parceria formal com nutricionista antes de lançar, mesmo que
   atrase o início?
4. **Qual é o valor real cobrado hoje dos 10 alunos legados?** Isso corrige a linha
   "Base hoje" da projeção do §3, que hoje está estimada, não medida.

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
