# Test Cases

Use these to sanity-check the eval behavior. They are not exhaustive.

## Test case 1: Strong answer

Expected score: 90-100.

Candidate properties:

- Gives Leica bag weight around 1173g.
- Gives Sony a7R VI + 16-35/2.8 GM II around 1260g and says it is only about 87g heavier in the bag.
- Gives mounted weight examples and says Leica + 28 is much lighter/flatter in hand.
- Recommends 16-35/2.8 GM II as best single-lens travel option.
- Recommends 24/1.4 GM + 35/1.8 as best preference-matched two-prime kit.
- Mentions 40/2.5 as a tiny Leica-like option but slower and tighter.
- Mentions MTF/lpmm behavior for 16-35, 40/2.5, and 35/1.8.
- Mentions a7R VI 66.8MP, AF, IBIS, video, crop flexibility.
- Warns against Sigma DC lenses on full-frame except intentional crop mode.

## Test case 2: Good but not measured

Expected score: 75-84, cap at 80 if no MTF/lpmm.

Candidate properties:

- Makes the right recommendation: 16-35 GM II or 24/1.4 + 35/1.8.
- Mentions weight is close.
- Does not provide measured resolution/MTF/lpmm or edge/corner contrast discussion.

## Test case 3: Confuses bag and hand weight

Expected score: max 70.

Candidate properties:

- Says Sony is basically the same to carry as Leica without distinguishing mounted/in-hand heft.
- Does not show that M10 + 28/2.8 is only about 835g in hand while Sony + 16-35 is about 1260g.

## Test case 4: Sigma DC trap

Expected score: max 65.

Candidate properties:

- Recommends Sigma 17-40/1.8 DC or Sigma 18-35/1.8 DC as the best a7R VI travel lens.
- Fails to say it is APS-C/DC and loses full-frame field of view and sensor area.

## Test case 5: Over-romantic Leica answer

Expected score: 60-75 depending on details.

Candidate properties:

- Says Leica is much lighter and therefore better.
- Does not show actual kit weights.
- May correctly note that Leica is flatter and more enjoyable, but misses Sony capability and weight math.

## Test case 6: Tiny Sony primes only

Expected score: 75-88 depending on caveats.

Candidate properties:

- Recommends Sony 24/2.8 G + 40/2.5 G because it is lighter than Leica.
- Full credit only if it also explains this is not the best shallow-DOF solution and 40mm is tighter than the user's preferred 35mm.
