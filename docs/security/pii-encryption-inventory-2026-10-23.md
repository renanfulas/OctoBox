# Inventário de cifragem de PII — G1

Data de inspeção: 2026-10-23. Este relatório descreve código e migrations no
checkout; não consulta nem estima conteúdo de bases ativas.

## Estado atual observado

`shared_support/crypto_fields.py` deriva uma chave Fernet de
`SECRET_KEY[:32].ljust(32, b'O')`, codificada em URL-safe base64. Os campos
`EncryptedCharField` e `EncryptedTextField` escrevem tokens Fernet sem versão
nem identificador de chave até o rollout do novo writer. Desde G2, a leitura
classifica plaintext legado, Fernet e envelope versionado; valor cifrado
inválido lança erro sanitizado. A escrita segue no formato Fernet legado,
falha fechada se a cifra não estiver disponível e não passa ciphertext de
entrada sem criptografar.

| Modelo / campo | Tabela e schema | Armazenamento ORM atual | Busca/integração observada |
|---|---|---|---|
| `Student.phone` | `boxcore_student`, tenant | Model declara `max_length=255`, `storage_max_length=2048`; migration muda `varchar(255)` para `varchar(2048)` | `phone_lookup_index` HMAC `v1:` em coluna separada; busca de telefone deve usar esse índice |
| `Student.cpf` | `boxcore_student`, tenant | Model declara `max_length=255`, `storage_max_length=2048`; migration muda `varchar(255)` para `varchar(2048)` | Novo `cpf_lookup_index` HMAC com domínio separado; `boxcore.0034` e backfill command locais, ainda não aplicados a tenant real |
| `Student.email` | `boxcore_student`, tenant | `EmailField`, `varchar(254)` por contrato Django | OAuth faz igualdade `email__iexact`; diretório mantém busca parcial `email__icontains`; Admin também pesquisa. Escritores incluem `QuerySet.update()` de membership e fluxos de onboarding/import. Cifra exigiria separar igualdade de busca parcial e adaptar os três consumidores |
| `StudentIdentity.email` | `student_identity_studentidentity`, public/shared | `EmailField` permanece em claro; migration `student_identity.0006` adiciona `email_lookup_index` separado, sem alterar a coluna existente | Quatro leitores passam por `student_identity.queries.email_lookup`: resolver OAuth tenant, login público, repository por Box e validação de conflito no formulário; HMAC com domínio próprio, dual-write e backfill agregado; leitura indexada só após gate de prontidão |
| `StudentInvitationDelivery.recipient` | `student_identity_studentinvitationdelivery`, public/shared | `EncryptedCharField(max_length=255, storage_max_length=2048)`; migration `student_identity.0005` amplia a coluna e mantém leitor legado/versionado | Sem lookup funcional no app; exibição operacional pelo ORM. Busca por recipient removida do Admin porque substring em ciphertext não funciona; acesso Admin segue Owner/DEV staff ou superuser |
| `StudentAppInvitation.invited_email` | `student_identity_studentappinvitation`, public/shared | `EncryptedEmailField(blank=True, max_length=254, storage_max_length=2048)`; `0007` marca `is_qa_seed`, `0008` adiciona `email_lookup_index` HMAC e `0009` amplia o armazenamento físico sem mudar o limite lógico | ORM lê plaintext legado e Fernet/envelope; seed usa marker + Box + jornada + tipo; Admin usa igualdade exata por helper/HMAC. `STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY=False` mantém plaintext. Ao habilitar, grava Fernet legado com a derivação histórica de `SECRET_KEY`; envelope G1 é etapa de rotação separada. Gate HMAC segue independente |
| `PublicWorkoutAccount.email` | `public_workout_account`, public/shared | `EmailField(unique=True, db_index=True)` permanece em claro; `public_workouts.0048` adiciona HMAC indexado não único | Login/OAuth/billing/seed usam helper reader-first e dual-write via `save()`; Admin de conta, assinatura e seis Admins relacionados pesquisam email exato pelo helper/HMAC, mantendo os demais campos textuais. Stripe/notificações recebem plaintext pelo ORM. Gate desligado. Unicidade HMAC e variantes casefold aguardam census/reconciliação; cifra ainda bloqueada |
| `PublicWorkoutCheckoutLead.email` | `public_workout_checkoutlead`, public/shared | `EmailField(db_index=True)` permanece em claro; índice composto `(email, paid_at)` e unicidade parcial plaintext `email WHERE paid_at IS NULL` preservados; `public_workouts.0049` adiciona `email_lookup_index` HMAC indexado | Checkout/criação, retomada e busca Admin exata usam `public_workouts.email_lookup`; dual-write via model save e backfill shared dry-run/apply CAS/verify. Gate desativado; Stripe continua lendo plaintext via ORM. Não está cifrado |
| `PublicWorkoutWaitlistEntry.email` | `public_workout_waitlistentry`, public/shared | `EmailField(db_index=True)` permanece em claro; unicidade parcial plaintext `(email, tier) WHERE status='waiting'` preservada; `public_workouts.0049` adiciona `email_lookup_index` HMAC indexado | Convite, adesão, webhook e busca Admin exata usam helper reader-first; webhook mantém update bulk após revalidar candidatos exatos. Dual-write e backfill shared; gate desativado. Notificações continuam via ORM; não está cifrado |
| `PendingSignup.email` | `signup_pendingsignup`, public/shared | `EncryptedEmailField(max_length=254, storage_max_length=2048)`; `signup.0003` adiciona `email_lookup_index` HMAC e remove o B-tree plaintext | Admin agora pesquisa endereço exato pelo helper HMAC/legacy e preserva texto parcial nos demais campos. Stripe/onboarding recebem plaintext pelo ORM. Sem unicidade intencional: tentativas repetidas são válidas. Gate de HMAC e writer de cifra desligados |
| `auth.User.email` (Django) | `auth_user`, public/shared | Campo herdado do modelo de autenticação Django, em claro | Admin de usuários/framework e fluxos de conta podem depender dele; não foi incluído na contagem de declarações `EmailField` do código do produto. Fronteira central de autenticação, fora das conversões por domínio listadas abaixo |
| `StudentIntake.phone` | `boxcore_studentintake`, tenant | Model declara `max_length=255`, `storage_max_length=2048`, sem índice redundante na cifra | Busca exata administrativa usa `phone_lookup_index` HMAC; substring sobre ciphertext não é suportado |
| `StudentIntake.email` | `boxcore_studentintake`, tenant | Model declara `max_length=255`, `storage_max_length=2048`, sem índice sobre ciphertext | Nenhum filtro de aplicação por email foi encontrado; busca administrativa por email não é anunciada até existir blind index com justificativa |
| `WhatsAppContact.phone` | `boxcore_whatsappcontact`, tenant | Model declara `max_length=255`, `storage_max_length=2048`; migration muda `varchar(255)` para `varchar(2048)` | `phone_lookup_index` HMAC separado; deduplicação também usa identificadores externos |
| `WhatsAppMessageLog.body` | `boxcore_whatsappmessagelog`, tenant | `EncryptedTextField`; coluna `text` sem limite declarado | Mensagens WhatsApp e exportação/log de entrega; sem limite de tamanho no tipo |

Os campos da tabela tenant continuam no estado legado `app_label='boxcore'` e
exigem migrations `boxcore` por schema. `StudentInvitationDelivery` é a exceção
shared deste inventário: seu modelo pertence ao app `student_identity` em
`SHARED_APPS`, e a alteração física usa migration própria aplicada uma vez em
`public`.

## Capacidade do envelope proposto

O formato G1 é `octobox:v1:<key_id>:<fernet-token>`. Fernet autentica o token;
o ID segue `[a-z0-9][a-z0-9_-]{0,31}`. Para 255 caracteres lógicos, assumindo
até quatro bytes UTF-8 por caractere, o token Fernet máximo calculado é 1.444
caracteres. Prefixo e ID máximo somam 44, total 1.488. Uma coluna de 2.048
caracteres comporta o formato e preserva `max_length=255` como limite lógico;
runtime atual do banco ainda pode usar `varchar(255)`. G2 agora declara a
capacidade física customizada e adiciona
`boxcore.0033_encrypted_char_storage_capacity`; a migration foi aplicada
somente no canário sintético `box_test`, em DB descartável, para validar tipo e
capacidade; nenhum tenant real foi alterado. `EncryptedTextField` não requer
expansão.

O cálculo é de tamanho, não de conteúdo. O writer atual pode já produzir tokens
que ultrapassam `varchar(255)` para alguns valores; a quantidade é desconhecida
até census por schema em homologação, sem plaintext em logs.

## Contratos de e-mail ainda fora da conversão

A varredura estática encontrou sete declarações `EmailField` nos modelos do
produto, além de `auth.User.email` herdado do Django. Isso descreve o código do
checkout, não o censo de registros. Os campos vivem em duas fronteiras distintas:
`Student.email` em schemas tenant e os demais listados como shared/public.

Não existe um único índice de e-mail que possa ser aplicado a todos os campos:
`StudentIdentity.email` já tem HMAC de domínio próprio e gate reader-first;
`PublicWorkoutAccount.email` exige unicidade global; checkout lead e waitlist têm
unicidades parciais com predicados diferentes; `Student.email` precisa manter
busca parcial no diretório além do lookup exato OAuth. O ciphertext aleatório não
preserva igualdade, ordenação nem `icontains`. HMAC determinístico atende apenas
igualdade normalizada e introduz correlação dentro do domínio; não atende busca
parcial. Cada domínio precisa de chave/contexto, normalização, dual-write,
revalidação do candidato em memória, census/duplicidade, constraint, leitores,
escritores, Admin e rollback próprios.

