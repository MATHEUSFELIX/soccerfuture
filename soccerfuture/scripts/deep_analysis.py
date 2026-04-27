"""Deep analysis: category breakdown, error analysis, and v3 recommendation.

Usage:
    python scripts/deep_analysis.py
"""

import json
import sys
import os
import dataclasses
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulation_evaluator_v2 import evaluate_branch
from src.utils.serialization import report_to_dict


def load_data():
    with open("data/benchmark_input.json", "r", encoding="utf-8") as f:
        benchmark = json.load(f)
    with open("data/benchmark_annotated.json", "r", encoding="utf-8") as f:
        annotations = json.load(f)
    ann_map = {a["branch_id"]: a for a in annotations["annotations"]}
    return benchmark, ann_map


def evaluate_all_branches(benchmark):
    results = []
    branches = benchmark["branches"]
    windows = benchmark["continuation_windows"]
    for i, branch in enumerate(branches):
        window = windows[i] if i < len(windows) else {}
        report = evaluate_branch(branch, window)
        rd = report_to_dict(report)
        results.append({
            "id": branch["branch_id"],
            "label": branch.get("expected_label", "?"),
            "report": report,
            "report_dict": rd,
        })
    return results


# =========================================================================
# PART 1: Category Analysis
# =========================================================================

CATEGORY_LABELS_PT = {
    "corredor": "Corredor",
    "passe_curto": "Passe Curto",
    "passe_profundidade": "Passe em Profundidade",
    "finalizacao_curta": "Finalização Curta",
    "ataque_posicional": "Ataque Posicional",
    "jogada_lateral": "Jogada Lateral",
}


def category_analysis(results, ann_map):
    print("\n" + "=" * 100)
    print("PARTE 1: AVALIAÇÃO POR CATEGORIA DE JOGADA")
    print("=" * 100)

    by_category = defaultdict(list)
    for r in results:
        ann = ann_map.get(r["id"], {})
        cat = ann.get("play_category", "desconhecido")
        by_category[cat].append((r, ann))

    category_stats = {}
    for cat, items in sorted(by_category.items()):
        cat_label = CATEGORY_LABELS_PT.get(cat, cat)
        print(f"\n--- {cat_label} ({len(items)} branches) ---")

        validities = []
        opportunities = []
        errors = []

        for r, ann in items:
            rep = r["report"]
            bid = r["id"]
            label = r["label"]

            v = rep.validity_score
            o = rep.opportunity_score
            validities.append(v)
            opportunities.append(o)

            exp_v = ann.get("expected_validity_range", [0, 1])
            exp_o = ann.get("expected_opportunity_range", [0, 1])
            exp_gate = ann.get("expected_gating", "pass")

            v_ok = exp_v[0] <= v <= exp_v[1]
            o_ok = exp_o[0] <= o <= exp_o[1]
            gate_ok = (exp_gate == "pass") == rep.passed_gating

            status = "OK" if (v_ok and o_ok and gate_ok) else "ERRO"
            if status == "ERRO":
                err_details = []
                if not gate_ok:
                    err_details.append(f"gating={'PASS' if rep.passed_gating else 'FAIL'} esperado={exp_gate}")
                if not v_ok:
                    err_details.append(f"validity={v:.3f} fora de [{exp_v[0]:.1f},{exp_v[1]:.1f}]")
                if not o_ok:
                    err_details.append(f"opportunity={o:.3f} fora de [{exp_o[0]:.1f},{exp_o[1]:.1f}]")
                errors.append((bid, err_details))

            print(f"  {bid:<35} {label:<12} v={v:.3f} o={o:.3f} [{status}]")

        avg_v = sum(validities) / len(validities) if validities else 0
        avg_o = sum(opportunities) / len(opportunities) if opportunities else 0
        err_rate = len(errors) / len(items) if items else 0

        category_stats[cat] = {
            "count": len(items),
            "avg_validity": avg_v,
            "avg_opportunity": avg_o,
            "error_count": len(errors),
            "error_rate": err_rate,
            "errors": errors,
        }

        print(f"  >> Média: validity={avg_v:.3f}, opportunity={avg_o:.3f}, erros={len(errors)}/{len(items)}")

    # Summary table
    print(f"\n{'=' * 80}")
    print(f"{'CATEGORIA':<25} {'N':>3} {'AVG_V':>8} {'AVG_O':>8} {'ERROS':>7} {'TAXA':>7}")
    print(f"{'-' * 80}")
    for cat, stats in sorted(category_stats.items(), key=lambda x: -x[1]["error_rate"]):
        cat_label = CATEGORY_LABELS_PT.get(cat, cat)[:24]
        print(f"{cat_label:<25} {stats['count']:>3} {stats['avg_validity']:>8.3f} {stats['avg_opportunity']:>8.3f} {stats['error_count']:>5}/{stats['count']:<2} {stats['error_rate']:>6.0%}")

    # Diagnostic questions
    print(f"\n--- Diagnóstico por categoria ---")

    # Check: does v2 overvalue goal proximity?
    finalizacao = category_stats.get("finalizacao_curta", {})
    others_opp = [s["avg_opportunity"] for c, s in category_stats.items()
                  if c != "finalizacao_curta" and s["avg_opportunity"] > 0]
    avg_others = sum(others_opp) / len(others_opp) if others_opp else 0
    fin_opp = finalizacao.get("avg_opportunity", 0)
    if fin_opp > avg_others * 1.3:
        print(f"  ⚠ Supervaloriza aproximação ao gol: finalização ({fin_opp:.3f}) >> outras ({avg_others:.3f})")
    else:
        print(f"  ✓ Não supervaloriza aproximação ao gol: finalização ({fin_opp:.3f}) vs outras ({avg_others:.3f})")

    # Check: does v2 punish retention plays?
    lateral = category_stats.get("jogada_lateral", {})
    if lateral.get("avg_opportunity", 0.5) < 0.3:
        print(f"  ⚠ Pune demais jogadas de retenção/lateral: opportunity={lateral['avg_opportunity']:.3f}")
    else:
        print(f"  ✓ Jogadas laterais com opportunity razoável: {lateral.get('avg_opportunity', 0):.3f}")

    # Check: positional attack
    posicional = category_stats.get("ataque_posicional", {})
    if posicional.get("error_rate", 0) > 0.5:
        print(f"  ⚠ Alta taxa de erro em ataque posicional: {posicional['error_rate']:.0%}")
    else:
        print(f"  ✓ Ataque posicional OK (taxa de erro: {posicional.get('error_rate', 0):.0%})")

    return category_stats


