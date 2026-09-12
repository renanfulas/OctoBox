<!--
ARQUIVO: C.O.R.D.A. de correcao dos bugs de login/magic link/cadastro do app do aluno (onda 2026-09-11).

TIPO DE DOCUMENTO:
- plano de correcao de bugs em producao
- plano de execucao por ondas, bug a bug

AUTORIDADE:
- alta para esta onda especifica de correcao (login, magic link, cadastro, 404, mensageria de erro, senha do owner)

DOCUMENTOS PAI:
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)
- [../architecture/octobox-mobile-architecture.md](../architecture/octobox-mobile-architecture.md)

QUANDO USAR:
- quando for implementar a correcao dos bugs relatados em 2026-09-11 sobre login/magic link/cadastro do app do aluno e a UX de senha na criacao do box
- quando precisar saber, bug a bug, o que quebra, o que nao quebra, onde mexer e por que

POR QUE ELE EXISTE:
- registra o diagnostico completo feito por leitura de codigo (sem traceback de producao ainda) para nao repetir a investigacao.
- separa "parar o sangramento" (fix minimo e seguro) de "solucao elegante" (fix que fecha a classe de bug, nao so o sintoma) — e registra explicitamente as solucoes elegantes que foram COGITADAS E DESCARTADAS, com o motivo, para ninguem propor de novo sem ler o porque.
- evita que os bugs sejam tratados como patches isolados quando na verdade compartilham uma causa estrutural comum (ver secao D).

O QUE ESTE ARQUIVO FAZ:
1. documenta a fotografia atual de cada bug com evidencia de arquivo:linha.
2. separa, por bug, o que foi CONFIRMADO como causa raiz do que foi DESCARTADO por leitura de codigo.
3. propoe, para cada bug, o fix mais simples que resolve a causa raiz sem inventar mecanismo novo — e registra quando uma solucao "mais esperta" foi cogitada e rejeitada por ir contra a arquitetura do app.
4. ordena a execucao em ondas pequenas, com "o que entra" / "o que nao entra" / "pronto quando" por onda.

PONTOS CRITICOS:
- Bug 1 (erro ao gerar link do grupo) NAO tem causa raiz confirmada por leitura estatica — o plano trata isso como investigacao instrumentada, nao como fix as cegas.
- Bug 2 e Bug 3 tem causa raiz confirmada com arquivo:linha e sao os unicos que causam erro 500 real (nao so UX ruim).
- para Bug 2 e Bug 3, uma solucao "inteligente" de auto-juncao/auto-merge foi cogitada e DESCARTADA depois de confirmar que o app nao tem nenhum sinal seguro pra inferir "essas duas contas sao a mesma pessoa" — toda `StudentIdentity` ja nasce com credencial de provider real, entao merge por e-mail seria abrir uma porta de sequestro de conta. A solucao inteligente de verdade, aqui, e mensagem de erro especifica (ex.: "voce ja usou Google antes, entra com Google") em vez de fusao automatica.
- Bug 6 (novo, adicionado nesta revisao) e sobre a senha do Owner na criacao do box: falta feedback vivo de requisitos, e o backend hoje so exige tamanho minimo — nenhuma das validacoes de senha que o staff ja tem (`AUTH_PASSWORD_VALIDATORS`) se aplica a conta mais privilegiada do box.

REVISAO 1 (mesmo dia, apos reler `oauth_actions.py`, `use_cases.py` e `repositories.py` com foco adversarial):
- a Onda 1 original era mais complexa do que precisa — ja existe um caminho de erro generico bom em `oauth_actions.py:90-105` que usa `_map_failure_reason` (`views.py:108-119`), que ja tem a copy certa para `box-root-mismatch`. Nao e preciso inventar mensagem nova, so parar de desviar desse caminho.
- a causa raiz mais profunda do Bug 2 foi refinada: nao e (so) o `if/else` do `oauth_journeys.py` — e que `save_identity` (`repositories.py:258`) procura identidade existente por `find_live_by_student_id(student.id)`, uma chave que so existe DENTRO do schema do tenant atual, enquanto `StudentIdentity` e um modelo de schema publico (compartilhado entre boxes).
- a Onda 5 deixou de propor um arquivo novo (`error_copy.py`) e passou a propor generalizar `_map_failure_reason`, que ja e esse registro, so que hoje vive preso dentro de `StudentSignInView`.
- o risco de ortografia quebrar teste foi verificado e descartado.
- a unificacao visual de `403.html` com os outros 4 templates foi separada como sub-onda opcional.

REVISAO 2 (mesmo dia, apos investigar se dava pra "deixar o aluno entrar de verdade no box novo" e se dava pra resolver duplicatas com merge automatico):
- a Onda 2 original (auto-criar `StudentBoxMembership` para o box novo quando acha `provider_subject` de outro box) foi DESCARTADA. Motivo: e o unico mecanismo hoje que liga uma identidade a um box diferente e chama-se `TransferStudentToBox` (`use_cases.py:123-152`) — e ele e deliberadamente um MOVE (nao um "vinculo duplo"), exige `actor_id` (acao de staff, auditada) e checa conflito de e-mail no box de destino (`target-box-email-conflict`). Criar membership automatico a partir de um callback OAuth publico, sem ator e sem essa checagem de conflito, seria abrir um caminho novo e nao revisado de vincular identidade a box — contra o proprio principio ja documentado em `student-access-invite-switch-corda.md`: "Membership e vinculo explicito, nao inferencia". A Onda 1 sozinha (mostrar o erro que ja existe) passa a ser a solucao COMPLETA do Bug 2, nao so o "fix minimo".
- pelo caminho, confirmei duas coisas que tornam outras partes do plano mais seguras: (a) a sessao do aluno e um cookie assinado e autocontido (`infrastructure/session.py:33-44`) — mudar `identity.box_root_slug` no banco nao afeta sessoes ja abertas; (b) nenhum dos 11 handlers do dispatcher (`staff_action_dispatcher.py`) levanta `Http404`/`PermissionDenied` de proposito, entao o try/except generico da Onda 0 e seguro.
- para Bug 3 (duplicatas), cogitei um "claim automatico" de identidade por e-mail (se a pessoa que esta se cadastrando bate o e-mail de uma identidade ja existente no mesmo box, reaproveitar em vez de bloquear). Investigado e DESCARTADO pelo mesmo motivo do Bug 2: toda `StudentIdentity` no banco ja nasce com `provider_subject` real (nao existe estado de "identidade pendente sem provider" pra reivindicar) — entao um e-mail batendo em duas autenticacoes de provider diferentes sao, por definicao, dois logins diferentes reivindicando o mesmo e-mail. Fundir automaticamente seria deixar login B assumir o historico de login A so por coincidencia de e-mail: risco de sequestro de conta. A saida inteligente e mais simples e mais segura: enriquecer a mensagem de erro com um dado que ja temos (qual provider a conta existente usou) para guiar a pessoa certa pro caminho certo, sem fundir nada.
- adicionado Bug 6 a pedido do usuario: falta de feedback vivo de requisito de senha na criacao do Box, e o achado extra de que o backend so valida tamanho (nao usa `AUTH_PASSWORD_VALIDATORS`, que ja protege a troca de senha do staff).