`StudentAppInvitation.invited_email` participava da limpeza de fixtures por
sufixo `@qa.seed`; migration `student_identity.0007` adiciona o ownership marker,
marca convites legados desse domínio reservado, e o seed grava/busca pelo marcador
em vez do email. `student_identity.0008` e o helper reader-first preservam busca
operacional exata com HMAC de domínio próprio; a busca parcial foi substituída por
email exato e os campos `student_name`/`box_root_slug` seguem busca de texto.
`student_identity.0009` converte o campo para `EncryptedEmailField`, mantém
`max_length=254` lógico e amplia o armazenamento a `varchar(2048)`. O reader
aceita plaintext legado e formatos cifrados. O writer gate fica desligado por
padrão; quando ativo, grava Fernet legado sob a derivação histórica da `SECRET_KEY`,
não o envelope G1. A ativação depende de migration, backfill/verificação HMAC e
release reader-capable em todos os processos. Desligar o gate interrompe novas
escritas cifradas, mas não permite rollback binário para um `EmailField` antigo
após existirem tokens; é necessário permanecer no reader compatível até existir
uma rotina reversa aprovada e validada. `PendingSignup.email` e os emails de
Public Workouts atravessam Stripe; preservar envio e reconciliação exige que o
ORM continue retornando plaintext autorizado e que os leitores de busca usem o
índice correto. A busca Admin agora é exata por HMAC/legacy em PublicWorkoutAccount,
checkout, waitlist e PendingSignup, preservando os outros campos textuais.

As próximas fatias locais são fechar os consumidores/escritores restantes de
Student e planejar `auth.User.email` como fronteira central independente. Não há
census, backfill, alteração de chave ou migration aplicada a dados reais nesta
rodada; habilitação e rotação shared continuam gates operacionais.

### Escritores observados no checkout (2026-10-24)

Busca estática por atribuições, argumentos ORM e caminhos de persistência
confirmou estes pontos de entrada relevantes; ela não prova ausência de
scripts/integrações externos nem de chamadas dinâmicas:

| Campo | Escritores/caminhos observados | Implicação para dual-write futuro |
|---|---|---|
| `Student.email` | `StudentForm`/fluxos de cadastro e `students.infrastructure.django_quick_flow`; `student_identity.staff_membership_actions._update_student_email_in_tenant()` usa `QuerySet.update(email=...)` dentro do schema correto | O update direto bypassa `Student.save()` e precisa migrar para serviço que grave valor e índice atomicamente; revisar também import/management commands antes de rollout |
| `StudentIdentity.email` | views de identidade, repository, OAuth/login e ação staff; `save(update_fields=['email', ...])` cobre a mudança observada | Dual-write atual está no model `save()`; manter `update_fields` e não introduzir bulk update sem helper explícito |
| `StudentAppInvitation.invited_email` | `onboarding.intake_invite_actions`, `student_identity.infrastructure.repositories` e `seed_onboarding_scenarios` criam/get-or-create convites | Seed usa plaintext e sufixo QA; se houver blind index, todos os writers devem entrar no helper e a limpeza precisa do marcador independente do email |
| `PublicWorkoutAccount.email` | `public_workouts.account_email_lookup` centraliza `get_or_create`; login por link/código, Google OAuth, billing e seed usam o helper; atualização de email observada usa `save()` com dual-write | A unicidade física atual é case-sensitive, mas o lookup normaliza com `casefold`, então variantes podem coexistir e os callers que resolvem uma conta escolhem a primeira ordenada. O backfill reporta grupos HMAC duplicados. Antes de criar unicidade HMAC ou cifrar, census/reconciliação são obrigatórios; todos os filtros Admin por conta agora usam email exato via helper, e o roster ordena em memória pelo valor ORM. Checkout/notificações/analytics mantêm leitura ORM autorizada; o projection `values('account__email')` não filtra nem ordena no SQL |
| `PublicWorkoutCheckoutLead.email` | `student_identity.public_workout_views` cria lead não pago pelo helper; billing transforma lead em conta por PK; Admin pesquisa igualdade exata | Lookup reader-first usa domínio HMAC independente, revalida email normalizado e mantém a constraint parcial plaintext como backstop de corrida. Stripe ainda lê pelo ORM; Admin não usa `icontains` |
| `PublicWorkoutWaitlistEntry.email` | view pública cria espera pelo helper; consulta de convite, webhook Stripe e Admin usam lookup helper; webhook atualiza PKs revalidados em bulk | Domínio e normalização são compartilhados pelos leitores; constraint parcial plaintext `waiting` permanece. Notificações ainda leem pelo ORM; ativação não cifra nem altera ACL |
| `PendingSignup.email` | `signup.views` cria a captura; `signup.services`/`integrations.stripe.router` enviam à Stripe e entregam onboarding; ativação copia para o usuário novo; Admin faz busca exata | Criação/save dual-write o índice HMAC quando a chave está configurada e respeita `update_fields`; nenhum filtro runtime por email foi encontrado. Repetições de signup não são deduplicadas nem únicas. O ORM descriptografa para Stripe/onboarding; writer reader-first fica desligado até backfill e leitores verificados |
| `auth.User.email` | provisionamento de Owner e `signup.services` criam usuário; `access.access_profile_actions` altera email do usuário e salva `email` junto a outros campos | Modelo/framework e identidade de login centrais; precisa de projeto próprio que cubra backend de autenticação, reset, admin e todas as caixas |

O próximo scan deve confirmar os formulários e todos os command/import paths,
inclusive `QuerySet.update`, `bulk_create` e `bulk_update`, por modelo-alvo. Os
itens desta tabela são evidências de callsites encontrados, não a autorização
para cifrar nem uma garantia de completude de escrita.

### Decisão de contrato para Student e autenticação central (2026-10-24)

`Student.email` continua plaintext: OAuth exige igualdade `email__iexact`, mas o
diretório e o Admin oferecem `icontains`. HMAC de igualdade não substitui essa
busca parcial, e este pacote não altera a experiência para busca exata nem cria
índice sem consumidor. O writer de membership usa `QuerySet.update()` no schema
tenant e deverá gravar valor e eventual índice na mesma operação se uma futura
decisão mudar o contrato. O model mantém o label histórico `boxcore`; qualquer
migration de Student é tenant-local em `boxcore/migrations/` e requer census por
schema. Nenhum writer/gate foi alterado agora.

`auth.User.email` é o User padrão do Django em `public.auth_user`, compartilhado
por staff e boxes e sem unicidade. Admin padrão conserva busca parcial; reset usa
igualdade case-insensitive e envia um link por conta ativa elegível. Signup,
provisionamento e edição de perfil escrevem o campo. `provision_box` usa lookup
case-sensitive por email e pode falhar com resultado ambíguo; essa dependência
precisa de contrato próprio antes de qualquer conversão. Campo, query framework,
Admin, reset e writers não foram alterados; não há migration ou índice HMAC
proposto nesta rodada. A cifragem depende de arquitetura central, censo de
duplicidades e cobertura de todas as caixas.

### Census agregado shared habilitado (2026-10-24)

`report_pii_encryption_formats --shared` agora inclui o recipient já cifrado e os
sete campos de e-mail shared/plaintext identificados: StudentIdentity,
StudentAppInvitation, PublicWorkoutAccount, PublicWorkoutCheckoutLead,
PublicWorkoutWaitlistEntry, PendingSignup e `auth.User`. O comando lê valores
brutos em transação read-only e emite apenas contagens de formato e comprimentos
agregados. `rotate_pii_encryption --shared` continua allowlisted somente para
`StudentInvitationDelivery.recipient`; nenhum novo campo foi habilitado para
rotação.

`tests/test_shared_pii_encryption.py` passou **2/2** com migrations reais em
PostgreSQL descartável. O teste materializou um canário em cada alvo, confirmou
a lista exata de campos, plaintext detectado e ausência de endereços na saída,
além do contrato existente de leitura/rotação do recipient. Isso valida o
comando e o esquema sintético, não mede public real nem cobre produção.

`PublicWorkoutAccount.email` agora tem preparação reader-first: HMAC com domínio
`public-workout-account-email`, migration aditiva `public_workouts.0048`, dual-write
em `save()`, gate independente e helper comum para igualdade/login/criação. O
comando `backfill_public_workout_account_email_lookup_index` oferece dry-run,
apply com CAS e verify; mede grupos de índices duplicados sem emitir endereços ou
HMACs. A coluna original e sua unicidade case-sensitive permanecem intactas; o
índice HMAC não é único até reconciliar variantes casefold. A busca parcial no
Admin continua dependente do plaintext, então esta etapa não cifra o campo.
`public_workouts.test_account_email_lookup_index` passou **6/6** e as regressões
`student_identity.test_public_workout_login` + `test_public_workout_oauth`
passaram **136/136** com migrations em PostgreSQL descartável; `manage.py check`
passou. A chave/gate estão desligados e nenhuma conta real foi lida ou alterada.

`PublicWorkoutCheckoutLead.email` e `PublicWorkoutWaitlistEntry.email` agora têm
preparação equivalente via `public_workouts.0049`: domínios HMAC separados, dual-write
que respeita `update_fields`, leitores/criadores reader-first e backfill combinado
CAS/verify por lote. Os dois Admins consultam email por igualdade exata usando os
mesmos helpers, em legacy e HMAC; busca parcial não retorna linhas. As flags
independentes seguem desligadas e as constraints parciais existentes continuam
sobre plaintext; webhook de conversão preserva bulk update depois de filtrar e
revalidar os endereços. A suíte focal commerce passou **8/8** em PostgreSQL
descartável com migrations reais. Nenhuma chave foi provisionada, nenhum dado shared
real foi lido/backfilled e a cifra segue dependente de census/reconciliação, Stripe,
notificações e rollout reader-first.

`PendingSignup.email` também foi preparado para o mesmo rollout, respeitando seu
contrato diferente: registros repetidos por endereço são tentativas comerciais
válidas, portanto não há constraint de unicidade nem reconciliação/dedupe. A
migration `signup.0003` adiciona HMAC indexado e amplia o campo a
`varchar(2048)` por `EncryptedEmailField`, removendo o B-tree anterior sobre
plaintext. O Admin consulta endereço completo via `pending_signups_for_email` e
mantém busca textual em nome, box, telefone, sessão Stripe e campanha. O helper
retorna todas as tentativas com endereço igual; Stripe e onboarding continuam
recebendo texto pelo ORM. O backfill `backfill_pending_signup_email_lookup_index`
faz dry-run, apply por lotes com CAS raw-value e verify agregado, sem exibir email.
O writer gate exige gate HMAC e chave; a allowlist de rotação shared também exige
leitor HMAC verificado. Census/read/rotation sintéticos foram estendidos; nenhum
dado real, secret, backfill, gate ou chamada Stripe foi usado.

