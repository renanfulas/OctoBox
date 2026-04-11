<!--
ARQUIVO: porta de entrada da zona de prototipos do repositorio.

TIPO DE DOCUMENTO:
- referencia leve de laboratorio

AUTORIDADE:
- baixa para runtime, media para uso seguro da pasta

DOCUMENTO PAI:
- [../docs/reference/support-material-map.md](../docs/reference/support-material-map.md)

QUANDO USAR:
- quando alguem entrar em `prototypes/`
- quando houver duvida se um exemplo daqui faz parte do produto oficial

POR QUE ELE EXISTE:
- evita confundir experimento com codigo de producao
- deixa explicito que a pasta e laboratorio, nao contrato do runtime
-->

# Prototypes

Esta pasta e a bancada de laboratorio do repositorio.

Ela existe para guardar:

1. exemplos copiaveis
2. prototipos leves
3. ensaios tecnicos antes de promover algo para o produto

## Regra de ouro

Nada aqui vira verdade oficial automaticamente.

Se um prototipo funcionar bem, ele precisa:

1. ser integrado deliberadamente no app real
2. ganhar ownership claro
3. entrar no fluxo normal de testes, docs e manutencao

## O que fazer com esta pasta

1. manter exemplos que ainda ensinam algo
2. remover prototipos quebrados, redundantes ou abandonados
3. evitar dependencia do runtime principal em qualquer arquivo daqui

## O que nao fazer

1. nao usar `prototypes/` como fonte canonica de arquitetura
2. nao assumir que exemplos daqui seguem todos os contratos do produto
3. nao acoplar deploy ou CI a prototipos experimentais sem promover o codigo antes
