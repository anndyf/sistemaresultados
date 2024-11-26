from django.contrib import admin
from django.http import HttpResponseForbidden
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django.contrib import messages
from django import forms
from django.utils.html import format_html
from django.contrib.admin.views.decorators import staff_member_required
from .models import Turma, Estudante, Disciplina, NotaFinal, NotaFinalAudit
from .views import upload_csv
from .forms import DisciplinaMultipleForm, NotaFinalForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

if User in admin.site._registry:
    del admin.site._registry[User]
    
class BulkUserCreationForm(forms.Form):
    """
    Formulário para criação de múltiplos usuários.
    """
    usuarios = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Digite no formato: nome,email\nExemplo:\nJoão,joao@example.com\nMaria,maria@example.com',
            'rows': 8,
            'cols': 40
        }),
        help_text="Digite cada usuário em uma linha no formato: nome,email",
    )
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        help_text="Selecione o grupo ao qual os usuários serão adicionados."
    )


class CustomUserAdmin(UserAdmin):
    """
    Extensão do admin de usuários para permitir criação em lote através de um botão.
    """
    change_list_template = "admin/criar_usuarios_em_lote_button.html"  # Template customizado

    def get_urls(self):
        """
        Adiciona uma URL personalizada para a funcionalidade de criação de usuários em lote.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                'criar-usuarios-em-lote/',
                self.admin_site.admin_view(self.criar_usuarios_em_lote_view),
                name='criar_usuarios_em_lote',
            ),
        ]
        return custom_urls + urls

    def criar_usuarios_em_lote_view(self, request):
        """
        View para criar usuários em lote e adicioná-los ao grupo selecionado.
        """
        if request.method == 'POST':
            form = BulkUserCreationForm(request.POST)
            if form.is_valid():
                usuarios_raw = form.cleaned_data['usuarios']
                grupo = form.cleaned_data['grupo']

                # Processa os usuários da entrada
                usuarios = [user.strip() for user in usuarios_raw.split('\n') if user.strip()]
                criados = []
                erros = []

                for usuario in usuarios:
                    try:
                        nome, email = usuario.split(',')
                        nome = nome.strip()
                        email = email.strip()

                        # Gera senha aleatória
                        senha = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

                        # Cria o usuário
                        user, created = User.objects.get_or_create(username=email, email=email)
                        if created:
                            user.set_password(senha)
                            user.first_name = nome
                            user.save()
                            user.groups.add(grupo)

                            # Verifica se o grupo é "Professores" e marca como membro da equipe
                            if grupo.name.lower() == 'professores':
                                user.is_staff = True  # Define automaticamente como membro da equipe
                                user.save()

                            # Envia o e-mail com a senha
                            self._enviar_email_senha(nome, email, senha)
                            criados.append(email)
                        else:
                            erros.append(f"O usuário '{email}' já existe.")
                    except ValueError:
                        erros.append(f"Formato inválido para '{usuario}'. Deve ser 'nome,email'.")

                # Exibe mensagens de sucesso e erro
                if criados:
                    messages.success(request, f"{len(criados)} usuários criados com sucesso.")
                if erros:
                    messages.warning(request, "\n".join(erros))
                return redirect('admin:auth_user_changelist')

        else:
            form = BulkUserCreationForm()

        return render(request, 'admin/criar_usuarios_em_lote.html', {
            'title': 'Criar Usuários em Lote',
            'form': form,
            'opts': self.model._meta,
        })

    def _enviar_email_senha(self, nome, email, senha):
        """
        Função auxiliar para enviar a senha gerada por e-mail.
        """
        try:
            assunto = "Bem-vindo ao Sistema - Credenciais de Acesso"
            mensagem = (
                f"Olá {nome},\n\n"
                f"Seu acesso ao sistema foi criado com sucesso.\n\n"
                f"Credenciais de acesso:\n"
                f"Usuário: {email}\n"
                f"Senha: {senha}\n\n"
                f"Por favor, altere sua senha assim que fizer login no sistema.\n\n"
                f"Atenciosamente,\nEquipe de Administração"
            )
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            raise Exception(f"Erro ao enviar e-mail para {email}: {e}")
        
class NotaFinalAuditAdmin(admin.ModelAdmin):
    """
    Admin para o modelo NotaFinalAudit, exibindo informações detalhadas de auditoria de notas.
    """
    list_display = ('nota_final', 'get_modified_by_name', 'nota_anterior', 'nota_atual', 'created_at')
    list_filter = ('modified_by', 'created_at')
    search_fields = ('nota_final__estudante__nome', 'modified_by__username')

    def get_modified_by_name(self, obj):
        """
        Retorna o nome completo do usuário que modificou a nota.
        """
        if obj.modified_by:
            # Retorna o nome completo ou username se o nome completo não existir
            return obj.modified_by.get_full_name() or obj.modified_by.username
        return "Usuário desconhecido"

    get_modified_by_name.short_description = "Modificado por "
# Formulário para selecionar a disciplina e lançar notas para os estudantes associados
class LancaNotaPorDisciplinaForm(forms.Form):
    """
    Formulário para permitir a seleção de uma disciplina e lançar notas associadas a ela.
    """
    disciplina = forms.ModelChoiceField(queryset=Disciplina.objects.all(), required=True, label="Disciplina")

# Inline para exibir e lançar notas dos estudantes em uma disciplina específica
class NotaFinalInline(admin.TabularInline):
    """
    Inline para exibir e editar notas diretamente na interface do admin.
    """
    model = NotaFinal
    extra = 0
    fields = ('estudante', 'nota', 'status')
    readonly_fields = ('estudante',)

# Configuração do admin para o modelo Estudante
class EstudanteAdmin(admin.ModelAdmin):
    """
    Configurações do admin para o modelo Estudante.
    """
    list_display = ('nome', 'turma')
    search_fields = ('nome',)
    ordering = ('nome',)
    list_filter = ('turma',)
    inlines = [NotaFinalInline]
    change_list_template = "admin/sistema_notas/estudante_change_list.html"

    def get_urls(self):
        """
        Adiciona uma URL customizada para upload de CSV.
        """
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv_view, name='upload-csv'),
        ]
        return custom_urls + urls

    @staff_member_required
    def upload_csv_view(self, request):
        """
        Permite o upload de arquivos CSV diretamente pelo admin.
        """
        return upload_csv(request)

# Inline para exibir estudantes em uma turma
class EstudanteInline(admin.TabularInline):
    """
    Inline para gerenciar estudantes diretamente dentro de uma turma.
    """
    model = Estudante
    extra = 0

# Configuração do admin para o modelo Turma

class TurmaAdmin(admin.ModelAdmin):
    """
    Configurações do admin para o modelo Turma.
    """
    list_display = ('nome', 'listar_professores', 'acoes')  # Incluímos listar_professores
    filter_horizontal = ('usuarios_permitidos',)
    ordering = ('nome',)
    inlines = [EstudanteInline]

    def listar_professores(self, obj):
        """
        Retorna uma lista formatada dos professores associados à turma.
        """
        professores = obj.usuarios_permitidos.all()  # Obtém todos os usuários permitidos
        if professores.exists():
            return format_html("<br>".join([prof.first_name for prof in professores]))
        return "Nenhum professor associado."

    listar_professores.short_description = "Professores Associados"

    def acoes(self, obj):
        """
        Retorna ações customizadas para cada turma, como gerar relatório.
        """
        url = reverse('relatorio_status_turma', args=[obj.id])
        return format_html('<a href="{}" class="button">Ver Relatório</a>', url)

    acoes.short_description = 'Ações'
# Configuração do admin para o modelo Disciplina

class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'turma')
    filter_horizontal = ('usuarios_permitidos',)
    search_fields = ('nome', 'turma__nome')
    list_filter = ('turma',)

    def get_form(self, request, obj=None, **kwargs):
        """
        Substitui o formulário padrão pelo DisciplinaMultipleForm.
        """
        if obj is None:  # Apenas para a criação, usa o DisciplinaMultipleForm
            kwargs['form'] = DisciplinaMultipleForm
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        Salva o modelo e associa usuários permitidos da disciplina à turma.
        """
        super().save_model(request, obj, form, change)
        self.associar_usuarios_com_turma(obj)

    def add_view(self, request, form_url='', extra_context=None):
        """
        Personaliza a exibição e processamento do formulário de criação.
        """
        if request.method == 'POST':
            form = DisciplinaMultipleForm(request.POST)
            if form.is_valid():
                nomes = form.cleaned_data['nome'].split(',')
                turmas = form.cleaned_data['turmas']

                if not turmas:
                    messages.error(request, "Selecione pelo menos uma turma.")
                    return redirect('admin:sistema_notas_disciplina_add')

                for nome in [n.strip() for n in nomes]:
                    for turma in turmas:
                        disciplina, created = Disciplina.objects.get_or_create(nome=nome, turma=turma)
                        if created:
                            disciplina.usuarios_permitidos.add(request.user)
                            self.associar_usuarios_com_turma(disciplina)

                messages.success(request, "Disciplinas criadas com sucesso.")
                return redirect('admin:sistema_notas_disciplina_changelist')

        return super().add_view(request, form_url, extra_context)

    def associar_usuarios_com_turma(self, disciplina):
        """
        Adiciona os usuários permitidos da disciplina à turma relacionada.
        """
        disciplina.turma.usuarios_permitidos.add(*disciplina.usuarios_permitidos.all())