## Keyring e compatibilidade aprovados em G1

- `PII_ENCRYPTION_KEYRING_JSON`: objeto JSON `key_id` → chave Fernet
  URL-safe-base64, incluindo chaves de dados e chaves históricas de leitura.
- `PII_ENCRYPTION_ACTIVE_KEY_ID`: chave de dados ativa do codec novo; deve
  permanecer vazio até o leitor G2 estar em todos os workers, jobs, scripts e
  comandos.
- `SharedSupportConfig.ready()` valida o JSON/keyring em todo startup Django;
  keyring vazio é aceito no rollout reader-first. Configuração malformada ou
  `ACTIVE_KEY_ID` ausente no mapa impede o boot com erro sanitizado, sem incluir
  chave, ciphertext ou ID configurado na mensagem.
- O codec injeta a chave derivada da `SECRET_KEY` com ID reservado
  `legacy-django-secret-v1`, reproduzindo exatamente os 32 bytes históricos.
  Tokens Fernet sem ID tentam esta chave e as chaves explicitamente retidas.
- Envelope malformado, versão desconhecida, chave desconhecida ou token
  inválido nunca é devolvido como plaintext. Escrita sem chave ativa falha.
- `PHONE_BLIND_INDEX_KEY` permanece estável e fora deste keyring.
- O leitor G2 está conectado aos `Encrypted*Field`; durante o rollout
  reader-first, os campos continuam escrevendo o formato Fernet legado.
- A migration `boxcore.0033` amplia somente a capacidade dos cinco campos
  curtos, sem reescrever dados; foi aplicada somente no canário sintético
  descartável `box_test`, não em tenant real.
- Em 23/10/2026, os testes puros de codec/campos/census passaram 33/33 com o
  fixture global de DB fora do escopo; `manage.py check` validou o startup com
  keyring reader-first vazio. Isso não cobre runtime-wide nem chave real.
- O loader rejeita IDs JSON duplicados em vez de aceitar silenciosamente o
  último valor. Dois casos sintéticos (valores distintos e iguais) passaram por
  validação direta sem fixture de banco. A suíte pytest completa do módulo foi
  bloqueada antes dos testes pelo fixture global, que consulta o DB compartilhado
  e encontra drift (`control_box.write_frozen_at` ausente); nenhum schema
  compartilhado foi migrado.

## Compatibilidade de leitura — auditoria estática de call sites

Materialização ORM de `obj.phone`, `obj.cpf`, `obj.email` de intake, `obj.body`
e `values()` que leia esses campos usa `from_db_value()` e o reader conectado
ao field. Isso decorre do contrato Django/código local; não prova que todos os
workers, jobs, scripts e commands executem a mesma release compatível com as
mesmas chaves. O rollout runtime-wide não foi feito.

Call-site audit encontrou filtros SQL por conteúdo diretamente nos valores
cifrados. Foram corrigidos localmente: `api/v1/views.py::StudentAutocompleteView`
agora usa nome parcial e telefone completo por `phone_lookup_index`;
`catalog/student_directory_queries.py::_apply_student_directory_filters` usa
nome/e-mail parciais e telefone completo por índice; não consulta CPF cifrado
nem coluna `whatsapp` ausente do model. Os hints das buscas foram ajustados. Os
formulários `catalog/form_definitions/student_forms.py` e `student_app/forms.py`
agora dependem do blind index para igualdade de telefone: chave ausente levanta
erro de configuração na validação duplicada, e a resolução de lead não faz
fallback SQL sobre ciphertext.

`StudentQuickForm.clean_cpf()` agora consulta `Student.cpf_lookup_index`, não o
ciphertext. `generate_cpf_blind_index()` aplica HMAC com domínio
`octobox:cpf:v1:` para que o índice de CPF não seja correlacionável com o
telefone que contenha os mesmos dígitos, reutilizando a raiz estável de
`PHONE_BLIND_INDEX_KEY`. `Student.save()` faz dual-write, inclusive quando
`update_fields` inclui CPF; `boxcore.0034_student_cpf_lookup_index` adiciona a
coluna e um índice parcial não único. Constraint unique foi adiada até medir e
resolver duplicatas legadas.

**G2 — ordenação padrão de contatos cifrados (24/10/2026):** a consulta curta
`get_unlinked_whatsapp_contacts()` já usava `(display_name, pk)`, mas o
`Meta.ordering` de `WhatsAppContact` ainda terminava em `phone`; o queryset
padrão, incluindo o admin, compilava `ORDER BY` sobre ciphertext Fernet
aleatório. O default agora é `(display_name, pk)`, sem migration. A suíte pura
`EncryptedAdminSearchTests` passou **6/6 + 4 subtests** e verifica o SQL do
ModelAdmin, que ordena pelo nome e PK sem incluir `phone`. Censo Django dos
cinco modelos instalados com campos `EncryptedCharField`/`EncryptedTextField`
confirmou que os outros `Meta.ordering` usam somente status, nome ou timestamps;
nenhum ciphertext aparece na ordenação padrão restante.

**G2 — auditoria de blind index com projeção mínima (24/10/2026):**
`audit_blind_index` recalcula o HMAC do telefone, então ainda precisa materializar
`phone`, mas agora seleciona somente `id`, `phone` e `phone_lookup_index` e usa
`iterator(chunk_size=500)`, evitando carregar CPF, e-mail, notas e outros campos
do objeto. Diagnósticos de drift/duplicidade não exibem o HMAC pseudônimo; IDs
e contagens continuam disponíveis para investigação operacional. A regressão
capturou SQL e saída do comando. `boxcore/tests/test_blind_index.py` passou
**11/11** em DB de teste PostgreSQL reutilizado; nenhuma migration ou dado real
foi alterado.

`backfill_student_cpf_lookup_index --schema box_<slug>` é read-only por padrão;
`--apply` atualiza somente índices vazios em lotes/row locks, e `--verify`
recalcula e compara sem escrever. Relata contagens agregadas, não plaintext,
índices HMAC ou CPF. `CPF_LOOKUP_INDEX_READY` inicia false e o formulário
recusa CPF não vazio até migration, backfill e verificação concluírem no
tenant. `CPF_LOOKUP_INDEX_READY_BOXES` libera schemas verificados um a um;
`CPF_LOOKUP_INDEX_READY=True` libera todos e só cabe depois que todos estiverem
prontos. Migration/backfill foram exercitados somente no PostgreSQL descartável
`box_test`; não há census ou backfill de CPF real.

Na revisão local de 23/10, `tests/test_student_cpf_lookup_index.py` passou **7/7** em PostgreSQL descartável com migrations reais. O caso adicional criou dois alunos sintéticos com o mesmo CPF: `--apply` preencheu os dois índices, reportou um grupo duplicado e `--verify` recusou o tenant. Isso prova a detecção do caso controlado, não mede duplicatas reais nem autoriza adicionar constraint unique ou habilitar o flag em produção.

`integrations/whatsapp/poll_processor.py` agora busca telefone somente por
`phone_lookup_index` exato, rejeita colisões em vez de escolher o primeiro aluno
e não consulta `Student.whatsapp` nem cifra em SQL. O endpoint agora exige HMAC
canonicalizada e resolução de Box por allowlist server-side; novas intents têm
inbox tenant-local cifrada, unicidade `(provider,event_id)` e retries tenant-aware
sob write fence. `WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON` permanece vazia e o emissor
Evolution ainda não implementa o contrato. Eventos legados da inbox `public` sem
identidade confiável são contados e ignorados, não migrados por inferência.
O diretório web mantém busca local parcial no
índice autorizado já materializado no navegador; isso é distinto de query SQL
sobre ciphertext e não oferece matching parcial de CPF.

`Student.email` permanece EmailField em claro e indexado; StudentIdentity
também mantém seu email de control plane em claro. A inspeção não encontrou
lookup de igualdade para `StudentIntake.email`, mas leitura/importação/formulários
precisam ser cobertos ao testar o envelope versionado. Foram inspecionados
call sites de import, auditoria de blind index, limpeza e processamento de
WhatsApp; commands/scripts não foram executados como prova de rollout. Os
testes focais de autocomplete/diretório/validação de chave passaram 6/6 (com
duas subcases), dois testes existentes de deduplicação/lead claim passaram 2/2,
e a suíte focal combinada de busca/autocomplete e CPF/codec passou 15/15
(duas subcases) em PostgreSQL descartável. `manage.py check` também passou.
Não é validação runtime-wide.

### StudentIdentity.email — preparação do blind index compartilhado (2026-10-24)

RAG apontou convenções históricas de blind index para telefone, dual-write via
`save()` e necessidade de plano de rotação; não encontrou contrato de email
atual. O código confirmou quatro buscas shared por `StudentIdentity.email`:
reidentificação OAuth no tenant resolver, associação de login público, busca
por Box no repository e validação de conflito no formulário de identidade. Elas
agora usam um helper comum com gate reader-first e queryset escopado por Box
quando a consulta conhece o tenant.
`student_identity.0006` adiciona a coluna HMAC indexada em `public`; a chave
`EMAIL_BLIND_INDEX_KEY` é separada da cifra e dos domínios de phone/CPF. O comando
`backfill_student_identity_email_lookup_index` oferece dry-run, apply com CAS,
verify e saída agregada, sem emitir emails. O campo email segue plain-text nesta
etapa, a flag de leitura segue false por padrão, e não há constraint de unicidade
no índice. `--verify` também reporta grupos candidatos de duplicidade para
identidades pending/active pelo `box_root_slug` legado e HMAC, sem emitir valores;
o relatório só declara cobertura completa após scan integral sem índice ausente
ou divergente. Testes focais em PostgreSQL descartável cobrem normalização/domínio,
dual-write, modo legado/indexado, colisão, formulário por Box e apply/verify
(**7/7**) e a regressão existente de alias/formulário por Box passou **1/1**
na mesma execução; nenhum dado real foi lido ou alterado. A chave precisa ser
provisionada e o backfill verificado em
ambiente autorizado antes de ativar o gate; só depois se pode planejar a cifra
do campo e a remoção da busca em claro. Busca estática de escritores encontrou
criações e updates de `StudentIdentity` via `save()`/`update_fields`; o único
`QuerySet.update()` observado no model atualiza `photo_url`, não `email`. Isso
não cobre código dinâmico, scripts externos ou chamadas de operador.

