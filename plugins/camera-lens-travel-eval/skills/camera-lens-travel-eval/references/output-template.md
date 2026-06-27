# Output Template

Use this structure for every eval result. Adapt the criterion names to the active mode's rubric.

```markdown
# Camera Travel Gear Eval Result

## Verdict

Eval mode: lens-kit | business-backpack | leica-water-sling  
Score: NN/100  
Result: Pass | Borderline | Fail

One-sentence summary: ...

## Candidate line map

Only include this section if the input had no line numbers. Keep each line short.

- L001: ...
- L002: ...

## Line-selected scoring

| Criterion | Points | Evidence | Notes |
| --- | ---: | --- | --- |
| Criterion 1 from active rubric | X/N | L... | ... |
| Criterion 2 from active rubric | X/N | L... | ... |
| Criterion 3 from active rubric | X/N | L... | ... |
| Criterion 4 from active rubric | X/N | L... | ... |
| Criterion 5 from active rubric | X/N | L... | ... |
| Communication / usefulness | X/N | L... | ... |

Subtotal before caps: NN/100  
Caps applied: None | Max NN because ...

## Critical misses or hallucinations

- ...

## Corrected answer skeleton

A minimally strong answer would say:

1. ...
2. ...
3. ...

## Most important improvement

...
```

## Pass thresholds

- 90-100: Excellent. Correct, quantified, and decision-useful.
- 80-89: Good. Minor omissions, but core conclusion and tradeoffs are right.
- 70-79: Borderline. Some correct conclusions but important missing evidence.
- 60-69: Weak. May have a useful recommendation but contains major gaps.
- Below 60: Fail. Wrong gear logic, wrong constraints, or unsupported conclusion.