# =========================================================================
# PART 2: Error Analysis
# =========================================================================

ERROR_TAXONOMY = {
    "erro_fisico": "Erro Físico — gating rejeitou/aceitou incorretamente",
    "erro_alinhamento": "Erro de Alinhamento — residual alto distorceu scores",
    "erro_compactacao": "Erro de Compactação — formação/densidade mal avaliada",
    "erro_cobertura": "Erro de Cobertura — role consistency mal calibrado",
    "erro_decisao": "Erro de Decisão — opportunity score não reflete qualidade tática",
    "erro_proxy_xt": "Erro de Proxy xT — supervaloriza posição no campo",
    "erro_weighting": "Erro de Weighting — pesos entre módulos mal calibrados",
}


def classify_error(bid, ann, report):
    """Classify the root cause of an evaluation error."""
    exp_gate = ann.get("expected_gating", "pass")
    exp_v = ann.get("expected_validity_range", [0, 1])
    exp_o = ann.get("expected_opportunity_range", [0, 1])

    v = report.validity_score
    o = report.opportunity_score
    sm = report.sub_metrics

    gate_ok = (exp_gate == "pass") == report.passed_gating
    v_ok = exp_v[0] <= v <= exp_v[1]
    o_ok = exp_o[0] <= o <= exp_o[1]

    if not gate_ok:
        if exp_gate == "pass" and not report.passed_gating:
            return "erro_fisico", f"Gating rejeitou branch plausível (flags: {report.gating_flags})"
        else:
            return "erro_fisico", f"Gating aceitou branch implausível"

    if not v_ok:
        if sm.alignment_residual > 0.8:
            return "erro_alinhamento", f"Residual alto ({sm.alignment_residual:.2f}) puxou validity para {v:.3f}"
        if sm.plausibility_score < 0.3 and v < exp_v[0]:
            return "erro_fisico", f"Plausibility muito baixa ({sm.plausibility_score:.2f}) para branch plausível"
        return "erro_weighting", f"Validity={v:.3f} fora do esperado [{exp_v[0]:.1f},{exp_v[1]:.1f}]"

    if not o_ok:
        if o > exp_o[1]:
            # Opportunity too high
            if sm.decision_value_score > 0.7 and ann.get("expected_label") in ("worse", "neutral"):
                if report.sub_metrics.scoring_probability_delta > 0.6:
                    return "erro_proxy_xt", f"Opportunity={o:.3f} alta por proximidade ao gol (scoring_prob={sm.scoring_probability_delta:.2f})"
                return "erro_decisao", f"Decision value={sm.decision_value_score:.2f} alto demais para branch {ann.get('expected_label')}"
            if sm.tactical_consistency_score > 0.8:
                return "erro_compactacao", f"Tactical consistency={sm.tactical_consistency_score:.2f} inflou opportunity para {o:.3f}"
            return "erro_weighting", f"Opportunity={o:.3f} acima do esperado [{exp_o[0]:.1f},{exp_o[1]:.1f}]"
        else:
            # Opportunity too low
            if sm.role_consistency_score < 0.3:
                return "erro_cobertura", f"Role consistency={sm.role_consistency_score:.2f} puxou opportunity para baixo"
            if sm.decision_value_score < 0.3:
                return "erro_decisao", f"Decision value={sm.decision_value_score:.2f} baixo demais"
            return "erro_weighting", f"Opportunity={o:.3f} abaixo do esperado [{exp_o[0]:.1f},{exp_o[1]:.1f}]"

    return None, None


