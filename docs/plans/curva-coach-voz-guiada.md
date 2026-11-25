# Curva — Coach de voz no treino guiado (plano)

Status: em execução · atualizado 2026-11-15 · voz única (Renan)

## Objetivo

Durante o treino guiado, a voz do Renan conduz o treino ("top set, oitenta e
dois quilos, foco") por cima da música que o aluno já ouve (Spotify ou outro
app). Barato, offline-first, sem serviço pago.

## Decisões vigentes

| Tema | Decisão | Evidência |
|---|---|---|
| Geração | VoiceStudio local (RTX 5060), perfil `4db30ba2`, `speed=0.88`, `steps=64` | ~6,5 s de GPU por frase; custo zero |
| Quando gerar | Em lote, na máquina do Renan, por `scripts/coach_voice/build_coach_voice.py` | Sem GPU na VPS; funciona offline |
| Forma das falas | **Frase inteira** quando há número de carga; nada abaixo de ~1,5 s | Teste de escuta 2026-11-12: pedaços curtos "comem" sílabas; versão B aprovada |
| Master | WAV float 32 bits em `~/.octobox/coach_voice_masters` (fora do repo), cache por hash | Re-edição sem regerar |
| Entrega | MP3 mono 96 kbps + `manifest.json` + `bip.mp3` em `static/audio/coach/v<n>/` | ~85 KB por frase |
| Mixagem | corte suave, corta < 90 Hz, +4 dB em 3 kHz, loudness alto com limitador, fade 40 ms, bip antes de cada fala | "Furar" a música sem abaixá-la |
| Música | Do aluno (Spotify etc.), botão "Abrir minha playlist" | Sem API do Spotify |
| Mistura no PWA | `audioSession.type = 'ambient'` (voz por cima) | Spike iPhone abaixo |
| Pausar e voltar o Spotify | **Só no app nativo** (Capacitor, `notifyOthersOnDeactivation`) | Safari não devolve o áudio; API do Spotify limitada a ~5 usuários |

## Resultado do spike (iPhone, Safari, 2026-11-12)

| `audioSession.type` | Voz | Spotify |
|---|---|---|
| padrão / `transient-solo` | toca (ignora silencioso) | pausa e **não volta** |
| `transient` / `ambient` | muda no silencioso; com som, toca | mistura, não abaixa |

