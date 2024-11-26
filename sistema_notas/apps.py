from django.apps import AppConfig


class SistemaNotasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sistema_notas'
    verbose_name = "EduClass - CETEP/LNAB"
    
    def ready(self):
        import sistema_notas.signals  # Importa os signals