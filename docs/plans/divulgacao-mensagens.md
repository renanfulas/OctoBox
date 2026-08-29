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

_(a redigir quando as primeiras indicações chegarem — a copy muda conforme quem indicou e o quê
o Fernando contar sobre a relação)_

## Canal 3 — Primeiro contato frio

_(a redigir na próxima rodada do ciclo semanal)_
