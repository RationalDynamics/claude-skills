---
name: camera-lens-travel-eval
description: evaluate model answers about the user's camera travel gear decisions, including sony/leica travel lens kits, premium business-travel backpacks that can hold a 16-inch macbook plus camera carry, and small leica sling/camera-bag options with water-bottle tradeoffs. use when grading or line-selecting an lm output against this discussion, especially whether it preserves the final backpack conclusion favoring the aer travel pack 4 28l, correctly compares black ember h2, patagonia mini mlc, evergoods ctb26/ctb20, and evaluates 3-5l leica bags such as moment, wotancraft, think tank, peak, and domke-style alternatives.
---

# Camera Lens And Travel Gear Eval

Use this skill to grade a candidate LM answer to one of the user's camera travel gear discussions. The evaluator should produce a line-selected, evidence-backed score rather than a general opinion.

The skill supports three eval modes:

1. `lens-kit`: Sony a7R VI/a7R V versus Leica M10 travel lens choices.
2. `business-backpack`: quality business-travel backpack for a 16-inch MacBook, iPad, lunch, jacket, cables, water bottle, luggage pass-through, and optional camera/sling carry.
3. `leica-water-sling`: 3-5L Leica M10 sling/satchel/camera-bag options that can hold Leica M10 + 28mm + 50mm and support water somehow without becoming too camera-y.

## Inputs

Expect one of these inputs:

1. A candidate LM answer only.
2. The original prompt plus a candidate LM answer.
3. A file containing one or more candidate answers.

If the candidate answer has no line numbers, create stable line or sentence IDs before grading. Do not ask for clarification unless the candidate answer itself is missing.

## Mode selection

Infer the eval mode from the prompt or candidate answer.

- Use `lens-kit` for Sony/Leica lens kit comparisons, a7R VI/a7R V, 16-35 GM II, 24/35 primes, crop mode, MTF/lpmm, or Leica M10 lens-kit reasoning.
- Use `business-backpack` for backpack choices such as Aer Travel Pack 4 28L, Black Ember Citadel H2, Patagonia Mini MLC, EVERGOODS CTB26/CTB20, Osprey Radial, luggage pass-through, under-seat fit, 16-inch laptop, water-bottle pockets, and camera-bag nesting.
- Use `leica-water-sling` for small camera slings/satchels such as Moment Everything 4L, Moment Slate 4L, Wotancraft Pilot 3.5L/7L, Think Tank TurnStyle 5L V3, Peak Everyday Sling 3L/6L, Domke F8/F-803, bottle carry, and Leica M10 + 28/50 fit.
- If an answer covers both backpack and sling choices, grade the requested section if the user specified one. If not, grade both modes separately and average the final score only if the candidate attempts both.

## Required references

Always load:

- `references/line-selection-protocol.md` for evidence selection rules.
- `references/output-template.md` for the required grading format.

Load mode-specific references before grading:

### Lens-kit mode

- `references/gold-facts.md`
- `references/rubric.md`
- `references/expected-reasoning-traces.md`

### Business-backpack mode

- `references/backpack-gold-facts.md`
- `references/backpack-rubric.md`
- `references/backpack-expected-reasoning-traces.md`

### Leica-water-sling mode

- `references/leica-sling-gold-facts.md`
- `references/leica-sling-rubric.md`
- `references/leica-sling-expected-reasoning-traces.md`

Use `references/test-cases.md`, `references/backpack-test-cases.md`, or `references/leica-sling-test-cases.md` only when building or validating an eval harness. Use `references/source-notes.md` only when checking source provenance or updating factual assumptions. Use `references/prompt-library.md` when generating eval prompts or examples.

## Evaluation workflow

1. Normalize the prompt context. Preserve user-specific discoveries from the discussion, especially tried-and-rejected options.
2. Number the candidate answer. Prefer original line numbers if present. Otherwise split into short paragraphs or sentences and label them `L001`, `L002`, etc.
3. Select evidence lines. For every scored criterion, cite the candidate's exact line IDs or mark `MISSING`, `CONTRADICTED`, `UNSUPPORTED`, or `AMBIGUOUS`.
4. Score against the appropriate rubric. Apply score caps for critical errors before assigning the final score.
5. Provide a compact corrected answer. Include the minimum facts the answer should have contained, not a full rewrite.

## Output requirements

Return:

- A verdict: pass, borderline, or fail.
- A numeric score out of 100.
- The eval mode used.
- A line-evidence table with selected lines and points awarded.
- Critical misses and hallucinations.
- A corrected answer skeleton.
- A one-sentence recommendation for how to improve the candidate answer.

## Grading stance

Be strict about preserving the user's actual constraints and discoveries, not just spec-sheet popularity. Award full credit for materially correct reasoning even if dimensions or weights are rounded. Penalize answers that recommend generic camera bags without respecting style, water, luggage pass-through, under-seat geometry, actual fit of nested slings, or tried-and-rejected bags.
