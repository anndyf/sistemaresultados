from django.core.management.base import BaseCommand
from sistema_notas.models import NotaFinal
from django.db.models import Count

class Command(BaseCommand):
    help = "Remove duplicatas de NotaFinal com base nos campos estudante e disciplina."

    def handle(self, *args, **kwargs):
        duplicates = (
            NotaFinal.objects.values('estudante', 'disciplina')
            .annotate(count_id=Count('id'))
            .filter(count_id__gt=1)
        )

        for duplicate in duplicates:
            estudante = duplicate['estudante']
            disciplina = duplicate['disciplina']
            
            # Busca duplicatas e exclui as mais recentes
            duplicates_to_delete = NotaFinal.objects.filter(
                estudante=estudante,
                disciplina=disciplina
            ).order_by('id')[1:]

            for duplicate in duplicates_to_delete:
                duplicate.delete()

        self