REVISAO 3 (pente-fino de seguranca sobre as proprias correcoes propostas — cacando bug escondido nas ondas, nao no codigo original):
- achado critico: `save_identity` ja e `@transaction.atomic` (`repositories.py:247`). Um `try/except IntegrityError` direto em volta de `identity.save()`, DENTRO desse mesmo bloco atomico, nao funciona — o Django marca a transacao "precisa de rollback" assim que o erro de banco acontece, e qualquer query seguinte no mesmo bloco (ex.: `_ensure_membership_status`, que roda logo depois) estoura `TransactionManagementError`. A correcao do 500 criaria outro 500. Fix: savepoint interno (`with transaction.atomic(): identity.save()`) dentro do try. Esse cuidado NAO se aplica a `_handle_change_email` (`staff_membership_actions.py`), que nao e atomico — la, try/except direto ja basta. `IntegrityError` tambem nao esta importado ainda em `repositories.py`.
- achado critico: a Onda 5 ia usar `message.tags` direto como `tone` de `state_notice.html`. So que o Django marca `messages.error()` com a tag `'error'` por padrao (`MESSAGE_TAGS` nao e customizado nas settings), e o CSS de `state_notice.html` so define `.state-notice-danger` (`states.css:165`), nao `.state-notice-error` — toda mensagem de erro renderizaria sem estilo de perigo, silenciosamente. Remapear `MESSAGE_TAGS` globalmente pra `danger` foi cogitado e descartado: isso quebraria dois componentes que ja funcionam hoje e dependem do valor cru `'error'` (`checkout-message--error` em signup-checkout.css, `student-flash--error` em flash.css). Fix: mapeamento local (so no ponto de uso de `state_notice.html`), nao mudanca global.
- achado: o plano pedia pra `_map_failure_reason` "migrar" de string pra `{eyebrow,title,copy,hint}`. Isso quebraria `oauth_actions.py:91`, que ja faz `messages.error(request, map_failure_reason(...))` esperando string — o dict viraria texto literal da mensagem. Fix: a funcao que devolve string continua existindo do jeito que esta (compatibilidade), a versao rica e uma funcao irma nova, nao uma migracao.
- achado nao-critico, registrado para o futuro: `StudentIdentityStatus.BLOCKED` existe no enum mas nunca e setado em lugar nenhum do codigo hoje. Diferente do e-mail (constraint condicional), `provider_subject` tem `unique=True` incondicional — se `BLOCKED` for implementado um dia, aquela conta Google/Apple fica banida de criar qualquer identidade nova, pra sempre, em qualquer box. Nao e bug ativo (o estado nunca e alcancado hoje), so uma pegadinha de design a observar quando/se banimento for implementado.
- achado de sequenciamento: a Onda 6 (senha) so deve subir com as duas partes juntas — validacao de backend mais rigida sem o indicador vivo na mesma entrega seria pior que nao mexer (cliente que acabou de pagar levaria rejeicao de senha sem nenhuma pista visual).

REVISAO 4 (cyberseguranca — o plano abre brecha nova ou deixa brecha antiga aberta?):
- confirmado, nao suposto: nenhum ponto onde a mensagem fica mais especifica (Onda 1, Onda 3, Onda 5) vira oraculo de enumeracao barato. `find_by_provider_subject` e o e-mail duplicado so disparam depois de um OAuth de verdade ja concluido (o "atacante" precisaria ja controlar a conta Google/Apple alheia). `_student_phone_exists` so e chamado dentro de `clean_phone()` de formulario (sem endpoint AJAX/JSON, confirmado por grep) e so e alcancado apos OAuth (`student_app/forms.py`) ou com autenticacao de staff (`catalog/form_definitions/student_forms.py`) — nao e sonda anonima escalavel.
- a decisao de nao fazer auto-merge/auto-join (Onda 2 descartada) e a maior contribuicao de seguranca do plano: evita vincular identidade a um box sem ator humano e sem checagem de conflito.
- achado novo: `signup/services.py:315` — `raise InvalidMagicTokenError(f'status-invalido:{pending.status}')` injeta o valor bruto do enum interno (`pending.status`) na string de erro. Hoje isso e inofensivo porque o `else` generico do template nao printa esse valor. Ao implementar a cobertura dessa causa na Onda 5 (item 5), NAO ecoar `pending.status` cru pro usuario — vira uma unica mensagem generica e estavel ("Este link ainda não está pronto para uso."), nunca um passthrough do enum. Vazamento baixo (vocabulario interno, nao acesso a conta), mas do tipo que passa despercebido numa implementacao apressada de UX.
- distincao a manter em mente para qualquer token assinado (HMAC via `django.core.signing`, usado no source-capture e no magic-token de ativacao do Owner): diferenciar "expirado" de "assinatura invalida" e seguro (verificacao HMAC e tudo-ou-nada, saber qual dos dois nao ajuda a forjar uma assinatura nova) — e exatamente o padrao que o plano ja usa. Ja tokens em UUID de banco (invite individual, box invite link) tambem sao seguros com erro verboso, porque o espaco de busca (128 bits aleatorios) torna irrelevante qualquer diferenca de mensagem. A regra pratica: verbosidade da mensagem de erro deve escalar com o valor protegido pelo token, nao ser aplicada por reflexo em todo lugar.
- guardrail novo, adicionado na Onda 5: `cta_href`/`cta_label` (campo novo em `state_notice.html`) sempre precisa ser URL fixa/`reverse()`, nunca construida a partir de request/query string — sem essa trava, um botao de ajuda numa tela de erro pode virar open redirect.
- guardrail novo, adicionado na Onda 0: o log de excecao nao pode despejar `request.POST` cru — so metadados estruturados (`action`, `request.user.id`, `box_root_slug`). Importa mais depois da Onda 6, com senha/e-mail/telefone passando perto desses handlers.
- guardrail novo, adicionado na Onda 6: o JS do indicador de senha nunca pode transmitir ou logar o valor da senha — tudo calculado em memoria no navegador, sem request de rede, e sem passar perto de script de analytics/session-replay que capture inputs de formulario.

REVISAO 5 (implementacao real da Onda 5 — achado que reduziu o escopo original):
- o item "trocar `_flash_stack.html`/`checkout.html`/`onboarding.html` para `state_notice.html`" foi CORTADO desta implementacao. Motivo: `student_app` carrega so `css/student_app/app.css` (`templates/student_app/_partials/_head_assets.html`) e `signup/onboarding.html`/`checkout.html` carregam so `tokens.css` + `marketing-landing.css` + `signup-checkout.css` — nenhum dos dois bundles inclui `design-system/components/states.css`, onde `.state-notice`/`.state-notice-danger` sao definidos (confirmado via grep, nao suposto). Trocar o componente sem isso renderizaria uma mensagem de erro SEM ESTILO NENHUM numa pagina pos-pagamento — pior do que nao mexer. Sem Postgres/Docker disponivel nesta sessao pra verificar visualmente (ver nota de ambiente), a decisao mais segura foi nao arriscar. Entregue em vez disso, com o mesmo objetivo (mensagem clara com proximo passo) mas sem risco de CSS: extracao de `map_student_oauth_failure_reason` pra modulo reutilizavel; enriquecimento de `email-conflict` com o provider da conta existente (a "acao inteligente" pedida, sem merge automatico); CTA na mensagem de WhatsApp duplicado; e as causas orfas de `token_error` em `signup/onboarding.html` cobertas (com o guardrail de nao ecoar `pending.status` cru, normalizado na fronteira em `signup/views.py::OnboardingWizardView.dispatch`). A troca de componente visual fica registrada como item futuro, a fazer numa passada com verificacao visual real (browser + servidor rodando).
-->

# C.O.R.D.A. - Bugs de login, magic link, cadastro e senha do app do aluno/box

## C - Contexto

Bugs relatados em 2026-09-11 na area de login/magic link/link de grupo/cadastro do app dos alunos, mais um pedido de UX na criacao do box. Cada um foi investigado por leitura de codigo (sem acesso a traceback de producao). Abaixo, bug a bug: o que quebra, o que nao quebra, e a evidencia.

### Bug 1 - Dono do box: erro ao clicar em "gerar link do grupo"

**Caminho real do clique:** `templates/student_identity/operations_invites.html:34` (POST `action=create-box-link`) -> [student_identity/staff_action_dispatcher.py:11](../../student_identity/staff_action_dispatcher.py) -> [student_identity/staff_invite_actions.py:107-136](../../student_identity/staff_invite_actions.py) (`_handle_create_box_link`) -> `CreateStudentBoxInviteLink.execute()` ([use_cases.py:61-71](../../student_identity/application/use_cases.py)) -> [repositories.py:211-237](../../student_identity/infrastructure/repositories.py) (`create_or_replace_box_invite_link`).

