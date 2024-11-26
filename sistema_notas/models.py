from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
# Obtém o modelo de usuário do Django
User = get_user_model()

# Modelo para representar uma Turma
class Turma(models.Model):
    nome = models.CharField(max_length=100)
    usuarios_permitidos = models.ManyToManyField(
        User,
        blank=True,
        related_name="turmas_permitidas",
        verbose_name="Usuários Permitidos"
    )

    def __str__(self):
        return self.nome

# Modelo para representar um Estudante
class Estudante(models.Model):
    """
    Representa um estudante associado a uma turma específica.
    """
    nome = models.CharField(max_length=100)  # Nome do estudante
    turma = models.ForeignKey(
        Turma, 
        on_delete=models.CASCADE, 
        related_name='estudantes'
    )  # Relaciona o estudante a uma turma

    def __str__(self):
        return self.nome

# Modelo para representar uma Disciplina
class Disciplina(models.Model):
    nome = models.CharField(max_length=100)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='disciplinas')
    usuarios_permitidos = models.ManyToManyField(User, blank=True, related_name='disciplinas_permitidas')

    def __str__(self):
        return f"{self.nome} - {self.turma.nome}"

# Signal para associar automaticamente os usuários da disciplina à turma
@receiver(m2m_changed, sender=Disciplina.usuarios_permitidos.through)
def sync_turma_usuarios(sender, instance, action, **kwargs):
    """
    Atualiza os usuários permitidos na turma quando alterados na disciplina.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        # Atualiza os usuários permitidos na turma da disciplina
        usuarios = instance.usuarios_permitidos.all()
        instance.turma.usuarios_permitidos.add(*usuarios)


# Modelo para representar uma Nota Final
class NotaFinal(models.Model):
    estudante = models.ForeignKey(
        'Estudante', 
        on_delete=models.CASCADE, 
        related_name='notas'
    )
    disciplina = models.ForeignKey(
        'Disciplina', 
        on_delete=models.CASCADE, 
        related_name='notas'
    )
    nota = models.FloatField()
    STATUS_CHOICES = [
        ('Aprovado', 'Aprovado'),
        ('Recuperação', 'Recuperação'),
        ('Desistente', 'Desistente'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        blank=True
    )
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notas_modificadas'
    )
    modified_at = models.DateTimeField(auto_now=True)  # Atualizado automaticamente quando salvo

    class Meta:
        unique_together = ('estudante', 'disciplina')
        verbose_name = 'Nota Final'
        verbose_name_plural = 'Notas Finais'

    def save(self, *args, **kwargs):
        if self.nota == -1:
            self.status = 'Desistente'
        elif self.nota < 5:
            self.status = 'Recuperação'
        else:
            self.status = 'Aprovado'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estudante.nome} - {self.disciplina.nome}: {self.nota} ({self.status})"

class NotaFinalAudit(models.Model):
    nota_final = models.ForeignKey(
        'NotaFinal',
        on_delete=models.CASCADE,
        related_name='auditoria',
        verbose_name='Nota Final'
    )
    nota_anterior = models.FloatField(null=True, blank=True, verbose_name='Nota Anterior')
    nota_atual = models.FloatField(verbose_name='Nota Atual')
    status = models.CharField(max_length=20, verbose_name='Status Atual')  # Este campo
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="notafinal_audits"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data de Modificação')