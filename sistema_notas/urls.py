from django.urls import path
from . import views
from .views import DisciplinaAutocomplete, EstudanteAutocomplete,lancar_notas_por_turma, redirecionar_ou_boas_vindas
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('turma/<int:turma_id>/status/', views.listar_status_turma, name='listar_status_turma'),
    path('carregar-disciplinas/', views.carregar_disciplinas, name='carregar_disciplinas'),
    path('admin/sistema_notas/upload-csv/', views.upload_csv, name='upload_csv'),
    path('carregar-disciplinas/', views.carregar_disciplinas, name='carregar_disciplinas'),
    path('disciplina-autocomplete/', DisciplinaAutocomplete.as_view(), name='disciplina-autocomplete'),
    path('estudante-autocomplete/', EstudanteAutocomplete.as_view(), name='estudante-autocomplete'),
    path('admin/sistema_notas/notafinal/lancar-notas-turma/', lancar_notas_por_turma, name='lancar_notas_turma'),
    path('relatorio-status-turma/<int:turma_id>/', views.relatorio_status_turma, name='relatorio_status_turma'),
    path('relatorio-status-turma/<int:turma_id>/pdf/', views.gerar_pdf_relatorio_turma, name='gerar_pdf_relatorio_turma'),
    path('boas-vindas-professor/', redirecionar_ou_boas_vindas, name='boas_vindas_professor'),
    path('carregar-disciplinas/', views.carregar_disciplinas, name='carregar_disciplinas'),
    

]
