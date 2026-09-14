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
from public_workouts.parser import build_program_payload_from_html, parse_legacy_html


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
