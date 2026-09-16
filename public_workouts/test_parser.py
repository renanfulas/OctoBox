"""
ARQUIVO: testes do parser determinístico de HTML legado -> payload
(Onda A2 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- `parser.py` é a peça mais arriscada da migração: 10 clientes pagantes
  reais, texto de prescrição livre (schema.py não valida formato de
  reps_spec/rir_spec) — um erro de mapeamento vira aluno instruído errado,
  não um erro visível de validação. Cada teste aqui nasceu de um caso real
  encontrado rodando `migrate_legacy_workouts --dry-run` contra os 10 HTMLs
  de verdade (não são casos hipotéticos).
- fixtures são recortes fiéis (às vezes verbatim) dos HTMLs reais que
  motivaram cada regra — ver o comentário de cada uma.
"""

from django.test import SimpleTestCase

from public_workouts import schema
from public_workouts.parser import (
    build_program_payload_from_html,
    parse_cardio_tab,
    parse_embedded_stage_content,
    parse_legacy_html,
    parse_periodization_tab,
)


def _one_day(day_id: str, label: str, body: str) -> str:
    return f'<div id="{day_id}" class="session"><div class="sess-hdr"><div class="sess-title">{label}</div></div>{body}</div>'


class ParseLegacyHtmlTests(SimpleTestCase):
    def test_gym_reps_wins_over_sets_table_and_last_top_row_supplies_rir(self):
        # Recorte de henrique.html: ramp Prep/Feeder/Top 1/Top 2/Top 3/Max —
        # reps_spec vem do resumo do treinador (gym-reps), rir_spec vem da
        # ÚLTIMA linha "Top" (o estímulo-alvo mais pesado do ramp), não da
        # primeira.
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Supino inclinado com halteres</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-incline-bench-press">Ver</a>
            </div>
            <div class="gym-card">
              <div class="gym-summary"><strong>Supino</strong><div class="gym-reps">Feeder → 3× Top (crescente) → 1× Max</div></div>
            </div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Intensidade / Nota</th></tr>
              <tr><td><span class="st st-f">Feeder</span></td><td>1×</td><td>8</td><td>RIR 4</td></tr>
              <tr><td><span class="st st-t">Top 1</span></td><td>1×</td><td>7-8</td><td>RIR 3</td></tr>
              <tr><td><span class="st st-t">Top 2</span></td><td>1×</td><td>6-7</td><td>RIR 2</td></tr>
              <tr><td><span class="st st-t">Top 3</span></td><td>1×</td><td>5-6</td><td>RIR 1 · carga mais pesada</td></tr>
            </table></div>
            <div class="tracker"></div>
          </div>
        ''')

        days, skipped = parse_legacy_html(html)

        self.assertEqual(skipped, [])
        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['movement_slug'], 'dumbbell-incline-bench-press')
        self.assertEqual(movement['reps_spec'], 'Feeder → 3× Top (crescente) → 1× Max')
        self.assertEqual(movement['rir_spec'], 'RIR 1 · carga mais pesada')
        self.assertTrue(movement['is_tracked'])

    def test_exercise_without_gym_reps_synthesizes_from_sets_table(self):
        html = _one_day('seg', 'Pernas', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Agachamento livre</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-squat">Ver</a>
            </div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>8-10</td><td>RIR 2</td></tr>
            </table></div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['reps_spec'], 'Top Set 3× 8-10')
        self.assertEqual(movement['rir_spec'], 'RIR 2')
        self.assertFalse(movement['is_tracked'])

    def test_exercise_without_gym_reps_or_table_falls_back_to_note_text(self):
        html = _one_day('sab', 'Cardio', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Corrida leve</div></div></div>
            <div class="ex-note">20 min em ritmo confortável.</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['movement_slug'], 'corrida-leve')
        self.assertEqual(movement['reps_spec'], '20 min em ritmo confortável.')
        self.assertEqual(movement['rir_spec'], '')
        self.assertIsNone(movement['reference_url'])

    def test_no_wiki_btn_falls_back_to_slugified_name(self):
        # rafael.html, vaga genuinamente aberta: sem wiki-btn, mas com
        # gym-reps/sets-tbl normais -- só o link que falta.
        html = _one_day('sex', 'Bônus', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Acessório livre (o que precisar)</div></div></div>
            <div class="gym-card"><div class="gym-summary"><strong>Acessório livre</strong><div class="gym-reps">2-3× 12-15</div></div></div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>RIR</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>2-3×</td><td>12-15</td><td>2</td></tr>
            </table></div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['movement_slug'], 'acessorio-livre-o-que-precisar')
        self.assertIsNone(movement['reference_url'])
        self.assertEqual(movement['reps_spec'], '2-3× 12-15')

    def test_bare_rir_number_normalizes_to_rir_prefix(self):
        # rafael.html: coluna literalmente chamada "RIR" com número nu
        # ("2"), sem o texto "RIR" na frente -- precisa normalizar pra ficar
        # igual ao formato "RIR N" que os outros 9 programas usam.
        html = _one_day('seg', 'Core', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Pallof press no cabo</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/cable-pallof-press">Ver</a>
            </div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>RIR</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>2-3×</td><td>10-12</td><td>2</td></tr>
            </table></div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        self.assertEqual(days[0]['blocks'][0]['movements'][0]['rir_spec'], 'RIR 2')

    def test_flat_table_without_type_column_splits_series_reps_and_rir(self):
        # franciele.html e' o unico dos 10 programas cuja sets-tbl NAO tem a
        # coluna "Tipo" (sem <span class="st ...">): 3 colunas (Series x
        # Reps | RIR | Descanso), 1 linha por exercicio, sem ramp.
        html = _one_day('seg', 'Pernas', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Leg press horizontal</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/machine-horizontal-leg-press">Ver</a>
            </div>
            <table class="sets-tbl">
              <tr><th>Séries x Reps</th><th>RIR</th><th>Descanso</th></tr>
              <tr><td>3x12</td><td>3</td><td>90s</td></tr>
            </table>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['reps_spec'], '3x12')
        self.assertEqual(movement['rir_spec'], 'RIR 3')

    def test_flat_table_dash_rir_means_no_rir_not_a_literal_dash(self):
        html = _one_day('sex', 'Core', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Pallof press no cabo</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/cable-pallof-press">Ver</a>
            </div>
            <table class="sets-tbl">
              <tr><th>Séries x Reps</th><th>RIR</th><th>Descanso</th></tr>
              <tr><td>3x30-40s cada lado</td><td>-</td><td>-</td></tr>
            </table>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        self.assertEqual(days[0]['blocks'][0]['movements'][0]['rir_spec'], '')

    def test_biset_inline_maps_table_rows_to_movements_by_index(self):
        # juliana.html verbatim: gym-wiki aponta pra um exercicio DIFERENTE
        # do wiki-btn -- 1 unico `.ex`, 2 movimentos, mapeados por posicao
        # na sets-tbl (linha 1 -> wiki-btn, linha 2 -> gym-wiki).
        html = _one_day('qua', 'Core', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Prancha isométrica + Elevação de perna</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/forearm-plank">Ver</a>
            </div>
            <div class="gym-card">
              <div class="gym-summary"><strong>Prancha + Elevação (biset)</strong><div class="gym-reps">2× 45-60s → 2× 12-15</div></div>
              <a class="gym-wiki" href="https://musclewiki.com/exercise/laying-leg-raises">Ver</a>
            </div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps / Tempo</th><th>Intensidade / Nota</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>2×</td><td>45-60s (prancha)</td><td>Isometria</td></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>2×</td><td>12-15 (perna)</td><td>RIR 1</td></tr>
            </table></div>
          </div>
        ''')

        days, skipped = parse_legacy_html(html)

        self.assertEqual(skipped, [])
        movements = days[0]['blocks'][0]['movements']
        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[0]['movement_slug'], 'forearm-plank')
        self.assertEqual(movements[0]['reps_spec'], 'Top Set 2× 45-60s (prancha)')
        self.assertEqual(movements[0]['rir_spec'], 'Isometria')
        self.assertEqual(movements[1]['movement_slug'], 'laying-leg-raises')
        self.assertEqual(movements[1]['reps_spec'], 'Top Set 2× 12-15 (perna)')
        self.assertEqual(movements[1]['rir_spec'], 'RIR 1')

    def test_biset_wrapped_produces_two_movements_in_one_block(self):
        # milene.html verbatim: .biset-wrap com 2 `.ex` irmaos, cada um
        # autocontido com sua propria tabela de 1 linha.
        html = _one_day('qua', 'Glúteo', '''
          <div class="biset-wrap">
            <div class="biset-badge">BISET</div>
            <div class="ex">
              <div class="ex-top">
                <div class="ex-left"><div class="ex-name">Step up com halteres</div></div>
                <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-step-up">Ver</a>
              </div>
              <div class="sets-tbl-wrap"><table class="sets-tbl">
                <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
                <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>10-12</td><td>RIR 1-2</td></tr>
              </table></div>
            </div>
            <div class="biset-connector">DIRETO para →</div>
            <div class="ex">
              <div class="ex-top">
                <div class="ex-left"><div class="ex-name">Afundo com halteres</div></div>
                <a class="wiki-btn" href="https://musclewiki.com/exercise/forward-lunges">Ver</a>
              </div>
              <div class="sets-tbl-wrap"><table class="sets-tbl">
                <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
                <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>10-12</td><td>RIR 1-2 · descanso após o biset</td></tr>
              </table></div>
            </div>
          </div>
        ''')

        days, skipped = parse_legacy_html(html)

        self.assertEqual(skipped, [])
        self.assertEqual(len(days[0]['blocks']), 1)
        movements = days[0]['blocks'][0]['movements']
        self.assertEqual([m['movement_slug'] for m in movements], ['dumbbell-step-up', 'forward-lunges'])

    def test_or_alternative_inside_biset_wrap_is_excluded_and_reported(self):
        # milene.html verbatim: o "OU" e o exercicio alternativo ficam
        # DENTRO do proprio .biset-wrap -- schema nao modela escolha entre
        # exercicios, entao o 3o `.ex` precisa ser excluido do payload
        # (nunca virar um 3o movimento do bloco).
        html = _one_day('qua', 'Glúteo', '''
          <div class="biset-wrap">
            <div class="ex">
              <div class="ex-top"><div class="ex-left"><div class="ex-name">Step up com halteres</div></div>
                <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-step-up">Ver</a></div>
              <div class="sets-tbl-wrap"><table class="sets-tbl">
                <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
                <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>10-12</td><td>RIR 1-2</td></tr>
              </table></div>
            </div>
            <div class="biset-connector">DIRETO para →</div>
            <div class="ex">
              <div class="ex-top"><div class="ex-left"><div class="ex-name">Afundo com halteres</div></div>
                <a class="wiki-btn" href="https://musclewiki.com/exercise/forward-lunges">Ver</a></div>
              <div class="sets-tbl-wrap"><table class="sets-tbl">
                <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
                <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>10-12</td><td>RIR 1-2</td></tr>
              </table></div>
            </div>
            <div class="or-divider">OU (substituir o biset inteiro por)</div>
            <div class="ex">
              <div class="ex-top"><div class="ex-left"><div class="ex-name">Hip thrust com barra</div></div>
                <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-hip-thrust">Ver</a></div>
              <div class="sets-tbl-wrap"><table class="sets-tbl">
                <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
                <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>10-12</td><td>RIR 1-2</td></tr>
              </table></div>
            </div>
          </div>
        ''')

        days, skipped = parse_legacy_html(html)

        movements = days[0]['blocks'][0]['movements']
        self.assertEqual(len(movements), 2)
        self.assertNotIn('barbell-hip-thrust', [m['movement_slug'] for m in movements])
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].name, 'Hip thrust com barra')

    def test_or_alternative_at_session_level_is_excluded_and_reported(self):
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Supino reto com barra</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-bench-press">Ver</a></div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>8-10</td><td>RIR 2</td></tr>
            </table></div>
          </div>
          <div class="or-divider">OU</div>
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Supino com halteres</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-bench-press">Ver</a></div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>8-10</td><td>RIR 2</td></tr>
            </table></div>
          </div>
        ''')

        days, skipped = parse_legacy_html(html)

        self.assertEqual(len(days[0]['blocks']), 1)
        self.assertEqual(days[0]['blocks'][0]['movements'][0]['movement_slug'], 'barbell-bench-press')
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].name, 'Supino com halteres')

    def test_day_order_matches_document_order_not_alphabetical(self):
        # juliana.html: a primeira sessao do documento e' "ter", nao "seg" —
        # a ordem de `days` tem que ser a de APARICAO no HTML, nunca
        # reordenada (e' isso que o teste de Categoria 3 dela verifica).
        html = (
            _one_day('ter', 'Terça', '<div class="ex"><div class="ex-top"><div class="ex-left"><div class="ex-name">X</div></div></div><div class="ex-note">n</div></div>')
            + _one_day('seg', 'Segunda', '<div class="ex"><div class="ex-top"><div class="ex-left"><div class="ex-name">Y</div></div></div><div class="ex-note">n</div></div>')
        )

        days, _ = parse_legacy_html(html)

        self.assertEqual([d['day_id'] for d in days], ['ter', 'seg'])


class ParseNameAndVariationTests(SimpleTestCase):
    """`ex.name` (nome em portugues escrito pelo treinador) sempre foi
    capturado — so' era usado como fallback de slug, nunca guardado pra
    exibicao (aluno via o slug do MuscleWiki em ingles humanizado). `.ex-var`
    (variacao sugerida) nunca foi capturado. Os dois sao aditivos ao
    schema (name/variations), achados reais pedidos pelo Renan."""

    def test_captures_portuguese_name_alongside_english_slug(self):
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Supino reto com barra</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-bench-press">Ver</a>
            </div>
            <div class="ex-note">n</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['movement_slug'], 'barbell-bench-press')
        self.assertEqual(movement['name'], 'Supino reto com barra')

    def test_captures_single_variation_label_and_url(self):
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left">
                <div class="ex-name">Supino reto com barra</div>
                <div class="ex-var"><span class="var-lbl">Variação:</span><a class="var-link" href="https://musclewiki.com/exercise/dumbbell-bench-press" target="_blank" rel="noopener">Supino com halteres</a></div>
              </div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-bench-press">Ver</a>
            </div>
            <div class="ex-note">n</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['variations'], [
            {'label': 'Supino com halteres', 'reference_url': 'https://musclewiki.com/exercise/dumbbell-bench-press'},
        ])

    def test_captures_multiple_variations_on_same_exercise(self):
        # Recorte fiel de bruno.html (agachamento livre — 2 variacoes
        # sugeridas no mesmo .ex-var, unico caso real dos 10 clientes).
        html = _one_day('ter', 'Pernas', '''
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left">
                <div class="ex-name">Agachamento livre</div>
                <div class="ex-var"><span class="var-lbl">Variação:</span><a class="var-link" href="https://musclewiki.com/exercise/machine-hack-squat" target="_blank" rel="noopener">Hack squat</a><a class="var-link" href="https://musclewiki.com/exercise/machine-leg-press" target="_blank" rel="noopener">Leg press 45°</a></div>
              </div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-squat">Ver</a>
            </div>
            <div class="ex-note">n</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(len(movement['variations']), 2)
        self.assertEqual(movement['variations'][0]['label'], 'Hack squat')
        self.assertEqual(movement['variations'][1]['label'], 'Leg press 45°')

    def test_exercise_without_variation_has_no_variations_key(self):
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Supino reto com barra</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-bench-press">Ver</a></div>
            <div class="ex-note">n</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertNotIn('variations', movement)

    def test_exercise_without_wiki_btn_still_captures_name(self):
        # Cardio solto (sem link) tambem tem nome em portugues, ex.:
        # "🏃 Corrida — 10 min" (bruno.html) — so' nao tem reference_url.
        html = _one_day('seg', 'Peito', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">🏃 Corrida — 10 min</div></div></div>
            <div class="ex-note">10 min a 10-12 km/h.</div>
          </div>
        ''')

        days, _ = parse_legacy_html(html)

        movement = days[0]['blocks'][0]['movements'][0]
        self.assertEqual(movement['name'], '🏃 Corrida — 10 min')
        self.assertIsNone(movement['reference_url'])


class BuildProgramPayloadFromHtmlTests(SimpleTestCase):
    def test_returns_schema_valid_payload_with_business_metadata_injected(self):
        html = _one_day('seg', 'Segunda', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento livre</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-squat">Ver</a></div>
            <div class="sets-tbl-wrap"><table class="sets-tbl">
              <tr><th>Tipo</th><th>Séries</th><th>Reps</th><th>Nota</th></tr>
              <tr><td><span class="st st-t">Top Set</span></td><td>3×</td><td>8-10</td><td>RIR 2</td></tr>
            </table></div>
          </div>
        ''')

        payload, skipped = build_program_payload_from_html(
            html=html,
            program_id='exemplo-legado-v1',
            program_label='Treino Exemplo',
            started_on='2026-01-05',
            weeks=4,
            accent_variant='F',
        )

        self.assertEqual(skipped, [])
        self.assertEqual(schema.validate_payload(payload), [])
        self.assertEqual(payload['program_id'], 'exemplo-legado-v1')
        self.assertEqual(payload['accent_variant'], 'F')
        self.assertEqual(payload['weeks'], 4)

    def test_metadata_is_never_guessed_from_html_content(self):
        # Mesmo que o HTML mencione "Semana 8" em algum lugar, `weeks` do
        # payload final e' sempre o que foi passado por fora -- decisao de
        # negocio, nao dado extraivel (ver docstring do modulo parser.py).
        html = _one_day('seg', 'Semana 8 de progressão', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento livre</div></div></div>
            <div class="ex-note">n</div>
          </div>
        ''')

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(payload['weeks'], 4)


class ParseCardioTabTests(SimpleTestCase):
    """Recortes fieis de juliana.html (formato de aba dedicada de cardio
    semanal — ver docstring de _CardioTabParser sobre por que so' esse
    formato, nao o cardio embutido por dia de franciele/milene)."""

    def test_extracts_title_badge_details_and_note(self):
        html = '''
        <div id="tab-cardio" style="display:none">
          <div class="cardio-week">
            <div class="cw-item"><div class="cw-day">Quarta</div><div class="cw-type">🟢 LISS</div></div>
          </div>
          <div class="c-card">
            <div class="c-head">LISS leve <span class="km-badge">Quarta · pós-treino</span></div>
            <div class="c-row"><span class="c-lbl">Duração</span><span>20 min contínuos</span></div>
            <div class="c-row"><span class="c-lbl">Modalidade</span><span>Esteira inclinada, bike ou elíptico</span></div>
            <div class="c-note">Feito depois do Superior A — pernas ficam de fora.</div>
          </div>
        </div>
        '''

        result = parse_cardio_tab(html)

        self.assertEqual(len(result['sessions']), 1)
        session = result['sessions'][0]
        self.assertEqual(session['title'], 'LISS leve')
        self.assertEqual(session['badge'], 'Quarta · pós-treino')
        self.assertEqual(session['details'], [
            {'label': 'Duração', 'value': '20 min contínuos'},
            {'label': 'Modalidade', 'value': 'Esteira inclinada, bike ou elíptico'},
        ])
        self.assertEqual(session['note'], 'Feito depois do Superior A — pernas ficam de fora.')

    def test_multiple_sessions_are_all_captured_in_order(self):
        html = '''
        <div id="tab-cardio">
          <div class="c-card">
            <div class="c-head">LISS leve <span class="km-badge">Quarta</span></div>
          </div>
          <div class="c-card">
            <div class="c-head">Moderado <span class="km-badge">Sexta</span></div>
          </div>
        </div>
        '''

        result = parse_cardio_tab(html)

        self.assertEqual([s['title'] for s in result['sessions']], ['LISS leve', 'Moderado'])

    def test_no_cardio_tab_returns_none(self):
        html = '<div id="tab-treino"><div class="ex"></div></div>'

        self.assertIsNone(parse_cardio_tab(html))

    def test_cardio_tab_without_any_card_returns_none(self):
        html = '<div id="tab-cardio"><p>Sem sessoes ainda.</p></div>'

        self.assertIsNone(parse_cardio_tab(html))

    def test_session_without_badge_still_captures_title(self):
        html = '''
        <div id="tab-cardio">
          <div class="c-card">
            <div class="c-head">Corrida livre</div>
            <div class="c-note">Qualquer dia da semana.</div>
          </div>
        </div>
        '''

        result = parse_cardio_tab(html)

        self.assertEqual(result['sessions'][0]['title'], 'Corrida livre')
        self.assertEqual(result['sessions'][0]['badge'], '')


class ParsePeriodizationTabTests(SimpleTestCase):
    """Recortes fieis de juliana.html (grafico + tabela semanal + tabela de
    volume por grupo muscular)."""

    def test_extracts_weeks_table_ignoring_header_row(self):
        html = '''
        <div id="tab-period">
          <div class="period-tbl">
            <table>
              <tr><th>Semana</th><th>Foco</th><th>Reps (top sets)</th><th>Diretriz de carga</th></tr>
              <tr><td>Semana 1</td><td>Adaptação</td><td>Teto da faixa</td><td>Carga base</td></tr>
              <tr><td>Semana 2</td><td>Volume</td><td>Meio da faixa</td><td>+2,5 kg vs. Semana 1</td></tr>
            </table>
          </div>
        </div>
        '''

        result = parse_periodization_tab(html)

        self.assertEqual(result['weeks_table'], [
            {'week': 'Semana 1', 'focus': 'Adaptação', 'reps': 'Teto da faixa', 'guidance': 'Carga base'},
            {'week': 'Semana 2', 'focus': 'Volume', 'reps': 'Meio da faixa', 'guidance': '+2,5 kg vs. Semana 1'},
        ])

    def test_extracts_volume_table_and_note(self):
        html = '''
        <div id="tab-period">
          <div class="period-tbl">
            <table>
              <tr><th>Semana</th><th>Foco</th><th>Reps</th><th>Diretriz</th></tr>
              <tr><td>Semana 1</td><td>Adaptação</td><td>Teto</td><td>Base</td></tr>
            </table>
          </div>
          <div class="vnote">Respeite o deload da última semana.</div>
          <table class="vol-tbl">
            <tr><th>Grupo muscular</th><th>Séries/sem</th><th>Frequência</th><th>Onde</th></tr>
            <tr><td>Quadríceps</td><td>~22</td><td>2×/sem</td><td>Terça + Quinta</td></tr>
          </table>
        </div>
        '''

        result = parse_periodization_tab(html)

        self.assertEqual(result['note'], 'Respeite o deload da última semana.')
        self.assertEqual(result['volume_table'], [
            {'muscle_group': 'Quadríceps', 'sets_per_week': '~22', 'frequency': '2×/sem', 'where': 'Terça + Quinta'},
        ])

    def test_extracts_chart_json_from_embedded_script(self):
        html = '''
        <div id="tab-period">
          <div class="period-tbl">
            <table><tr><th>H</th></tr><tr><td>Semana 1</td><td>x</td><td>x</td><td>x</td></tr></table>
          </div>
        </div>
        <script type="application/json" id="period-chart-data">
        [{"label": "S1", "focus": "Adaptação", "reps": "Teto", "color": "#FB7185", "bg": "#FFF1F2", "fg": "#BE123C", "h": 65}]
        </script>
        '''

        result = parse_periodization_tab(html)

        self.assertEqual(result['chart'], [
            {'label': 'S1', 'focus': 'Adaptação', 'reps': 'Teto', 'color': '#FB7185', 'bg': '#FFF1F2', 'fg': '#BE123C', 'h': 65},
        ])

    def test_missing_chart_script_yields_empty_chart_list(self):
        html = '''
        <div id="tab-period">
          <div class="period-tbl">
            <table><tr><th>H</th></tr><tr><td>Semana 1</td><td>x</td><td>x</td><td>x</td></tr></table>
          </div>
        </div>
        '''

        result = parse_periodization_tab(html)

        self.assertEqual(result['chart'], [])

    def test_no_period_tab_returns_none(self):
        html = '<div id="tab-treino"><div class="ex"></div></div>'

        self.assertIsNone(parse_periodization_tab(html))

    def test_period_tab_without_weeks_table_returns_none(self):
        html = '<div id="tab-period"><p>Sem periodizacao ainda.</p></div>'

        self.assertIsNone(parse_periodization_tab(html))


class BuildProgramPayloadFromHtmlCardioPeriodizationTests(SimpleTestCase):
    """`build_program_payload_from_html` inclui cardio/periodization no
    payload final so' quando o HTML tem as abas -- aditivo, nunca quebra o
    contrato existente pros clientes sem elas."""

    def test_payload_includes_cardio_and_periodization_when_present(self):
        html = _one_day('seg', 'Segunda', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento livre</div></div></div>
            <div class="ex-note">n</div>
          </div>
        ''') + '''
        <div id="tab-cardio">
          <div class="c-card"><div class="c-head">LISS leve <span class="km-badge">Quarta</span></div></div>
        </div>
        <div id="tab-period">
          <div class="period-tbl">
            <table><tr><th>H</th></tr><tr><td>Semana 1</td><td>Adaptação</td><td>Teto</td><td>Base</td></tr></table>
          </div>
        </div>
        '''

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(schema.validate_payload(payload), [])
        self.assertEqual(len(payload['cardio']['sessions']), 1)
        self.assertEqual(len(payload['periodization']['weeks_table']), 1)

    def test_payload_omits_cardio_and_periodization_when_absent(self):
        html = _one_day('seg', 'Segunda', '''
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento livre</div></div></div>
            <div class="ex-note">n</div>
          </div>
        ''')

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(schema.validate_payload(payload), [])
        self.assertNotIn('cardio', payload)
        self.assertNotIn('periodization', payload)


