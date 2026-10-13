# Analytics de aquisição Curva

## Acesso e ativação

Acesse `/treinos/analytics/`. O cockpit pertence ao produto Curva, possui
layout e autenticação próprios e não usa usuários, papéis, tenant ou navegação
do OctoBox. As credenciais autorizadas ficam em
`PublicWorkoutStaffCredential` — a mesma tabela usada pelo login da fila de
ativação (`public_workouts/staff_auth.py`), com senha armazenada somente como
hash PBKDF2. A sessão expira em oito horas e o login limita tentativas por
origem.
Selecione coortes de 7, 30 ou 90 dias e exporte o JSON agregado pelo cockpit.
O Django Admin serve apenas para inspecionar os registros brutos de aquisição.

O painel interno exclusivo da parceria com a Jully fica em
`/treinos/analytics/influencers/jully/`. A página de divulgação é
`/treinos/jully/`. O painel geral mantém as sessões de parceiros fora das
coortes, canais, experimentos e indicadores de aquisição das campanhas próprias.
No painel da Jully, aberturas do link, visitantes, cadastros, checkouts e
primeiros pagamentos aparecem separados. A comissão é exibida como estimativa
de 60% da primeira fatura paga; renovações não entram. O painel não cria saldo
financeiro nem realiza transferências.
### Canais de influencers

A página de indicação da Jully está em `/treinos/jully/`. Ela registra o código
de parceiro em campos analíticos separados; não sobrescreve `source`, `medium`
ou `campaign` das campanhas próprias. No cockpit, a tabela **Influencers** fica
separada da tabela **Origem e campanha**. A visão consolidada continua contando
pagantes uma única vez. A comissão de 60% da primeira fatura ainda não é
transferida automaticamente pelo runtime.

`PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True` é o novo padrão. Uma variável
explícita `False` no ambiente continua desligando a coleta. O painel mostra
um aviso nesse caso; o JavaScript deixa de enviar eventos. O rollout requer
as migrations existentes de aquisição, pagamentos e eventos já aplicadas.
Não é necessário contratar ou configurar um provedor de analytics externo.

Também é possível consultar sem gravar dados:

```powershell
python manage.py report_public_workout_funnel --days 30 --conversion-days 7
```

O comando existente `capture_public_workout_metrics` inclui o relatório de
aquisição no snapshot diário, agora versão 2. Manter a execução diária já
prevista no runbook operacional; o painel consulta os dados atuais e não
depende do agendamento para funcionar.

## Experimentos e otimização contínua

A fundação de experimentos usa a própria sessão anônima de aquisição como
unidade de randomização. Cada visitante recebe uma variante de forma
determinística e mantém essa variante durante todo o experimento. Iniciar um
experimento não altera a landing sozinho: o payload atribuído fica disponível
no elemento JSON `curva-experiment-assignments` para uma implementação visual
posterior consumir explicitamente.

Crie primeiro como rascunho:

```powershell
python manage.py configure_public_workout_experiment `
  --key hero-promessa-v1 `
  --name "Promessa principal do hero" `
  --hypothesis "Uma promessa mais concreta aumenta o primeiro pagamento" `
  --variant controle:50 `
  --variant promessa-concreta:50 `
  --minimum-sample-size 100
```

Revise as variantes e execute novamente com `--start` para iniciar. O relatório
considera o primeiro pagamento positivo confirmado pelo servidor dentro da
janela configurada, usa somente visitantes com janela encerrada para a decisão
e mostra intervalo de Wilson de 95%. Um candidato aparece apenas quando todas
as variantes atingem a amostra mínima e o intervalo do líder não se sobrepõe ao
segundo colocado. Isso é recomendação: `winner_variant_key` nunca é preenchido
e nenhuma experiência é promovida automaticamente.

Regras operacionais:

- não execute dois experimentos que alterem a mesma parte da landing;
- não mude o significado de uma variante durante um experimento em execução;
- pause antes de alterar pesos; atribuições existentes permanecem imutáveis;
- avalie reembolso, falha de checkout e qualidade da atribuição antes de
  publicar qualquer vencedor;
- registre a hipótese antes de iniciar, para evitar escolher uma narrativa
  depois de ver os números.

## Definição da conversão