class TurmaFilter(admin.SimpleListFilter):
    """
    Filtro personalizado para turmas baseado nas permissões do usuário logado.
    """
    title = _('turma')
    parameter_name = 'turma'

    def lookups(self, request, model_admin):
        turmas = Turma.objects.filter(usuarios_permitidos=request.user)
        return [(turma.id, turma.nome) for turma in turmas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(disciplina__turma_id=self.value())
        return queryset


class DisciplinaFilter(admin.SimpleListFilter):
    """
    Filtro personalizado para disciplinas baseado nas permissões do usuário logado.
    """
    title = _('disciplina')
    parameter_name = 'disciplina'

    def lookups(self, request, model_admin):
        disciplinas = Disciplina.objects.filter(usuarios_permitidos=request.user)
        return [(disciplina.id, disciplina.nome) for disciplina in disciplinas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(disciplina_id=self.value())
        return queryset


class NotaFinalAdmin(admin.ModelAdmin):
    list_display = ('estudante', 'disciplina', 'nota', 'status', 'modified_by', 'modified_at')
    list_filter = (TurmaFilter, DisciplinaFilter)  # Substituímos os filtros padrão pelos personalizados
    list_editable = ('nota',)
    readonly_fields = ('status', 'modified_by', 'modified_at')

    def get_queryset(self, request):
        """
        Filtra as turmas e disciplinas que o usuário logado pode acessar.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(disciplina__usuarios_permitidos=request.user)

    def get_urls(self):
        """
        Adiciona URLs customizadas, como a funcionalidade de lançar notas por turma.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                'lancar-notas-turma/',
                self.admin_site.admin_view(self.lancar_notas_turma_view),
                name='lancar_notas_turma'
            ),
        ]
        return custom_urls + urls

    def lancar_notas_turma_view(self, request):
        """
        View customizada para lançar notas de forma mais interativa.
        Restringe turmas e disciplinas com base no usuário logado.
        """
        turmas = Turma.objects.filter(usuarios_permitidos=request.user)
        if not turmas.exists():
            return HttpResponseForbidden("Você não tem permissão para lançar notas em nenhuma turma.")
        
        disciplinas = []
        estudantes_com_dados = []
        turma_id = request.GET.get('turma')
        disciplina_id = request.GET.get('disciplina')

        if turma_id:
            try:
                turma = turmas.get(id=turma_id)  # Verifica permissão
                disciplinas = Disciplina.objects.filter(turma=turma)
            except Turma.DoesNotExist:
                return HttpResponseForbidden("Você não tem permissão para acessar esta turma.")

        if turma_id and disciplina_id:
            try:
                disciplina = disciplinas.get(id=disciplina_id)  # Verifica permissão
                estudantes = Estudante.objects.filter(turma_id=turma_id)
            except Disciplina.DoesNotExist:
                return HttpResponseForbidden("Você não tem permissão para acessar esta disciplina.")

            for estudante in estudantes:
                nota_final = NotaFinal.objects.filter(estudante=estudante, disciplina_id=disciplina_id).first()
                estudantes_com_dados.append({
                    'id': estudante.id,
                    'nome': estudante.nome,
                    'nota': nota_final.nota if nota_final else "Sem nota",
                    'status': nota_final.status if nota_final else "Sem status",
                })

        if request.method == 'POST':
            for estudante in estudantes:
                nota = request.POST.get(f"nota_{estudante.id}")
                if nota:
                    try:
                        nota_float = float(nota.replace(',', '.'))
                        nota_final, created = NotaFinal.objects.update_or_create(
                            estudante=estudante,
                            disciplina_id=disciplina_id,
                            defaults={'nota': nota_float, 'modified_by': request.user},
                        )
                        nota_final.save()  # Recalcula o status ao salvar
                    except ValueError:
                        messages.error(request, f"Nota inválida para o estudante {estudante.nome}: {nota}")
                        continue

            messages.success(request, "Notas salvas com sucesso!")
            return redirect(f"{request.path}?turma={turma_id}&disciplina={disciplina_id}")

        return render(request, 'admin/sistema_notas/notafinal/lancar-notas-turma.html', {
            'title': 'Lançar Notas por Turma',
            'turmas': turmas,
            'disciplinas': disciplinas,
            'estudantes_com_dados': estudantes_com_dados,
            'turma_id': turma_id,
            'disciplina_id': disciplina_id,
        })

    def save_model(self, request, obj, form, change):
        """
        Adiciona o usuário atual ao campo 'modified_by' ao salvar.
        Também cria uma entrada no NotaFinalAudit para fins de auditoria.
        """
        # Captura o usuário que está modificando
        obj.modified_by = request.user

        # Se já existir, salva os dados antigos para auditoria
        if change:
            old_obj = NotaFinal.objects.get(pk=obj.pk)
            NotaFinalAudit.objects.create(
                nota_final=obj,
                modified_by=request.user,
                nota_anterior=old_obj.nota,
                nota_atual=obj.nota,
            )

        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """
        Adiciona o botão de Lançar Notas por Turma na página principal do admin.
        """
        extra_context = extra_context or {}
        extra_context['lancar_notas_turma_url'] = reverse('admin:lancar_notas_turma')
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        """
        Remove a permissão para adicionar novas notas para usuários que não são superusuários.
        """
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Remove a permissão de excluir notas, exceto para superusuários.
        """
        return request.user.is_superuser

# Configuração do admin para os outros modelos
admin.site.register(Turma, TurmaAdmin)
admin.site.register(Estudante, EstudanteAdmin)
admin.site.register(Disciplina, DisciplinaAdmin)
admin.site.register(NotaFinal, NotaFinalAdmin)
admin.site.register(NotaFinalAudit, NotaFinalAuditAdmin)

# Registra o modelo User com CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

# Customização do Django Admin
admin.site.site_header = "EduClass - CETEP/LNAB"
admin.site.site_title = "Administração do Sistema"
admin.site.index_title = "Painel de Administração"
 