class ParseEmbeddedStageContentTests(SimpleTestCase):
    """Recortes fieis de franciele.html (sem aba dedicada #tab-cardio —
    mobilidade/ativacao/coordenacao e cardio vem embutidos por dia, sob um
    `.stage-title` "Etapa N - <nome>", cada etapa com seu proprio
    `.c-card`). Ver docstring de _EmbeddedStageParser."""

    def _franciele_terca(self) -> str:
        return '''
        <div id="ter" class="session">
          <div class="sess-hdr"><div><div class="sess-title">Terça - Superior A</div></div></div>

          <div class="stage-title">Etapa 1 - Mobilidade e Postura (10-12 min)</div>
          <div class="c-card">
            <div class="c-row"><span class="c-lbl">Torácica</span><span>Mobilidade em quadrupedia (thread the needle) - 2x8 cada lado</span></div>
            <div class="c-row"><span class="c-lbl">Escapular</span><span>Wall slide - 2x10</span></div>
            <div class="c-row"><span class="c-lbl">Escapular</span><span>Band pull-apart - 2x15</span></div>
            <div class="c-row"><span class="c-lbl">Core</span><span>Pallof press (anti-rotação) - 2x8 cada lado</span></div>
          </div>

          <div class="stage-title">Etapa 2 - Força</div>
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Supino reto (halteres ou máquina)</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-bench-press">Ver</a>
            </div>
            <table class="sets-tbl"><tr><td>3x10-12</td><td>3</td><td>90s</td></tr></table>
          </div>

          <div class="stage-title">Etapa 3 - Cardio</div>
          <div class="c-card">
            <div class="c-head"><span>Esteira, sem inclinação</span><span class="km-badge">15-20 min</span></div>
            <div class="c-row"><span class="c-lbl">Progressão</span><span>Ver fase atual na aba Periodização</span></div>
            <div class="c-note">Feito depois do treino de força, nunca antes.</div>
          </div>
        </div>
        '''

    def test_mobility_stage_becomes_auxiliary_movements_for_that_day(self):
        auxiliary_by_day, _ = parse_embedded_stage_content(self._franciele_terca())

        self.assertIn('ter', auxiliary_by_day)
        blocks = auxiliary_by_day['ter']
        self.assertEqual(len(blocks), 1)
        movements = blocks[0]['movements']
        self.assertEqual(len(movements), 4)
        self.assertEqual(movements[0]['name'], 'Mobilidade em quadrupedia (thread the needle)')
        self.assertEqual(movements[0]['reps_spec'], '2x8 cada lado')
        self.assertEqual(movements[0]['movement_slug'], 'mobilidade-em-quadrupedia-thread-the-needle')
        self.assertFalse(movements[0]['is_tracked'])
        self.assertEqual(movements[0]['load_type'], 'free')
        self.assertIsNone(movements[0]['reference_url'])

    def test_repeated_c_lbl_in_same_day_does_not_collide_slugs(self):
        # "Escapular" aparece 2x no mesmo dia com descricoes diferentes --
        # o slug tem que vir da descricao, nunca do label.
        auxiliary_by_day, _ = parse_embedded_stage_content(self._franciele_terca())

        slugs = [m['movement_slug'] for m in auxiliary_by_day['ter'][0]['movements']]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_cardio_stage_becomes_cardio_session(self):
        _, cardio_sessions = parse_embedded_stage_content(self._franciele_terca())

        self.assertEqual(len(cardio_sessions), 1)
        session = cardio_sessions[0]
        self.assertEqual(session['title'], 'Esteira, sem inclinação')
        self.assertEqual(session['badge'], '15-20 min')
        self.assertEqual(session['details'], [{'label': 'Progressão', 'value': 'Ver fase atual na aba Periodização'}])
        self.assertEqual(session['note'], 'Feito depois do treino de força, nunca antes.')

    def test_identical_cardio_card_repeated_across_days_is_deduplicated(self):
        html = self._franciele_terca() + self._franciele_terca().replace('id="ter"', 'id="qui"')

        _, cardio_sessions = parse_embedded_stage_content(html)

        self.assertEqual(len(cardio_sessions), 1)

    def test_force_stage_never_produces_auxiliary_movements(self):
        # "Etapa 2 - Forca" usa `.ex`, nunca `.c-card` -- garante que o
        # parser novo nao tenta reclassificar exercicios de forca de
        # verdade como movimento auxiliar.
        html = '''
        <div id="seg" class="session">
          <div class="stage-title">Etapa 2 - Força</div>
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento livre</div></div></div>
          </div>
        </div>
        '''

        auxiliary_by_day, cardio_sessions = parse_embedded_stage_content(html)

        self.assertEqual(auxiliary_by_day, {})
        self.assertEqual(cardio_sessions, [])

    def test_cardio_card_without_any_stage_title_is_still_classified_as_cardio(self):
        # rafael.html nao tem `.stage-title` NENHUM -- o card de cardio vem
        # solto logo apos os `.ex`. Classificacao tem que vir do `.c-head`
        # (presenca de titulo+badge), nunca de texto de estagio.
        html = '''
        <div id="seg" class="session">
          <div class="ex">
            <div class="ex-top"><div class="ex-left"><div class="ex-name">Supino reto</div></div></div>
          </div>
          <div class="c-card">
            <div class="c-head"><span>LISS pós-treino</span><span class="km-badge">20-25 min</span></div>
            <div class="c-row"><span class="c-lbl">Modalidade</span><span>Bike ou esteira inclinada</span></div>
            <div class="c-note">Feito depois do treino de força.</div>
          </div>
        </div>
        '''

        auxiliary_by_day, cardio_sessions = parse_embedded_stage_content(html)

        self.assertEqual(len(cardio_sessions), 1)
        self.assertEqual(cardio_sessions[0]['title'], 'LISS pós-treino')
        self.assertNotIn('seg', auxiliary_by_day)

    def test_dedicated_cardio_tab_outside_any_session_is_ignored(self):
        # `.c-card` de uma aba dedicada (fora de `.session`) e' trabalho do
        # _CardioTabParser -- esta classe nunca deve pegar isso tambem
        # (duplicaria a sessao pros 5 clientes que ja tem aba dedicada).
        html = '''
        <div id="tab-cardio">
          <div class="c-card"><div class="c-head"><span>LISS leve</span><span class="km-badge">Quarta</span></div></div>
        </div>
        '''

        auxiliary_by_day, cardio_sessions = parse_embedded_stage_content(html)

        self.assertEqual(auxiliary_by_day, {})
        self.assertEqual(cardio_sessions, [])

    def test_day_without_any_c_card_is_absent_from_auxiliary_dict(self):
        html = _one_day('seg', 'Segunda', '''
          <div class="ex"><div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento</div></div></div></div>
        ''')

        auxiliary_by_day, cardio_sessions = parse_embedded_stage_content(html)

        self.assertEqual(auxiliary_by_day, {})
        self.assertEqual(cardio_sessions, [])

    def test_row_without_dash_separator_falls_back_to_whole_text_as_name(self):
        html = '''
        <div id="seg" class="session">
          <div class="stage-title">Etapa 1 - Mobilidade</div>
          <div class="c-card">
            <div class="c-row"><span class="c-lbl">Core</span><span>Prancha frontal</span></div>
          </div>
        </div>
        '''

        auxiliary_by_day, _ = parse_embedded_stage_content(html)

        movement = auxiliary_by_day['seg'][0]['movements'][0]
        self.assertEqual(movement['name'], 'Prancha frontal')
        self.assertEqual(movement['reps_spec'], '')


