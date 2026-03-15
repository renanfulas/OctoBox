"""
ARQUIVO: entrada publica dos presenters de tela do catalogo.

POR QUE ELE EXISTE:
- oferece um ponto canonico para a camada de montagem de payload visual do catalogo.
"""

from .class_grid_page import build_class_grid_page
from .finance_center_page import build_finance_center_page
from .membership_plan_page import build_membership_plan_page
from .student_directory_page import build_student_directory_page
from .student_form_page import build_student_form_page


__all__ = ['build_class_grid_page', 'build_finance_center_page', 'build_membership_plan_page', 'build_student_directory_page', 'build_student_form_page']