**O que verifiquei e descartei, com evidencia:**
1. Nao existe `UniqueConstraint`/`unique_together` em `StudentBoxInviteLink` que rejeite criar um novo link quando ja existe um ativo ([models.py:449-489](../../student_identity/models.py)) — o codigo revoga o ativo (`update(revoked_at=now)`) e cria um novo, dentro de `@transaction.atomic`. Padrao correto.
2. `created_by=` no `models.py:466` existe como `ForeignKey` real — `created_by_id=actor_id` em `repositories.py:235` e uma kwarg valida, nao quebra.
3. `reverse("student-identity-box-invite", kwargs={"token": result.token})` (`staff_invite_actions.py:118`) aponta para uma rota que **existe** ([student_identity/urls.py:20](../../student_identity/urls.py)) — nao e um `NoReverseMatch`.
4. `get_box_runtime_slug()` ([shared_support/box_runtime.py:28-57](../../shared_support/box_runtime.py)) tem fallback defensivo e nao levanta excecao em caminho nenhum.
5. O gate de permissao (`can_operate_invites`) e consistente entre template e view — nao ha brecha de quem ve o botao vs quem passa no POST.

**Achado real (nao e causa raiz, e um sintoma estrutural):** `_handle_create_box_link` e o **unico** handler do dispatcher (`staff_action_dispatcher.py:10-22`, 11 actions) sem nenhum try/except ao redor e sem teste de integracao que toque o banco de verdade. Confirmei tambem que nenhum dos 11 handlers levanta `Http404`/`PermissionDenied` de proposito — entao um error-boundary generico no dispatcher e seguro (nao ha controle de fluxo por excecao pra atropelar).

**Veredito:** sem traceback real, apontar uma linha especifica seria chute. O plano trata isso como **Onda 0: instrumentar antes de adivinhar**.

### Bug 2 - Aluno que ja tem box: link nao funciona (nem app, nem direto) — **causa raiz confirmada**

Fluxo: aluno abre o "link do grupo" (`box_invite_link`) -> OAuth Google/Apple -> [student_identity/oauth_journeys.py:57-113](../../student_identity/oauth_journeys.py) (`handle_student_special_oauth_journey`, branch `box_invite_link`).

**O que quebra:**
```python
# oauth_journeys.py:75
if result.success and result.identity is not None:
    ...
    return response
repository.record_box_invite_acceptance(box_invite_link)   # linha 84
...
return redirect('student-app-onboarding')                   # linha 113
```
Esse `if/else` trata **qualquer** `result.success == False` como "e aluno novo, manda pro wizard". So existe UM motivo de falha que deveria cair aqui: `invite-not-found` (aluno sem `StudentIdentity` previa). Mas [use_cases.py:83-86](../../student_identity/application/use_cases.py) tambem devolve `success=False` com `failure_reason='box-root-mismatch'` quando o aluno **ja tem uma `StudentIdentity`** (ja logou antes, em outro box) — e esse motivo cai no mesmo `else`, sendo tratado como "aluno novo".

O aluno preenche o wizard de novo, e o crash real acontece em [student_app/workflows/onboarding_workflows.py:84-101](../../student_app/workflows/onboarding_workflows.py) -> [repositories.py:248-283](../../student_identity/infrastructure/repositories.py) (`save_identity`): como `find_live_by_student_id` nao acha nada para o `Student` novo, o codigo cria uma **`StudentIdentity` nova** com um `provider_subject` que **ja existe** em outra identity (campo `unique=True`, [models.py:173](../../student_identity/models.py)). `identity.save()` estoura `IntegrityError` **nao capturado em lugar nenhum da cadeia** -> erro 500 cru, igual pelo navegador direto ou pelo app.

**O que NAO quebra (contraste que prova o diagnostico):** o branch de convite individual (`invitation`, linhas 115-162) faz certo: se `not result.success`, retorna `None` e deixa `oauth_actions.py:90-105` mostrar a mensagem de erro ja mapeada (`_map_failure_reason`, `views.py:108-119`). Essa funcao **ja tem** a copy certa: `'box-root-mismatch': 'Esta conta de aluno pertence a outro box.'`. O bug esta isolado no branch `box_invite_link`, que nunca chega a esse caminho porque sempre devolve um redirect proprio, nunca `None`.

**Por que so mudar o `if/else` nao basta sozinho (a causa mais profunda):** `StudentIdentity` e um modelo de **schema publico** — compartilhado entre todos os boxes (por isso `find_by_provider_subject` roda no callback OAuth, que executa em `PUBLIC_SCHEMA_PATHS`, antes de qualquer tenant ser ativado). Ja `Student` (o cadastro/ficha do aluno) e um modelo **por-tenant** — uma linha por box. Quando o aluno de outro box usa o link em massa, o wizard cria um `Student` novo dentro do schema do box B e so entao chama `save_identity`, que decide se ha identidade existente assim:
```python
# repositories.py:258
identity = self.find_live_by_student_id(student.id)  # student.id e LOCAL ao schema do box B
```
Esse `student.id` e a chave primaria do `Student` **recem-criado no box B** — nunca vai bater com a identidade que pertence ao `Student` de outro schema (box A). Resultado: `save_identity` nunca encontra a identidade antiga por esse caminho e tenta `StudentIdentity.objects.create(..., provider_subject=...)` com um `provider_subject` que ja existe -> `IntegrityError`.

**Solucao "esperta" cogitada e DESCARTADA — por que nao vamos deixar o aluno entrar automaticamente no box novo:** cheguei a desenhar um fix onde `save_identity` tambem procuraria por `find_by_provider_subject` e, ao achar a identidade de outro box, criaria um `StudentBoxMembership(status=PENDING_APPROVAL)` pro box novo — reaproveitando `_ensure_membership_status`, que ja existe. Investiguei se isso bate com como o app ja resolve "essa identidade agora se relaciona com outro box" e achei que sim, ja existe um mecanismo — `TransferStudentToBox` ([use_cases.py:123-152](../../student_identity/application/use_cases.py)) — so que ele e **deliberadamente diferente** do que eu ia construir:
1. e um **move** (troca o box), nao um vinculo duplo silencioso.
2. exige `actor_id` — e sempre uma acao de staff, auditada.
3. checa conflito de e-mail no box de destino (`target-box-email-conflict`) antes de mover.

Criar membership automaticamente a partir de um callback OAuth publico (sem ator, sem essa checagem) seria abrir um segundo caminho, mais fraco, pra a mesma decisao que o app ja trata com cuidado em outro lugar — e contraria o principio ja registrado em [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md): *"Membership e vinculo explicito, nao inferencia."* **Decisao: nao fazer.** Se o produto realmente quiser "aluno ativo em 2 boxes ao mesmo tempo" via link em massa, isso merece um desenho novo com os mesmos cuidados do `TransferStudentToBox` (ator, auditoria, checagem de conflito) — nao um efeito colateral de bug fix.

**O que a Onda 1 faz, entao, e e suficiente:** para de mascarar `box-root-mismatch` como "aluno novo" e deixa cair na mensagem que ja existe. Mais um cinto de seguranca (checar `find_by_provider_subject` em `save_identity` antes de criar) para nenhum outro caminho, presente ou futuro, conseguir duplicar `provider_subject` — mas so pra devolver uma falha limpa, nunca pra criar membership sozinho.

### Bug 3 - Cadastro com WhatsApp/telefone/email ja existente — **causa raiz confirmada**

**Telefone/WhatsApp: ja protegido, nao e a causa.** [student_app/forms.py:174-183](../../student_app/forms.py) e [catalog/form_definitions/student_forms.py:303-310](../../catalog/form_definitions/student_forms.py) chamam `_student_phone_exists(...)` e devolvem "Ja existe um aluno cadastrado com este WhatsApp." de forma limpa.

