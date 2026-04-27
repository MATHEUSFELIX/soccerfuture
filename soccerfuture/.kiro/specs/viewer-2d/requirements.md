# Documento de Requisitos — Viewer 2D

## Introdução

Este recurso implementa um visualizador 2D leve para o pipeline de avaliação de simulações de jogadas de futebol americano. O viewer renderiza os 3 cenários demo existentes em um campo 2D, exibe os top-K branches ranqueados para cada cenário, e apresenta as explicações de ranking e o resumo de telemetria produzidos pelo pipeline.

O viewer consome exclusivamente a saída existente do pipeline (`PipelineReport`) como fonte de dados — não introduz lógica de scoring nem modifica o pipeline. É uma ferramenta de visualização pura, construída com dependências mínimas (apenas a biblioteca padrão do Python + `matplotlib` para renderização), projetada para dar "olhos" ao pipeline e permitir avaliação humana nas sprints seguintes.

## Glossário

- **Viewer_2D**: Módulo de visualização (`src/viewer/viewer_2d.py`) que renderiza `PipelineReport` em imagens 2D de campo de futebol americano.
- **Campo_2D**: Representação gráfica do campo de futebol americano com dimensões regulamentares (100 jardas × 53.33 jardas), incluindo end zones, linhas de 10 jardas e hashmarks.
- **Cenário_Demo**: Um dos 3 play states de demonstração existentes em `data/play_states/` (`first_and_ten_midfield`, `third_and_short_goal_line`, `second_and_long_after_sack`).
- **Branch_Visual**: Representação gráfica de um branch simulado, mostrando as trajetórias dos jogadores como linhas/setas sobre o Campo_2D.
- **Painel_Explicação**: Área da visualização que exibe o `ranking_explanation` de um branch — fatores promovidos, fatores penalizados, bloco de maior/menor score.
- **Painel_Telemetria**: Área da visualização que exibe o resumo de telemetria do pipeline — branches gerados, taxa de rejeição, scores médios por estratégia, tempo por estágio.
- **Pipeline_Report**: Saída estruturada JSON do pipeline contendo branches ranqueados, relatórios de avaliação e metadados (modelo existente em `src/models/pipeline_report.py`).
- **PlayState**: Snapshot da situação de jogo no ponto de decisão, incluindo posições dos jogadores, down, distância e posição no campo (modelo existente em `src/models/play_state.py`).
- **Top_K**: Conjunto dos K branches com maior composite score retornados pelo pipeline após ranking e filtragem.
- **Ranking_Explanation**: Dicionário com `promoted_factors`, `penalized_factors`, `top_scoring_block`, `bottom_scoring_block` e opcionalmente `near_threshold_warning`, produzido pelo módulo de explainability existente.
- **Telemetria**: Dicionário em `PipelineReport.metadata["telemetry"]` contendo `branches_generated`, `hard_fail_count`, `score_filtered_count`, `avg_score_by_strategy`, `time_per_stage`.

## Requisitos

### Requisito 1: Renderização do Campo 2D

**User Story:** Como analista de futebol americano, quero ver um campo 2D com dimensões corretas e marcações regulamentares, para que eu possa interpretar as posições dos jogadores em contexto espacial real.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL renderizar um Campo_2D com dimensões proporcionais a 100 jardas de comprimento por 53.33 jardas de largura.
2. THE Viewer_2D SHALL desenhar linhas de marcação a cada 10 jardas no Campo_2D, com rótulos numéricos de jardagem.
3. THE Viewer_2D SHALL desenhar as duas end zones nas extremidades do Campo_2D, diferenciadas visualmente do campo de jogo.
4. THE Viewer_2D SHALL desenhar a line of scrimmage como uma linha destacada na posição `field_position` do PlayState.
5. THE Viewer_2D SHALL desenhar a first-down line como uma linha destacada na posição `field_position + distance` do PlayState.

### Requisito 2: Renderização das Posições Iniciais dos Jogadores

**User Story:** Como analista de futebol americano, quero ver as posições dos jogadores no ponto de decisão, para que eu possa entender a formação e o contexto tático antes da simulação.

#### Critérios de Aceitação