def error_analysis(results, ann_map):
    print("\n" + "=" * 100)
    print("PARTE 2: ERROR ANALYSIS")
    print("=" * 100)

    errors_by_type = defaultdict(list)
    all_errors = []

    for r in results:
        ann = ann_map.get(r["id"], {})
        report = r["report"]

        exp_v = ann.get("expected_validity_range", [0, 1])
        exp_o = ann.get("expected_opportunity_range", [0, 1])
        exp_gate = ann.get("expected_gating", "pass")

        v = report.validity_score
        o = report.opportunity_score
        gate_ok = (exp_gate == "pass") == report.passed_gating
        v_ok = exp_v[0] <= v <= exp_v[1]
        o_ok = exp_o[0] <= o <= exp_o[1]

        if not (gate_ok and v_ok and o_ok):
            err_type, err_detail = classify_error(r["id"], ann, report)
            if err_type:
                errors_by_type[err_type].append((r["id"], err_detail))
                all_errors.append({
                    "id": r["id"],
                    "label": r["label"],
                    "category": ann.get("play_category", "?"),
                    "error_type": err_type,
                    "detail": err_detail,
                    "validity": v,
                    "opportunity": o,
                })

    if not all_errors:
        print("\n  ✓ Nenhum erro encontrado! Todos os branches dentro das faixas esperadas.")
        return {}, all_errors

    print(f"\n  Total de erros: {len(all_errors)}/{len(results)} branches")

    # Error table
    print(f"\n{'ID':<35} {'LABEL':<10} {'TIPO':<20} {'DETALHE'}")
    print("-" * 100)
    for e in all_errors:
        detail = e["detail"][:50] if len(e["detail"]) > 50 else e["detail"]
        print(f"{e['id']:<35} {e['label']:<10} {e['error_type']:<20} {detail}")

    # Error distribution
    print(f"\n--- Distribuição de erros por tipo ---")
    print(f"{'TIPO':<25} {'COUNT':>5} {'%':>6}  DESCRIÇÃO")
    print("-" * 90)
    for err_type, items in sorted(errors_by_type.items(), key=lambda x: -len(x[1])):
        pct = len(items) / len(all_errors) * 100
        desc = ERROR_TAXONOMY.get(err_type, err_type)[:45]
        print(f"{err_type:<25} {len(items):>5} {pct:>5.0f}%  {desc}")

    # Error by category
    print(f"\n--- Erros por categoria de jogada ---")
    cat_errors = defaultdict(int)
    cat_total = defaultdict(int)
    for r in results:
        ann = ann_map.get(r["id"], {})
        cat = ann.get("play_category", "?")
        cat_total[cat] += 1
    for e in all_errors:
        cat_errors[e["category"]] += 1

    for cat in sorted(cat_total.keys()):
        errs = cat_errors.get(cat, 0)
        total = cat_total[cat]
        cat_label = CATEGORY_LABELS_PT.get(cat, cat)
        bar = "█" * errs + "░" * (total - errs)
        print(f"  {cat_label:<25} {bar} {errs}/{total}")

    return errors_by_type, all_errors


# =========================================================================
# PART 3: V3 Recommendation
# =========================================================================

