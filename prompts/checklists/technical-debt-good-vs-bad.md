<!--
ARQUIVO: guia de debito tecnico bom vs ruim no OctoBOX.

POR QUE ELE EXISTE:
- ajuda a acelerar sem transformar velocidade em erosao silenciosa.

O QUE ESTE ARQUIVO FAZ:
1. define o que e debito tecnico aceitavel.
2. mostra sinais de debito tecnico perigoso.
3. oferece perguntas de triagem antes de aceitar um atalho.

PONTOS CRITICOS:
- confundir aceleracao consciente com abandono estrutural e uma das formas mais caras de perder tempo.
-->

# Technical Debt: Good vs Bad

## Debito tecnico bom

Debito tecnico bom e aquele que e:

- explicito
- isolado
- documentado
- reversivel
- de baixo raio de explosao
- com dono claro
- com motivo de negocio claro

Exemplos:

- adaptador transicional enquanto um corredor oficial nasce
- alias temporario para migrar namespace sem quebrar tudo
- fallback manual para uma integracao ainda em maturacao

## Debito tecnico ruim

Debito tecnico ruim e aquele que e:

- escondido
- acoplado em muitos lugares
- perigoso para dados, seguranca ou permissao
- sem dono
- sem plano de retirada
- silencioso
- vendido como "temporario" pela decima vez

Exemplos:

- side effect de banco no import
- senha fraca hardcoded em superficie sensivel
- CSS global carregando modulo de dominio sem necessidade
- regra critica espalhada em view, template e JS ao mesmo tempo

## Perguntas de triagem

Antes de aceitar um atalho, responda:

- esse atalho esta isolado ou vai vazar para metade do sistema?
- eu consigo explicar por que ele existe em uma frase honesta?
- eu sei quem vai pagar isso depois?
- eu sei como detectar quando ele virou risco real?
- se outra pessoa entrar no projeto, ela vai encontrar esse debito ou tropecar nele?

## Regra pratica

Se o atalho parece uma ponte provisoria bem sinalizada, ele pode ser um debito bom.
Se parece fio desencapado atras do armario, ele ja e debito ruim.