1. WHEN um PlayState é fornecido, THE Viewer_2D SHALL renderizar cada jogador como um marcador no Campo_2D na posição (x, y) correspondente.
2. THE Viewer_2D SHALL diferenciar visualmente os jogadores por role (QB, WR, RB, TE, OL) usando cores ou formas distintas.
3. THE Viewer_2D SHALL exibir o `player_id` como rótulo próximo a cada marcador de jogador.
4. THE Viewer_2D SHALL incluir uma legenda mapeando cores/formas aos roles dos jogadores.

### Requisito 3: Renderização dos Top-K Branches

**User Story:** Como analista de futebol americano, quero ver as trajetórias dos top-K branches sobrepostas no campo, para que eu possa comparar visualmente as continuações simuladas mais bem ranqueadas.

#### Critérios de Aceitação

1. WHEN um PipelineReport é fornecido, THE Viewer_2D SHALL renderizar as trajetórias de cada branch no Top_K como linhas sobre o Campo_2D.
2. THE Viewer_2D SHALL diferenciar visualmente cada branch no Top_K usando cores distintas.
3. FOR EACH branch no Top_K, THE Viewer_2D SHALL renderizar a trajetória de cada jogador como uma sequência de segmentos conectando as posições ordenadas por timestamp.
4. THE Viewer_2D SHALL exibir o `branch_id` e o `composite_score` de cada branch no Top_K em uma legenda ou anotação.
5. THE Viewer_2D SHALL indicar a direção do movimento dos jogadores usando setas ou marcadores direcionais nos segmentos de trajetória.

### Requisito 4: Exibição do Painel de Explicação de Ranking

**User Story:** Como analista de futebol americano, quero ver a explicação de ranking de cada branch top-K, para que eu possa entender por que o pipeline ranqueou cada branch na posição em que está.

#### Critérios de Aceitação

1. FOR EACH branch no Top_K que possua `ranking_explanation`, THE Viewer_2D SHALL exibir os `promoted_factors` como uma lista de fatores positivos.
2. FOR EACH branch no Top_K que possua `ranking_explanation`, THE Viewer_2D SHALL exibir os `penalized_factors` como uma lista de fatores negativos.
3. FOR EACH branch no Top_K que possua `ranking_explanation`, THE Viewer_2D SHALL exibir o `top_scoring_block` e o `bottom_scoring_block`.
4. IF um branch possui `near_threshold_warning` no `ranking_explanation`, THEN THE Viewer_2D SHALL exibir o aviso de proximidade ao threshold de forma destacada.
5. THE Viewer_2D SHALL exibir o `validity_score`, `opportunity_score` e `composite_score` de cada branch no Top_K.

### Requisito 5: Exibição do Painel de Telemetria

**User Story:** Como mantenedor do pipeline, quero ver o resumo de telemetria da execução, para que eu possa avaliar a saúde do pipeline e identificar gargalos rapidamente.

#### Critérios de Aceitação

1. WHEN um PipelineReport contém `metadata["telemetry"]`, THE Viewer_2D SHALL exibir o número total de branches gerados (`branches_generated`).
2. WHEN um PipelineReport contém `metadata["telemetry"]`, THE Viewer_2D SHALL exibir a contagem de hard fails (`hard_fail_count`) e de branches filtrados por score (`score_filtered_count`).
3. WHEN um PipelineReport contém `metadata["telemetry"]`, THE Viewer_2D SHALL exibir o score médio por estratégia de perturbação (`avg_score_by_strategy`).
4. WHEN um PipelineReport contém `metadata["telemetry"]`, THE Viewer_2D SHALL exibir o tempo por estágio do pipeline (`time_per_stage`).
5. IF o PipelineReport não contém telemetria, THEN THE Viewer_2D SHALL exibir uma mensagem indicando que dados de telemetria não estão disponíveis.

### Requisito 6: Informações Contextuais do Cenário

**User Story:** Como analista de futebol americano, quero ver as informações contextuais do cenário (down, distância, posição no campo, placar), para que eu possa interpretar os branches no contexto tático correto.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL exibir o down e a distância do PlayState (ex: "1st & 10") como título ou anotação proeminente.
2. THE Viewer_2D SHALL exibir a posição no campo em jardas (ex: "Own 50").
3. THE Viewer_2D SHALL exibir o diferencial de placar (`score_differential`) do PlayState.
4. WHEN o PlayState contém `metadata["formation"]`, THE Viewer_2D SHALL exibir o nome da formação.
5. WHEN o PlayState contém `metadata["description"]`, THE Viewer_2D SHALL exibir a descrição do cenário.

