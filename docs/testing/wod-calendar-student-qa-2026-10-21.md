# QA de WOD, calendário e app do aluno — 21/10/2026

Revisão local do fluxo de um coach/gestor: colar texto, organizar a semana, revisar movimentos, escolher modalidade e aulas, distribuir, aprovar e ler no app do aluno. Ambiente: PostgreSQL 15 e Redis em Docker, Django com schema de teste e navegador Chromium. Consulta ao RAG usada para localizar os contratos existentes.

## Problemas corrigidos

| Problema | Efeito | Correção |
|---|---|---|
| Modalidade desaparecia do formulário após organizar | A prévia persistia a trilha, mas o seletor voltava vazio | Preservar a modalidade na resposta e mostrá-la no resumo |
| Trocar modalidade não invalidava a prévia | Confirmação podia usar o destino antigo apesar da seleção visível | Bloquear confirmação até organizar novamente |
| Ano omitido após organizar e na confirmação | Programação de outro ano podia ser rejeitada ou confundida com o ano corrente | Manter `dd/mm/aaaa` em todo o percurso e comparar também o ano |
| Data inexistente, como `31/02`, gerava `ValueError` | Erro de servidor no lugar de orientação | Converter em erro de validação sem criar plano |
| Revisão em aba antiga não verificava a versão | Podia sobrescrever revisão nova ou acessar um item que já não existia | Token de revisão, bloqueio da linha durante a escrita e aviso com a prévia atual |
| Revisão tardia alterava plano já confirmado | Divergência entre plano e WOD distribuído | Recusar edição de plano confirmado nesse corredor |
| Colagem e processamento sem atalho/estado explícito | Mais passos no celular e pouca informação durante a organização | Botão de colar, preservação da seleção, orientação se o navegador negar acesso e estado de processamento |
| Campo vazio permitido | Submissão sem treino útil | Exigir texto antes de organizar |
| Cartão rolava internamente ao focar o texto | Início dos rótulos ficava cortado no celular, apesar de a página não ter overflow | Conter o halo decorativo dentro do cartão e testar os limites reais do campo após colar |
| Revisão exigia identificadores técnicos | Nome legível podia ser rejeitado mesmo sendo conhecido | Aceitar aliases exatos do catálogo, sem adivinhar combinações |
| Códigos internos e conteúdo repetido na prévia | `warmup`, `push_up` e `skip_existing_workout` confundiam a leitura | Nomes legíveis, estados explicativos e remoção de repetição no detalhe |
| Títulos técnicos e rounds repetidos no app do aluno | `warmup` e `3x · 3 rounds` poluíam a leitura do treino publicado | Normalizar somente a apresentação desses títulos e evitar repetição do formato exato, preservando a prescrição |

## Verificação

Backend/app: bateria inicial ampliada com **267 testes passando**; após as últimas mudanças, **169 testes focados passando e 7 subtests passando**. Os números se sobrepõem e não devem ser somados. Os cenários cobrem erros de data, confirmação de ano seguinte, edição antiga, preservação de prescrições, nomes/aliases, falha da revisão automática, idempotência, concorrência de distribuição, modalidade e leitura do WOD publicado.

Verificações Django, sintaxe JavaScript e `git diff --check` passaram. O espelho local de arquivos estáticos foi sincronizado com `collectstatic`; `check_static_drift --strict` passou.

Os testes de navegador cobrem temas claro/escuro e larguras de celular/desktop, revisão por diálogo, colagem com permissão negada, confirmação, distribuição após resposta perdida, aprovação e navegação no calendário do aluno.

Resultado final do navegador: **38 cenários E2E passaram**. O percurso completo foi executado separadamente em CrossFit e HYROX, com uma aula da modalidade vizinha no mesmo horário permanecendo intacta. A leitura no aluno preservou os três movimentos do texto colado e a navegação do mês seguinte continuou funcionando com múltiplas aulas.

Evidências visuais locais geradas pelos testes ficam em `tmp/visual_contract/smart_paste/`, incluindo `clipboard-mobile.png`, `smart-paste-dialog-mobile-dark.png` e `student-wod-hyrox-mobile-dark.png`. O teste da colagem mede também as margens do campo dentro do cartão depois de receber foco, além da largura total da página.

## Limites ainda relevantes

- **IA real:** `ANTHROPIC_API_KEY` não está configurada no ambiente local. Foram verificados os caminhos de sucesso/falha com respostas controladas e o fallback manual; não há evidência de chamada real bem-sucedida nesta rodada. O normalizador também depende da configuração de habilitação por box.
- **Significado da correção:** o resolvedor identifica o movimento canônico; ele preserva o texto original do coach e os números da prescrição. O nome identificado fica visível para conferência. Não é um corretor ortográfico irrestrito.
- **Modalidades paralelas:** o roteamento de WOD preserva trilhas separadas. Disponibilidade de coach, espaço e equipamento entre duas aulas no mesmo horário continua sendo uma política operacional separada.
- **Dispositivo físico:** emulação de largura de iPhone no Chromium não substitui Safari/iOS físico, teclado móvel, menu de colar e permissões do sistema operacional.
- **Publicação:** estas mudanças são locais na branch de QA; exigem PR/deploy para chegar à aplicação publicada.
