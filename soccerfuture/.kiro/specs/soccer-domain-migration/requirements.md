# Documento de Requisitos — Migração de Domínio para Futebol (Soccer)

## Introdução

Este documento especifica os requisitos para migrar todo o codebase do projeto "soccerfuture" do domínio de futebol americano para o domínio de futebol (association football/soccer). A migração abrange modelos de dados, constantes, lógica de avaliação, visualização, cenários de demonstração, testes e documentação de steering. A arquitetura do pipeline (geração de branches → avaliação → ranking → visualização) permanece inalterada — trata-se de uma migração de terminologia e dados de domínio, não de uma mudança arquitetural.

## Glossário

- **Sistema_de_Avaliação**: O pipeline completo que gera branches simulados, avalia-os e produz rankings. Corresponde ao código em `src/`.
- **PlayState**: Modelo de dados que representa o estado de uma partida de futebol em um ponto de decisão. Definido em `src/models/play_state.py`.
- **Branch**: Uma continuação simulada de uma jogada real a partir de um ponto de decisão. Definido em `src/models/branch.py`.
- **Campo_de_Futebol**: Campo de futebol padrão FIFA com dimensões 105m × 68m, sem end zones, com áreas de penalidade, áreas de gol, círculo central, linha do meio-campo e arcos de escanteio.
- **Posição_de_Jogador**: Papel tático de um jogador no futebol: GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST.
- **Estado_de_Jogo**: Conjunto de atributos que descrevem o momento da partida: match_time, possession_team, ball_position, game_phase.
- **Evento_de_Futebol**: Ação discreta durante uma simulação: pass, shot, tackle, interception, dribble, cross, header, goal, corner_kick, free_kick, throw_in, goal_kick, offside, foul, save, clearance, dispossession.
- **Fase_de_Jogo**: Estado corrente do jogo: open_play, set_piece, transition, dead_ball.
- **Módulo_de_Gating**: Módulo que executa verificações binárias de aprovação/rejeição antes de qualquer scoring. Definido em `src/scoring/gating.py`.
- **Módulo_de_Plausibilidade**: Módulo que avalia a plausibilidade física dos movimentos dos jogadores. Definido em `src/scoring/physical_plausibility.py`.
- **Módulo_de_Consistência_Tática**: Módulo que avalia se os jogadores mantêm comportamento consistente com seus papéis. Definido em `src/scoring/tactical_consistency.py`.
- **Módulo_de_Valor_de_Decisão**: Módulo que quantifica a oportunidade tática de um branch. Definido em `src/scoring/decision_value.py`.
- **Viewer_2D**: Módulo de visualização que renderiza o campo e as trajetórias dos branches. Definido em `src/viewer/viewer_2d.py`.
- **Gerador_de_Branches**: Módulo que produz N branches alternativos a partir de um PlayState. Definido em `src/generation/branch_generator.py`.
- **Cenário_Demo**: Arquivo JSON em `data/play_states/` que define uma situação de jogo para demonstração.
- **Constantes_Globais**: Arquivo centralizado de constantes em `src/utils/constants.py`.
- **Constantes_do_Viewer**: Arquivo de constantes visuais em `src/viewer/constants.py`.
- **Estratégias_de_Teste**: Módulo de estratégias Hypothesis reutilizáveis em `tests/strategies.py`.

## Requisitos

### Requisito 1: Dimensões do Campo e Sistema de Coordenadas

**User Story:** Como analista de futebol, quero que o sistema utilize as dimensões padrão FIFA de um campo de futebol, para que todas as simulações e visualizações reflitam o esporte correto.

#### Critérios de Aceitação

1. THE Constantes_Globais SHALL definir FIELD_LENGTH como 105.0 (metros) e FIELD_WIDTH como 68.0 (metros)
2. THE Constantes_Globais SHALL remover a constante END_ZONE_DEPTH e substituí-la por constantes de áreas do campo de futebol: PENALTY_AREA_LENGTH (16.5m), PENALTY_AREA_WIDTH (40.3m), GOAL_AREA_LENGTH (5.5m), GOAL_AREA_WIDTH (18.3m), CENTER_CIRCLE_RADIUS (9.15m), CORNER_ARC_RADIUS (1.0m)
3. THE Constantes_Globais SHALL definir o sistema de coordenadas como x = 0–68m (largura) e y = 0–105m (comprimento)
4. WHEN uma posição de jogador é validada, THE Módulo_de_Gating SHALL verificar os limites do campo como x em [0, 68] e y em [0, 105], sem end zones
5. THE Constantes_Globais SHALL atualizar MAX_FORMATION_AREA para utilizar as novas dimensões do campo de futebol (FIELD_WIDTH × 40.0 em metros)