### Requisito 7: Script de Geração de Visualizações

**User Story:** Como mantenedor do pipeline, quero um script que gere visualizações para todos os 3 cenários demo de uma vez, para que eu possa inspecionar o estado do pipeline rapidamente.

#### Critérios de Aceitação

1. THE projeto SHALL incluir um script (`scripts/render_viewer.py`) que executa o pipeline nos 3 Cenários_Demo e gera uma visualização para cada um.
2. THE script SHALL salvar as visualizações como arquivos de imagem (PNG) no diretório `output/viewer/`.
3. THE script SHALL gerar uma visualização por cenário mostrando o campo, posições iniciais, top-K branches, explicações e telemetria.
4. THE script SHALL imprimir um resumo no stdout indicando quais cenários foram renderizados e o caminho dos arquivos gerados.
5. THE script SHALL sair com código 0 em sucesso e código 1 se qualquer cenário falhar.

### Requisito 8: Renderização Individual de Branch

**User Story:** Como analista de futebol americano, quero poder gerar uma visualização focada em um único branch, para que eu possa analisar em detalhe a trajetória e explicação de um branch específico.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL fornecer uma função que renderiza um único branch do Top_K isoladamente no Campo_2D, com suas trajetórias, scores e explicação.
2. WHEN renderizando um branch individual, THE Viewer_2D SHALL exibir todas as trajetórias de jogadores daquele branch com maior destaque visual do que na visualização multi-branch.
3. WHEN renderizando um branch individual, THE Viewer_2D SHALL exibir a explicação de ranking completa do branch ao lado do campo.

### Requisito 9: Módulo de Renderização do Campo — Funções Puras

**User Story:** Como desenvolvedor, quero que a lógica de renderização do campo seja composta por funções puras e reutilizáveis, para que eu possa testar e compor visualizações de forma modular.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL ser implementado como um módulo em `src/viewer/viewer_2d.py` contendo funções puras que recebem dados e retornam objetos de figura `matplotlib`.
2. THE Viewer_2D SHALL separar a renderização do campo (linhas, marcações) da renderização de branches (trajetórias) e da renderização de painéis (explicação, telemetria) em funções distintas.
3. THE Viewer_2D SHALL aceitar um `PipelineReport` (ou seu dict equivalente via `to_dict()`) como entrada principal, sem depender de acesso ao filesystem ou ao pipeline diretamente.
4. THE Viewer_2D SHALL ser importável e utilizável programaticamente sem efeitos colaterais na importação.

### Requisito 10: Serialização e Carregamento de PipelineReport para o Viewer

**User Story:** Como desenvolvedor, quero poder salvar a saída do pipeline em JSON e carregá-la no viewer sem re-executar o pipeline, para que eu possa iterar na visualização rapidamente.

#### Critérios de Aceitação

1. THE script `scripts/render_viewer.py` SHALL aceitar um argumento opcional `--from-json <path>` que carrega um PipelineReport previamente salvo em vez de executar o pipeline.
2. WHEN o argumento `--from-json` é fornecido, THE script SHALL carregar o JSON, reconstruir o PipelineReport via `PipelineReport.from_dict()`, e renderizar a visualização.
3. THE script SHALL aceitar um argumento opcional `--save-json <path>` que salva o PipelineReport gerado como JSON antes de renderizar.
4. FOR ALL PipelineReport dicts válidos, carregar o JSON salvo via `--save-json` e reconstruí-lo via `PipelineReport.from_dict()` SHALL produzir um PipelineReport equivalente ao original (propriedade round-trip).

### Requisito 11: Configuração Visual

**User Story:** Como desenvolvedor, quero que as constantes visuais (cores, tamanhos, espaçamentos) sejam definidas em um único local, para que eu possa ajustar a aparência do viewer sem modificar a lógica de renderização.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL definir todas as constantes visuais (cores por role, cores por branch, tamanho de marcadores, espessura de linhas, fontes) em `src/viewer/constants.py`.
2. THE Viewer_2D SHALL usar as constantes de `src/viewer/constants.py` em todas as funções de renderização, sem valores mágicos hardcoded.
3. THE Viewer_2D SHALL definir um mapeamento de cores para os roles de jogadores (QB, WR, RB, TE, OL) e um mapeamento de cores para os top-K branches (pelo menos 5 cores distintas).
