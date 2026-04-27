"""Mini benchmark: run evaluator v2 on 15 manually-classified branches.

Labels:
  plausible   — physically realistic, should pass gating
  implausible — physically impossible, should be rejected
  better      — tactically superior to reality
  worse       — tactically inferior to reality
  neutral     — roughly equivalent to reality

Usage:
    python scripts/run_benchmark.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulation_evaluator_v2 import evaluate_branch
from src.utils.serialization import report_to_dict


def main() -> None:
    with open("data/benchmark_input.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    branches = data["branches"]
    windows = data["continuation_windows"]

    results: list[dict] = []
    for i, branch in enumerate(branches):
        window = windows[i] if i < len(windows) else {}
        report = evaluate_branch(branch, window)
        label = branch.get("expected_label", "?")
        results.append({
            "id": branch["branch_id"],
            "label": label,
            "passed_gating": report.passed_gating,
            "passed_validity": report.passed_validity,
            "validity": round(report.validity_score, 3),
            "opportunity": round(report.opportunity_score, 3),
            "explanations": report.explanations[:2],
        })

    # ── Print results table ──
    print("=" * 100)
    print(f"{'ID':<35} {'LABEL':<14} {'GATING':<8} {'VALID':<8} {'VALIDITY':>9} {'OPPORT':>9}  NOTES")
    print("-" * 100)
    for r in results:
        gate = "PASS" if r["passed_gating"] else "FAIL"
        valid = "PASS" if r["passed_validity"] else "FAIL"
        notes = "; ".join(r["explanations"][:1]) if r["explanations"] else ""
        if len(notes) > 35:
            notes = notes[:32] + "..."
        print(f"{r['id']:<35} {r['label']:<14} {gate:<8} {valid:<8} {r['validity']:>9.3f} {r['opportunity']:>9.3f}  {notes}")

    # ── Evaluate accuracy ──
    print("\n" + "=" * 100)
    print("BENCHMARK ANALYSIS")
    print("=" * 100)

    # 1. Did it reject all implausible branches?
    implausible = [r for r in results if r["label"] == "implausible"]
    implausible_rejected = sum(1 for r in implausible if not r["passed_gating"])
    print(f"\n1. Implausible rejection:  {implausible_rejected}/{len(implausible)} rejected at gating")
    for r in implausible:
        status = "REJECTED" if not r["passed_gating"] else "MISSED!"
        print(f"   {r['id']}: {status}")

    # 2. Did it pass all plausible branches?
    plausible = [r for r in results if r["label"] == "plausible"]
    plausible_passed = sum(1 for r in plausible if r["passed_gating"])
    print(f"\n2. Plausible acceptance:   {plausible_passed}/{len(plausible)} passed gating")
    for r in plausible:
        status = "PASSED" if r["passed_gating"] else "FALSE REJECT!"
        print(f"   {r['id']}: {status} (validity={r['validity']:.3f})")

    # 3. Did "better" branches score higher opportunity than "worse"?
    better = [r for r in results if r["label"] == "better"]
    worse = [r for r in results if r["label"] == "worse"]
    neutral = [r for r in results if r["label"] == "neutral"]

    avg_better_opp = sum(r["opportunity"] for r in better) / len(better) if better else 0
    avg_worse_opp = sum(r["opportunity"] for r in worse) / len(worse) if worse else 0
    avg_neutral_opp = sum(r["opportunity"] for r in neutral) / len(neutral) if neutral else 0

    print(f"\n3. Opportunity ranking:")
    print(f"   Better avg opportunity:  {avg_better_opp:.3f}")
    print(f"   Neutral avg opportunity: {avg_neutral_opp:.3f}")
    print(f"   Worse avg opportunity:   {avg_worse_opp:.3f}")
    ranking_ok = avg_better_opp >= avg_neutral_opp >= avg_worse_opp
    print(f"   Ranking correct (better >= neutral >= worse): {'YES' if ranking_ok else 'NO'}")

    # 4. Did worse-than-reality branches get opportunity < 0.5?
    worse_below_half = sum(1 for r in worse if r["opportunity"] < 0.5)
    print(f"\n4. Worse branches below 0.5 opportunity: {worse_below_half}/{len(worse)}")
    for r in worse:
        status = "OK (<0.5)" if r["opportunity"] < 0.5 else f"HIGH ({r['opportunity']:.3f})"
        print(f"   {r['id']}: opportunity={r['opportunity']:.3f} — {status}")

    # 5. Trap check: did any branch get high opportunity just for being near the end zone?
    print(f"\n5. End-zone proximity trap check:")
    b09 = next((r for r in results if r["id"] == "B09-better-td-opportunity"), None)
    if b09:
        print(f"   B09 (TD near end zone): opportunity={b09['opportunity']:.3f}, validity={b09['validity']:.3f}")
        if b09["opportunity"] > 0.7:
            print("   -> High opportunity justified by TD event + end zone position")
        elif b09["opportunity"] == 0.0 and not b09["passed_validity"]:
            print("   -> Opportunity=0 because validity below threshold (not a false positive)")

    # ── Summary ──
    total_checks = 4
    passed_checks = sum([
        implausible_rejected == len(implausible),
        plausible_passed == len(plausible),
        ranking_ok,
        worse_below_half == len(worse),
    ])
    print(f"\n{'=' * 100}")
    print(f"SCORE: {passed_checks}/{total_checks} checks passed")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