**E-mail: aqui esta o bug.** O commit `bd01222e` removeu o campo `email` do formulario de onboarding e, junto, removeu a chamada ao validador de duplicidade (`_student_identity_email_exists`, [student_app/forms.py:38-49](../../student_app/forms.py)), que **ficou orfa**. E-mail duplicado hoje so e pego pela constraint condicional do Postgres ([models.py:186-194](../../student_identity/models.py)), que nao passa pela validacao de formulario — estoura `IntegrityError` cru, sem try/except, em dois pontos:
1. [student_identity/infrastructure/repositories.py:258-283](../../student_identity/infrastructure/repositories.py) (`save_identity`).
2. [student_identity/staff_membership_actions.py:176](../../student_identity/staff_membership_actions.py) (`_handle_change_email`).

O "erro de sobreposicao" relatado e, com alta probabilidade, essa mensagem tecnica do Postgres vazando crua pra tela.

**"Acao inteligente" pedida para duplicatas — o que investiguei:** cogitei um "claim automatico" — se o e-mail que esta chegando ja bate com uma `StudentIdentity` existente no mesmo box, reaproveitar aquela identidade (anexar o novo login) em vez de bloquear. Pra isso ser seguro, precisaria existir um estado de "identidade pendente, ainda sem provider definido" pra reivindicar. **Confirmei que esse estado nao existe**: toda `StudentIdentity` e criada exclusivamente por `save_identity`, sempre com `provider`/`provider_subject` reais vindos de uma troca OAuth ja concluida ([repositories.py:260-269](../../student_identity/infrastructure/repositories.py) — `create_invitation` so cria `StudentAppInvitation`, nunca `StudentIdentity`). Ou seja: se um e-mail novo bate com uma identidade que ja tem provider, sao **necessariamente dois logins diferentes** disputando o mesmo e-mail (ex.: a pessoa trocou de conta Google, ou e outra pessoa com e-mail parecido). Fundir automaticamente por coincidencia de e-mail deixaria um login novo assumir o historico de um login antigo sem prova nenhuma de que e a mesma pessoa — **risco de sequestro de conta, nao conveniencia**. **Decisao: nao fazer merge automatico.**

**O que E seguro e inteligente, e vai entrar na Onda 5:** em vez de fundir, enriquecer a mensagem de erro com um dado que o sistema ja tem — qual provider a conta existente usou (`identity.provider`, campo ja existente em `StudentIdentity`) — pra guiar a pessoa certa: *"Esse e-mail ja tem cadastro neste box, feito com Google. Entra com Google em vez de criar um cadastro novo."* Isso e estritamente leitura (nenhuma escrita nova), zero risco de sequestro, e resolve a parte do pedido que realmente importa: parar de deixar a pessoa presa num erro sem saber o que fazer.

### Bug 4 - Pagina 404 frequente + ortografia

**Ortografia confirmada (nao so no 404):**

| Arquivo:linha | Atual | Correcao |
|---|---|---|
| `templates/404.html:12` | `aria-label="Pagina nao encontrada"` | "Página não encontrada" |
| `templates/404.html:23` | `aria-label="Acoes"` | "Ações" |
| `templates/400.html:21` | "Algo nesse pedido nao fez sentido..." | "...não fez sentido..." |
| `templates/400.html:23` | `aria-label="Acoes"` | "Ações" |
| `templates/429.html:23` | `aria-label="Acoes"` | "Ações" |
| `templates/500.html:21` | "Nao foi possivel concluir essa etapa agora." | "Não foi possível concluir..." |
| `templates/500.html:23` | `aria-label="Acoes"` | "Ações" |
| `templates/403.html:14,17,20` | "Voce", "nao", "permissao", "voce acha", "e um erro", "seguranca" | acentuar tudo |

Achado extra: `templates/403.html` usa um layout e um tom de copy diferentes dos outros 4. Inconsistencia de familia visual, nao so ortografia.

**Causa do 404 frequente (o sintoma real, a ortografia e secundaria):** [catalog/views/student_views.py:888-954](../../catalog/views/student_views.py) (`StudentSourceCaptureView`, rota publica `/alunos/origem/qualificar/`). Seis causas de falha diferentes — token ausente, `BadSignature`, `SignatureExpired`, tenant ambiguo — todas colapsadas em `raise Http404('Link de qualificacao invalido.')`, caindo direto na pagina 404 generica. Contraste: `StudentInviteLandingView`/`StudentBoxInviteLandingView` ja tratam isso com contexto dedicado e nunca levantam `Http404`.

**O que NAO e a causa** (verificado e descartado): `boxcore/urls.py` e codigo morto; o fluxo OAuth do aluno ja mapeia praticamente toda falha para `messages.error` + redirect.

### Bug 5 - Mensagens de erro nao explicam o que aconteceu

**O componente certo ja existe** — [templates/includes/ui/states/state_notice.html](../../templates/includes/ui/states/state_notice.html) ja suporta `tone` + `eyebrow` + `title` + `copy` + `hint` + modo `compact`. So que ele so e usado na area logada/staff.

As duas telas pre-auth relevantes reinventam versoes mais pobres:
- [templates/student_app/_partials/_flash_stack.html](../../templates/student_app/_partials/_flash_stack.html) — renderiza so `{{ message }}` cru.
- `templates/signup/checkout.html:78-83` e `templates/signup/onboarding.html:63-69` — um terceiro componente proprio (`checkout-messages`).

Nao ha registro central de "motivo de falha -> copy humana" fora de `_map_failure_reason`. E exatamente por isso que Bug 2, 3 e 4 viram tela ruim.

**Gap encontrado no diagnostico inicial e que nao tinha virado item de nenhuma Onda ainda:** [templates/signup/onboarding.html:109-125](../../templates/signup/onboarding.html) (tela de "criar senha do Owner apos pagamento") so trata explicitamente `token_error == 'token-expirado'` e `'ja-ativado'`. As outras causas que `signup/services.py` ja distingue — `'token-vazio'`, `'token-invalido'`, `'pending-nao-encontrado'`, `'status-invalido:*'` — caem todas no mesmo `else` generico: *"Não conseguimos validar este link."* Nao e um 500 nem um 404 (a mensagem ja e razoavel), mas e exatamente o mesmo padrao dos outros bugs desta onda: causa especifica conhecida no backend, colapsada em mensagem generica na tela. Isso pega o mesmo Owner que acabou de pagar, num momento de alto risco de frustracao — mesmo publico e mesmo motivo do Risco 7 (Onda 6). Entra na Onda 5 (ver Acao).

### Bug 6 (novo) - Criacao do Box: senha sem feedback vivo de requisito

O usuario pediu: na hora de criar o box, o campo de senha exige um minimo de caracteres mas nao mostra ao vivo quantos caracteres tem, nem se a senha bate o padrao (letras, numeros, quantidade).

**Onde isso acontece:** [signup/forms.py:103-119](../../signup/forms.py) (`OnboardingForm`, o wizard de 1 tela que o Owner usa apos o pagamento pra criar username + senha). O campo real:
```python
password = forms.CharField(
    label='Crie uma senha',
    widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 10 caracteres'}),
    min_length=10,
    max_length=128,
)
```
(o minimo real e **10**, nao 9 — o numero exato que o usuario lembrou esta um pouco errado, mas o problema que ele descreveu e real.) O template ([templates/signup/onboarding.html:80-91](../../templates/signup/onboarding.html)) renderiza o form genericamente (`{% for field in form %}{{ field }}...`), sem nenhum JS de feedback — a unica pista e o `placeholder`, que some assim que a pessoa comeca a digitar.