**Revisão do writer (24/10/2026):** `StudentIdentity.save()` agora trata
`update_fields` como intenção explícita de persistência: não grava o HMAC quando
`email` ficou fora da lista; quando o email está incluído, grava também o índice
se a chave ou o gate de leitura estiver configurado. O baseline usado para
detectar mudanças só avança quando `email` foi persistido. Testes reproduziram
os dois estados de drift antes da correção e passaram depois em PostgreSQL
descartável. O contrato evita índice de busca incompatível com o email salvo,
mas não substitui backfill, verify nem census do `public` real.

### Entry points e propagação de configuração — auditoria estática G2 (2026-10-23)

Busca no código por `cursor.execute`, `.raw()`, `RawSQL` e `connection.cursor()` não
encontrou outro leitor de valor PII cifrado fora do ORM além dos comandos
allowlisted `report_pii_encryption_formats` e `rotate_pii_encryption`, que
deliberadamente classificam/transformam o valor bruto. `migrate_existing_data_to_pilot`
faz cópia tabular bruta em fluxo operacional manual, sem interpretar conteúdo;
permanece pausado durante o drill F2 e precisa manter o mesmo conjunto de chaves
se for usado após a ativação de envelopes. As demais ocorrências inspecionadas
consultam metadados, locks ou integridade estrutural.

| Entry point/processo versionado | Inicialização/configuração observada | Alcance comprovado no código |
|---|---|---|
| Gunicorn WSGI | `config.wsgi` chama `get_wsgi_application()`; settings importam `shared_support.apps.SharedSupportConfig`; unit Hostgator aponta `EnvironmentFile=/srv/octobox/shared/octobox.env` e `.release.env` | A configuração do keyring é validada antes de servir requests. O código não prova o conteúdo do arquivo nem o SHA rodando no host |
| ASGI | `config.asgi` chama `get_asgi_application()` e passa pelo mesmo app registry/settings | Mesma validação se iniciado; não foi encontrado unit ASGI versionado nesta inspeção |
| Management commands | `manage.py` carrega env do projeto e encaminha ao Django; os timers/workers systemd versionados chamam `manage.py` pela venv da release e carregam `octobox.env` | `SharedSupportConfig.ready()` valida o keyring em cada processo/execução; unidades instaladas, estado e processo em voo no host não foram inspecionados |
| Scripts Python com `django.setup()` | Os call sites versionados usam as settings do projeto; `config.settings.base` carrega `.env` local antes de construir settings | Recebem a validação de startup quando inicializam Django; não foi encontrado serviço de produção separado para estes scripts |
| Celery/worker distribuído | Celery não consta nos requirements atuais; o shim de background observado é síncrono | Não há worker Celery atual a validar; qualquer introdução futura precisa propagar a mesma configuração antes de gravar envelopes novos |

Os manifests systemd de Hostgator (release atual documentada) e Hostinger legado
referenciam `octobox.env`; isso é evidência de configuração versionada, não de que
ambos — ou qualquer unit específica — estejam instalados/ativos. O bootstrap
Hostgator escreve `DJANGO_SECRET_KEY` e `PHONE_BLIND_INDEX_KEY`; as variáveis de
keyring continuam opcionais e vazias no rollout reader-first. A validade de uma
chave histórica real não é provada pela validação sintática do startup: precisa
de census e leitura controlada.

Antes da primeira escrita envelope, configure o keyring no env compartilhado e
faça rollout/restart de todos os processos que leem esses campos. Confirme em
cada processo a mesma release e os key IDs requeridos, incluindo timers, comandos
long-running e callbacks; só depois habilite o active key ID no escritor. Após a
primeira gravação versionada, uma release sem reader G2 deixa de ser rollback
compatível. O backup cifrado de `octobox.env` passa a ser parte da retenção das
chaves; teste restore desse arquivo junto com dumps antigos e novos antes de
remover qualquer key ID.

## Census e limites

Nenhuma contagem em tenant real foi executada: não houve acesso autorizado a
uma base de homologação/produção. O comando read-only e tenant-scoped foi preparado:
`.venv/Scripts/python.exe manage.py report_pii_encryption_formats --schema box_<slug>`.
Exige schema cadastrado e PostgreSQL; cobre os seis campos cifrados e o
`Student.email` em claro, emitindo somente contagens por formato e comprimentos
agregados, sem valores, IDs ou hashes. O classificador separa
vazio, plaintext legado, token legado válido, inválido, envelope válido,
formato malformado, versão desconhecida e key ID desconhecido. No DB descartável,
`boxcore.0033` foi aplicada ao tenant sintético `box_test`; o census classificou
os canários e sua saída foi conferida sem plaintext, IDs ou hashes. Census real,
contagens e comprimentos continuam pendentes e são gate antes da primeira
escrita nova. Nenhuma chave ativa ou writer versionado foi habilitado.
Não coletar plaintext, CPF/telefone, nem hashes ingênuos desses valores em
relatório ou log.

## Rotação G3 preparada

`shared_support/management/commands/rotate_pii_encryption.py` oferece dry-run
por padrão e exige schema cadastrado, modelo/campo allowlisted, PostgreSQL e
key ID ativo. `--apply` recriptografa texto legado e ciphertext autenticado
legível com o envelope ativo; tokens inválidos/ilegíveis são contados e
preservados. A gravação usa comparação do ciphertext bruto lido e reverte o
lote se houver edição concorrente. `--checkpoint` grava atomicamente apenas
schema/modelo/campo/modo/key ID ativo/última PK e permite retomar; a retomada
recusa mudar o key ID no meio do lote. `--verify` não grava.
Quatro testes em PostgreSQL descartável passaram, incluindo pausa entre
lotes e retomada em novo processo. Em Docker/PostgreSQL 15.19 isolado, dois
canários sintéticos foram rotacionados em duas etapas; dumps full e tenant com
manifests foram criados antes/depois e restaurados com o runbook em bancos novos
`octobox_restore_g3_before`/`octobox_restore_g3_after`. O par pré-rotação foi
legível com a SECRET_KEY de laboratório; o pós-rotação foi legível com o keyring
que contém o key ID novo. Os manifests/hash foram aceitos e o restore reportou
zero FKs não validadas. Não houve chave/tenant real, census/backfill de todos os
campos, morte forçada no meio de transação ou prova runtime-wide. O laboratório
usa chaves e dados sintéticos e não autoriza `--apply` em tenant real: primeiro
concluir census, rollout reader-first e operação de retenção do keyring real.

O workflow `.github/workflows/backup-integrity-check.yml` agora inclui o gate
PostgreSQL/Linux para codec, census, rotação e blind index junto ao fence F2.
As execuções anteriores passaram 64/64 em Windows e container Linux. A
reprodução local mais recente do step exato (oito caminhos, migrations reais)
passou **75 testes + 8 subtests em 40,28 s** com Python da `.venv` no Windows e
PostgreSQL 15 descartável em Docker; `tests/test_crypto_codec.py` inclui a nova
prova do hook de startup. Houve somente warning de permissão ao gravar
`.pytest_cache`. O runner do GitHub ainda não foi executado; chave ativa,
census/backfill real e validação runtime-wide continuam pendentes.

### Ensaio adicional de retenção e restore após troca de segredo (24/10/2026)

Em Docker/PostgreSQL 15.19 descartável, `octobox_g3_source` continha somente dois
tenants e quatro campos sintéticos (`Student.phone`/`Student.cpf`). Os scripts
reais geraram pares full/tenant e manifests antes e depois da rotação. O restore
pré-rotação foi criado pelo `restore_tenant_schema.sh` em banco isolado: 58
tabelas e zero FKs não validadas. Após trocar a `SECRET_KEY` de laboratório, o
snapshot antigo continuou legível porque o keyring de teste reteve explicitamente
a chave derivada antiga sob um ID histórico; ambos os tenants e os quatro campos
foram lidos.

Os quatro campos foram então rotacionados para o ID de dados sintético
`g3-data-2026`. Um segundo par full/tenant foi restaurado pelo mesmo script,
com o tenant A substituído pelo backup seletivo e o tenant B vindo do backup
full. A leitura ORM de A e B passou com a nova `SECRET_KEY` e um keyring que
continha somente a chave ativa nova; os quatro ciphertexts raw usavam o envelope
do ID novo. Isso comprova, nesse corpus, que o restore antigo depende da retenção
da chave antiga e que o restore pós-rotação não depende dela. A chave antiga foi
omitida apenas do ambiente efêmero de verificação; nenhuma chave real foi
removida.

Os gates de codec, rotação, census, PII compartilhada e índice CPF passaram
**52/52** em PostgreSQL com migrations reais. Todos os dados, dumps e chaves
sintéticos permaneceram no container descartável, removido ao final. O ensaio
não cobre chave/tenant real, census de todos os campos, retenção efetiva dos
backups no host, todos os leitores/processos do runtime ou execução no GitHub;
esses gates continuam obrigatórios antes do rollout.

## Backup e restauração

O runbook atual de backup cifrado de `octobox.env` protege a `DJANGO_SECRET_KEY`,
que hoje é também a chave de dados legada. Após ativar o keyring, os backups de
segredos precisam incluir todas as chaves necessárias aos dados e backups
retidos. A private key age permanece fora da VPS. G3 precisa restaurar backup
antigo e novo com o keyring correspondente antes de retirar qualquer chave.
Para executar backup manual usa-se `systemctl start octobox-env-backup.service`:
a unit carrega o arquivo completo por `EnvironmentFile`. O comando antigo do
runbook chamava o script diretamente sem carregar o ambiente e podia falhar por
ausência de recipient/remoto. O runbook agora manda capturar um backup assim que
o keyring muda e manter cada chave até expirarem todos os dumps dependentes,
considerando as retenções reais de DB e do arquivo de ambiente.
O fixture de age em `.github/workflows/backup-integrity-check.yml` agora inclui
keyring e active key ID sintéticos. Sua reprodução local em Ubuntu 24.04 passou
com archive sem plaintext e comparação byte a byte após descriptografia; o run
GitHub e qualquer restore dos segredos reais continuam pendentes.

## Writer CSV e blind indexes