### Requisito 2: Papéis dos Jogadores

**User Story:** Como analista de futebol, quero que os papéis dos jogadores reflitam posições de futebol, para que as simulações representem formações e táticas reais do esporte.

#### Critérios de Aceitação

1. THE Sistema_de_Avaliação SHALL reconhecer exclusivamente os seguintes papéis de jogador: GK (goleiro), CB (zagueiro), LB (lateral esquerdo), RB (lateral direito), CDM (volante), CM (meio-campista), CAM (meia-atacante), LW (ponta esquerda), RW (ponta direita), ST (atacante/centroavante)
2. THE Sistema_de_Avaliação SHALL rejeitar os papéis de futebol americano: QB, WR, RB (running back), TE, OL, DL, LB (linebacker), CB (cornerback), S, K, P, FB
3. THE Gerador_de_Branches SHALL utilizar vetores de movimento base (_ROLE_BASE_VECTORS) específicos para cada posição de futebol, refletindo padrões de movimentação táticos do esporte
4. THE Estratégias_de_Teste SHALL gerar PlayStates com papéis de jogador exclusivamente do conjunto de posições de futebol

### Requisito 3: Modelo de Estado de Jogo (PlayState)

**User Story:** Como desenvolvedor, quero que o modelo PlayState represente o estado de uma partida de futebol, para que os dados de entrada reflitam corretamente o contexto tático do esporte.

#### Critérios de Aceitação

1. THE PlayState SHALL conter os campos: match_time (float, 0–90+ minutos), possession_team (str), ball_position (dict com x e y em metros), game_phase (str: open_play | set_piece | transition | dead_ball)
2. THE PlayState SHALL remover os campos: down, distance, field_position (yards da própria end zone)
3. THE PlayState SHALL manter os campos: score_differential, player_positions, decision_point_timestamp, player_roles, metadata
4. THE PlayState SHALL manter a serialização round-trip: converter para dict e reconstruir a partir de dict produz um objeto equivalente
5. WHEN um PlayState é carregado de um arquivo JSON, THE Sistema_de_Avaliação SHALL validar que os campos obrigatórios do futebol estão presentes (match_time, possession_team, ball_position, game_phase)

### Requisito 4: Tipos de Eventos

**User Story:** Como analista de futebol, quero que os eventos simulados representem ações de futebol, para que as simulações sejam semanticamente corretas para o esporte.

#### Critérios de Aceitação

1. THE Sistema_de_Avaliação SHALL reconhecer os seguintes tipos de evento de futebol: pass, shot, tackle, interception, dribble, cross, header, goal, corner_kick, free_kick, throw_in, goal_kick, offside, foul, save, clearance, dispossession
2. THE Sistema_de_Avaliação SHALL remover os tipos de evento de futebol americano: snap, throw, catch, sack, fumble, touchdown, field_goal, handoff, reception, carry, turnover_on_downs, block, hit
3. THE Constantes_Globais SHALL atualizar CONTACT_EVENT_TYPES para conter eventos de contato do futebol: tackle, foul, dispossession
4. THE Gerador_de_Branches SHALL gerar eventos consistentes com futebol nas estratégias de perturbação (pass, dribble, shot em vez de throw, catch, handoff)

### Requisito 5: Limiares Físicos para Futebol

**User Story:** Como desenvolvedor, quero que os limiares de velocidade e aceleração reflitam as capacidades de jogadores de futebol de elite, para que a avaliação de plausibilidade física seja precisa para o esporte.

#### Critérios de Aceitação

1. THE Constantes_Globais SHALL definir MAX_HUMAN_SPRINT_SPEED como 10.0 metros por segundo (velocidade máxima de sprint de jogadores de futebol de elite)
2. THE Constantes_Globais SHALL definir MAX_ACCELERATION e MAX_DECELERATION em metros por segundo ao quadrado, com valores calibrados para futebol
3. THE Constantes_Globais SHALL definir CONTACT_SPEED_THRESHOLD em metros por segundo, ajustado para o contexto de contato no futebol
4. THE Módulo_de_Plausibilidade SHALL utilizar os limiares atualizados em metros por segundo para avaliar a plausibilidade dos movimentos dos jogadores
5. THE Módulo_de_Gating SHALL utilizar os limiares atualizados em metros por segundo para as verificações de velocidade máxima

### Requisito 6: Consistência Tática para Futebol

**User Story:** Como analista de futebol, quero que a avaliação de consistência tática reflita formações e zonas posicionais do futebol, para que os branches sejam avaliados corretamente quanto à coerência tática.

#### Critérios de Aceitação

