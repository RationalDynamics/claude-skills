# Line Selection Protocol

Use this protocol to ground every score in the candidate answer.

## Step 1: Create line IDs

If the candidate has no line numbers:

- Split long paragraphs into sentences or short logical chunks.
- Prefix each chunk with `L001`, `L002`, etc.
- Preserve the candidate's wording.
- Do not silently merge separate claims when they affect scoring.

## Step 2: Select evidence

For each rubric criterion, choose the smallest set of lines that proves the point. Evidence can be:

- `L012` for one line.
- `L012-L014` for a range.
- `L012, L018` for separate lines.

Use these labels when evidence is absent or flawed:

- `MISSING`: no relevant claim appears.
- `CONTRADICTED`: the candidate says the opposite of the gold fact.
- `UNSUPPORTED`: the candidate reaches a conclusion but gives no arithmetic or factual support.
- `AMBIGUOUS`: the claim could be correct, but the lens/body/kit is not specified clearly enough.

## Step 3: Quote sparingly

Quote at most a short phrase per evidence item. The line ID is the important part. Avoid long quotations.

## Step 4: Apply score caps

After the initial subtotal, scan for critical failures in `rubric.md`. Apply the strictest cap that fits. Explain the cap with line evidence.

## Step 5: Produce actionable correction

Do not only say the candidate was wrong. Give the specific missing line or reasoning move that would have earned credit, such as:

- Add mounted-weight versus bag-weight table.
- Identify Sigma DC as APS-C crop on full-frame.
- Add MTF/lpmm comparison for 16-35 GM II, 40/2.5, and 35/1.8.
- State that the Sony stabilization advantage is body IBIS, not lens OSS for the lenses discussed.

## Evidence table format

Use this table in the final grading output:

| Criterion | Points | Evidence | Notes |
| --- | ---: | --- | --- |
| Bag vs hand weight | 14/20 | L004-L006 | Correct bag totals, but misses mounted Leica + 28 weight. |
| 16-35 GM II hierarchy | 8/8 | L011 | Correctly names it as best single-lens travel zoom. |
| Sigma crop caveat | 0/15 | CONTRADICTED: L018 | Calls Sigma 17-40 a full-frame lens. |
