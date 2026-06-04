from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_students_page_uses_command_kpi_contract_classes():
    kpi_panel = _read("templates/catalog/includes/student/student_interactive_kpis.html")
    kpi_card = _read("templates/catalog/includes/student/student_metric_card.html")

    assert "kpi-command-overview" in kpi_panel
    assert "kpi-command-grid" in kpi_panel
    assert "student-kpi-grid" in kpi_panel

    assert "kpi-command-card" in kpi_card
    assert "kpi-command-card-body" in kpi_card
    assert "kpi-command-icon-box" in kpi_card
    assert "kpi-command-card-label" in kpi_card
    assert "kpi-command-card-value" in kpi_card


def test_design_system_owns_command_kpi_surface_styles():
    cards_css = _read("static/css/design-system/components/cards.css")
    students_scene_css = _read("static/css/catalog/students/scene.css")
    students_responsive_css = _read("static/css/catalog/students/responsive.css")

    expected_selectors = [
        ".kpi-command-overview",
        ".kpi-command-grid",
        ".kpi-command-card",
        ".kpi-command-card-body",
        ".kpi-command-icon-box",
        ".kpi-command-card-label",
        ".kpi-command-card-value",
        'body[data-theme="dark"] .kpi-command-card',
    ]

    for selector in expected_selectors:
        assert selector in cards_css

    assert "student-kpi-" not in students_scene_css
    assert "student-kpi-" not in students_responsive_css


def test_students_hero_remains_visual_baseline_anchor():
    page_hero = _read("templates/includes/ui/layout/page_hero.html")

    assert "hero hero--system hero--command operation-hero" in page_hero
    assert 'data-panel="{{ hero.data_panel }}"' in page_hero
    assert "operation-hero-action-rail" in page_hero