1. THE Módulo_de_Consistência_Tática SHALL definir zonas posicionais (_ROLE_ZONES) para cada posição de futebol: GK (próximo ao gol), CB (zona central defensiva), LB/RB (laterais), CDM (meio-campo defensivo central), CM (meio-campo central), CAM (meio-campo ofensivo), LW/RW (pontas), ST (zona de ataque)
2. THE Módulo_de_Consistência_Tática SHALL remover a sub-métrica line_integrity_score (integridade de linha OL/DL) e substituí-la por formation_shape_score, que avalia a manutenção da forma da formação tática (4-3-3, 4-4-2, 3-5-2)
3. THE Módulo_de_Consistência_Tática SHALL atualizar a lógica de defensive_density para identificar o portador da bola usando eventos de futebol (dribble, pass recebido) em vez de eventos de futebol americano (handoff, catch, reception, carry)
4. THE Módulo_de_Consistência_Tática SHALL atualizar os papéis defensivos para futebol: CB, LB, RB, CDM (em vez de DL, LB, CB, S do futebol americano)
5. THE Módulo_de_Consistência_Tática SHALL manter as sub-métricas: role_consistency_score, formation_coherence_score, compactness_score, defensive_density_score, e a nova formation_shape_score

### Requisito 7: Valor de Decisão para Futebol

**User Story:** Como analista de futebol, quero que a avaliação de oportunidade tática utilize métricas relevantes para futebol, para que o ranking dos branches reflita o valor tático no contexto do esporte.

#### Critérios de Aceitação

1. THE Módulo_de_Valor_de_Decisão SHALL substituir yard_gain_differential por ball_progression, que mede a progressão da bola em metros em direção ao gol adversário
2. THE Módulo_de_Valor_de_Decisão SHALL atualizar os tipos de evento de turnover para futebol: interception, dispossession (em vez de fumble, interception, turnover, turnover_on_downs)
3. THE Módulo_de_Valor_de_Decisão SHALL atualizar os tipos de evento de scoring para futebol: goal (em vez de touchdown, field_goal, safety, scoring_play)
4. THE Módulo_de_Valor_de_Decisão SHALL utilizar FIELD_LENGTH em metros (105.0) para normalização da progressão da bola
5. THE Módulo_de_Valor_de_Decisão SHALL manter a estrutura de resultado com opportunity_score, ball_progression (substituindo yard_gain_differential), turnover_risk_delta e scoring_probability_delta

### Requisito 8: Visualização do Campo de Futebol

**User Story:** Como analista de futebol, quero que o viewer 2D renderize um campo de futebol padrão FIFA, para que a visualização das simulações seja fiel ao esporte.

#### Critérios de Aceitação

1. THE Viewer_2D SHALL renderizar um campo de futebol com: áreas de penalidade (16.5m × 40.3m), áreas de gol (5.5m × 18.3m), círculo central (raio 9.15m), linha do meio-campo, arcos de escanteio (raio 1.0m) e gols
2. THE Viewer_2D SHALL remover elementos de futebol americano: end zones, yard lines, hashmarks, linha de scrimmage e linha de first-down
3. THE Constantes_do_Viewer SHALL atualizar ROLE_COLORS para mapear as posições de futebol (GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST) com cores distintas
4. THE Constantes_do_Viewer SHALL remover as constantes de futebol americano: END_ZONE_DEPTH_YARDS, END_ZONE_COLOR, SCRIMMAGE_LINE_COLOR, FIRST_DOWN_LINE_COLOR, YARD_LINE_WIDTH, YARD_LABEL_FONTSIZE
5. THE Viewer_2D SHALL atualizar draw_scenario_info para exibir match_time, possession_team e game_phase em vez de down, distance e field_position
6. THE Viewer_2D SHALL remover a função draw_scrimmage_and_first_down e substituí-la por draw_ball_position, que marca a posição da bola no campo

### Requisito 9: Cenários de Demonstração

**User Story:** Como analista de futebol, quero cenários de demonstração que representem situações reais de futebol, para que eu possa testar e demonstrar o sistema com dados relevantes.

#### Critérios de Aceitação

1. THE Sistema_de_Avaliação SHALL fornecer um cenário de demonstração "contra-ataque no meio-campo" (counter_attack_midfield.json) com jogadores em formação 4-3-3, match_time entre 30–60 minutos, game_phase "transition" e ball_position no meio-campo
2. THE Sistema_de_Avaliação SHALL fornecer um cenário de demonstração "construção de jogo na defesa" (build_up_from_defense.json) com jogadores em formação 4-4-2, match_time entre 0–30 minutos, game_phase "open_play" e ball_position no terço defensivo
3. THE Sistema_de_Avaliação SHALL fornecer um cenário de demonstração "bola parada na grande área" (set_piece_penalty_area.json) com jogadores posicionados para cobrança de falta, match_time entre 60–90 minutos, game_phase "set_piece" e ball_position próxima à área de penalidade
4. THE Sistema_de_Avaliação SHALL remover os cenários de futebol americano: first_and_ten_midfield.json, second_and_long_after_sack.json, third_and_short_goal_line.json
5. WHEN um cenário de demonstração é carregado, THE Sistema_de_Avaliação SHALL validar que todos os jogadores possuem papéis de futebol válidos e que as posições estão dentro dos limites do campo de futebol