Auditoria estática encontrou um bypass em `operations/services/student_importer.py`:
`bulk_create` e `bulk_update` não executam `Student.save()`, que é onde vive o
dual-write normal de `phone_lookup_index` e `cpf_lookup_index`. O caminho em
lote agora deriva os dois índices antes da escrita e os inclui nos campos de
atualização. A suíte focal `tests/test_student_cpf_lookup_index.py` passou 9/9
em PostgreSQL descartável com migrations reais; dois casos verificam criação e
atualização de CPF pelo importador CSV. Isso fecha a consistência desse writer
no código local, sem comprovar census/backfill dos dados reais nem habilitar
`CPF_LOOKUP_INDEX_READY` em qualquer tenant.

Complemento (2026-10-23): o importador CSV inicial `boxcore/management/commands/import_students_csv.py` usa `update_or_create`, portanto executa `Student.save()`. A suíte `boxcore/tests/test_import_students.py` foi ampliada para verificar os blind indexes de CPF ao criar e atualizar e passou 1/1 em PostgreSQL descartável com migrations reais. Com isso, os dois importadores CSV conhecidos têm cobertura focal; não houve census real nem ativação.

Validação integrada posterior (2026-10-23): o step PostgreSQL/Linux do workflow de backup foi reproduzido com os oito caminhos de teste e passou 71 testes + 8 subtests em 37,04 s, após as mudanças nos importadores CSV. Banco descartável e migrations reais; o resultado local não substitui execução no GitHub nem censo real/runtime-wide.

## Busca administrativa dos campos cifrados

Auditoria dos `search_fields` encontrou usos de `icontains` incompatíveis com
ciphertext Fernet aleatório: telefone de Student/Intake/WhatsAppContact e
relações de Enrollment/Payment/Attendance/log; `WhatsAppMessageLog.body` também
era pesquisado sem índice. Os admins agora mantêm busca textual somente em
campos plaintext e usam `BlindIndexPhoneSearchAdminMixin` para busca exata de
telefone pelo caminho de índice apropriado, inclusive por relações.
`StudentIntake.email` não tinha nenhum consumidor de igualdade além do
`search_fields` inválido. Foi removida a alegação de busca por email e o B-tree
no ciphertext; também foram removidos `db_index`/`unique` sem semântica dos
campos telefone cifrados. Unicidade efetiva segue nos blind indexes HMAC de
Student e WhatsAppContact; intake preserva duplicatas intencionais.

A migration tenant-local `boxcore.0038_remove_redundant_encrypted_search_indexes`
faz apenas a remoção dos índices/constraints sobre ciphertext. Cinco contratos
SQL puros e dois casos com dados reais passaram **7/7** em PostgreSQL 15
descartável com migrations: busca exata de Student/Intake retornou a linha
certa; email de intake não retornou falso match; Enrollment, Payment,
Attendance e logs compilam o predicado para o blind index relacionado. O
autodetector em banco descartável respondeu `No changes detected`. A suíte
combinada `tests/test_encrypted_admin_search.py` + `boxcore/tests/test_blind_index.py`
passou **18/18**, preservando as regressões de unicidade dos blind indexes.
Isso valida o código/migration local, não sua aplicação em tenants ou
compatibilidade runtime-wide.

## Inicialização reader-first — verificação do hook Django

`SharedSupportConfig.ready()` chama a validação do keyring, e `INSTALLED_APPS`
carrega esse AppConfig no registry compartilhado usado por `manage.py`, WSGI e
ASGI. O teste focal chama o hook com JSON malformado. O módulo completo
`tests/test_crypto_codec.py` passou **33/33** com
`--confcutdir=tests`, isolando-o do fixture tenant global. Como verificação do
fluxo real de startup, `manage.py check` com keyring Fernet sintético válido
passou sem issues; com `PII_ENCRYPTION_KEYRING_JSON` malformado encerrou com
código 1 e `ImproperlyConfigured` originado em `ready()`. O boot inválido foi
recusado antes das verificações do banco. A execução pytest com configuração
normal não é evidência: o fixture global requer migrations shared e falhou
contra o DB default com `control_box.write_frozen_at` ausente; em PostgreSQL
descartável, `--nomigrations` também não cria as tabelas shared que ele espera.
Nenhum processo instalado no host ou keyring real foi inspecionado; prova
runtime-wide permanece pendente.

## Falhas de importação e dados operacionais — auditoria G2 (2026-10-24)

A trilha Student CSV foi rastreada de `StudentImporter` até o worker de thread,
o polling Redis e a tarefa `operations.tasks`/`AsyncJob`. Antes da correção, o
importador registrava caminho e texto da exceção com traceback; o worker copiava
`str(exc)` para logs e `error_message`; a tarefa copiava o texto para logs,
resultado e `AsyncJob.error`. A view também persistia o nome fornecido pelo
usuário em `job.metadata.filename`.

Agora os caminhos mantêm `job_execution_failed`/códigos de classe para
diagnóstico e retry, com mensagem fixa no cache, sem texto livre de exceção ou
traceback; a tarefa emite `SanitizedImportJobError` para o backend de retry e
armazena somente o código em `AsyncJob.error/result`. Logs identificam job,
correlation ID e tipo de exceção, sem mensagem, caminho ou traceback. O nome do
arquivo não é copiado à metadata/polling. Os relatórios por linha já usam reason
message fixa e continuam sem nome/telefone/CPF.

As regressões inserem marcadores sintéticos em erro e filename e verificam sua
ausência em log, cache e erro persistido. `test_operations_tasks.py` passou
**4/4** com fixture global isolado; o teste do worker passou **1/1** em DB
PostgreSQL reutilizado, e o teste do log do importador passou **1/1** no mesmo
DB. A primeira execução de `test_operations_tasks.py` com fixture global tentou
consultar o banco default incompatível (`control_box.write_frozen_at` ausente);
`--confcutdir=tests` permitiu validar corretamente os testes puros. A
configuração real do broker/backend Celery e retenção de logs do host não foram
inspecionadas; Celery não está instalado no ambiente local deste checkout.

## Erros de ações em lote e idempotência — auditoria G2 (2026-10-24)

`shared_support.bulk_executor.execute_bulk_action()` registrava `str(item)` e
`str(exc)` com traceback. Seu callsite atual é a ação em lote de alunos; o
modelo Student representa o item pelo nome completo, e exceptions de validação
podem conter valores da entrada. O executor agora registra somente o tipo da
exceção e retorna uma mensagem fixa para consumo pela view, que continua
identificando o aluno separadamente para o usuário autorizado.

`shared_support.decorators.idempotent_action()` também registrava o texto livre
da exceção. O log agora usa evento e classe da exceção, e o retry relança com
`raise` sem alterar o objeto original. Dois testes unitários com marcadores
sintéticos confirmam ausência do texto em log/resultado e preservação do
tratamento de falha; `tests/test_bulk_executor_pii.py` passou **2/2** com
`--confcutdir=tests`. `git diff --check` passou. A regressão de interface da
ação em lote e a validação dos endpoints idempotentes reais não foram repetidas
nesta etapa; nenhuma migration ou dado real foi alterado.

O mesmo padrão apareceu no catch-all de `run_in_background()` e nas falhas de
email/push/WhatsApp de `notify_payment_confirmed()`: `logger.exception()` podia
anexar resposta/recipient presente na mensagem de um provedor. Esses logs agora
retêm somente evento, canal e classe da exceção, preservando os status de
retorno (`error`) e o comportamento de não propagar falhas de canal. Testes
confirmam ausência do marcador e resultado equivalente: `test_background_jobs_schema.py`
focal **1/1** com PostgreSQL reutilizado; `test_finance_notification_diagnostics.py`
incluído na execução focal **4 testes**; ações bulk/idempotência **2/2**.
`git diff --check` passou. Não foram repetidas integrações externas de email,
push ou thread com tenant real; sem migration e sem envio real.

## Falha do login de treinos não registra o destinatário — G2 (2026-10-24)

`student_identity.public_workout_login.request_login_token()` registrava o
endereço normalizado em texto aberto ao falhar o envio do magic link. O token
continuava válido e a falha era absorvida. O evento agora registra apenas a
classe da exceção; a criação/validade do token e o contrato sem oráculo de
existência do e-mail permanecem iguais. Regressão com destinatário sintético
passou **1/1** em PostgreSQL reutilizado com migrations reais. Não houve envio
real; sem migration.

## Notificações do corredor de treinos usam códigos seguros de falha — G2 (2026-10-24)

`public_workouts.notifications` tinha catch blocks de email com traceback e,
para publicação de programa/plano alimentar, persistia `str(exc)` em campos
`last_error`. O provedor pode incluir recipient, conteúdo enviado ou resposta
com dados pessoais. As notificações agora registram evento/tipo sem traceback;
os dois campos persistem somente `email_delivery_failed`. Retornos, contagem de
tentativas e política de retry mantidos. Regressão de publicação de programa
passou **1/1** em PostgreSQL reutilizado com migrations reais, verificando o
código persistido e o log. Nenhum provedor real chamado; sem migration.

## OAuth de aluno não persiste nem registra token de convite — G2 (2026-10-24)

`StudentOAuthStartView` copiava `invite_token`, que funciona como capability,
para `AuditEvent.metadata` e incluía o valor no log de falha de auditoria. O
evento agora guarda somente `invite_present` (boolean) e o erro registra
provider/classe, sem traceback ou token. A URL/state/cookie continuam levando o
token necessário para OAuth. Testes de sucesso e falha passaram **2/2** em
PostgreSQL reutilizado com migrations reais; o teste confirma que o token não
está no metadata e não aparece no log. Sem migration ou tráfego de provedor.

## Texto do SmartPlan e Stripe não entra em log bruto — G2 (2026-10-24)

Dois logs de warning interpolavam exceções: conversão do JSON SmartPlan colado
(texto editável do coach) e consulta de Checkout Session. Ambos agora registram
somente a classe da exceção; o parser mantém sua mensagem genérica de erro e a
consulta Stripe continua retornando `None`. Regressões sintéticas passaram
**1/1** no parser e **1/1** no teste de falha Stripe com `--confcutdir=tests`;
sem chamada Stripe real e sem migration.

