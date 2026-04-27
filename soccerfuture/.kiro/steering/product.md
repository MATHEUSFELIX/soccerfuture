---
inclusion: always
---

# Product Overview

This project evaluates soccer (association football) play simulation branches by comparing them against real continuation windows. Each branch is scored on physical validity and tactical opportunity, with gating logic to reject impossible or incoherent outcomes.

## Domain Context

- A "branch" is a simulated continuation of a real soccer play from a specific decision point.
- A "continuation window" is the set of plausible real-world outcomes from that same point.
- Evaluation determines whether a branch is physically possible, tactically meaningful, and worth surfacing to analysts.

## Target Users

- Soccer analysts reviewing simulated play outcomes
- Tactical researchers studying decision-point alternatives
- Sports AI engineers building or consuming branch generation pipelines

## Core Outputs

Every evaluation produces a branch-level report containing:

| Output             | Description                                                  |
|--------------------|--------------------------------------------------------------|
| `validity_score`   | How physically plausible the branch is (0–1)                 |
| `opportunity_score`| Tactical value relative to the real continuation window (0–1)|
| `gating_flags`     | Boolean flags that hard-reject invalid branches              |
| `explanations`     | Human-readable reasons for any gating failures or low scores |

## Product Conventions

- Scores are always normalized to the 0–1 range. Never return raw or unbounded values.
- Gating is binary: a branch either passes all gates or is rejected. No partial gating.
- Every rejection must include a human-readable explanation. Silent failures are not acceptable.
- Evaluation results must be fully serializable to JSON for downstream consumption.
- Scoring dimensions (validity, opportunity, gating) are independent. Do not couple their logic.
- Prefer transparency over brevity: sub-metrics should always accompany aggregate scores so analysts can trace how a score was derived.
