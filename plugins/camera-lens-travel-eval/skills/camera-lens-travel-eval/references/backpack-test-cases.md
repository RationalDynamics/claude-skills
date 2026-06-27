# Business Backpack Test Cases

Use these to sanity-check the eval behavior. They are not exhaustive.

## Test case 1: Strong answer

Expected score: 90-100.

Candidate properties:

- Recommends Aer Travel Pack 4 28L as top pick.
- Gives top four: Aer TP4, EVERGOODS CTB26, Black Ember H2, Patagonia Mini MLC.
- Correctly states external bottle pockets, luggage pass-through, 16-inch laptop support, and approximate size/weight for the top options.
- Explains under-seat plausible but not guaranteed.
- Explains camera-sling fit and why Aer TP4 gives more room than CTB20/CPP2.
- Flags Patagonia's laptop caveat and H2's rigidity.
- Compares Osprey Radial 26 as too deep/framed/no pass-through and already disliked.

## Test case 2: CTB26-first but good

Expected score: 82-92 depending on Aer treatment.

Candidate properties:

- Recommends CTB26 first based on backpack-native function and comfort.
- Still identifies Aer TP4 28L as the user's final/top business-travel target or close second.
- Correctly covers water, pass-through, 16-inch laptop, under-seat caveats, and camera nesting.

## Test case 3: CTB20 overfit

Expected score: max 70.

Candidate properties:

- Recommends CTB20 because it fits under airplane seats better.
- Ignores that the user's normal load includes lunch, jacket, camera sling, laptop, iPad, and cables.
- Does not explain the capacity tradeoff.

## Test case 4: Black Ember-only answer

Expected score: 70-84 depending on coverage.

Candidate properties:

- Recommends Black Ember H2 as the main pick.
- Correctly covers water, pass-through, 16-inch laptop, premium style.
- Loses points if it ignores Aer TP4, CTB26, or the H2 rigidity/camera-nesting caveat.

## Test case 5: Generic backpack answer

Expected score: below 60.

Candidate properties:

- Recommends generic backpacks or camera backpacks without considering luggage pass-through, water, business style, or the final Aer TP4 conclusion.
- No dimensions or under-seat reasoning.

## Test case 6: Patagonia Mini MLC answer

Expected score: 70-86 depending on caveats.

Candidate properties:

- Recommends Mini MLC for open travel packing and value.
- Full credit requires flagging 16-inch laptop uncertainty, less premium business style/harness, and that it is better as an airport/hotel travel container than quick-access camera backpack.