- Visitante: identificador assinado em cookie próprio, HttpOnly, SameSite=Lax,
  Secure fora de DEBUG, válido por 90 dias. É um navegador reconhecido, não
  uma identificação garantida de pessoa. Não soma reloads como visitantes.
- Coorte: primeira identificação dentro do período escolhido e ao menos uma
  visita à landing registrada até o horário do relatório. Retornos de coortes
  antigas não entram como novos visitantes. Clientes que já tinham pago antes
  da primeira identificação são excluídos quando essa associação é conhecida.
- Pagante: primeiro pagamento positivo da conta, confirmado no registro
  financeiro do servidor, dentro de 7 dias da primeira identificação. Não
  depende de um pixel, da página de sucesso ou de `invoice_paid` do navegador.
- Conversão: pagantes da coorte / visitantes da mesma coorte. A divisão vazia
  é indisponível, nunca zero. Renovações, retries e cobranças zero não somam
  aquisições. Reembolso mantém a aquisição histórica e aparece separadamente.
- Janela encerrada: visitantes com os 7 dias completos. Use essa taxa para
  comparar com a meta de 10%; a taxa "até agora" ainda pode crescer.
- Sem avanço: visitante com janela encerrada que não alcançou a etapa
  seguinte em 7 dias. Não significa desistência definitiva nem identifica
  automaticamente a causa. Uma compra depois de 7 dias aparece na cobertura
  do período, mas não na conversão de 7 dias. O CLI permite janelas maiores.

O funil comercial é **visita → cadastro aceito → checkout criado → primeiro
pagamento**. Um fato posterior implica os anteriores quando um evento faltou.
As etapas opcionais de navegação ficam separadas para um bloqueador de scripts
não apagar uma venda real. O nome `checkout_started` significa sessão criada
no servidor, não prova de que a página hospedada foi visualizada.

## Eventos e diagnóstico

| Sinal | Fonte | Uso |
| --- | --- | --- |
| `landing_viewed` | servidor | Entrada na landing |
| `cta_clicked`, `pricing_viewed` | navegador | Interesse e exposição ao preço |
| `signup_started`, `signup_submitted` | navegador | Início e envio válido |
| `signup_invalid`, `signup_failed` | navegador | Validação ou falha visível |
| `tier_selected`, `checkout_started` | servidor | Cadastro aceito e sessão de pagamento criada |
| `checkout_redirected` | navegador | Navegação enviada ao checkout externo |
| `checkout_authorized` | webhook | Checkout completado na Stripe; não equivale a recebimento |
| primeiro pagamento positivo | registro financeiro | Conversão, deduplicada por conta |
| `login_required` | servidor | Conta existente precisa autenticar |
| `waitlist_joined` | servidor | Demanda bloqueada pela capacidade |
| `checkout_failed` | servidor | Configuração impede criação do checkout |
| `payment_failed` | webhook | Falha de pagamento |
| `checkout_canceled` | retorno autenticado | Retorno sem conclusão |
| `faq_opened` | navegador | Consulta de objeções |

Eventos do navegador são deduplicados por tipo/plano em cada carregamento e
por UUID no servidor. O endpoint exige cookie de aquisição válido, CSRF e
campos permitidos; nunca aceita confirmação de pagamento do cliente. Limite
de 60 envios por minuto por cookie. Não captura valores de campos, mensagens
de erro livres, gravações de sessão ou dados de saúde.

## Origem, cobertura e limites

Use links com `utm_source`, `utm_medium` e `utm_campaign`, por exemplo:
`/treinos/?utm_source=instagram&utm_medium=paid_social&utm_campaign=curva_setembro`.
Não coloque dados pessoais nas UTMs. O painel compara o primeiro contato por
origem, mídia, campanha e versão da landing. Contatos seguintes ficam no
registro de aquisição. Navegação interna não sobrescreve a origem; referrer
externo guarda apenas host, sem caminhos, credenciais ou query strings.