## Erros de gateways, webhooks e reembolsos não persistem texto externo — G2 (2026-10-24)

Resend e SMTP podiam propagar corpo de resposta/erro do provedor, incluindo
destinatário e conteúdo. Os gateways agora retornam erros fixos; Resend mantém
apenas o status HTTP. A falha de convite é armazenada como `email_delivery_failed`
no registro/audit, sem texto livre. O outbox Curva armazena apenas
`delivery_failed:<ExceptionType>`. Falhas dos dois routers Stripe persistem
`webhook_handler_failed:<ExceptionType>` e não emitem traceback ou detalhe do
evento. Reembolsos persistem `refund_failed:<ExceptionType>`, registram tipo sem
traceback e expõem ao Admin somente `stripe_refund_failed`.

Regressões: gateways **3/3**; conjunto PostgreSQL de outbox/reembolso/jornada
Curva/reprocessamento Stripe/notificações passou **49/49**; OAuth/convite
focal **3/3**; gateways são testes puros. Integrações externas não foram
chamadas. Sem migration. A
configuração efetiva de provedores e retenção em produção não foi inspecionada.

## Falhas de provedores AI e Stripe sem payload sensível em log — G2 (2026-10-24)

RAG retornou planos antigos sem contrato atual para esses logs. No código, os
prompts incluem métricas de saúde, anamnese, revisão semanal, texto colado pelo
coach e nomes de movimentos; respostas/erros de APIs também podem conter
conteúdo do request. Logs de erro em AI de avaliação, geração de programa,
revisão semanal, Smart Paste e resolução de slugs agora registram evento,
provedor quando aplicável e classe de erro, sem texto livre. O log de payload
inválido registra apenas contagem de problemas. Checkout Stripe e falhas de
onboarding de proprietário também não registram traceback ou exceção bruta.

Cinco regressões sintéticas de provider/prompt passaram **5/5**; as suítes
existentes de AI pública e resolução WOD passaram **45/45**. Sem chamada a
provedor real ou migration. Logs históricos/retention do host não foram
inspecionados.

## Falhas operacionais restantes sem texto bruto — G2 (2026-10-24)

Revisão dos call sites encontrou mais caminhos em que `logger.exception` ou
`str(exc)` podia expor conteúdo externo/PII em traceback ou estado persistido:
falha de step de provisioning (`BoxProvisioningEvent.detail`), actions da
central de convites, geração de link Stripe, congelamento financeiro, reset de
senha, alertas/workers de descanso, resolução de membership, operações de
membership/auditoria de plataforma, auditoria de billing, tenant write fence,
migração de dados, tenant sweep, onboarding, escrita de progresso e cache de
undo diário. O evento de provisioning agora persiste
`step_failed:<ExceptionType>`; os logs dessas bordas guardam evento/tipo sem
traceback, IDs de usuário/pagamento/aluno, destinatário, URL de push ou mensagem
do provedor. Retry e respostas públicas mantêm seus contratos.

RAG retornou um plano amplo de hardening e documentos WOD sem relação direta com
esses writers; a evidência decisiva foi o código e o teste de provisioning. O
teste existente foi ajustado para exigir reason code sanitizado. `test_control_services`
passou **30/30**, falha de entrega do reset **1/1**, alertas Curva **25/25**,
`py_compile` e `git diff --check` passaram. A execução agregada incluiu falhas
adjacentes de RBAC/reset presencial e erros de setup tenant (`boxcore_student`
ausente no `--keepdb`); o reset de email focal passou isolado. Não há migration
ou chamada externa. Scan atual dos `.py` de produção não encontrou
`logger.exception`; a anamnese de treino, avaliação e carga foram atualizadas
com mensagens fixas. Mensagens de domínio adicionais em APIs de sessão, OAuth e
checkout ainda exigem revisão de contrato e verificação de que não incluem
valores dinâmicos.
Retenção/configuração de logs do host, broker e serviços externos não foram
inspecionados; esses gates permanecem antes de fechar G2.

## Respostas de validação não ecoam dados enviados — G2 (2026-10-24)

A inspeção da anamnese pública mostrou que `TrainingIntakeValidationError`
incluía valores inválidos de objetivo, experiência, local, dias e tags de
restrição; a view os re-renderizava na página. As mensagens agora são fixas e
orientam a correção sem repetir o POST. O mesmo padrão existia em erros de
avaliação/carga: peso, altura, sexo, repetições, RIR, papel de série e parsers
numéricos eram interpolados e devolvidos por endpoints autenticados. Esses
erros agora mantêm limites e orientação sem os valores enviados.

Regressões com marcador de email passaram: treinamento/anamnese e endpoints de
carga/avaliação **68/68** em `manage.py test --keepdb`; nenhum dado é escrito no
caso inválido. Sem migration ou chamada externa. Erros que são códigos de
domínio fixos (ex.: conflito/not-found) permanecem estáveis para os clientes.

## Transporte para logs externos, access logs e Sentry — G2 (2026-10-24)

RAG localizou `ADR-001-invite-token-cookie.md`, que já evitava query string de
convite, mas não cobria capabilities em segmentos de path. O código confirma
token em `/onboarding/<token>/` e `/login/senha/redefinir/<uidb64>/<token>/`,
além de state/code OAuth e IDs de checkout. Gunicorn usava a request-line padrão
em stdout e Nginx mantinha access logs nos virtual hosts. Units/templates e o
bootstrap agora fazem Nginx `access_log off`; Gunicorn mantém método/status/
duração/tamanho sem URI, query, referrer, IP ou user-agent. `%` está duplicado
nas units (`%%`) para chegar literalmente ao formatter após o parsing do
systemd.

Também foi verificado o SDK realmente instalado (`sentry-sdk 2.12.0`):
`send_default_pii=False` não bastava para remover corpo de request, exceções e
locals. A configuração agora desativa request bodies e locals, usa nomes de
view no lugar de URL e callbacks `before_send`/`before_send_transaction` removem
request, identidade, mensagens livres, breadcrumbs, valores de exceção e dados
de spans; classe/arquivo/linha, operação e tempos permanecem. Os testes puros de
Sentry/access-log passaram **4/4**.

O projeto não inclui Celery (`celery` não instalado nem em `requirements*.txt`);
background local usa thread/Redis e os workers de produção são systemd. O
checkout não prova o journal efetivo, sua retenção, proxy config instalada,
scrubbing server-side do projeto Sentry nem configuração dos secrets/provedores.
Nada foi enviado a Sentry, Redis remoto, SMTP, Stripe ou push; nenhum host foi
operado. Esses gates externos continuam pendentes.

## Erros Stripe e importação sem texto bruto — G2 (2026-10-24)

Revisão das fronteiras de erro encontrou outro caminho: `integrations/stripe/services.py`
copiava a mensagem do SDK para a descrição de `AuditEvent` e para a exceção
propagada ao caller. Checkout e reembolso agora registram somente a classe da
exceção e levantam `stripe_checkout_failed` / `stripe_refund_failed`; nenhum
detalhe do provedor é persistido nem devolvido por essa camada. Os relatórios
de erro de importação já normalizavam suas mensagens por `reason_code`, mas
montavam antes strings transitórias com exceção e caminho do arquivo; esses
valores foram removidos também da construção intermediária.

`tests.test_integrations_stripe_services` e
`tests.test_stripe_refund_initiation.RefundPaymentServiceTests` passaram **8/8**.
Uma tentativa agregada com testes tenant não concluiu: o DB `--keepdb` reutilizado
não possui `boxcore_student`, e dois labels informados (`tests.test_operations_*`)
não existem; não atribuo essa rodada às mudanças. Nenhum evento Stripe, importação
real ou migration foi executado.

Uma segunda leitura do middleware transversal achou dois caminhos que não eram
cobertos pelo scan de `logger.exception`: eventos de rate limit gravavam
`request.path` em AuditEvent/log e o honeypot gravava o path bruto; o evento de
rate limit também usava `SECURITY_LOGGER.exception`. Agora o path é substituído
por template/nome resolvido, o honeypot guarda somente o padrão malicioso
reconhecido, e a falha de auditoria registra classe sem traceback. O sweep
retorna `tenant_writes_frozen` em vez do texto da exceção. A varredura também
achou ID externo/fingerprint do webhook em log de deduplicação; o log agora
mantém apenas indicadores de presença. Testes de middleware, rate-limit com
marcador de capability, gateway e reembolso passaram **16/16**; `py_compile` e
`git diff --check` passaram.

## Fronteiras de erro, exportação e realtime — G2 (2026-10-24)

Uma busca independente encontrou superfícies residuais: `api/v1/bulk_views.py` devolvia texto arbitrário de exceção; `reporting/tasks.py` persistia a exceção em `AsyncJob.error`, registrava traceback e a propagava ao worker; os receivers Stripe registravam IP/mensagem e refletiam o erro; SSE e a memória de aliases WOD registravam exceção e, no stream do aluno, ID local. O snapshot do Red Beacon também incluía traceback em falha de cache.

Bulk agora retorna mensagem genérica. Exportações registram apenas a classe, persistem `export_failed` e propagam códigos fixos. Webhooks mantêm HTTP 400 com `invalid_webhook_request` sem IP. Barramentos SSE, alias WOD e fallback do Red Beacon registram evento/tipo sem payload, ID ou traceback. O teste sentinela `tests/test_g2_safe_error_surfaces.py` passou **6/6** sem banco; `manage.py check` e `py_compile` passaram. Stripe, Redis, Sentry, Celery e hosts não foram acionados; nenhuma migration foi criada.

A revisão estática não comprova conteúdo já retido em backends ou configuração e retenção nos hosts, nem é certificação runtime-wide. Esses gates permanecem antes da ativação de chave real.

### Follow-up de identificadores financeiros em logs — G2 (2026-10-24)

A revisão de fluxos financeiros encontrou payment/event IDs e valores monetários em logs de reconciliação; invoice, price, event e subscription IDs em diagnósticos do checkout público; e username/razão/ator em logs de operações de conta. Esses detalhes foram removidos dos logs de `finance/application/use_cases.py`, `public_workouts/stripe_handlers.py` e `control/services.py`, preservando reason codes e ações/auditoria. No router geral Stripe, esta rodada cobriu o adiamento por freeze, sessão sem metadata e espera de confirmação; outras mensagens estruturadas ainda requerem varredura focada.

