from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import NotaFinal, NotaFinalAudit
from .utils import get_current_user

@receiver(pre_save, sender=NotaFinal)
def registrar_historico(sender, instance, **kwargs):
    user = get_current_user()
    if instance.pk:  # Objeto existente
        nota_original = NotaFinal.objects.get(pk=instance.pk)
        if nota_original.nota != instance.nota:
            NotaFinalAudit.objects.create(
                nota_final=instance,
                modified_by=user,
                nota_anterior=nota_original.nota,
                nota_atual=instance.nota,
            )
            
