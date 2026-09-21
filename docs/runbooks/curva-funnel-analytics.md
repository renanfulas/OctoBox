# Analytics de aquisição Curva

## Acesso e ativação

No Django Admin, abra **Public workout acquisition sessions** e clique em
**Analytics · Funil e conversão**. A rota nomeada é
`admin:public_workouts_funnel_analytics`, sob o prefixo privado já configurado
para o admin. Exige a permissão de visualizar o modelo de aquisição; não é uma
rota pública. Selecione coortes de 7, 30 ou 90 dias e exporte o JSON agregado.

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