**Achado extra (nao pedido, mas relevante):** `OnboardingForm.password` e um `forms.CharField` puro — **nao** chama `django.contrib.auth.password_validation.validate_password()`. Isso significa que `AUTH_PASSWORD_VALIDATORS` ([config/settings/base.py:520-533](../../config/settings/base.py): `UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) **nao se aplica** a essa senha. Em contraste, `StaffSetPasswordForm` ([access/password_reset.py:118-133](../../access/password_reset.py)) estende `SetPasswordForm` do Django, que **ja chama** `validate_password()` — ou seja, hoje a troca de senha de um funcionario qualquer e mais protegida do que a criacao da senha do **Owner**, a conta mais privilegiada do box. Nenhum desses validators exige "letras E numeros" (isso nao existe nos validators padrao do Django — `NumericPasswordValidator` so rejeita senha 100% numerica), entao o indicador vivo deve mostrar exatamente o que e validado de verdade, nao inventar regra que o backend nao aplica.

## O - Objetivo

1. parar os dois erros 500 reais (Bug 2 e Bug 3) o mais rapido possivel, com o menor blast radius, sem inventar mecanismo de auto-juncao/merge que a arquitetura do app nao tem hoje.
2. dar visibilidade real ao Bug 1 (hoje nao reproduzivel por leitura de codigo).
3. fechar o buraco estrutural que faz Bug 2, 3 e 4 caírem em tela sem explicacao — generalizando o contrato "motivo de falha -> mensagem humana" que ja existe, em vez de escrever copy hardcoded em cada tela.
4. corrigir a ortografia dos templates de erro.
5. dar feedback vivo de requisito de senha na criacao do box, e alinhar a validacao dessa senha com a que o staff ja tem.

Sucesso significa:

1. nenhum fluxo de aluno (login, magic link, cadastro) pode terminar em `IntegrityError`/`Http404` cru visivel pro usuario.
2. toda falha de negocio conhecida tem uma frase clara de "o que aconteceu + por que + o que fazer" — incluindo, quando fizer sentido, qual e o proximo passo certo (ex.: qual provider usar).
3. nenhuma fusao/merge automatica de identidade acontece em lugar nenhum do sistema sem um ator humano e uma checagem de conflito, igual ao padrao que `TransferStudentToBox` ja estabelece.
4. o dono do box tem como saber, da proxima vez que "gerar link do grupo" falhar, exatamente o que quebrou.
5. a senha do Owner tem a mesma validacao de qualidade que a senha de staff ja tem, com feedback vivo no formulario.
6. nenhuma fachada publica (`save_identity`, `AuthenticateStudentWithProvider.execute`, rotas de invite) muda de assinatura.

## R - Riscos

### 1. Reintroduzir a ideia de auto-merge/auto-join mais tarde sem ler por que foi rejeitada

Esse e o risco mais importante desta revisao. Registrar a decisao (secao C, Bug 2 e Bug 3) e o proprio mecanismo de mitigacao — qualquer PR futuro que proponha "juntar automaticamente" deve linkar pra ca e explicar por que dessa vez e diferente.

### 2. Fechar demais o e-mail duplicado e travar reativacao legitima

A checagem de duplicidade de `save_identity` so deve olhar `status__in=[PENDING, ACTIVE]` — se checar contra identidades `REVOKED`/inativas, um aluno que saiu e voltou fica bloqueado por engano.

### 3. Registro central de copy virar over-engineering

Regra: continua um `dict` simples (extensao de `_map_failure_reason`), nao um framework novo.

### 4. Ortografia mudar contrato de teste — verificado e descartado

Nenhum teste hoje faz assert no texto dos templates de erro.

### 5. Onda 0 (Bug 1) virar desculpa para nao investigar de verdade

O ticket do Bug 1 continua aberto ate aparecer um traceback real.

### 6. Error-boundary da Onda 0 pode esconder inconsistencia de auditoria

Algumas actions fazem `AuditEvent.objects.create(...)` e depois `record_student_onboarding_event(...)` fora de um unico `@transaction.atomic`. O log de excecao da Onda 0 deve registrar ate onde a action chegou, pra essa inconsistencia pre-existente ficar visivel em vez de silenciosa.

### 7. Indicador de senha (Bug 6) prometer regra que o backend nao aplica

Se o indicador vivo mostrar "precisa ter letra e numero" sem o backend exigir isso, a UI mente. Mitigacao: o indicador so mostra o que `validate_password()` de fato valida (tamanho minimo, nao ser so numeros); checagens que dependem de lista grande (senha comum) ficam so no erro pos-submit, como e normal em qualquer formulario real.

### 8. `try/except IntegrityError` sem savepoint, dentro de funcao ja atomica

Achado na Revisao 3: capturar `IntegrityError` de um `.save()` que roda dentro de uma funcao `@transaction.atomic` (caso de `save_identity`), sem um `with transaction.atomic()` interno como savepoint, deixa a transacao externa marcada "precisa de rollback" — qualquer query seguinte na mesma funcao estoura `TransactionManagementError`. Mitigacao: savepoint interno em volta do `.save()`, especificado nas Ondas 1 e 3. `_handle_change_email` nao tem esse risco (nao roda dentro de nenhum `@transaction.atomic`).

### 9. `message.tags` usado direto como `tone` do `state_notice.html`

Achado na Revisao 3: o Django marca `messages.error()` com a tag `'error'`, mas o CSS do componente so define `.state-notice-danger` — usar a tag crua faz mensagens de erro renderizarem sem estilo de perigo. Mitigacao: mapeamento local `error`→`danger` no ponto de uso (Onda 5), nunca um `MESSAGE_TAGS` global (quebraria `checkout-message--error` e `student-flash--error`, que ja funcionam hoje com a tag crua).

### 10. Provider_subject nunca se libera se `BLOCKED` for usado no futuro

Registrado para vigilancia, nao para acao agora: `StudentIdentityStatus.BLOCKED` existe no enum mas nunca e setado hoje. `provider_subject` tem `unique=True` incondicional (diferente do e-mail, que e condicional a `status`) — se um banimento via `BLOCKED` for implementado no futuro, aquela conta Google/Apple fica impedida de criar qualquer identidade nova, para sempre, em qualquer box. Quem implementar `BLOCKED` no futuro precisa decidir se isso e intencional ou se `provider_subject` precisa virar constraint condicional tambem.

## D - Direcao

### Tese central (a "solucao mais brilhante" pedida)

Os bugs 2, 3, 4 e 5 nao sao problemas separados de UX — sao **1 problema estrutural** aparecendo em varios lugares: **o sistema tem pontos onde uma falha de negocio conhecida e tratada como excecional/generica**, em vez de virar mensagem humana previsivel. A parte nova desta revisao: em pelo menos dois desses lugares (Bug 2, Bug 3), a tentacao e resolver isso com inferencia automatica (juntar contas/boxes que "parecem" ser a mesma coisa) — e o app **ja tem uma opiniao formada contra isso** (`TransferStudentToBox` exige ator e checa conflito; nao existe estado de identidade "pendente sem provider" pra reivindicar). A solucao inteligente, entao, nao e inferir — e **usar o dado que ja existe pra guiar a pessoa pro caminho manual certo** (mensagem especifica, CTA certo), sem nunca decidir por ela.

Entao a Direcao deste plano e:

1. **generalizar, nao duplicar**, o registro de "codigo de falha -> copy" que ja existe (`_map_failure_reason`), reaproveitando o componente visual que ja existe (`state_notice.html`).
2. **fechar os buracos de 500 na fonte** (repository), nao so no template.
3. **nunca inferir identidade/merge por coincidencia de dado** (e-mail, provider_subject) sem ator humano e checagem de conflito — se o produto quiser isso um dia, e um design novo, nao um bug fix.
4. onde a causa da falha e conhecida, usar esse conhecimento pra enriquecer a mensagem (ex.: "essa conta usa Google", "essa senha e so numeros") em vez de so bloquear.

### Frases de arquitetura

1. `Falha de negocio conhecida nunca vira excecao generica — vira codigo de falha com copy dedicada.`
2. `Identidade e global (schema publico); Student e local a cada box — nenhuma busca de "identidade existente" pode usar so a chave local.`
3. `Duas identidades autenticadas por provider_subject diferentes nunca se fundem sozinhas — falta sempre um sinal seguro de que sao a mesma pessoa; quando o produto quiser permitir isso, e acao de ator com checagem de conflito, como `TransferStudentToBox` ja faz.`
4. `Nenhum .save() em StudentIdentity acontece sem checar duplicidade antes.`
5. `Um registro de copy, um componente de notice, tres telas — nao o contrario.`
6. `Indicador de senha mostra so o que o backend de fato valida.`

### Onde mexe / onde nao mexe (visao geral)

**Mexe:**
- `student_identity/oauth_journeys.py` (branch `box_invite_link` — so a condicao de quando seguir pro onboarding)
- `student_identity/infrastructure/repositories.py` (`save_identity` — cinto de seguranca contra `provider_subject` duplicado; checagem de duplicidade de e-mail)
- `student_identity/staff_membership_actions.py` (`_handle_change_email`)
- `student_identity/staff_action_dispatcher.py` (error boundary)
- `catalog/views/student_views.py` (`StudentSourceCaptureView`, causas de 404)
- `student_identity/views.py` (`_map_failure_reason` sai de metodo privado para funcao reutilizavel, com entradas novas incluindo o provider da conta existente)
- `templates/400.html`, `403.html`, `404.html`, `429.html`, `500.html` (ortografia)
- `templates/student_app/_partials/_flash_stack.html`, `templates/signup/checkout.html`, `templates/signup/onboarding.html` (reaproveitar `state_notice.html`)
- `signup/forms.py` (`OnboardingForm.clean_password`, wiring de `validate_password`)
- `templates/signup/onboarding.html` (indicador vivo de senha) + 1 arquivo JS pequeno novo

**Nao mexe:**
- assinatura publica de `save_identity`, `AuthenticateStudentWithProvider.execute`, `CreateStudentBoxInviteLink.execute`, `StudentIdentityAuthResult`.
- `_ensure_membership_status` continua privado do `DjangoStudentIdentityRepository` — nao vaza pra fora dele.
- `TransferStudentToBox` — continua sendo o unico caminho pra mover identidade entre boxes; nenhum caminho novo e criado nesta onda.
- `StudentIdentity`/`StudentBoxMembership` (modelos) — nenhuma migration.
- fluxo de convite individual (`invitation` branch em `oauth_journeys.py`) — ja funciona certo.
- telefone/WhatsApp em `student_app/forms.py` — ja funciona certo (so ganha CTA de copy na Onda 5).
- `StaffSetPasswordForm`/`access/password_reset.py` — ja usa `validate_password()` corretamente, nao muda.
- nenhum arquivo novo de registro de copy — `error_copy.py` NAO entra.
- nenhuma logica de merge/claim automatico de identidade por e-mail ou provider_subject.

## A - Acao

## Onda 0 - Rede de seguranca no dispatcher + instrumentacao do Bug 1

### O que fazer
1. envolver `dispatch_student_invitation_post_action` (`staff_action_dispatcher.py:26-29`) num try/except que loga a excecao completa (`action`, `request.user.id`, `box_root_slug`) e devolve uma resposta de erro amigavel em vez de deixar a excecao subir crua.
2. vale para as 11 actions do dispatcher, nao so `create-box-link`.
3. escrever o teste de integracao real que falta para `_handle_create_box_link` (banco real).
4. **guardrail de seguranca (achado na Revisao 4): o log de excecao so registra metadados estruturados** (`action`, `request.user.id`, `box_root_slug`, tipo da excecao) — **nunca `request.POST` cru**. Alguns dos 11 handlers passam perto de e-mail/telefone; nao dumpar o corpo do POST no log evita PII/segredo parando em arquivo de log por acidente.

### O que entra
- `student_identity/staff_action_dispatcher.py`
- 1 teste novo de integracao em `student_identity/tests.py`

### O que nao entra
- nenhuma mudanca em `staff_invite_actions.py` ainda.

### Pronto quando
1. qualquer excecao futura em qualquer action deste dispatcher vira log com traceback completo + tela de erro amigavel.
2. o teste de integracao de `create-box-link` roda contra banco real e passa.
3. o ticket do Bug 1 continua aberto ate aparecer um traceback real.

## Onda 1 - Bug 2, solucao completa (nao so "minima")

### O que fazer
1. em `oauth_journeys.py:75`, so seguir para o onboarding quando `not result.success and result.failure_reason == 'invite-not-found'` (aluno realmente novo). Para qualquer outro motivo (`box-root-mismatch`, `provider-subject-required`), o branch **devolve `None`** — exatamente como o branch `invitation` ja faz.
2. **nao e preciso escrever mensagem nova.** Ao devolver `None`, `finalize_student_oauth_callback` (`oauth_actions.py:90-105`) ja chama `messages.error(request, map_failure_reason(...))`, que **ja tem** `'box-root-mismatch': 'Esta conta de aluno pertence a outro box.'`.
3. em `save_identity`, antes de criar uma `StudentIdentity` nova, adicionar um cinto de seguranca: se `find_by_provider_subject(provider_subject)` achar uma identidade (de qualquer box), **nao criar uma segunda** — devolver uma falha explicita (nao um `IntegrityError` cru). Isso protege qualquer chamador futuro, nao so este.
4. **cuidado de implementacao (achado na Revisao 3):** `save_identity` ja e `@transaction.atomic`. Se ainda assim algum `.save()` disparar `IntegrityError` (ex.: corrida entre duas requests), capturar isso com um savepoint interno, nao um try/except cru no mesmo nivel:
```python
from django.db import IntegrityError, transaction
try:
    with transaction.atomic():
        identity.save()
except IntegrityError:
    return <registro de falha explicito>
```
Sem o `with transaction.atomic()` interno, o bloco atomico externo fica marcado "precisa de rollback" e qualquer query seguinte na mesma funcao (ex.: `_ensure_membership_status`, que roda logo depois) estoura `TransactionManagementError` — trocaria um 500 por outro.
4. **decisao explicita (ver Contexto/Direcao): nao criar `StudentBoxMembership` automaticamente para o box novo.** O aluno recebe a mensagem clara e, se quiser mesmo entrar no box novo, o caminho e pedir pro staff desse box novo usar o mecanismo que ja existe (`TransferStudentToBox`) ou mandar um convite individual apos resolver manualmente.

### O que entra
- `student_identity/oauth_journeys.py` (condicao do `if`)
- `student_identity/infrastructure/repositories.py` (cinto de seguranca em `save_identity`)

### O que nao entra
- qualquer criacao automatica de membership ou identidade compartilhada entre boxes.
- mudanca em `use_cases.py`/`StudentIdentityAuthResult`.

### Pronto quando
1. um aluno com identidade em outro box que abre o link do grupo nunca mais recebe 500 — recebe a mensagem que ja existe, pelo mesmo caminho que o convite individual ja usa.
2. teste de integracao cobrindo "provider_subject existente em box A, tentativa via link em massa do box B" confirma: sem crash, sem membership criado, 1 `StudentIdentity` so.

## Onda 2 (descartada) - registrada apenas para nao ser reproposta sem contexto

A ideia de criar `StudentBoxMembership(status=PENDING_APPROVAL)` automaticamente dentro de `save_identity` quando acha `provider_subject` de outro box foi cogitada e rejeitada — ver secao C (Bug 2) e D. Se o produto decidir que quer isso no futuro, comecar por desenhar o equivalente de `target-box-email-conflict` e exigir um ator (mesmo que seja "o proprio aluno confirma explicitamente", nao so o clique automatico do OAuth), nao reabrir esta onda como estava.

## Onda 3 - Bug 3 (e-mail duplicado)

### O que fazer
1. reconectar a checagem de duplicidade de e-mail **na fonte** (repository): antes do `identity.save()` em `save_identity`, checar `StudentIdentity.objects.filter(email__iexact=email, box_root_slug=box_root_slug, status__in=[PENDING, ACTIVE]).exclude(pk=identity.pk if identity else None).exists()` e devolver falha explicita (`email-already-registered`) em vez de deixar o `.save()` estourar.
2. mesma checagem antes de `identity.email = new_email` em `staff_membership_actions.py:176` (`_handle_change_email`) — extrair um helper pequeno reusado nos dois lugares em vez de duplicar a query.
3. cinto de seguranca: try/except `IntegrityError` nos dois `.save()` — **mas nao do mesmo jeito nos dois lugares** (achado na Revisao 3):
   - em `save_identity` (ja `@transaction.atomic`), o `.save()` precisa de savepoint interno (`with transaction.atomic(): identity.save()` dentro do try) — ver detalhe na Onda 1, item 4. Sem isso, o try/except nao protege nada, so troca o tipo do 500.
   - em `_handle_change_email` (nao esta dentro de nenhum `@transaction.atomic`), um try/except direto em volta de `identity.save(update_fields=[...])` ja e suficiente, sem precisar de savepoint.
4. a checagem antecipada (`.exists()`) e o cinto de seguranca (`except IntegrityError`) tem que devolver a **mesma mensagem** ao usuario. A checagem antecipada cobre o caso comum; o except cobre a corrida rara (dois cadastros simultaneos com o mesmo e-mail) — se as duas mensagens divergirem, o usuario ve um erro diferente dependendo de uma corrida que ele nem percebe que aconteceu.
5. **nao fazer claim/merge automatico** (ver Contexto) — o e-mail duplicado sempre vira mensagem, nunca reaproveitamento silencioso de identidade alheia.

### O que entra
- `student_identity/infrastructure/repositories.py`
- `student_identity/staff_membership_actions.py`

### O que nao entra
- `student_app/forms.py` (a funcao orfa pode ser removida depois, nao e pre-requisito).
- telefone/WhatsApp — ja funciona.
- qualquer logica de merge/claim.

### Pronto quando
1. tentar registrar/trocar para um e-mail ja ativo no mesmo box devolve mensagem clara em vez de `IntegrityError` cru.
2. teste cobrindo colisao de e-mail em `save_identity` e em `_handle_change_email` existe.

## Onda 4 - Bug 4 (404 frequente + ortografia)

### O que fazer
1. em `catalog/views/student_views.py:888-954`, parar de colapsar 6 causas em `Http404` generico — resolver a causa especifica e renderizar pagina propria nos moldes de `invite_landing.html`.
2. corrigir a acentuacao em `templates/400.html`, `403.html`, `404.html`, `429.html`, `500.html`.

### O que entra
- `catalog/views/student_views.py`
- novo template de erro de captura de origem
- os 5 templates de erro (so texto/acentuacao)

### O que nao entra
- `boxcore/urls.py` — codigo morto.
- rotas de convite — ja tratam erro certo.
- unificacao visual do `403.html` — vira Onda 4b, opcional.

### Pronto quando
1. nenhuma causa de falha em `StudentSourceCaptureView` cai mais em `Http404` generico.
2. os 5 templates de erro sem erro de acentuacao.

## Onda 4b (opcional, separada) - Unificar layout do `403.html`

### O que fazer
1. migrar `403.html` para o mesmo `checkout-status.css` e tom de copy dos outros 4.

### Pronto quando
1. as 5 paginas de erro compartilham layout e tom; pode ser adiada sem bloquear as outras.

## Onda 5 - Bug 5 (generalizar `_map_failure_reason` + reaproveitar `state_notice.html` + copy inteligente de duplicata)

### O que fazer
1. **nao migrar** `_map_failure_reason` (`views.py:108-119`) de tipo — extrair ela de metodo privado pra funcao de modulo reutilizavel, mas mantendo o retorno como string simples (achado na Revisao 3: `oauth_actions.py:91` ja faz `messages.error(request, map_failure_reason(...))` esperando string; se essa funcao passar a devolver um dict, o dict vira texto literal da mensagem). A versao rica e uma **funcao irma nova** (ex.: `get_failure_copy(code) -> {eyebrow, title, copy, hint}`), lendo do mesmo dicionario fonte — nao uma substituicao.
2. estender o dicionario fonte com os codigos novos das Ondas 1/3/4 (`email-already-registered`, causas do `StudentSourceCaptureView`).
3. **enriquecer especificamente `email-already-registered`** com o provider da conta existente (dado ja disponivel em `identity.provider`): *"Esse e-mail ja tem cadastro neste box, feito com {Google/Apple}. Entra com {provider} em vez de criar um cadastro novo."* — a "acao inteligente" pedida, sem merge automatico.
4. adicionar uma frase de proximo passo tambem na mensagem de WhatsApp/telefone duplicado (`_student_phone_exists`), ex.: CTA para "Já é aluno? Peça o link de acesso na recepção." — copy simples, sem mudar a validacao que ja funciona.
5. **cobrir as causas orfas do `token_error` em `templates/signup/onboarding.html:109-125`** (gap do diagnostico inicial, ver Contexto): hoje so `'token-expirado'` e `'ja-ativado'` tem branch propria; `'token-vazio'`, `'token-invalido'`, `'pending-nao-encontrado'` e `'status-invalido:*'` (ja distinguidos em `signup/services.py`) caem no mesmo `else` generico. Dar a cada um uma frase especifica, no mesmo espirito das causas de `StudentSourceCaptureView` (Onda 4) — mesmo publico de risco (Owner que acabou de pagar) que motiva o cuidado de sequenciamento da Onda 6. **Guardrail de seguranca (achado na Revisao 4):** `signup/services.py:315` levanta `InvalidMagicTokenError(f'status-invalido:{pending.status}')`, injetando o valor bruto do enum interno na mensagem. Ao dar uma frase pra essa causa, tratar `'status-invalido:*'` como **um unico bucket generico e estavel** ("Este link ainda não está pronto para uso.") — nunca ecoar `pending.status` cru pro usuario, pra nao vazar vocabulario interno do modelo de dados (ex.: um valor de status tipo `cancelled`/`refunded`).
6. adicionar `cta_label`/`cta_href` opcionais em `state_notice.html` (aditivo). **Guardrail de seguranca (achado na Revisao 4): `cta_href` sempre uma URL fixa/`reverse()`, nunca construida a partir de request/query string** — sem essa trava, um botao de ajuda numa tela de erro pode virar open redirect.
7. trocar `_flash_stack.html`, `signup/checkout.html` e `signup/onboarding.html` para usar `state_notice.html` em modo `compact`, usando `get_failure_copy` (item 1) quando a mensagem carregar um codigo.
8. **cuidado de implementacao (achado na Revisao 3): mapear a tag do Django pro `tone` do componente, nao usar `message.tags` direto.** Django marca `messages.error()` com a tag `'error'` por padrao (`MESSAGE_TAGS` nao e customizado nas settings), mas o CSS de `state_notice.html` so define `.state-notice-danger` (`states.css:165`) — usar `message.tags` cru faria toda mensagem de erro renderizar sem estilo de perigo, silenciosamente. Fix: um mapeamento pequeno e **local** (`error`→`danger`, resto igual) so no ponto de uso deste componente. **Nao** mudar `MESSAGE_TAGS` globalmente — isso quebraria dois componentes que ja funcionam hoje e dependem do valor cru `'error'` (`checkout-message--error`, `student-flash--error`). Se algum dia `extra_tags` for usado pra carregar um codigo junto da tag (ex.: `"error email-already-registered"`), lembrar que `message.tags` vira multi-token — extrair so o primeiro token pro `tone`, o resto e o codigo pra buscar em `get_failure_copy`.
9. rodar **depois** das Ondas 1, 3 e 4.

### O que entra
- `student_identity/views.py` (extracao da funcao)
- `student_app/forms.py` (copy do erro de WhatsApp duplicado)
- `templates/includes/ui/states/state_notice.html`
- `templates/student_app/_partials/_flash_stack.html`, `templates/signup/checkout.html`, `templates/signup/onboarding.html` (inclui os branches novos de `token_error`)

### O que nao entra
- componente usado pela area staff — continua igual.
- qualquer arquivo novo de registro.
- qualquer logica de merge/claim automatico.

### Pronto quando
1. app do aluno e telas de signup mostram erro com titulo + explicacao + proximo passo especifico.
2. os 3 componentes de mensagem viram 1.
3. a mensagem de e-mail duplicado diz qual provider usar.
4. `signup/onboarding.html` mostra uma frase especifica pra cada `token_error` que `signup/services.py` ja distingue — nenhuma causa nova cai mais no `else` generico.

## Onda 6 (novo) - Bug 6: senha do Owner, indicador vivo + alinhar validacao

### O que fazer
1. em `signup/forms.py` (`OnboardingForm`), chamar `django.contrib.auth.password_validation.validate_password(password)` — a mesma suite que `StaffSetPasswordForm` ja usa (`AUTH_PASSWORD_VALIDATORS`: tamanho minimo, nao ser senha comum, nao ser so numeros, nao ser parecida com o username). Fecha a inconsistencia de a conta mais privilegiada do box ter a validacao mais fraca. **Detalhe de implementacao:** para o `UserAttributeSimilarityValidator` (senha parecida com o username) funcionar de verdade, `validate_password` precisa receber um `user=` — como a conta ainda nao existe nesse ponto, montar um `User(username=self.cleaned_data.get('username'))` transitorio (nao salvo) e passar como `user=`. Isso so e possivel se a checagem rodar no `clean()` do form (onde `username` ja esta em `cleaned_data`, dado que o campo `username` vem antes de `password` na declaracao do form), nao num `clean_password()` isolado — sem o `user=`, os outros validators (tamanho, comum, so-numerico) continuam funcionando normalmente, so a similaridade com o username fica inerte.
2. em `templates/signup/onboarding.html`, adicionar um indicador vivo simples abaixo do campo de senha: contador de caracteres (`X/10`) que fica marcado quando atinge o minimo, e um check de "nao e so numeros" (regex simples, client-side, espelha o `NumericPasswordValidator`). Nao tentar replicar client-side a checagem de senha comum (precisaria de uma lista grande) — essa continua so no erro pos-submit, como e normal em qualquer formulario.
3. progressive enhancement: sem JS, o form continua funcionando exatamente como hoje (so com a validacao de backend, agora mais forte).
4. **guardrail de seguranca (achado na Revisao 4): o JS do indicador nunca transmite nem loga o valor da senha.** Contagem de caracteres e o check de "so numeros" rodam inteiramente em memoria no navegador (leitura direta do `value` do input, sem `fetch`/`XHR` nenhum) — nao existe motivo pra esse dado sair do campo. Cuidado extra se o projeto tiver qualquer script de analytics/session-replay com autocapture de formulario: o campo de senha precisa continuar excluido dessa captura (via atributo `data-*` de opt-out, se o script suportar, ou confirmando que o seletor de autocapture ja ignora `type="password"`).
4. **as duas partes (item 1 e item 2) tem que subir juntas, na mesma entrega** (achado na Revisao 3): colocar so a validacao de backend mais rigida no ar, sem o indicador vivo, seria pior que nao mexer em nada — um cliente que acabou de pagar levaria uma rejeicao de senha surpresa, sem nenhuma pista visual do motivo, bem no ultimo passo antes de usar o produto que pagou.

### O que entra
- `signup/forms.py`
- `templates/signup/onboarding.html`
- 1 arquivo JS pequeno novo (ex.: `static/js/pages/signup/password_hints.js`)

### O que nao entra
- `StaffSetPasswordForm`/`access/password_reset.py` — ja corretos.
- qualquer nova dependencia/biblioteca de força de senha.
- tentativa de checar "senha comum" no client-side.

### Pronto quando
1. senha totalmente numerica ou senha comum falha no submit com mensagem clara do Django.
2. o campo mostra ao vivo quantos caracteres faltam pro minimo e se a senha e so numeros.
3. sem JS, o formulario ainda funciona (so sem o feedback ao vivo).

## Critérios de pronto globais

1. nenhum fluxo de login/magic link/cadastro do aluno pode terminar em 500 cru visível pro usuário.
2. nenhuma causa de falha conhecida cai em `Http404` genérico quando existe causa específica identificável.
3. existe exatamente 1 componente de notice de erro usado em staff, app do aluno e signup.
4. aluno com identidade em outro box recebe erro claro e específico (não genérico, não 500) ao abrir o link de grupo — sem nenhuma junção automática de conta/box acontecer por trás.
5. os 5 templates de erro estão com acentuação correta (layout unificado do 403 é opcional, Onda 4b).
6. o Bug 1 tem rede de segurança mesmo sem causa raiz confirmada ainda.
7. a senha do Owner passa pela mesma validação de qualidade que a senha de staff, com feedback vivo no formulário.

## Failure checks

Se qualquer item abaixo acontecer, a onda foi executada errado:

1. capturar `IntegrityError` só para esconder o erro, sem corrigir a busca de identidade em `save_identity` que causa a duplicação.
2. qualquer código passar a criar `StudentBoxMembership` ou fundir `StudentIdentity` automaticamente (por e-mail ou por `provider_subject`) sem ator humano e sem checagem de conflito equivalente à de `TransferStudentToBox`.
3. a extração de `_map_failure_reason` virar uma classe abstrata/plugin system em vez de continuar um dict simples.
4. `AuthenticateStudentWithProvider.execute` ou `StudentIdentityAuthResult` mudarem de forma por causa deste plano.
5. `state_notice.html` perder compatibilidade com quem já o usa hoje (área staff).
6. o indicador de senha (Bug 6) afirmar uma regra que `validate_password()` não aplica de verdade.

## Resumo executivo

O mapa da obra é este:

1. Onda 0 dá rede de segurança pro Bug 1 sem chutar correção.
2. Onda 1 resolve o Bug 2 por completo: para o 500 removendo o desvio em `oauth_journeys.py` e reaproveitando mensagem que já existe. A ideia de deixar o aluno entrar automaticamente no box novo foi cogitada e descartada (Onda 2, registrada só para não ser reproposta sem contexto) porque o único mecanismo real de mover identidade entre boxes já existe (`TransferStudentToBox`) e é deliberadamente manual, auditado e com checagem de conflito.
3. Onda 3 fecha o mesmo tipo de buraco para e-mail duplicado — mesma decisão: mensagem clara, nunca merge automático (o app não tem, hoje, nenhum estado de identidade "pendente sem provider" que tornaria isso seguro).
4. Onda 4 resolve o 404 frequente pela causa e arruma ortografia; unificar o visual do 403 vira Onda 4b opcional.
5. Onda 5 fecha o padrão de mensagens — e é onde mora a "ação inteligente" real para duplicatas: usar o dado que já existe (qual provider a conta usou) para guiar a pessoa, em vez de decidir por ela.
6. Onda 6 (novo) resolve o pedido de UX da senha do Owner e, de brinde, alinha a validação dessa senha com a que o staff já tem.

Em linguagem simples:

1. dois bugs realmente quebram o sistema (2 e 3) — a causa dos dois vivia no mesmo lugar (`save_identity` decidindo criar identidade sem checar direito se já existia uma).
2. duas vezes a tentação foi "resolver juntando automaticamente" — e as duas vezes o app já tinha uma resposta melhor: fazer isso é ação de gente, não de inferência por coincidência de dado.
3. um bug não tem causa provada ainda (1) — ganha um alarme melhor, não um remendo.
4. um bug é sintoma de rota mal tratada (4) — vira igual às rotas que já fazem certo.
5. o pedido de UX melhor (5) é destravar um componente e um registro que já existem.
6. o pedido novo da senha (6) é dar ao Owner o mesmo cuidado de senha que o staff já tem, com feedback na hora.
