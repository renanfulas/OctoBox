<!--
ARQUIVO: mensagens prontas de abordagem do ciclo de divulgacao.

TIPO DE DOCUMENTO:
- biblioteca operacional de copy (texto pronto para envio)

AUTORIDADE:
- media — o texto aqui e ponto de partida versionado, nao camisa de forca.
  Ajustar tom para a relacao real com cada destinatario sempre vence o template.

DOCUMENTO PAI:
- [divulgacao-launch-plan.md](divulgacao-launch-plan.md)

DOCUMENTOS IRMAOS:
- [divulgacao-pipeline-tracker.md](divulgacao-pipeline-tracker.md)

QUANDO USAR:
- quando for enviar uma abordagem e quiser o texto ja pronto
- quando quiser ver o que ja foi testado e o que gerou resposta

POR QUE ELE EXISTE:
- o ciclo semanal do plano preve o agente redigindo mensagens toda semana; sem um lugar
  versionado, o que funciona se perde no chat e o que nao funciona volta a ser reescrito.

O QUE ESTE ARQUIVO FAZ:
1. guarda as mensagens por canal e por momento do funil.
2. registra o racional de cada escolha de copy (por que a mensagem e assim).
3. acumula o que gerou resposta e o que nao gerou.

PONTOS CRITICOS:
- pedido de indicacao a cliente atual sai do WhatsApp PESSOAL do dono do produto, nunca por
  numero de bot/automacao — sair por automacao enfraquece exatamente o que faz o pedido
  funcionar.
- nenhuma mensagem promete recurso que nao existe nem SLA de recuperacao de dados alem do que
  ja esta publicamente assumido hoje.
-->

# Mensagens de divulgação

## Canal 1 — Pedido de indicação ao cliente atual

**Destinatário:** Fernando — Endorfina Cross (Guarulhos), primeiro box pagante desde 2026-05-23.
**Meio:** WhatsApp pessoal do Renan. **Não** enviar por automação.
**Objetivo:** 2-3 indicações de outros donos de box.

### Racional da copy

1. **Abre dando saída.** "Fica à vontade pra dizer não" reduz a pressão e, na prática, aumenta
   a taxa de resposta — o pedido deixa de ser cobrança de quem já é cliente.
2. **Reenquadra o favor.** O pedido não é "me ajuda a vender"; é "você pode dar uma condição boa
   pra um amigo seu". A vaga limitada + preço de fundador viram algo que o Fernando *oferece*,
   não algo que ele pede em nome do Renan.
3. **Justifica a escassez com verdade.** "Poucas vagas porque quero acompanhar cada box de perto"
   é o motivo real (Fase 1, teto de 20 boxes, onboarding assistido), não escassez inventada.
4. **Tira trabalho dele.** "Se preferir, eu faço a ponte" — o Fernando só precisa dar um nome.
5. **Troca pergunta aberta por checklist.** A segunda mensagem é o ponto alto: "conhece alguém?"
   exige esforço de memória e costuma morrer em "vou pensar". Uma lista de 7 nomes da cidade dele
   vira reconhecimento, não lembrança — e o custo de responder cai para marcar nomes.

### Mensagem 1 — o pedido

```text
Fernando, tudo bem?

Chegando com um pedido, e fica super à vontade pra dizer não.

Tô abrindo mais algumas vagas do OctoBox no mesmo formato que você entrou: preço de fundador e o primeiro mês pra testar sem pagar. São poucas vagas porque eu quero acompanhar cada box de perto, do mesmo jeito que acompanhei a Endorfina.

Você conhece algum outro dono de box penando com planilha, WhatsApp e controle de mensalidade na mão? Se lembrar de 2 ou 3, eu falo com eles — e dá pra falar que veio de você, o que já abre a porta.

Se preferir, eu mesmo faço a ponte. Você só me diz o nome.
```

> **Linha opcional, se houver um ganho concreto da Endorfina para citar** (ex.: tempo economizado
> no fechamento do mês, inadimplência que caiu, aluno que parou de sumir na renovação): inserir
> logo depois do primeiro parágrafo, em uma frase. Ganho específico e verificável vale mais que
> qualquer adjetivo — mas **não** invente um: se não houver número real, a mensagem funciona sem.

### Mensagem 2 — a lista (enviar em seguida)

```text
Pra facilitar: separei os boxes aqui de Guarulhos. Se conhecer alguém dessa lista, me fala quem que eu já sei por onde começar 👇

• CrossFit Forvy — Jardim São Paulo
• CrossFit MK1 Vila Galvão
• CrossFit MK-1 — Timóteo Penteado
• CrossFit Vila Augusta — Santa Izabel
• CrossFit Saurus Bosque Maia — Salgado Filho
• CrossFit GRU — Castelo Branco
• Arujá CrossFit — Paulo Faccini
```

### Depois de enviar

1. Marcar no Airtable (campo `Conhece o Fernando?`) o que ele responder: `sim` / `não`.
2. Todo box marcado `sim` sobe para o topo da fila de contato — deixa de ser abordagem fria.
3. Registrar a data do envio na seção "Indicações pendentes" do
   [tracker](divulgacao-pipeline-tracker.md).