A consulta RAG retornou cinco resultados antigos sem contrato atual para esse conjunto; código atual e testes foram a autoridade. As regressões de roteamento do webhook público, serviços de Box e outbox/reconciliação passaram **62/62** com banco de teste reutilizado; sentinelas sem DB passaram **6/6**. `manage.py check` e `py_compile` passaram. Nenhuma chamada externa ou migration ocorreu.

### Minimização no router Stripe e identificação da rodada — G2 (2026-10-24)

O follow-up removeu do log do router central Stripe referências a payment/event, customer/subscription, PI, invoice, tenant slug/schema e status/valor externo; mantém códigos de evento/erro e as referências necessárias na trilha de auditoria estruturada. Também foram removidos os últimos logs com username em `control.services` e `signup.services`. RAG havia retornado referências históricas sem contrato atual; o código e os testes foram usados como autoridade.

A rodada pós-alteração executou 130 testes das suítes Stripe, reconciliação, checkout público, serviços de Box/signup e outbox. **129 passaram; 1 teve erro de fixture**: `ActivatePendingSignupTest.test_adds_user_to_owner_group_when_it_exists` tentou criar `Owner`, já presente no DB de teste `--keepdb`. O erro ocorre no setup da fixture por violação de unicidade, sem falha de asserção; não foi limpo nem recriado o banco. Sentinelas sem DB passaram **6/6**, `py_compile` e `manage.py check` passaram. O aviso de permissão `.pytest_cache` continua inofensivo. O resultado integrado não é 130/130 verde.

### Fixture signup idempotente e revalidação da rodada — G2 (2026-10-24)

O teste `ActivatePendingSignupTest.test_adds_user_to_owner_group_when_it_exists` agora usa `Group.get_or_create('Owner')`, mantendo o objetivo do cenário sem presumir que o banco `--keepdb` está vazio. A reexecução das seis suítes (webhook Stripe, reconciliação, checkout público, serviços Box/signup e outbox) passou **130/130** em 7,32 s. `manage.py check` passou. O banco reutilizado não foi resetado.

### Follow-up de telemetria e segurança operacional — G2 (2026-10-24)

A varredura adicional minimizou logs de middleware de tenant, write fence, fingerprint e honeypot, além de eventos de telemetria WOD, checkout, outbox financeiro, aquisição/reembolso públicos e identidade WhatsApp. IDs de usuário, sessão, workout, template, evento, entrega, request e blind index, IP e caminho concreto não seguem para logs de processo. O IP continua somente no metadata estruturado do `AuditEvent` restrito, necessário para investigação; a mensagem de falha do audit não o reproduz.

`tests/test_g2_safe_error_surfaces.py` passou **11/11**. A bateria de segurança/rate limit, tenant boundary/write fence, refund, aquisição, payment outbox e webhook Evolution passou **115 testes (6 skipped)** com `--keepdb`. Duas assertions foram atualizadas para refletir contratos já vigentes (texto de erro do sweep redigido; poll-vote roteia o tenant antes de qualquer consulta de idempotência compartilhada). `manage.py check`, `py_compile` focal e `git diff --check` passaram. O RAG retornou documentação histórica sem contrato decisivo; prevaleceram o código e os testes atuais. Nenhum segredo real, migration, provedor, serviço externo ou host de produção foi acionado. Permanecem pendentes a validação de retenção/configuração no runtime, journal, broker, audit store e demais hosts, além da revisão do tenant/schema correlation no conjunto de logs.

### Correlação pseudônima de Box em logs — G2 (2026-10-24)

A varredura AST seguinte encontrou ainda `user_id`/`path` em `RoleRequiredMixin`, `active_box_id` e ID de usuário no middleware de tenant, além de schema em logs estruturados do sweep e do comando de retenção WhatsApp. Os callsites de acesso agora registram evento/papel sem identidade ou caminho concreto; tenant lifecycle, write fence, sweep, auditoria assíncrona e retenção WhatsApp usam `tenant_log_ref()`, HMAC-SHA256 domain-separated sobre PK de Box quando disponível (schema apenas como fallback), chaveado por Django `SECRET_KEY`. A saída de dry-run/aplicação do comando de retenção também usa a referência pseudônima; o erro não ecoa o schema informado. A rotação de `SECRET_KEY` rotaciona os refs e portanto encerra a correlação longitudinal, comportamento deliberado documentado para operadores.

Testes de log redigido no provisionamento, sweep, permissões, retenção e estabilidade/ocultação da referência passaram no conjunto combinado **72/72** com `--keepdb`. `manage.py check`, compilação focal e diff whitespace passaram. O scanner AST atual não encontrou chamadas logger que interpolam IDs de pessoa, paths concretos ou nomes/schema de tenant; ocorrência de “fingerprint”/“client_ip” remanescente corresponde a nomes de eventos/categorias sem valores. A busca RAG trouxe documentação histórica sem contrato; código e testes prevaleceram. Referências em AuditEvent estruturado e saídas autorizadas dos comandos de gestão não foram convertidas indiscriminadamente. Logs antigos retidos, configuração de coleta, acesso ao audit store, chave instalada e retenção no host ainda não foram inspecionados.

### Controle de leitura e retenção da trilha — G2 (2026-10-24)

A leitura de `AuditEvent` pelo Django Admin já era limitada ao gate global: usuário autenticado, ativo, `is_staff` e papel Owner/Dev (ou superuser); add/change já eram negados. A inspeção encontrou que `has_delete_permission()` ainda herdava a regra permissiva do ModelAdmin. O Admin agora nega delete também, mantendo a trilha append-only pelo caminho administrativo. Não encontrei política/procedimento de retenção para `AuditEvent` no código atual. Como o domínio não define prazo nem descarte legal, não foi criado expurgo nem migration. Próximo gate é o responsável de produto/compliance fixar retenção/acesso operacional; a verificação física de role no banco, logs antigos, audit store, broker/journal e host continua externa.

`tests.test_g2_safe_error_surfaces` passou **14/14**; o conjunto com `test_control_services`, `B13TenantSweepTest` e `test_tenant_write_fence` passou **73/73** em DB `--keepdb`, cobrindo negação de delete, sanitização de acesso/tenant e output do comando de retenção. Nenhuma linha de auditoria foi apagada nem migration/serviço externo executado.

A checagem de auditoria local identificou outro limite: `PIIScrubber` saneia apenas metadata JSON com chaves de um denylist pequeno; `AuditEvent.description`, `target_label`, `actor` e identificadores de alvo são persistidos deliberadamente para trilha e algumas rotas seguem o ADR-002 de hash de token/IP. `AuditEventAdmin` limita a leitura, mas ainda expõe descrição/label para investigação a Owner/Dev staff e superuser. O Django Admin agora não pode excluir eventos. Não foi ampliada a sanitização de descrições nem removida a busca por conteúdo sem inventário por ação/caller, porque isso pode apagar evidência de operações e a política de retenção/descarte não está definida. Esta é uma lacuna real de governança e precisa de matriz de campos por ação, consulta de eventuais obrigações de auditoria e política formal de acesso/retention antes de expurgar ou alterar semântica.

### Minimização dos eventos de auditoria — G2 (2026-10-24)

A matriz sintética de callsites de `log_audit_event()` encontrou duplicações evitáveis: username do alvo no reset de senha; nome completo em descrição e `subject_label` nos contatos por WhatsApp; nome do aluno em metadata de ação RM; destinatário do convite; e `str(target)` arbitrário, que pode ser nome/e-mail/telefone dependendo de `__str__`. O writer agora usa o `verbose_name` do model como `target_label`; metadata do AuditEvent redige email/recipient/username/nome/IP/endereço/dados corporais/notas por chave, preservando somente `token_hash` e `ip_hash` hexadecimais (ADR-002); descrições conhecidas deixaram de interpolar nome/username e note/nome duplicados saíram da metadata RM. A destinatária continua no registro próprio de entrega porque é necessária ao envio; IDs de alvo permanecem como localizadores estruturais do audit.

`tests.test_g2_safe_error_surfaces` + `tests.test_auditing_services` passaram **40/40** com `--keepdb`, incluindo sentinel de target sem chamar `__str__` e preservação do hash explícito. O conjunto anterior após estas mudanças passou **74/74** focal e a bateria tenant/security/refund/acquisition/outbox/webhook **115 testes (6 skipped)**. Nenhuma migration, alteração em registro real ou chamada externa ocorreu. A cobertura é de metadata por chave e callsites inspecionados; descrições dinâmicas de outros callers, PlatformAuditEvent escrito diretamente fora do helper e dados antigos exigem inventário adicional.

### Webhook de entrega sem persistir payload bruto — G2 (2026-10-24)

A varredura do registro de delivery encontrou `StudentInvitationDeliveryEvent.payload=body`, retendo a estrutura bruta do Resend que contém recipient/email e metadados redundantes. O evento já possui colunas normalizadas para provider, event ID, tipo e timestamp; `payload` agora é `{}`. O AuditEvent de processamento não duplica provider event/message IDs. O email permanece somente no registro de delivery necessário para envio/reconciliação. O teste Django padrão em `--keepdb` não chegou à assertion porque o banco reutilizado não tem `boxcore_student`; a mesma regressão passou **1/1** em PostgreSQL descartável com migrations reais via pytest (`--create-db --migrations`). Sem migration/chamada Resend.

Correção desta rodada: os dois wrappers diretos de `PlatformAuditEvent` (`control.services` e router Stripe) agora usam `log_platform_audit_event`, de modo que metadata passa por `PIIScrubber`; falha best-effort registra kind e tipo da exceção, sem texto. Writers diretos remanescentes são apenas o helper central. A suíte combinada auditoria/sentinelas/control/Stripe passou **95/95** antes desta última mudança de payload; o teste focal tenant passou depois. `manage.py check`, `py_compile` e `git diff --check` passaram. Retenção da tabela de delivery, logs e dados históricos continuam sem política/inspeção no ambiente instalado.

### Minimização de callsites de identidade e onboarding — G2 (2026-10-24)

