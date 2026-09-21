import json

from django import forms


class NutritionPlanEditorWidget(forms.Widget):
    template_name = 'admin/public_workouts/nutrition_plan_editor.html'

    class Media:
        css = {'all': ('css/public_workouts/nutrition_editor.css',)}
        js = ('js/public_workouts/nutrition_editor.js',)

    def format_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        if not value:
            return json.dumps({
                'schema_version': 1,
                'daily_targets': {'kcal': 0, 'protein_g': 0, 'carbs_g': 0, 'fat_g': 0},
                'meals': [],
            }, ensure_ascii=False)
        return value


__all__ = ['NutritionPlanEditorWidget']
