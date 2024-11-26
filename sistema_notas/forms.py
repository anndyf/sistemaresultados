from dal import autocomplete
from django import forms
from .models import NotaFinal, Turma, Disciplina, Estudante
from django.core.exceptions import ValidationError

# Formulário para upload de arquivos CSV
class UploadCSVForm(forms.Form):
    """
    Formulário para permitir o upload de arquivos CSV no sistema.
    """
    arquivo_csv = forms.FileField(label='Selecione o arquivo CSV')  # Campo de upload de arquivo


# Formulário para criar várias disciplinas de uma vez
class DisciplinaMultipleForm(forms.ModelForm):
    """
    Formulário para criar várias disciplinas associadas a turmas.
    """
    nome = forms.CharField(
    widget=forms.TextInput(attrs={
        'placeholder': 'Digite várias disciplinas separadas por vírgula',
        'maxlength': 350,
        'style': 'width: 600px;'  # Ajuste a largura aqui
    }),
    help_text="Exemplo: Matemática, Física, Química"
    )
    turmas = forms.ModelMultipleChoiceField(
        queryset=Turma.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Selecione as turmas para associar cada disciplina."
    )

    class Meta:
        model = Disciplina
        fields = ['nome', 'turmas']


# Formulário para lançar notas para uma turma e disciplina
class LancaNotaForm(forms.Form):
    """
    Formulário para lançar notas vinculadas a uma turma e disciplina específicas.
    """
    turma = forms.ModelChoiceField(queryset=Turma.objects.all(), label="Turma")
    disciplina = forms.ModelChoiceField(queryset=Disciplina.objects.none(), label="Disciplina")

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário e ajusta o queryset de disciplinas baseado na turma.
        """
        super().__init__(*args, **kwargs)
        if 'turma' in self.data:
            try:
                turma_id = int(self.data.get('turma'))
                self.fields['disciplina'].queryset = Disciplina.objects.filter(turma_id=turma_id)
            except (ValueError, TypeError):
                self.fields['disciplina'].queryset = Disciplina.objects.none()


# Formulário para adicionar ou editar uma nota final
class NotaFinalForm(forms.ModelForm):
    """
    Formulário para registrar notas finais vinculadas a estudantes, turmas e disciplinas.
    """
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.all(),
        required=True,
        label="Turma"
    )
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.none(),
        required=True,
        label="Disciplina",
        widget=autocomplete.ModelSelect2(url='disciplina-autocomplete', forward=['turma'])
    )
    estudante = forms.ModelChoiceField(
        queryset=Estudante.objects.none(),
        required=True,
        label="Estudante",
        widget=autocomplete.ModelSelect2(url='estudante-autocomplete', forward=['turma', 'disciplina'])
    )
    nota = forms.FloatField(
        label="Nota",
        help_text="Digite -1 para classificar como desistente"
    )

    class Meta:
        model = NotaFinal
        fields = ['turma', 'disciplina', 'estudante', 'nota']

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário, ajustando os querysets com base na seleção de turma e disciplina.
        """
        super().__init__(*args, **kwargs)

        # Carregar disciplinas com base na turma
        if 'turma' in self.data:
            try:
                turma_id = int(self.data.get('turma'))
                self.fields['disciplina'].queryset = Disciplina.objects.filter(turma_id=turma_id)
            except (ValueError, TypeError):
                self.fields['disciplina'].queryset = Disciplina.objects.none()

        # Carregar estudantes com base na disciplina e turma
        if 'disciplina' in self.data:
            try:
                disciplina_id = int(self.data.get('disciplina'))
                turma_id = int(self.data.get('turma'))
                self.fields['estudante'].queryset = Estudante.objects.filter(
                    turma_id=turma_id,
                    turma__disciplinas__id=disciplina_id
                )
            except (ValueError, TypeError):
                self.fields['estudante'].queryset = Estudante.objects.none()

    def clean(self):
        """
        Valida os dados do formulário para evitar duplicatas de notas finais.
        """
        cleaned_data = super().clean()
        estudante = cleaned_data.get('estudante')
        disciplina = cleaned_data.get('disciplina')

        # Verificar duplicatas
        if NotaFinal.objects.filter(estudante=estudante, disciplina=disciplina).exists():
            raise ValidationError("Já existe uma nota cadastrada para este estudante nesta disciplina.")

        return cleaned_data


class LancarNotasForm(forms.Form):
    """
    Formulário simplificado para lançar notas em massa para uma turma e disciplina.
    """
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.all(),
        label="Turma",
        required=True,
        error_messages={
            'required': 'Você deve selecionar uma turma.',
            'invalid_choice': 'A turma selecionada é inválida.',
        },
    )
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.none(),
        label="Disciplina",
        required=True,
        error_messages={
            'required': 'Você deve selecionar uma disciplina.',
            'invalid_choice': 'A disciplina selecionada é inválida.',
        },
    )
    notas = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )  # Campo oculto para receber as notas em formato JSON

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário e ajusta o queryset de disciplinas baseado na turma.
        """
        super().__init__(*args, **kwargs)

        if 'turma' in self.data:  # Se 'turma' foi enviada via request
            try:
                turma_id = int(self.data.get('turma'))
                self.fields['disciplina'].queryset = Disciplina.objects.filter(turma_id=turma_id)
            except (ValueError, TypeError):
                self.fields['disciplina'].queryset = Disciplina.objects.none()

    def clean(self):
        """
        Validação personalizada para garantir que a disciplina pertence à turma selecionada
        e para validar as notas.
        """
        cleaned_data = super().clean()
        turma = cleaned_data.get('turma')
        disciplina = cleaned_data.get('disciplina')
        notas_json = cleaned_data.get('notas')

        # Validação da turma e disciplina
        if turma and disciplina:
            if disciplina.turma != turma:
                raise forms.ValidationError("A disciplina selecionada não pertence à turma escolhida.")

        # Validação das notas
        import json
        erros = []
        try:
            notas = json.loads(notas_json)  # Processa o JSON de notas
        except (ValueError, TypeError):
            raise forms.ValidationError("Erro ao processar as notas enviadas.")

        for estudante_id, nota in notas.items():
            try:
                nota = float(nota)  # Converte a nota para float
                if nota < -1 or nota > 10:
                    erros.append(f"A nota {nota} para o estudante com ID {estudante_id} deve estar entre -1 e 10.")
            except ValueError:
                erros.append(f"A nota fornecida para o estudante com ID {estudante_id} é inválida.")

        if erros:
            raise forms.ValidationError(erros)  # Levanta todas as mensagens de erro de uma vez

        return cleaned_data