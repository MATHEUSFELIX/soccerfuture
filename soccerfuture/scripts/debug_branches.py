import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.simulation_evaluator_v2 import evaluate_branch
from src.utils.serialization import report_to_dict

with open("data/benchmark_input.json") as f:
    data = json.load(f)

for idx in [12, 13, 14]:
    b = data["branches"][idx]
    w = data["continuation_windows"][idx]
    r = evaluate_branch(b, w)
    d = report_to_dict(r)
    sm = d["sub_metrics"]
    print(f"{b['branch_id']}:")
    print(f"  gating={d['passed_gating']} validity={d['validity_score']:.3f} opportunity={d['opportunity_score']:.3f}")
    print(f"  similarity={sm['branch_window_similarity']:.3f} tactical={sm['tactical_consistency_score']:.3f}")
    print(f"  decision_value={sm['decision_value_score']:.3f} turnover_delta={sm['turnover_risk_delta']:.3f}")
    if d["explanations"]:
        print(f"  explanations: {d['explanations'][:2]}")
    print()