Pendentes: **Android** e **tela bloqueada** com `ambient` (botão "repetir a
cada 20 s" da página de spike).

## 1. Quando a voz fala (regra de ouro: silêncio durante a série)

| Momento | Fala | Arquivo |
|---|---|---|
| Início do treino | boas-vindas | `workout_start__v*` |
| Novo exercício | "Próximo exercício…" | `exercise_start__v*` |
| Fim da série (registrada) | "Boa. Série registrada." | `set_logged__v*` |
| Início do descanso | "Descansa. Noventa segundos…" | `rest_start__s<seg>` |
| **Faltando ~15 s do descanso** | **anuncia a PRÓXIMA série**: fase + carga, depois reps (+ "é a última") | `set_<fase>__kg<kg>` → `set_reps__r<n>` → `set_last__v*` |
| Faltando 10 s | "Prepara…" (só se não houve anúncio) | `rest_10s__v*` |
| Durante a série | **nada** — exceto "Contar comigo" na top set/AMRAP (abaixo) | `count_*` |
| Bi-set | "Sem descanso…" | `superset_next__v*` |
| Fim | encerramento | `workout_end__v*` |

Mudança em relação à 1ª versão: a carga da série é anunciada **no fim do
descanso**, não quando a série começa. O aluno ouve com calma, monta a carga e
executa em silêncio. A 1ª série de cada exercício (sem descanso antes) é
anunciada no `exercise_start`.

### Exceção: contagem intra-série (top set e AMRAP) — v3, 2026-11-16

Pedido do Renan: "como um personal mesmo, contando as repetições". Só na top
set (com meta de reps) e na AMRAP (`stage: max` ou `amrap: true`), e só quando
o aluno toca **"Contar comigo"** na tela da série.

- O celular não vê a repetição: **a voz dita o ritmo** e o aluno acompanha.
  3 s por rep (2 desce, 1 sobe); o número sai no alto da subida e a dica cai na
  descida seguinte. Perto da falha desacelera (top: 3,5 s e 4 s nas duas
  últimas; AMRAP depois da meta: 4 → 5 s).
- Roteiro: preparo ("Top set. Posiciona, pés firmes…") → bips 3-2-1 do app →
  "Valendo! Desce controlando." → contagem com dicas em revezamento → metade →
  "faltam duas" → "falta uma" → na top set, "Sobe! Sobe! Empurra!" no fundo da
  última e "Oito! Isso! Pode soltar." → fechamento.
- AMRAP: "Meta batida. Agora é tudo seu." → "Se a técnica quebrar, para." →
  incentivo até 30 → **"Parei"** → "Fechou em doze repetições…". As reps
  contadas preenchem o campo (o aluno confere e registra).
- Faixa (8-10) conta até o topo da faixa; "Parei" vale em qualquer momento.
- Número e dica numa frase só (número sozinho sai "comido"); falas da reta
  final em `speed 0.95`, mais urgentes.
- Teste de escuta 2026-11-16: 1ª versão "mais ou menos"; a 2ª (roteiro acima,
  com preparo, 3-2-1 e desaceleração) aprovada.
- "Contar comigo" corta a fala que ainda estiver tocando (ex.: o anúncio da
  série) e só começa o 3-2-1 quando o preparo acaba. Teste no navegador
  2026-11-16: sem isso o 3-2-1 entrava na fila atrás do anúncio e o áudio
  ficava atrás do número na tela. Com o corte, áudio e tela batem (±1 ms).

## 2. Pacote de áudio

Fonte: `public_workouts/coach_voice/copy.yaml`. Hoje: **538 falas**
(4 templates × 120 cargas + 30 reps + 11 descansos + 27 variações), ~1 h de
GPU, ~45 MB.

### Melhorias a aplicar no `copy.yaml` (v2)

1. **Cargas de halter/máquina.** A faixa atual é de 2,5 em 2,5 kg; halteres e
   máquinas usam 1 kg (13 kg, 27 kg). Faixa proposta: 1–40 kg de 1 em 1, e
   40–300 kg de 2,5 em 2,5.
2. **Fallback sem carga.** Se a carga prescrita não existir no pacote
   (ex.: 83,75 kg), tocar uma variante sem número: "Agora é a top set. Confere
   a carga na tela." Hoje não há fallback.
3. **Cortar o volume pela metade.** `set_feeder` e `set_plain` podem reusar uma
   única frase de carga ("Coloca oitenta e dois quilos na barra.", ≥ 1,5 s)
   precedida da frase da fase. Mantém frase inteira só em `set_top` e
   `set_max` (as que o Renan aprovou). ~538 → ~330 falas.
4. **Seed fixa** no VoiceStudio, para a mesma frase sair igual se for regerada.

### Pacote v3 (2026-11-16)

780 falas: as 372 do v2 (mesmos masters, sem regerar) + 408 de contagem
(`count_*`, reps 1–30) + `tick.mp3` / `go.mp3` do 3-2-1.

**O "dá" antes da fala.** O VoiceStudio solta um estalo de ~100 ms em ~50 ms,
depois ~300 ms de silêncio, e só então a fala — em 486 de 488 masters,
inclusive o pacote v2 publicado. `remover_estalo()` no tratamento corta do
começo até o fim desse silêncio; como os masters ficam guardados, corrigir não
custa GPU. Os MP3 do v2 nunca mudam no lugar (cache do SW), por isso v3.

### QA automático (`--qa`, implementado)

O VoiceStudio transcreve (`/v1/audio/transcriptions`, ~9 s fixos por chamada
+ ~0,55 s por segundo de áudio) e o gerador compara com o texto:
- lotes de 8 falas por chamada; lote com palavra faltando é retranscrito fala
  a fala; reprovada é regerada com outra seed (até 3×) e fica a melhor;
- lotes em ordem embaralhada (semente fixa): 8 frases quase iguais seguidas
  ("A carga dessa série é…") o transcritor junta numa só e o lote inteiro
  reprova — em ordem de id o QA levava ~3 h;
- o transcritor escreve "top 7" para "top set" e "para" para "pra": a
  comparação trata como iguais;
- retomável: a nota fica no manifesto a cada lote; VoiceStudio caindo no meio
  deixa a fala sem nota para a próxima rodada, sem derrubar o build;
- **número faltando reprova** (a palavra que mais importa e a que mais some);
  comparação por multiconjunto ("mais uma… mais uma" conta duas vezes) e
  normalizada ("82,5 kg" = "oitenta e dois quilos e meio", "21" = "vinte e um");
- 0,5 s de silêncio antes de transcrever: sem isso o transcritor engole a 1ª
  palavra e reprova fala boa;
- o que nem assim passa vai para `~/.octobox/coach_voice_masters/qa_report_v<n>.json`,
  a lista de escuta humana.

### Onde guardar o pacote

45 MB de MP3 no git pesa (cada regeneração soma outro tanto ao histórico).
Opções, em ordem de preferência:
1. Aplicar a melhoria 3 + 64 kbps → ~20 MB, commitar.
2. Git LFS para `static/audio/coach/`.
3. Fora do git: upload direto para a VPS no deploy (precisa de passo novo no
   `deploy-vps.yml`).

O celular nunca baixa tudo: o service worker cacheia só as cargas da
prescrição do aluno (~10–30 arquivos, < 3 MB).

## 3. Cliente (PWA)

- `guided-voice.js`: fila de áudio (nunca sobrepõe falas), bip + falas com
  ~150 ms entre elas, agenda os anúncios pelo cronômetro de descanso que já
  existe (`guided-timer.js` / `guided-rest-alert.js`).
- `audioSession.type = 'ambient'` antes de tocar; desbloqueio de áudio no toque
  "Iniciar treino".
- Toggle "Coach de voz" (desligado por padrão no piloto) + botão "Abrir minha
  playlist".
- **Tela de 1º uso** com a regra para o aluno: (1) Spotify → Configurações →
  Reprodução → Nível de volume: **Silencioso**; (2) volume do celular alto;
  (3) tire do silencioso. Mais um botão "Testar voz" que toca uma fala.
- Pré-cache das falas da prescrição quando o toggle é ligado.
- Telemetria: toggle ligado/desligado, falas tocadas, falhas de `play()`.

## 4. Fases

| Fase | Entrega | Status |
|---|---|---|
| 0. Spike de mistura | página + teste no iPhone | ✅ iPhone · ⏳ Android e tela bloqueada |
| 1. Copy | `copy.yaml` | ✅ v1 · ⏳ revisão do Renan + melhorias v2 |
| 2. Pacote | gerador + pacote v2 (370 falas, 23 MB) + treino-exemplo com música | ✅ 2026-11-15 — Renan aprovou: voz clara por cima da música |
| 3. QA automático | transcrição + regeração | ✅ 2026-11-16 (`--qa`, pacote v3) |
| 4b. Contagem intra-série | "Contar comigo" / "Parei" na top set e AMRAP + 408 falas | ✅ 2026-11-16 atrás da mesma flag · ⏳ teste no iPhone |
| 4. Player no guiado | `guided-voice.js` + toggle e regra de volume no lançador + cache offline no SW + testes | ✅ 2026-11-15 atrás de `CURVA_COACH_VOICE_ENABLED` (desligado) · 2026-11-16 beta por aluno em `CURVA_COACH_VOICE_PLANS` (slugs, ex.: `andressa-cristina`) · ⏳ teste no iPhone |
| 5. Piloto | 3–5 alunos | a fazer |
| 6. App nativo | Capacitor: pausar/voltar ou abaixar o Spotify + tela bloqueada | depois do piloto |

## Riscos

- Tela bloqueada no iOS pode cortar o áudio do PWA → testar; solução
  definitiva é o app nativo.
- **Contagem com a tela bloqueada:** os timers de JS congelam e a contagem
  para no meio da série. Saída se o teste confirmar: montar a série inteira
  como um áudio contínuo no começo (áudio já tocando tende a seguir).
- **JS antigo depois do deploy (corrigido 2026-11-16):** o service worker
  pré-carregava os assets sem `?v=` pelo cache HTTP do navegador, guardava a
  versão anterior e a servia para o `?v=` novo (`ignoreSearch`). Agora o
  pré-cache usa `cache: 'reload'`.
- Ritmo fixo de 3 s pode não bater com o aluno → "Parei" a qualquer momento;
  cadência por exercício fica para depois (não há campo de cadência hoje).
- Música alta engole a voz mesmo mixada → regra de 1º uso + teste no piloto.
- Consentimento: o perfil de voz ainda não está marcado como voz própria
  verificada no VoiceStudio — registrar antes de publicar.
- Limpeza: apagar `static/curva-lab/` e `static/audio/coach/spike/` quando o
  spike acabar; backup do nginx em `/root/octobox.conf.bak-curva-spike-*` na
  produção pode ser removido.