A revisão das escritas diretas de `AuditEvent` reduziu novos dados redundantes em callbacks OAuth/landing, onboarding, convites, membership, push e pedidos de congelamento. Callbacks guardam hash de IP e nome de rota; landing não guarda path/token bruto nem texto da exceção de provedor. `record_student_onboarding_event()` sanitiza metadata, substitui `box_root_slug` por HMAC de tenant e usa rótulo de classe; writers de membership/convite omitem nomes, e-mails e justificativas livres. O alerta de anomalia usa referência HMAC do alvo e metadata sanitizada. URL bearer não é duplicada no handoff WhatsApp. O recipient permanece em `StudentInvitationDelivery` como dado funcional de entrega, sujeito à retenção desse modelo; registros antigos, storage/runtime e política formal não foram inspecionados. `git diff --check` focal passou; testes não foram executados nesta rodada, sem migration ou chamada externa.

### Resposta Resend e recipient persistido — follow-up G1/G2 (2026-10-24)

O gateway Resend extraía `id` normalizado, mas também copiava a resposta inteira para `StudentInvitationDelivery.metadata`. Agora persiste metadata vazia para esse gateway; o ID necessário ao webhook permanece na coluna dedicada, e novas respostas brutas não são guardadas. `StudentInvitationDelivery.recipient` foi confirmado como PII shared/public. Não há lookup da aplicação; a busca por recipient saiu do Admin para não consultar ciphertext, enquanto exibição ORM permanece legível aos papéis autorizados. Migration `student_identity.0005` declara `EncryptedCharField` e amplia a capacidade para 2048. O comando de census aceita `--shared`; a rotação aceita `--shared --model StudentInvitationDelivery --field recipient`, com dry-run padrão, verify/apply, lotes, checkpoint e compare-and-swap. A rotação shared grava apenas em `public` e não usa o tenant fence; é escopada explicitamente e usa transações por lote. `MigrationLoader`/`MigrationAutodetector` não encontraram drift para `student_identity` nem `shared_support`; `makemigrations --check --dry-run` não conseguiu verificar porque o histórico do banco local está inconsistente (`public_workouts.0040` antes da dependência `0039`). Nenhum census, migration aplicada ou rotação foi executado em DB real. Census/rotação reais seguem pendentes antes da chave versionada ativa. Entregas antigas podem conter metadata de resposta; nenhuma foi lida ou alterada. Política de retenção de delivery não foi encontrada.

### Validação do recipient cifrado em shared/public — G1/G2 (2026-10-24)

O teste de integração executou `student_identity.0005` em PostgreSQL descartável, confirmou `varchar(2048)`, gravou uma linha plaintext sintética, verificou que o census `--shared` só retorna contagens/formatos, e aplicou rotação CAS até envelope da chave de teste com leitura ORM do recipient. Também confirma que `StudentInvitationDeliveryAdmin` não busca recipient cifrado. O teste de gateway Resend garante metadata vazio com resposta sintética contendo recipient/conteúdo; o ID normalizado permanece preservado. As duas suítes passaram **6/6**. `manage.py check`, help dos dois comandos e MigrationLoader/Autodetector passaram; `makemigrations --check --dry-run` não avançou por inconsistência preexistente do banco local, preservado sem reset. Nada foi aplicado a dados reais. Seguem pendentes census/rotação de produção, retenção formal e inventário dos demais campos shared (email OAuth exige blind index pela consulta exata).

### Leitor e writer reader-first de `StudentAppInvitation.invited_email` (2026-10-24)

`EncryptedEmailField` preserva validação de email e limite lógico 254, enquanto
`storage_max_length=2048` comporta ciphertext sem alterar o limite lógico. A
migration `student_identity.0009` é somente schema: não cifra nem reescreve
linhas. O campo lê plaintext, Fernet legado e envelope versionado via ORM. O
gate `STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY` permanece `False`;
ligado, grava Fernet legado derivado de `SECRET_KEY`, não o envelope G1. A
configuração bloqueia o boot se o gate for ligado sem o reader HMAC pronto ou
sem `EMAIL_BLIND_INDEX_KEY`. O Admin usa busca exata/HMAC, o seed usa ownership
marker e os demais leitores observados carregam o campo pelo ORM.

As suítes `student_identity.test_invitation_email_lookup_index` e
`tests.test_shared_pii_encryption`, mais a regressão de seed, passaram **10/10**
em PostgreSQL descartável com migrations reais. Cobrem as duas fases de escrita,
lookup HMAC enquanto o email está cifrado, census agregado e rotação sintética
para envelope ativo sem expor o endereço. `manage.py check` passou; o gate de
configuração bloqueou writer sem HMAC e aceitou configuração sintética completa.
MigrationLoader/Autodetector disk-only não reportou drift nos apps desta alteração;
o diff também listou options padrões de apps Django não relacionados. A evidência
não autoriza migration, census/backfill em `public` real, provisionamento de
chave ou ativação do writer. Após a primeira escrita cifrada,
rollback para binário antigo não é suportado sem rotina de decifragem/reversão;
o rollout deve manter release reader-capable até essa rotina ser projetada e
ensaiada.

### Busca administrativa exata para `PublicWorkoutAccount.email` (2026-10-24)

A revisão ampliada encontrou oito Admins que consultavam o email da conta com
`icontains`: o Admin de conta, assinatura, work items, perfil nutricional, plano
alimentar, draft de treino, reembolso e depoimento. Todos agora resolvem email
exato pelo helper reader-first; índices HMAC são revalidados em memória. Busca
parcial continua nos demais campos textuais existentes. Os dois Admins cujo
único campo de busca era email mantêm a caixa do Django Admin, mas seu
`get_search_results()` não chama o caminho de `icontains`. Nenhuma permissão foi
alterada.

`CoachStudentRosterView` deixou de ordenar no banco pela coluna email; carrega a
relação e preserva ordem alfabética em memória, com `account_id` como desempate.
`training_analytics.recent_training_sessions()` projeta `account__email` via
ORM, sem filtrar, ordenar ou agregar por esse campo. Login, Google OAuth,
checkout/billing, mensagens e notificações obtêm email pela helper ou pelo ORM
e passam o valor autorizado aos serviços de entrega/Stripe; nenhuma busca SQL
de igualdade adicional foi encontrada fora do helper, Admin e comando de
backfill.

A constraint atual `unique=True` é case-sensitive; o lookup normaliza por
`casefold`, portanto variantes podem coexistir e o helper devolve todas as
correspondências na ordem padrão existente (os fluxos que selecionam uma usam
a primeira). O backfill agrega grupos HMAC duplicados. Este pacote não muda essa
semântica nem cria unicidade HMAC: census e reconciliação em ambiente autorizado
são pré-condições para constraint única e cifra. Gate de lookup permanece
desligado; email e constraint plaintext não mudaram.

Validação em PostgreSQL descartável com migrations reais: conta/Admin/comércio,
draft, plano alimentar, modelos nutricionais e ordenação do roster passaram
**51/51**. Os testes cobrem busca exata nos modos legacy/HMAC, rejeição de busca
parcial por email, busca parcial preservada para `plan_slug` e compilação dos
seis caminhos de FK relacionados (incluindo reembolso aninhado).
`manage.py check` passou e o autodetector disk-only não reportou drift em
`public_workouts`/`shared_support`. Nenhum dado real, chave ou gate foi
acessado/ativado; não houve migration funcional nem chamada Stripe.

### Varredura ampliada de escritores (2026-10-24)

O checkout também grava `Student.email` por onboarding de convite em massa/lead
importado (`student_app.workflows.onboarding_workflows`), criação do aluno a
partir de `StudentIntake`, sincronização condicional de `StudentIdentity`,
importação CSV e seeds sintéticos. O importador operacional usa
`bulk_create`/`bulk_update`, inclui email em `_UPDATE_FIELDS` e não chama
`Student.save()` nos caminhos em lote; `_sync_lookup_indexes()` atualmente cobre
somente telefone e CPF. Um HMAC futuro precisa ser calculado nesse helper e no
writer de membership que usa `QuerySet.update()`, além dos saves convencionais.

O upload do diretório chama o importador em thread por
`submit_background_job`, que reaplica schema e fence. A rota API de importação
usa `jobs.dispatcher` e a task Celery sem `tenant_schema` explícito nem fence; o
worker não foi executado porque Celery não está instalado. Essa trilha deve
permanecer desabilitada até transportar schema, buscar `AsyncJob` dentro dele e
aplicar `tenant_write_guard`.

Para `auth.User.email`, além de signup e Access Profile, a busca encontrou
`provision_owner`, `bootstrap_superdev` e writers de massa sintética/performance,
seed do Box e scripts locais de smoke/simulação/manutenção. Um deles cria
superuser com email posicional. Não foram encontrados bulk writes ou update por
queryset em auth.User no checkout. As evidências são uma varredura estática de
arquivos Python sem testes/migrations; chamadas dinâmicas, jobs externos e
scripts fora do repositório continuam não provados.

### Correção do corredor de importação API/worker (2026-10-24)

O contexto do dispatcher agora inclui `tenant_schema`; o dispatcher recusa jobs
de importação sem schema `box_<slug>`. As tasks de aluno e contato validam esse
schema, entram no tenant e aplicam o fence antes de ler `AsyncJob` e executar a
importação. A view mantém o fence desde a criação do CSV temporário até a criação
do job e despacho, evitando materializar upload quando o Box está congelado. O
`raw_reference` usa referência fixa do tipo de importação e não registra o nome
original do arquivo. Celery não está instalado e a view não está publicada em
`api/v1/urls.py`; execução com broker e jobs antigos sem schema continuam
pendentes de reconciliação antes de ativação. O comando cron de retry já usa o
sweep por tenant sob fence; a task Celery direta agora exige `tenant_schema` e
entra em `schema_context` + fence. Não foi encontrado callsite de `.delay()` para
essa task no checkout. Não foi feito census de `AsyncJob.result` persistidos;
metadata histórico criado por chamada direta pode exigir sanitização antes de
retenção/export.

Validação focal: **21/21 + 3 subtests** passaram via pytest com `TEST_DATABASE_URL`
apontando para uma base PostgreSQL inexistente. Isso confirma que os cenários
usam mocks e a fixture pytest não acessou database; integração PostgreSQL,
Celery/broker, jobs antigos e sanitização do metadata persistido seguem fora da
prova.
