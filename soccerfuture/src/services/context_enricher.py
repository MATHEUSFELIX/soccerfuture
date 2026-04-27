"""Derives deterministic ContextSignals from a MatchContext.

Uses heuristic rules based on comparative edges and team metrics
to produce tactical signals that inform branch evaluation adjustments.
"""

from src.domain.match_context import ContextSignals, MatchContext


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


def enrich_context(match_context: MatchContext) -> ContextSignals:
    """Derive deterministic tactical signals from pre-match context.

    Args:
        match_context: The pre-match context containing team metrics
            and comparative signals.

    Returns:
        A ContextSignals instance with aggression_bias, risk_tolerance,
        retention_bias, likely_game_state_pressure, and explanatory notes.
    """
    home = match_context.home_team
    comp = match_context.comparative_signals
    home_m = match_context.home_metrics
    away_m = match_context.away_metrics

    aggression = 0.0
    risk = 0.0
    retention = 0.0
    pressure = 0.0
    notes: list[str] = []
    has_partial = False

    # --- aggression_bias ---
    if comp.attack_edge == home:
        aggression += 0.1
        notes.append("Home team has attacking edge; slight aggression bias applied.")
    elif comp.attack_edge is not None:
        aggression -= 0.1
        notes.append("Away team has attacking edge; negative aggression bias applied.")

    if home_m.xg_for_avg is not None and away_m.xg_for_avg is not None:
        if home_m.xg_for_avg > away_m.xg_for_avg:
            aggression += 0.05
            notes.append("Home xG creation exceeds away; minor aggression boost.")
    else:
        has_partial = True

    aggression = _clamp(aggression, -1.0, 1.0)

    # --- risk_tolerance ---
    if comp.form_edge == home:
        risk += 0.1
        notes.append("Home team has form edge; increased risk tolerance.")
    elif comp.form_edge is not None:
        # Away has form edge — no positive risk boost for home
        pass

    # score_differential proxy: if home goals_for < away goals_for, home is
    # likely trailing on average → more risk
    if home_m.goals_for_avg is not None and away_m.goals_for_avg is not None:
        if home_m.goals_for_avg < away_m.goals_for_avg:
            risk += 0.15
            notes.append("Home team likely trailing on average; risk tolerance increased.")
    else:
        has_partial = True

    risk = _clamp(risk, -1.0, 1.0)

    # --- retention_bias ---
    if comp.defense_edge == home:
        retention += 0.1
        notes.append("Home team has defensive edge; retention bias applied.")
    elif comp.defense_edge is not None:
        pass

    if (
        home_m.goals_against_avg is not None
        and away_m.goals_against_avg is not None
    ):
        if home_m.goals_against_avg < away_m.goals_against_avg:
            retention += 0.05
            notes.append("Home concedes fewer goals; minor retention boost.")
    else:
        has_partial = True

    retention = _clamp(retention, -1.0, 1.0)

    # --- likely_game_state_pressure ---
    if home_m.form_points is not None and away_m.form_points is not None:
        diff = abs(home_m.form_points - away_m.form_points)
        if diff > 10:
            pressure = 0.3
            notes.append("Large form disparity; high game-state pressure.")
        elif diff > 5:
            pressure = 0.15
            notes.append("Moderate form disparity; moderate game-state pressure.")
    else:
        has_partial = True

    pressure = _clamp(pressure, 0.0, 1.0)

    # --- partial data note ---
    if has_partial:
        notes.append("Partial data; neutral defaults used for missing values.")

    return ContextSignals(
        aggression_bias=aggression,
        risk_tolerance=risk,
        retention_bias=retention,
        likely_game_state_pressure=pressure,
        notes=notes,
    )
