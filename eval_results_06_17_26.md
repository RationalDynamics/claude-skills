# Camera-gear research eval results — 2026-06-17

Scores from `camera-lens-travel-eval` run on three research tools across three eval modes.
Each tool received the **same blind benchmark prompt** (no rubric or gold-facts leaked) and was
graded against the mode's gold-anchored rubric with line-grounded scoring + score caps.

- **storm-research** — native STORM skill (this repo), single agent, web research + citation audit.
- **deep-research** — built-in deep-research workflow harness (~100 parallel agents).
- **ChatGPT** — browser ChatGPT deep-research output, pasted in; **scored on report text only**.

## Scores

| Eval mode | storm-research | deep-research | ChatGPT |
|---|---:|---:|---:|
| lens-kit | **94** — Pass (excellent) | 65 — Borderline | **82** — Pass (good) |
| business-backpack | **90** — Pass | 58 — Fail | 76 — Borderline |
| leica-water-sling | **73** — Borderline | 46 — Fail | 71 — Borderline |
| **Average** | **85.7** | 56.3 | 76.3 |

Verdict bands: 90-100 excellent · 80-89 good · 70-79 borderline · 60-69 weak · <60 fail.

## Token + cost (measured telemetry; Opus 4.8 rates)

Both storm-research and deep-research ran on Opus 4.8. ChatGPT exposes no token telemetry → n/a.
Dollar figures use the ~$7/MTok "likely" blend (≈90% input / 10% output); the **token counts are
measured**, the dollars are estimates (true cost is lower if cache reads are counted at face value).

| Eval | storm tokens | storm ~$ | deep tokens | deep ~$ | ChatGPT |
|---|---:|---:|---:|---:|---:|
| lens-kit | 164,535 | $1.15 | 2,842,014 | $19.9 | n/a |
| business-backpack | 100,617 | $0.70 | 2,559,300 | $17.9 | n/a |
| leica-water-sling | 120,314 | $0.84 | 2,494,479 | $17.5 | n/a |
| **Total (3 evals)** | **385,466** | **~$2.70** | **7,895,793** | **~$55** | n/a |

deep-research used **~20× the tokens** of storm-research overall (~$55 vs ~$2.70).

## Per-eval one-line summary

- **lens-kit:** storm 94 ≫ ChatGPT 82 > deep 65. Both storm and ChatGPT did the bag-vs-in-hand
  weight math and nailed both recommendations (16-35 GM II single; 24/1.4 GM + 35/1.8 two-prime);
  deep-research gave MTF for only a minor lens and never assembled the weight tables (its cap).
- **business-backpack:** storm 90 > ChatGPT 76 > deep 58. storm ranked the Aer TP4 #1 (gold's
  settled pick) and diagnosed the Osprey shirt-ride-up; ChatGPT and deep both re-litigated to
  City Pack Pro 2 #1 / Aer TP4 #3 (tripping the "doesn't name TP4 as the bag-to-beat" cap, max 82),
  but ChatGPT recovered ground by addressing the Osprey complaint, the Patagonia 15″ caveat, and a
  3L/5L/6-7L sling-nesting matrix that deep skipped.
- **leica-water-sling:** storm 73 ≈ ChatGPT 71 ≫ deep 46. storm + ChatGPT used the gold's Wotancraft
  **Pilot** 3.5L and did careful bottle geometry; deep used the wrong Wotancraft model (Canteener),
  omitted the Moment Slate 4L, and recommended the user's own Sony Domke F-803 as a Leica pick.

## Reading notes / caveats

- **Fixed-baseline effect.** The rubrics encode the user's *settled* conclusions and *tested
  rejections* (Aer TP4 = bag-to-beat; Osprey ride-up; WANDRD/Peak-6L rejected; specific gold-named
  products). Low scores for deep-research and ChatGPT are mostly **gold-mismatch** — re-litigating a
  settled choice, naming a different product variant, or dropping a tested rejection — **not
  hallucinated specs**. All three tools produced accurate, sourced figures.
- **ChatGPT comparability.** Scored on the pasted report text only; no token/cost data, and the run
  wasn't observed end-to-end. Treat its column as quality-of-output, not cost-adjusted.
- **storm self-verification.** Every storm-research report also passed its own citation audit
  (lens 93%, backpack 93%, sling 90%; 0 dangling/ungrounded citations).

## Bottom line

Across all three evals, ranking is **storm-research > ChatGPT > deep-research**, and storm leads on
cost by ~20×. ChatGPT writes strong, well-sourced, table-rich reports and was competitive on the
lens-kit and sling; its recurring weakness (shared with deep-research) is overriding or under-
preserving the user's stated constraints, which these preference-strict evals penalize.
