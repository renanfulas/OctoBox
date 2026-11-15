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
| Durante a série | **nada** | — |
| Bi-set | "Sem descanso…" | `superset_next__v*` |
| Fim | encerramento | `workout_end__v*` |

Mudança em relação à 1ª versão: a carga da série é anunciada **no fim do
descanso**, não quando a série começa. O aluno ouve com calma, monta a carga e
executa em silêncio. A 1ª série de cada exercício (sem descanso antes) é
anunciada no `exercise_start`.

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

### QA automático (evita "palavras comidas" sem ouvir 500 arquivos)

O VoiceStudio tem `/v1/audio/transcriptions`. Depois de gerar, transcrever cada
fala e comparar com o texto; se a diferença passar de um limiar, regerar com
outra seed e marcar para escuta humana. O Renan só ouve o que o QA reprovou e
o treino-exemplo.

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
| 3. QA automático | transcrição + regeração | a fazer |
| 4. Player no guiado | `guided-voice.js` + toggle e regra de volume no lançador + cache offline no SW + testes | ✅ 2026-11-15 atrás de `CURVA_COACH_VOICE_ENABLED` (desligado) · ⏳ teste no iPhone |
| 5. Piloto | 3–5 alunos | a fazer |
| 6. App nativo | Capacitor: pausar/voltar ou abaixar o Spotify + tela bloqueada | depois do piloto |

## Riscos

- Tela bloqueada no iOS pode cortar o áudio do PWA → testar; solução
  definitiva é o app nativo.
- Música alta engole a voz mesmo mixada → regra de 1º uso + teste no piloto.
- Consentimento: o perfil de voz ainda não está marcado como voz própria
  verificada no VoiceStudio — registrar antes de publicar.
- Limpeza: apagar `static/curva-lab/` e `static/audio/coach/spike/` quando o
  spike acabar; backup do nginx em `/root/octobox.conf.bak-curva-spike-*` na
  produção pode ser removido.
