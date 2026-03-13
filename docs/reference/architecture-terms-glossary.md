<!--
ARQUIVO: glossario de termos arquiteturais em linguagem simples.

TIPO DE DOCUMENTO:
- referencia conceitual

AUTORIDADE:
- media

DOCUMENTO PAI:
- [personal-architecture-framework.md](personal-architecture-framework.md)

QUANDO USAR:
- quando a duvida for o significado de um termo arquitetural e como ele aparece na pratica do projeto

POR QUE ELE EXISTE:
- Traduz os termos tecnicos usados na evolucao do projeto para uma linguagem clara e aplicavel.
- Evita que vocabulario tecnico pareca uma barreira maior do que realmente e.

O QUE ESTE ARQUIVO FAZ:
1. explica os principais termos em portugues simples.
2. conecta cada termo a exemplos do proprio projeto.
3. mostra por que esses conceitos importam na pratica.

PONTOS CRITICOS:
- este glossario deve continuar fiel a pratica do projeto, nao a definicoes academicas distantes.
- termos novos podem ser adicionados conforme a arquitetura evoluir.
-->

# Glossario pratico de arquitetura

Este glossario foi escrito para um contexto real: voce pode usar os termos abaixo sem precisar virar teorico de arquitetura.

## Boundary

Em portugues simples: fronteira.

E a linha que separa uma area da outra. Diz ate onde uma responsabilidade vai e onde a outra comeca.

Exemplo no projeto:

1. communications virou uma fronteira para WhatsApp e intake
2. operations virou uma fronteira para agenda, presenca e ocorrencias
3. finance virou uma fronteira para plano, matricula e pagamento

Por que importa:

1. evita que tudo se misture no mesmo lugar
2. ajuda a localizar responsabilidade

## Acoplamento

Em portugues simples: dependencia forte entre partes.

Duas partes estao acopladas quando uma sabe demais sobre a outra ou depende demais dela para funcionar.

Exemplo no projeto:

1. quando muitas areas dependiam diretamente de boxcore.models, havia acoplamento alto

Por que importa:

1. muito acoplamento torna mudanca perigosa
2. diminuir acoplamento costuma facilitar manutencao e evolucao

## Compatibilidade

Em portugues simples: capacidade de mudar sem quebrar quem ainda usa o jeito antigo.

Exemplo no projeto:

1. varios modulos antigos viraram fachadas para que o sistema continuasse funcionando durante a reorganizacao

Por que importa:

1. em sistema real, quase nunca da para mover tudo de uma vez
2. compatibilidade protege a operacao durante a transicao

## Superficie publica

Em portugues simples: o ponto oficial pelo qual o resto do sistema deveria enxergar uma area.

Exemplo no projeto:

1. students/models.py virou uma superficie publica para modelos de aluno
2. finance/models.py virou uma superficie publica para modelos financeiros
3. onboarding/models.py virou uma superficie publica para intake

Por que importa:

1. voce evita espalhar imports perigosos por toda a base
2. se o interior mudar, o resto sofre menos

## State anchor

Em portugues simples: ancora de estado.

E o lugar historico que ainda segura parte importante do estado do sistema, como models, migrations ou app label, mesmo que o resto da arquitetura ja tenha mudado.

Exemplo no projeto:

1. boxcore ainda e a ancora historica de estado para models e migrations

Por que importa:

1. muda-lo cedo demais pode quebrar schema, admin e historico de migrations
2. reconhecer isso evita refatoracao imprudente

## App label

Em portugues simples: o nome interno que o Django usa para identificar os modelos.

Exemplo:

1. mesmo com varios apps reais novos, muitos modelos ainda apontam historicamente para boxcore

Por que importa:

1. ele afeta admin, migrations, content types e referencias internas do Django

## Fachada

Em portugues simples: uma capa de compatibilidade.

Ela parece o ponto antigo por fora, mas por dentro redireciona para o lugar novo.

Exemplo no projeto:

1. varios arquivos em boxcore viraram fachadas que reexportam implementacoes reais dos apps novos

Por que importa:

1. ajuda a migrar sem quebrar tudo de uma vez

## Orquestracao

Em portugues simples: coordenar o fluxo entre partes diferentes.

Exemplo:

1. uma view recebe a requisicao, chama o fluxo certo, monta contexto e devolve resposta

Por que importa:

1. a view nao deveria carregar toda a regra de negocio sozinha

## Regra de negocio

Em portugues simples: a parte que traduz como o negocio deve funcionar.

Exemplo:

1. como intake vira aluno
2. como matricula e pagamento se conectam
3. quais limites a grade deve respeitar

Por que importa:

1. isso e o coracao do produto
2. quando essa regra fica muito espalhada, o sistema fica fragil

## Infraestrutura

Em portugues simples: a parte que conversa com framework, banco, servicos externos e adaptadores tecnicos.

Exemplo:

1. adapters Django
2. admin
3. integracoes com WhatsApp

Por que importa:

1. o dominio nao deveria depender demais dos detalhes tecnicos

## Migrations

Em portugues simples: o historico de evolucao do banco que o Django guarda.

Por que importa:

1. quando voce mexe nisso sem estrategia, o risco sobe muito
2. por isso o projeto desacoplou o codigo primeiro e adiou mudancas pesadas de estado

## Como usar este glossario

Quando ouvir um termo tecnico, faca duas perguntas:

1. isso descreve uma estrutura real do sistema?
2. isso me ajuda a tomar uma decisao melhor?

Se a resposta for sim, use o termo como ferramenta. Se for nao, ignore a pose tecnica e volte para o problema real.