4. Sem resposta em ~4 dias: um único lembrete curto, nunca um segundo pedido completo.

## Canal 2 — Primeiro contato em box indicado

Quando o Fernando (ou outro cliente) devolver nomes, a abordagem deixa de ser fria. A diferença
não é cosmética: citar quem indicou logo na primeira linha é o que separa "número desconhecido
vendendo algo" de "conhecido de conhecido".

### Mensagem 1 — abertura com a indicação

```text
Oi, tudo bem? Meu nome é Renan.

O Fernando, da Endorfina Cross, me passou seu contato — ele usa um sistema que eu desenvolvi pra gestão de box e comentou que talvez fizesse sentido pra você também.

Posso te fazer uma pergunta rápida? Como você controla mensalidade e presença dos alunos hoje?
```

Regras:

1. **Nunca citar quem indicou sem autorização.** Confirmar com o Fernando que ele topa ser
   mencionado antes de mandar.
2. Se ele indicou mas pediu para não ser citado, usar a copy fria do Canal 3.
3. Se o Fernando contar algo específico da relação ("treinamos juntos", "ele abriu o box no mesmo
   ano"), trocar a segunda linha por isso — vale mais que qualquer template.

## Canal 3 — Primeiro contato frio

**Meio principal:** WhatsApp (é o que os dados entregam — 24 dos 31 leads têm celular).
**Meio secundário:** e-mail, quando houver.

### Racional da copy

1. **Curta de verdade.** Parede de texto vinda de número desconhecido no WhatsApp é bloqueio na
   certa. A mensagem 1 cabe em uma tela de celular sem rolar.
2. **Objetivo da mensagem 1 é resposta, não venda.** Nada de preço, nada de lista de recursos,
   nada de "podemos agendar uma call?". Só uma pergunta fácil de responder.
3. **Sem link no primeiro contato.** Link de número desconhecido tem cara de golpe e derruba a
   taxa de resposta. O Calendly entra só depois que a pessoa respondeu.
4. **Prova local em vez de credencial.** "Atendo um box aqui em Guarulhos" vale mais para um dono
   vizinho do que qualquer adjetivo sobre o produto. Concreto, verificável, e ele provavelmente
   conhece a Endorfina.
5. **A pergunta é escolhida para dar vontade de responder.** Controle de mensalidade na mão é
   dor universal e queixa fácil — dono de box gosta de falar disso. "Tem interesse em conhecer
   nosso sistema?" só produz silêncio.

### Mensagem 1 — abertura fria (WhatsApp)

```text
Oi, tudo bem? Meu nome é Renan, sou de Guarulhos.

Desenvolvi um sistema de gestão pra box de CrossFit e hoje atendo a Endorfina Cross aqui na região.

Posso te fazer uma pergunta rápida? Como vocês controlam mensalidade e presença dos alunos hoje — planilha, caderno, algum sistema?
```

### Mensagem 2 — só depois que a pessoa responder

Encaixar na dor que ela **de fato** citou. Não mandar isso solto.

```text
É exatamente por isso que eu construí o OctoBox — [conectar com o que a pessoa respondeu].

Tô abrindo poucas vagas agora, porque acompanho cada box de perto no começo. O primeiro mês é livre pra testar, sem cartão, e o preço é de fundador pra quem entra nessa fase.

Se quiser ver funcionando, são 30 min: https://calendly.com/renanfulas/octobox-conversa-com-dono-de-box
```

### Variante e-mail (quando houver endereço)

Assunto: `pergunta sobre a gestão do <nome do box>`

```text
Oi, tudo bem?

Meu nome é Renan, sou de Guarulhos e desenvolvi um sistema de gestão pra box de CrossFit. Hoje atendo a Endorfina Cross aqui na região.

Escrevo porque estou abrindo poucas vagas para os próximos boxes, e queria entender se faz sentido pra vocês antes de tomar mais do seu tempo.

Como vocês controlam mensalidade, presença e cadastro de aluno hoje? Se for planilha somada a WhatsApp, é bem provável que eu consiga ajudar.

Se quiser ver funcionando, são 30 minutos:
https://calendly.com/renanfulas/octobox-conversa-com-dono-de-box

Abraço,
Renan
```

### Guardrails do contato frio

1. **Volume:** no máximo 5-8 contatos novos por dia no WhatsApp, espaçados. Disparo em rajada
   queima o número — e número queimado custa mais caro que qualquer lead.
2. **Horário:** comercial, e nunca nos picos de aula (06:00-10:00 e 17:00-21:00) — é quando o
   dono está no salão e a mensagem morre na rolagem.
3. **Follow-up:** um único toque se não houver resposta em ~5 dias úteis. Depois disso, para.
   Dois toques sem resposta é o limite; o terceiro vira incômodo e vira bloqueio.
4. **Nunca** prometer recurso que não existe, nem SLA de recuperação de dados além do que já está
   publicamente assumido hoje.
5. Antes de contatar, conferir as notas do [tracker](divulgacao-pipeline-tracker.md): há marcas
   com duas unidades (Saurus, ZN/ZN2) e um provável endereço duplicado (Crossfit Norte × Betta).
   Abordar a mesma gestão duas vezes queima a impressão logo na largada.