### Requisito 10: Geração de Branches para Futebol

**User Story:** Como desenvolvedor, quero que o gerador de branches produza simulações com movimentação e eventos de futebol, para que os branches gerados sejam fisicamente e taticamente plausíveis para o esporte.

#### Critérios de Aceitação

1. THE Gerador_de_Branches SHALL utilizar vetores de movimento base para posições de futebol: GK (movimentação mínima no gol), CB (cobertura central), LB/RB (subidas laterais), CDM (cobertura central), CM (movimentação box-to-box), CAM (movimentação ofensiva), LW/RW (corridas pelas pontas), ST (movimentação na área)
2. THE Gerador_de_Branches SHALL gerar eventos de futebol na estratégia de decisão: pass e dribble (em vez de throw e catch), shot (em vez de touchdown), tackle (em vez de sack)
3. THE Gerador_de_Branches SHALL limitar as posições geradas aos limites do campo de futebol: x em [0, 68] e y em [0, 105], sem end zones
4. THE Gerador_de_Branches SHALL utilizar velocidades em metros por segundo, respeitando o limite de segurança derivado de MAX_HUMAN_SPRINT_SPEED (10.0 m/s)
5. THE Gerador_de_Branches SHALL manter a estrutura de GenerationResult com branches, continuation_window e strategy_counts

### Requisito 11: Atualização de Testes

**User Story:** Como desenvolvedor, quero que todos os testes utilizem dados de futebol, para que a suíte de testes valide corretamente o comportamento do sistema no novo domínio.

#### Critérios de Aceitação

1. THE Estratégias_de_Teste SHALL gerar PlayStates com campos de futebol (match_time, possession_team, ball_position, game_phase) em vez de campos de futebol americano (down, distance, field_position)
2. THE Estratégias_de_Teste SHALL gerar posições de jogador dentro dos limites do campo de futebol (x: 0–68m, y: 0–105m) sem end zones
3. THE Estratégias_de_Teste SHALL utilizar papéis de jogador de futebol (_PLAYER_ROLES = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"])
4. THE Estratégias_de_Teste SHALL atualizar out_of_bounds_branch_strategy para usar os limites do campo de futebol (sem END_ZONE_DEPTH)
5. WHEN testes de scoring são executados, THE Sistema_de_Avaliação SHALL utilizar dados de teste com eventos, papéis e dimensões de futebol em todos os módulos de teste
6. WHEN testes do viewer são executados, THE Sistema_de_Avaliação SHALL validar a renderização de elementos do campo de futebol (áreas de penalidade, círculo central, linha do meio-campo) em vez de elementos de futebol americano

### Requisito 12: Documentação de Steering

**User Story:** Como desenvolvedor, quero que a documentação de steering reflita o domínio de futebol, para que as instruções do AI assistant sejam consistentes com o esporte correto.

#### Critérios de Aceitação

1. THE Sistema_de_Avaliação SHALL atualizar product.md para referenciar "futebol" (soccer) em vez de "football" (American football) em todas as descrições de domínio, contexto e usuários-alvo
2. THE Sistema_de_Avaliação SHALL atualizar agents.md para referenciar "simulação de futebol" em vez de "football play simulation" no contexto do projeto e nas regras do assistente
3. THE Sistema_de_Avaliação SHALL manter todas as convenções arquiteturais e de pipeline inalteradas nos documentos de steering (gating → validity → opportunity, independência de módulos, serialização JSON)

### Requisito 13: Unidades de Medida Consistentes

**User Story:** Como desenvolvedor, quero que todas as unidades de medida no sistema sejam metros e metros por segundo, para que haja consistência e não existam referências residuais a yards.

#### Critérios de Aceitação

1. THE Sistema_de_Avaliação SHALL utilizar metros como unidade de distância em todas as constantes, modelos, lógica de scoring e visualização
2. THE Sistema_de_Avaliação SHALL utilizar metros por segundo como unidade de velocidade em todas as constantes e lógica de avaliação
3. THE Sistema_de_Avaliação SHALL remover todas as referências a "yards" em docstrings, comentários, nomes de variáveis e mensagens de explicação
4. IF uma referência a "yards" for encontrada em qualquer módulo do sistema, THEN THE Sistema_de_Avaliação SHALL substituí-la pela referência equivalente em metros