A cobertura mostra novos pagantes do negócio no período versus os que possuem
visita anterior atribuída, incluindo outras coortes. Não dividir esse total
de pagamentos pelas visitas da coorte. O bloco `funnel.counts` nos snapshots
continua contendo eventos brutos para compatibilidade; as taxas de aquisição
da versão 2 usam visitantes da coorte. O relatório `acquisition` e o painel são
a fonte para conversão. `paid_by_source` e o CAC da versão 2 também usam
primeiros pagantes, atribuídos ao primeiro contato; renovações não reduzem o
CAC artificialmente. Custos da mesma campanha são somados. Se um lançamento
de custo cruza os limites do período, o CAC fica indisponível em vez de
prorratear um gasto cuja distribuição diária não conhecemos. A cobertura
legada `commercial.attribution` ainda descreve eventos de cobrança; a cobertura
de novos clientes está em `acquisition.coverage`.

Visitas de staff autenticado e robôs conhecidos não entram na coleta.
Bloqueadores, cookies removidos, troca de aparelho, robôs não identificados e
eventos anteriores à ativação limitam a precisão. O painel não reconstrói
visitas passadas nem promete identificação entre dispositivos. A origem já
vinculada a uma assinatura é preservada ao retomar em outro navegador.

## Validação depois do deploy

1. Confirmar coleta ativa no painel e webhook Stripe operacional.
2. Abrir uma visita de teste com UTM em navegador separado; ver preços,
   preencher e enviar. Conferir sinais e origem na aquisição correspondente.
3. Em ambiente de teste Stripe, concluir um pagamento e verificar uma única
   aquisição. Repetir o webhook e simular renovação: não somar novo pagante.
4. Validar lista de espera, login exigido e erro de cadastro separadamente.
5. Aguardar o fechamento da janela antes de comparar taxas por campanha.
   Abaixo de 100 visitantes maduros, o painel sinaliza amostra inicial; 100
   não é garantia estatística e não substitui um teste de hipótese planejado.

O rollback da coleta é a flag `False`; os dados históricos continuam legíveis.

## Treino guiado e notificações

O painel `/treinos/analytics/` mostra sessões guiadas iniciadas, concluídas,
parciais, canceladas e abandonadas, taxa de conclusão, séries e as 20 sessões
recentes na janela selecionada. A lista aceita filtro por conta e abre o detalhe
da sessão com as séries do aluno, sob a mesma autenticação interna do Curva.
"Sem encerramento" é calculado para sessões abertas há mais de 72 horas;
uma sincronização offline tardia pode reclassificá-las, sem cron que feche o fato antes da chegada.
`public_workouts/training_analytics.py` fornece a mesma agregação SQL para o
painel e para o snapshot diário; execução fica fora do funil de aquisição.
Quando presente, `guided_prescription` no programa publicado define estágios,
mínimo/máximo, papéis, descanso e regra de carga. `guided_workout.py` adapta
somente os programas antigos: faixas reconhecíveis mantêm séries opcionais;
texto ambíguo oferece registro livre `legacy_unknown`, sem inventar contagem.
O descanso estruturado vem da etapa; no legado permanece o padrão de 90 s.

`PublicWorkoutTrainingSession` aponta para a versão imutável de
`PublicWorkoutProgram`. Cada Top elegível e sua referência de carga são gravadas
na mesma transação. A conclusão integral exige o mínimo prescrito; séries
opcionais podem ficar abertas. O aluno pode encerrar como parcial, pular uma
série ou cancelar. Correções de Top supersedem o `LoadLog` anterior e preservam
uma revisão auditável. O GET de `/renan/<slug>/sessao` permite retomar uma
sessão recente e nunca entra no cache do service worker. As migrations `0041`,
`0042` e `0043` adicionam vínculo de programa, desfechos e decisões por série.

O aluno autenticado encontra o aviso **Receba avisos da Curva** na home. O
clique explícito solicita a permissão do navegador e grava a subscription do
dispositivo na conta Curva. O aluno pode desativar os avisos neste dispositivo.
O aviso de ativação, o de programa publicado e o de conclusão passam pela outbox Curva; o comando
`drain_public_workout_outbox` precisa estar agendado. Instalar o PWA sozinho
não concede permissão.
Configure `STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY`,
`STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY` e
`STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT` e
`PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS` (domínios exatos ou sufixos de host de
provedores de push permitidos, separados por vírgula) no ambiente antes de
ativar o botão. Sem essas configurações o aviso continua visível e informa
que a ativação está pendente. A migration `0040_training_sessions_and_push`
cria as tabelas de sessões, séries e dispositivos inscritos.
