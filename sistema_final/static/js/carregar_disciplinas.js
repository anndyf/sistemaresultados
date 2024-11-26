console.log("Script carregar_disciplinas.js carregado");

document.addEventListener('DOMContentLoaded', function() {
    const turmaSelect = document.getElementById('id_turma');
    const disciplinaSelect = document.getElementById('id_disciplina');

    if (turmaSelect && disciplinaSelect) {
        turmaSelect.addEventListener('change', function() {
            console.log("Turma selecionada:", turmaSelect.value);
            const turmaId = turmaSelect.value;

            // Limpa as opções atuais de disciplina
            disciplinaSelect.innerHTML = '<option value="">---------</option>';

            if (turmaId) {
                console.log(`Carregando disciplinas para a turma ID: ${turmaId}`);
                fetch(`/sistema_notas/carregar-disciplinas/?turma=${turmaId}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log("Disciplinas carregadas:", data);
                        data.forEach(disciplina => {
                            const option = document.createElement('option');
                            option.value = disciplina.id;
                            option.textContent = disciplina.nome;
                            disciplinaSelect.appendChild(option);
                        });
                    })
                    .catch(error => console.error("Erro ao carregar disciplinas:", error));
            }
        });
    } else {
        console.error("Elementos de seleção de turma ou disciplina não encontrados.");
    }
});
