"""Catálogo estático legado da Curva; sem imports de views, serviços ou ORM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicWorkoutAccent:
    """Rampa de accent do aluno — o UNICO eixo legitimo de branding.

    Todo o resto dos tokens (neutros, raio, sombra, badges de serie) e
    compartilhado. Os arquivos divergem no NOME da familia (--accent nos
    5 modernos, --amber na milene, --blue na giovanna) mas nao no papel.
    """

    base: str
    bg: str
    border: str
    light: str
    dark: str


@dataclass(frozen=True)
class PublicWorkoutPlan:
    """Configuracao de um treino publico.

    CONGELADO — mexer aqui causa dano silencioso:
    - `slug` esta em links ja distribuidos aos alunos (ver public_urls.py).
    - `store_key` e o namespace do localStorage: trocar apaga o historico
      de carga que o aluno digitou, sem aviso e sem backup.
    - `title` alimenta o manifest e `short_name` e derivado dele.
    """

    slug: str
    title: str
    theme_color: str
    background_color: str
    template_file: str
    accent: PublicWorkoutAccent
    tabs: tuple[tuple[str, str], ...]
    tracker_weeks: int = 0
    store_key: str | None = None
    # Constantes do aluno usadas pela aba Avaliacoes (public_workouts app)
    # para estimar %gordura (formula US Navy) e classificar RCQ — nao mudam
    # entre avaliacoes, por isso vivem na config do plano, nao no banco.
    # None desativa BF%/RCQ no relatorio (so IMC e circunferencias aparecem).
    assessment_sex: str | None = None
    height_cm: float | None = None

    @property
    def short_name(self) -> str:
        # Derivacao preservada: o teste do manifest assere 'Juliana'.
        return self.title.replace('Treino ', '')[:12]

    @property
    def manifest_url(self) -> str:
        return f'/renan/{self.slug}/manifest.webmanifest'


_TAB_TREINO = ('treino', 'Treinos')
_TAB_CARDIO = ('cardio', 'Cardio')
_TAB_PERIOD = ('period', 'Periodização')
_TAB_AVALIACOES = ('avaliacoes', 'Avaliações')

PUBLIC_WORKOUT_LIBRARY: dict[str, PublicWorkoutPlan] = {
    plan.slug: plan
    for plan in (
        PublicWorkoutPlan(
            slug='juliana',
            title='Treino Juliana',
            theme_color='#0f172a',
            background_color='#f5efe4',
            template_file='juliana.html',
            accent=PublicWorkoutAccent('#E11D48', '#FFF1F2', '#FECDD3', '#FBD7DF', '#BE123C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='juliana_alves_v3',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='bruno',
            title='Treino Bruno',
            theme_color='#11203b',
            background_color='#f4efe6',
            template_file='bruno.html',
            accent=PublicWorkoutAccent('#EA580C', '#FFF7ED', '#FED7AA', '#FFEDD5', '#C2410C'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, ('nutri', 'Nutrição'), _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='bruno_cutting_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='milene',
            title='Treino Milene',
            theme_color='#1a1a1a',
            background_color='#fafaf7',
            template_file='milene.html',
            accent=PublicWorkoutAccent('#D97706', '#FFFBEB', '#FDE68A', '#FEF3C7', '#92400E'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='milene_geraldes_treino',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='giovanna',
            title='Treino Giovanna',
            theme_color='#172017',
            background_color='#f8faf7',
            template_file='giovanna.html',
            # A giovanna so declara 3 degraus (--blue/-bg/-border), e sao os
            # mesmos valores do henrique. Os dois faltantes vem dele.
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            # store_key novo: esta pagina nunca teve tracker, entao nao ha
            # historico anterior para preservar.
            store_key='giovanna_fontes_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='thaislima',
            title='Treino Thais Lima',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='thaislima.html',
            accent=PublicWorkoutAccent('#7C3AED', '#F5F3FF', '#DDD6FE', '#EDE9FE', '#5B21B6'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='thais_lima_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='john',
            title='Treino John',
            theme_color='#111111',
            background_color='#f6f5f2',
            template_file='john.html',
            accent=PublicWorkoutAccent('#0891B2', '#ECFEFF', '#A5F3FC', '#CFFAFE', '#0E7490'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=6,  # unico plano com mesociclo de 6 semanas
            store_key='john_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='henrique',
            title='Treino Henrique',
            theme_color='#141414',
            background_color='#f6f5f2',
            template_file='henrique.html',
            accent=PublicWorkoutAccent('#2563EB', '#EFF6FF', '#BFDBFE', '#DBEAFE', '#1D4ED8'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='henrique_santos_souza_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
        ),
        PublicWorkoutPlan(
            slug='johnespanha',
            title='Treino John Espanha',
            theme_color='#141414',
            background_color='#fdf2f8',
            template_file='johnespanha.html',
            accent=PublicWorkoutAccent('#DB2777', '#FDF2F8', '#FBCFE8', '#FCE7F3', '#BE185D'),
            tabs=(_TAB_TREINO, _TAB_CARDIO, _TAB_AVALIACOES),
            tracker_weeks=5,
            store_key='john_espanha_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            # NAO convertido para o design system compartilhado: chegou em
            # main (PR #170/#171) depois desta refatoracao, ainda no formato
            # monolitico antigo (CSS/JS proprios embutidos no arquivo). Os
            # campos acima entram na PUBLIC_WORKOUT_LIBRARY so para manter o
            # manifest/service-worker corretos; renderiza como pagina
            # autocontida, igual os outros 7 rendiam antes desta PR.
        ),
        PublicWorkoutPlan(
            slug='franciele',
            title='Treino Franciele',
            theme_color='#241b2e',
            background_color='#faf6f3',
            template_file='franciele.html',
            accent=PublicWorkoutAccent('#A21CAF', '#FDF4FF', '#F5D0FE', '#FAE8FF', '#86198F'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=4,
            store_key='franciele_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            assessment_sex='F',
            height_cm=173,
        ),
        PublicWorkoutPlan(
            slug='rafael',
            title='Treino Rafael',
            theme_color='#0e2933',
            background_color='#f4fbfc',
            template_file='rafael.html',
            accent=PublicWorkoutAccent('#0891B2', '#ECFEFF', '#A5F3FC', '#CFFAFE', '#0E7490'),
            tabs=(_TAB_TREINO, _TAB_PERIOD, _TAB_AVALIACOES),
            tracker_weeks=4,
            store_key='rafael_v1',  # gitleaks:allow — namespace de localStorage, nao segredo
            assessment_sex='M',
            height_cm=175,
        ),
    )
}
