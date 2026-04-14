<!--
ARQUIVO: checklist operacional de auditoria e depuracao de UI do OctoBox.

POR QUE ELE EXISTE:
- transforma investigacao de bug visual em rotina repetivel.
- evita pular direto para remendo, grep cego ou `!important`.
- consolida o que deve ser verificado sempre que uma UI parecer errada.

O QUE ESTE ARQUIVO FAZ:
1. organiza uma checklist de abertura, investigacao, correcao e fechamento.
2. lembra os pontos de ownership, payload, CSS, JS e shell que mais geram regressao.
3. funciona como ritual curto para auditoria de UI.

PONTOS CRITICOS:
- esta checklist nao substitui pensamento tecnico; ela reduz esquecimento.
- nem todo item precisa produzir alteracao de codigo.
- se a mudanca afetar camada compartilhada, o smoke precisa subir de escopo junto.
-->

# Checklist operacional de auditoria de UI

Use esta checklist toda vez que uma interface parecer errada, incoerente ou fragil.

## 1. Abrir a investigacao

- [ ] Li [../../README.md](../../README.md), [documentation-authority-map.md](documentation-authority-map.md) e [front-end-ownership-map.md](front-end-ownership-map.md) se a tela ainda nao estiver clara na minha cabeca.
- [ ] Decidi se a suspeita parece mais visual ou mais contratual.
- [ ] Identifiquei a tela, a rota, o papel do usuario, o estado da pagina e a viewport onde o bug aparece.
- [ ] Decidi se o problema parece local de uma tela ou compartilhado entre varias superficies.

## 2. Provar ownership

- [ ] Localizei a view do dominio.
- [ ] Localizei o presenter ou builder da tela, se houver.
- [ ] Localizei o template principal.
- [ ] Localizei os includes locais da tela.
- [ ] Localizei o CSS local da tela.
- [ ] Localizei o JS local da tela, se houver.
- [ ] Provei a cadeia `template -> include -> CSS -> JS -> payload`.

## 3. Ler a cena do crime visual

- [ ] Verifiquei se existe `!important`.
- [ ] Verifiquei se existe `style=""` ou `<style>` no template.
- [ ] Verifiquei se ha seletor longo, seletor por id ou profundidade excessiva.
- [ ] Verifiquei se a pagina depende de classe visual para comportamento.
- [ ] Verifiquei se a regra parece local, compartilhada, legada ou canonica.

## 4. Ler a cena do crime contratual

- [ ] Confirmei se o dado ja chega errado no payload ou se so fica errado depois de renderizar.
- [ ] Confirmei se o template esta fazendo regra de negocio que deveria vir pronta.
- [ ] Confirmei se `behavior`, `assets` e `capabilities` da tela fazem sentido.
- [ ] Confirmei se o shell global, os counts e os alertas estao coerentes com a tela.
- [ ] Confirmei se existem aliases legados namespaced convivendo com contexto plano.

## 5. Procurar suspeitos recorrentes

- [ ] Revisei [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) quando o bug parece heranca ou helper historico.
- [ ] Revisei [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css) quando varias telas do catalogo parecem contaminadas.
- [ ] Revisei [../../static/css/design-system/components/states.css](../../static/css/design-system/components/states.css) antes de acusar `note-panel*`.
- [ ] Revisei [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py) quando hero, assets, reading panel ou payload parecem tortos.
- [ ] Revisei [../../access/context_processors.py](../../access/context_processors.py) e [../../access/shell_actions.py](../../access/shell_actions.py) quando o shell inteiro parece errado.

## 6. Classificar o achado antes de corrigir

- [ ] Decidi se o problema parece `override-hotspot`, `legacy-bridge`, `canonical-alias`, `candidate-unused`, `duplicate-rule` ou falha de contrato de tela.
- [ ] Se parece legado, confirmei se e ponte viva ou alias protegido antes de pensar em apagar.
- [ ] Se parece regra morta, confirmei templates, JS, payload strings e carregamento real da tela antes de chamar de morto.

## 7. Escolher a correcao de menor arrependimento

- [ ] Se o problema e local, corrigi primeiro na tela local.
- [ ] So subi para design system quando a responsabilidade era realmente compartilhada.
- [ ] Nao usei `!important` como primeira resposta.
- [ ] Nao corrigi bug semantico com remendo visual.
- [ ] Nao corrigi bug visual inflando payload cosmetico no backend.
- [ ] Mantive a ladder correta: `token -> primitivo canonico -> classe semantica local -> helper neutro`.

## 8. Fechar sem deixar debito escondido

- [ ] Fiz smoke visual da tela afetada.
- [ ] Se a mudanca foi compartilhada, revisei pelo menos uma segunda tela que consome a mesma camada.
- [ ] Se mexi em shell, nav ou counts, revisei o impacto em mais de um papel.
- [ ] Se mexi em presenter ou payload, confirmei que o template e o JS ainda recebem o contrato esperado.
- [ ] Se movi ownership, considerei atualizar docs de mapa ou contrato.

## 9. Ferramentas de apoio

- [ ] Rodei o scanner quando a suspeita era override, legado, residual ou codigo morto:

```powershell
py .agents\skills\octobox-ui-cleanup-auditor\scripts\frontend_forensics.py --base-path . --report "$env:TEMP\octobox-frontend-forensics.json"
```

- [ ] Consultei [front-end-forensics-map.md](front-end-forensics-map.md) para pistas visuais e [front-end-contract-forensics-map.md](front-end-contract-forensics-map.md) para pistas de payload, presenter e shell.

## Veredito rapido

Se eu nao consigo responder estas tres perguntas, ainda nao devo corrigir:

- [ ] Quem manda nessa tela?
- [ ] Onde a falha nasceu de verdade?
- [ ] Qual e a menor correcao que resolve sem contaminar outra camada?