def v3_recommendation(errors_by_type, all_errors):
    print("\n" + "=" * 100)
    print("PARTE 3: RECOMENDAÇÃO PARA V3")
    print("=" * 100)

    if not all_errors:
        print("\n  Sem erros significativos. Opções para v3:")
        print("  - Adicionar mais branches ao benchmark (20-50)")
        print("  - Testar com dados reais de tracking")
        print("  - Adicionar módulo de pressure model para cenários mais complexos")
        return

    # Find dominant error type
    dominant = max(errors_by_type.items(), key=lambda x: len(x[1])) if errors_by_type else (None, [])
    dominant_type = dominant[0]
    dominant_count = len(dominant[1])
    total_errors = len(all_errors)
    dominant_pct = dominant_count / total_errors * 100 if total_errors > 0 else 0

    print(f"\n  Erro dominante: {dominant_type} ({dominant_count}/{total_errors} = {dominant_pct:.0f}%)")
    print(f"  Descrição: {ERROR_TAXONOMY.get(dominant_type, '?')}")

    # Decision tree
    if dominant_type in ("erro_decisao", "erro_proxy_xt"):
        print(f"\n  >>> CASO A — Problema de decisão")
        print(f"  A v2 está premiando branches agressivas porém ruins,")
        print(f"  ou supervalorizando posição no campo.")
        print(f"")
        print(f"  Próximo módulo recomendado:")
        print(f"    - Pressure model: avaliar pressão defensiva sobre o portador")
        print(f"    - Pass lane model: avaliar qualidade das linhas de passe")
        print(f"    - Ajustar scoring_probability para considerar contexto defensivo")

    elif dominant_type in ("erro_compactacao", "erro_cobertura"):
        print(f"\n  >>> CASO B — Problema de coerência coletiva")
        print(f"  A v2 aceita shapes estranhos ou não avalia bem")
        print(f"  a consistência tática.")
        print(f"")
        print(f"  Próximo módulo recomendado:")
        print(f"    - Tactical consistency v2: avaliar compactação, linhas defensivas")
        print(f"    - Density model: medir densidade de jogadores por zona")
        print(f"    - Role-aware formation scoring")

    elif dominant_type == "erro_weighting":
        print(f"\n  >>> CASO C — Problema de calibração")
        print(f"  Os pesos entre módulos estão mal calibrados para")
        print(f"  certos tipos de jogada.")
        print(f"")
        print(f"  Próximo passo recomendado:")
        print(f"    - Calibração de pesos por tipo de lance (corredor vs passe)")
        print(f"    - Threshold adaptativo baseado no contexto da jogada")
        print(f"    - Expandir benchmark para 50+ branches com mais variedade")

    elif dominant_type == "erro_fisico":
        print(f"\n  >>> Problema de gating/plausibility")
        print(f"  O módulo físico está rejeitando/aceitando incorretamente.")
        print(f"")
        print(f"  Próximo passo recomendado:")
        print(f"    - Revisar thresholds de velocidade e aceleração")
        print(f"    - Considerar velocidade por posição (WR vs OL)")
        print(f"    - Adicionar contexto de aceleração/desaceleração por fase da jogada")

    elif dominant_type == "erro_alinhamento":
        print(f"\n  >>> Problema de alinhamento")
        print(f"  O módulo de alignment está gerando residuais altos")
        print(f"  que distorcem os scores downstream.")
        print(f"")
        print(f"  Próximo passo recomendado:")
        print(f"    - Revisar lógica de spatial alignment")
        print(f"    - Considerar alignment por player em vez de média global")
        print(f"    - Reduzir peso do alignment residual na fórmula de validity")

    # Summary
    print(f"\n  --- Resumo executivo ---")
    print(f"  Erros totais: {total_errors}/{len(all_errors) + (15 - total_errors)} branches")
    print(f"  Erro dominante: {dominant_type} ({dominant_pct:.0f}%)")
    print(f"  Categorias mais afetadas: ", end="")
    cat_err_counts = defaultdict(int)
    for e in all_errors:
        cat_err_counts[e["category"]] += 1
    worst_cats = sorted(cat_err_counts.items(), key=lambda x: -x[1])[:3]
    print(", ".join(f"{CATEGORY_LABELS_PT.get(c, c)} ({n})" for c, n in worst_cats))


def main():
    benchmark, ann_map = load_data()
    results = evaluate_all_branches(benchmark)

    category_stats = category_analysis(results, ann_map)
    errors_by_type, all_errors = error_analysis(results, ann_map)
    v3_recommendation(errors_by_type, all_errors)


if __name__ == "__main__":
    main()
