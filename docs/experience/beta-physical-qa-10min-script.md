# Beta Gate: QA Fisico e Papeis (Script de 10 Minutos)

> **Por que 10 minutos?** O objetivo aqui e pescar bloqueadores fatais (Gate), nao catalogar pixels ou fazer melhorias de copia. Se a porta nao abre, a casa nao esta pronta.

Este script foca 100% no teste com DEDO HUMANO em TELA REAL e garante o que os simuladores nao enxergam.

---

## Preparo
- **Dispositivo:** Real Mobile (Ex: iPhone 13, Galaxy S21, ou o menor celular da equipe).
- **Ambiente:** IP Local no celular (Acessar: `http://[IP-DA-SUA-MAQUINA]:8000`).
- **Seguranca (ALERTA):** Garantir que as credenciais `ghost/ghost` sejam destruidas se esse banco for para Homologacao Real na nuvem. Use apenas localhost.

---

## Etapa 1: Passeio pelo Shell e Busca (2 min) | Qualquer Admin/Owner

1. **Acessar `/login/`** -> Digite `ghost` e `ghost`.
2. **Dashboard Carregado?** -> Deslize de cima abaixo (Scroll vert.). Sem cortes nas bordas? ( ) Ok.
3. **Sidebar Total:** Toque no icone do Menu (Hamburger). Ele empurra a tela corretamente pro lado direito? ( ) Ok.
4. **Busca Global (Dataset Real):** Feche o Menu. Toque no input de buscar na barra de cima. Digite o nome de um aluno real e espere carregar o Dropdown. Tocou com o dedo e abriu a Ficha? ( ) Ok.

## Etapa 2: A Rota de Cadastros (3 min) | Papel: Recepcao

1. Va em `/alunos/` -> A tabela rola pro lado sob o dedo sem puxar a tela inteira? ( ) Ok.
2. Toque em "Novo Aluno".
3. **Toque na Tela Completa:** Desca a tela toda ate o meio do Formulario. Preencha algo, clique com o dedo nos botoes de Proximo. Se for longo, o teclado sobe tampando os campos? Consegue tirar o teclado de cima facil? ( ) Ok.
4. Va ate o fim e mande "Salvar" a ficha. Retornou erro 500 ou fechou suave? ( ) Ok.

## Etapa 3: Financeiro e Balcao (3 min) | Papel: Owner / Manager

1. Va em `/financeiro/` -> O portfolio de dividas ou sumario visual colapsa na tela sem encavalar valores? ( ) Ok.
2. Abra um Filtro com o dedo. A lista abriu legivel e pode ser tocada pra fechar? ( ) Ok.
3. **Ir para Recepcao:** Acesse `/operacao/recepcao/`. Veja os paineis de Entrada.
4. As tabelas dos recebiveis estao curtas ou pedem scroll? O botao verde de pagamento esta facil de ser tocado sem errar e clicar em cancelar? ( ) Ok.
5. **Ir para Rota Canonica de Manager:** Acesse `/operacao/manager/` e valide o carregamento inicial da rota do gerente. ( ) Ok.

## Etapa 4: Teste de Parede (Rate Limit & Roles) (2 min) | Papel: Coach Padrao (Sem Acesso)

1. Faca Logout (Sair).
2. Entre com uma conta de nivel Coach de Aula (ex: credencial criada para um Coach na sua maquina).
3. Tente acessar colando a URL no navegador do celular: `/financeiro/`, `/operacao/recepcao/` ou `/operacao/manager/`.
4. Ele parou voce dizendo que e "Acesso Restrito" ou deu tela estourada de Erro 500? ( ) Ok.

---

## Formato Curto de Retorno das Falhas
Pegue as falhas anotadas e reporte no formato curto:
- "A Busca Global nao aceitou meu dedo." -> Bloqueador
- "A Ficha de Cadastro o texto esta grandao demais e eu tive que descer por muito tempo." -> Toleravel (Resolve-se esteticamente, nao trava beta).
- "Tentei acessar /operacao/manager/ com gerente e deu erro." -> Bloqueador (Ajuste de permissao antes de prosseguir).