class BuildProgramPayloadFromHtmlEmbeddedStageTests(SimpleTestCase):
    """Integração: build_program_payload_from_html une os blocos auxiliares
    e o cardio embutido (franciele/rafael) no payload final, na mesma
    fatia que valida contra o schema."""

    def test_mobility_block_is_prepended_before_forca_block_same_order_as_html(self):
        html = '''
        <div id="ter" class="session">
          <div class="stage-title">Etapa 1 - Mobilidade</div>
          <div class="c-card">
            <div class="c-row"><span class="c-lbl">Core</span><span>Dead bug - 2x8 cada lado</span></div>
          </div>
          <div class="stage-title">Etapa 2 - Força</div>
          <div class="ex">
            <div class="ex-top">
              <div class="ex-left"><div class="ex-name">Supino reto</div></div>
              <a class="wiki-btn" href="https://musclewiki.com/exercise/dumbbell-bench-press">Ver</a>
            </div>
            <table class="sets-tbl"><tr><td>3x10-12</td><td>3</td><td>90s</td></tr></table>
          </div>
        </div>
        '''

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(schema.validate_payload(payload), [])
        blocks = payload['days'][0]['blocks']
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]['movements'][0]['name'], 'Dead bug')
        self.assertEqual(blocks[1]['movements'][0]['movement_slug'], 'dumbbell-bench-press')

    def test_embedded_cardio_only_used_when_no_dedicated_tab_exists(self):
        html = '''
        <div id="ter" class="session">
          <div class="stage-title">Etapa 2 - Força</div>
          <div class="ex"><div class="ex-top"><div class="ex-left"><div class="ex-name">Agachamento</div></div></div></div>
          <div class="stage-title">Etapa 3 - Cardio</div>
          <div class="c-card"><div class="c-head"><span>Esteira</span><span class="km-badge">15 min</span></div></div>
        </div>
        '''

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(schema.validate_payload(payload), [])
        self.assertEqual(payload['cardio']['sessions'][0]['title'], 'Esteira')

    def test_dedicated_cardio_tab_takes_priority_over_embedded(self):
        html = '''
        <div id="ter" class="session">
          <div class="stage-title">Etapa 3 - Cardio</div>
          <div class="c-card"><div class="c-head"><span>Esteira embutida</span></div></div>
        </div>
        <div id="tab-cardio">
          <div class="c-card"><div class="c-head"><span>LISS dedicado</span><span class="km-badge">Quarta</span></div></div>
        </div>
        '''

        payload, _ = build_program_payload_from_html(
            html=html, program_id='x', program_label='X', started_on='2026-01-05', weeks=4, accent_variant=None,
        )

        self.assertEqual(payload['cardio']['sessions'][0]['title'], 'LISS dedicado')
