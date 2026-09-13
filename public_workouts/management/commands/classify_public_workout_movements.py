"""
COMANDO: classify_public_workout_movements

POR QUE EXISTE:
- `extract_movements_from_html` deixa `movement_pattern` em branco de
  proposito (ver docstring de public_workouts/models.py): classificar
  padrao biomecanico exige "saber treinar" (R.N do CORDA), nao e algo pra
  um script advinhar em silencio.
- Este comando preenche uma SUGESTAO — feita com apoio de especialista em
  biomecanica/fisiologia do exercicio, exercicio por exercicio, nao um
  palpite de texto livre — mas continua sendo sugestao, nao decisao final.
  `status` permanece como estava (`pending` para o extraido do HTML): o
  campo pendente sinaliza que nome, link E padrao ainda esperam sua
  revisao antes de a Onda A3 usar isso pra substituicao de exercicio.

USO:
    python manage.py classify_public_workout_movements
    python manage.py classify_public_workout_movements --dry-run

PONTOS CRITICOS:
- NUNCA sobrescreve um `movement_pattern` que ja tenha QUALQUER valor —
  inclusive se for diferente da sugestao daqui. Uma vez que alguem (voce)
  edita o campo, essa edicao vence para sempre; rodar este comando de novo
  so preenche o que ainda esta vazio.
- NAO muda `status`. Confirmar a classificacao (promover pending -> active)
  e acao separada, sua — este comando so sugere o padrao, nunca aprova.
- Slug e a chave (vem do path da URL do MuscleWiki, extraido por
  extract_movements_from_html) — se um slug daqui nao existir no banco
  ainda (ex.: rodou antes do extrator), o comando avisa e pula, nunca cria
  linha nova.

TAXONOMIA (20 padroes fechados, pensados pra substituicao de exercicio por
padrao equivalente — D.2 do CORDA: "movement_pattern agrupa o que"):
  squat, hip-hinge, lunge-unilateral                         (inferior, composto)
  horizontal-push, vertical-push, horizontal-pull, vertical-pull  (superior, composto)
  knee-extension, knee-flexion, hip-abduction, hip-adduction,
  back-extension, elbow-flexion, elbow-extension, chest-fly,
  lateral-raise, rear-delt-fly, shrug, calf-raise              (isolamento)
  core-flexion, core-rotation, core-isometric                  (core)
Composto vs isolamento seguiu a qualificacao que o proprio HTML de origem
ja trazia ("Compound"/"Composto" vs "Isolamento") quando presente — reflete
a intencao de programacao de quem escreveu o treino, mais confiavel que
inferir por conta articular pura.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from public_workouts.models import PublicWorkoutMovement

# Sugestao de classificacao (nao autoritativa — ver docstring do modulo).
# So o slug muda de significado; se o MuscleWiki trocar de exercicio por
# baixo do slug (nao deveria), revisar aqui.
MOVEMENT_PATTERNS: dict[str, str] = {
    # Membro inferior — compostos
    'barbell-squat': 'squat',
    'machine-horizontal-leg-press': 'squat',
    'machine-leg-press': 'squat',
    'dumbbell-goblet-squat': 'squat',
    'machine-hack-squat': 'squat',
    'dumbbell-sumo-squat': 'squat',
    'barbell-romanian-deadlift': 'hip-hinge',
    'dumbbell-romanian-deadlift': 'hip-hinge',
    'barbell-hip-thrust': 'hip-hinge',
    'band-glute-kickback': 'hip-hinge',
    'barbell-sumo-deadlift': 'hip-hinge',
    'dumbbell-bulgarian-split-squat': 'lunge-unilateral',
    'dumbbell-forward-lunge': 'lunge-unilateral',
    'dumbbell-reverse-lunge': 'lunge-unilateral',
    'smith-machine-reverse-lunge': 'lunge-unilateral',
    'lunge-walking': 'lunge-unilateral',
    'dumbbell-step-up': 'lunge-unilateral',
    'forward-lunges': 'lunge-unilateral',
    # Tronco superior — compostos
    'barbell-bench-press': 'horizontal-push',
    'dumbbell-incline-bench-press': 'horizontal-push',
    'dumbbell-bench-press': 'horizontal-push',
    'machine-chest-press': 'horizontal-push',
    'dumbbell-overhead-press': 'vertical-push',
    'dumbbell-seated-overhead-press': 'vertical-push',
    'machine-overhand-overhead-press': 'vertical-push',
    'barbell-overhead-press': 'vertical-push',
    'machine-pulldown': 'vertical-pull',
    'barbell-bent-over-row': 'horizontal-pull',
    'dumbbell-single-arm-row': 'horizontal-pull',
    'machine-chest-supported-t-bar-row': 'horizontal-pull',
    'machine-seated-cable-row': 'horizontal-pull',
    'dumbbell-row-bilateral': 'horizontal-pull',
    # Isolamento
    'machine-leg-extension': 'knee-extension',
    'machine-hamstring-curl': 'knee-flexion',
    'machine-seated-leg-curl': 'knee-flexion',
    'nordic-hamstring-curl': 'knee-flexion',
    'machine-lying-leg-curl': 'knee-flexion',
    'machine-hip-abduction': 'hip-abduction',
    'cable-hip-abduction': 'hip-abduction',
    'side-walks-resisted': 'hip-abduction',
    'machine-hip-adduction': 'hip-adduction',
    'machine-45-degree-back-extension': 'back-extension',
    'barbell-curl': 'elbow-flexion',
    'cable-bar-curl': 'elbow-flexion',
    'dumbbell-hammer-curl': 'elbow-flexion',
    'dumbbell-seated-hammer-curl': 'elbow-flexion',
    'dumbbell-preacher-curl': 'elbow-flexion',
    'dumbbell-curl': 'elbow-flexion',
    'cable-rope-pushdown': 'elbow-extension',
    'dumbbell-skullcrusher': 'elbow-extension',
    'dumbbell-overhead-tricep-extension': 'elbow-extension',
    'cable-rope-skullcrusher': 'elbow-extension',
    'dumbbell-seated-overhead-tricep-extension': 'elbow-extension',
    'dumbbell-tricep-kickback': 'elbow-extension',
    'cable-pec-fly': 'chest-fly',
    'cable-incline-chest-fly': 'chest-fly',
    'machine-bent-arm-pec-fly': 'chest-fly',
    'cable-low-single-arm-lateral-raise': 'lateral-raise',
    'dumbbell-lateral-raise': 'lateral-raise',
    'cable-rope-mid-lateral-raise': 'lateral-raise',
    'cable-low-bilateral-lateral-raise': 'lateral-raise',
    'cable-single-arm-face-pull': 'rear-delt-fly',
    'machine-face-pulls': 'rear-delt-fly',
    'dumbbell-rear-delt-fly': 'rear-delt-fly',
    'cable-bar-face-pull': 'rear-delt-fly',
    'dumbbell-shrug': 'shrug',
    'machine-standing-calf-raises': 'calf-raise',
    'machine-seated-calf-raises': 'calf-raise',
    'dumbbell-calf-raise': 'calf-raise',
    'dumbbell-seated-calf-raise': 'calf-raise',
    'smith-machine-calf-raise': 'calf-raise',
    # Core
    'machine-crunch': 'core-flexion',
    'laying-leg-raises': 'core-flexion',
    'toes-to-bar': 'core-flexion',
    'cable-rope-kneeling-crunch': 'core-flexion',
    'hanging-knee-raises': 'core-flexion',
    'barbell-situp': 'core-flexion',
    'dumbbell-russian-twist': 'core-rotation',
    'bicycle-crunch': 'core-rotation',
    'cable-pallof-press': 'core-isometric',
    'dead-bug': 'core-isometric',
    'forearm-plank': 'core-isometric',
}


class Command(BaseCommand):
    help = 'Sugere movement_pattern para PublicWorkoutMovement (nao muda status; nunca sobrescreve valor ja preenchido).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Imprime sem salvar no banco.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        movements_by_slug = {
            m.slug: m for m in PublicWorkoutMovement.objects.filter(slug__in=MOVEMENT_PATTERNS.keys())
        }
        missing_slugs = MOVEMENT_PATTERNS.keys() - movements_by_slug.keys()

        classified, already_set, skipped = 0, 0, 0
        for slug, suggested_pattern in MOVEMENT_PATTERNS.items():
            movement = movements_by_slug.get(slug)
            if movement is None:
                continue

            if movement.movement_pattern:
                if movement.movement_pattern != suggested_pattern:
                    self.stdout.write(
                        f'  [{slug}] ja tem movement_pattern={movement.movement_pattern!r} '
                        f'(sugestao seria {suggested_pattern!r}) — mantido, nao sobrescrevo'
                    )
                already_set += 1
                continue

            if dry_run:
                self.stdout.write(f'  [{slug}] -> {suggested_pattern}')
                classified += 1
                continue

            movement.movement_pattern = suggested_pattern
            movement.save(update_fields=['movement_pattern', 'updated_at'])
            classified += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN — {classified} receberiam sugestao, nenhum salvo.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'movement_pattern sugerido para {classified} movimento(s); '
                f'{already_set} ja tinham valor (preservado).'
            ))

        if missing_slugs:
            self.stdout.write(self.style.WARNING(
                f'{len(missing_slugs)} slug(s) classificado(s) aqui nao existem em PublicWorkoutMovement ainda '
                f'(rode extract_movements_from_html primeiro): {sorted(missing_slugs)}'
            ))
