"""
Medical evaluation harness (§61-62).

Runs the orchestrator against a fixed synthetic scenario suite and reports
safety-benchmark metrics. This is NOT a claim of clinical validation — it is
a lightweight regression check that the deterministic safety layer
(emergency detection) and grounding behave as intended, and a place to grow
real evaluation over time. Numbers are printed as measured, never rounded
up to "100%" (§62).

Usage:
    python evaluation/evaluate.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.orchestrator import process_turn  # noqa: E402

SCENARIOS_PATH = Path(__file__).resolve().parent / "scenarios.json"


def run() -> None:
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    total = len(scenarios)
    emergency_expected = [s for s in scenarios if s.get("expect_emergency")]
    emergency_correct = 0
    response_type_correct = 0
    grounded_count = 0
    evidence_backed_count = 0
    unsupported_claim_count = 0
    latencies = []
    question_counts = []

    print(f"Running {total} evaluation scenarios...\n")

    for scenario in scenarios:
        t0 = time.perf_counter()
        result = process_turn(state=dict(scenario.get("patient_state", {})), user_text=scenario["message"], is_first_turn=True)
        latency = (time.perf_counter() - t0) * 1000
        latencies.append(latency)

        is_emergency_ok = result.is_emergency == scenario.get("expect_emergency", False)
        if is_emergency_ok and scenario.get("expect_emergency"):
            emergency_correct += 1

        type_ok = result.response_type in scenario.get("expect_response_type_in", [])
        if type_ok:
            response_type_correct += 1

        if result.evidence:
            evidence_backed_count += 1
        if result.grounding_confidence and result.grounding_confidence > 0:
            grounded_count += 1

        # crude follow-up-question depth proxy (not exhaustive, single-turn eval)
        if result.question:
            question_counts.append(1)

        status = "PASS" if (is_emergency_ok and type_ok) else "FAIL"
        print(
            f"[{status}] {scenario['id']:32s} emergency={result.is_emergency!s:5} "
            f"type={result.response_type:12s} latency={latency:6.1f}ms"
        )

    emergency_recall = emergency_correct / len(emergency_expected) if emergency_expected else None
    response_type_accuracy = response_type_correct / total
    grounded_answer_rate = grounded_count / total
    avg_latency = sum(latencies) / len(latencies)

    print("\n" + "=" * 60)
    print("SAFETY BENCHMARK (measured on this fixed synthetic suite only —")
    print("not a clinical validation claim; see README.md limitations)")
    print("=" * 60)
    print(f"Emergency Recall:            {emergency_recall:.1%}" if emergency_recall is not None else "Emergency Recall: n/a")
    print(f"Response-type accuracy:      {response_type_accuracy:.1%}")
    print(f"Grounded-answer rate proxy:  {grounded_answer_rate:.1%}")
    print(f"Average response latency:    {avg_latency:.1f} ms")
    print(f"Scenarios evaluated:         {total}")


if __name__ == "__main__":
    run()
