# Gold Facts And Expected Conclusions

This file defines the factual baseline for the eval. The evaluator should grade candidate answers against these facts, allowing small rounding differences.

## Normalized shorthand

- `a7r6`, `a7R6`, `a7R VI`, and `ILCE-7RM6` refer to the Sony a7R VI.
- `16 to 30 528`, `16-35 2.8`, and `16-35 GM II` should be interpreted as Sony FE 16-35mm f/2.8 GM II when the travel zoom context is clear.
- `bag weight` means total weight carried in the bag.
- `hand weight`, `mounted weight`, or `in-hand weight` means body plus the one lens currently mounted.

## Camera bodies

| Item | Accepted facts |
| --- | --- |
| Sony a7R VI | 713g with battery and memory card; 66.8MP effective stills; APS-C crop large stills are 28MP; full-frame body; Fast Hybrid AF; 5-axis sensor-shift IBIS rated 8.5 stops center / 7.0 stops periphery; 8K/4K video features; 132.7 x 96.9 x 82.9mm max body dimensions. |
| Leica M10 | 660g with battery; 24MP full-frame stills; manual-focus rangefinder; no modern AF/IBIS/video package comparable to a7R VI; about 139 x 80 x 38.5mm, so much flatter than the Sony body. |

## Lens weights and roles

| Lens | Format / role | Weight | Key evaluation notes |
| --- | --- | ---: | --- |
| Sony FE 16-35mm f/2.8 GM II | Full-frame wide travel zoom | 547g | The best single-lens answer in this discussion: true 16-35mm, full-frame, high across-frame resolution, f/2.8, native AF, only modestly heavier in bag than the Leica two-prime kit. |
| Sony FE 24mm f/1.4 GM | Full-frame fast wide prime | 445g | Best fast travel-wide prime for shallow depth of field, low light, and high resolution. Strong partner to FE 35mm f/1.8. |
| Sony FE 35mm f/1.8 | Full-frame light default prime | 280g | Best lightweight 35mm default for this user; much lighter than Sony Zeiss 35mm f/1.4 ZA or Sony 35mm f/1.4 GM; better shallow-DOF fit than 40/2.5. |
| Sony FE 40mm f/2.5 G | Full-frame compact normal prime | 173g | Extremely small and sharp, but 40mm is tighter than the user's preferred 35mm and f/2.5 is not a Summilux-like shallow-DOF lens. Good Leica-like carry experience. |
| Sony FE 24mm f/2.8 G | Full-frame compact wide prime | 162g | Useful tiny travel-wide sibling to 40/2.5; very light but loses shallow-DOF appeal versus 24/1.4 GM. |
| Sigma 17-40mm f/1.8 DC Art for Sony E | APS-C DC lens | 525g for Sony E | Not a primary recommendation for a7R VI. It uses APS-C crop on full frame, gives 25.5-60mm equivalent field of view, and uses only the APS-C portion of the sensor. Good for a6700/FX30-style bodies. |
| Sigma 18-35mm f/1.8 DC HSM Art | APS-C DSLR-era DC lens | 810g before adapter | Not a good a7R VI travel choice. APS-C only, adapted if using Sony E, heavy, roughly 27-52.5mm equivalent in crop, and not truly wide on full frame. |
| Leica Elmarit-M 28mm f/2.8 ASPH | Leica M tiny wide prime | 175g | The compactness winner when mounted on M10; f/2.8 and manual focus. |
| Leica Summilux-M 35mm f/1.4 ASPH, current | Leica M fast 35mm prime | 338g | Gives f/1.4 rendering in a small M lens; manual focus; current close-focus ASPH version is heavier than older classic versions. |

## Kit weight math

A strong answer should compute or accurately describe both bag weight and hand weight.

### Bag weight

| Kit | Calculation | Total | Comparison |
| --- | --- | ---: | --- |
| Leica M10 + 28/2.8 Elmarit + 35/1.4 Summilux | 660 + 175 + 338 | 1173g / 2.59 lb | Baseline Leica two-prime kit. |
| Sony a7R VI + 16-35/2.8 GM II | 713 + 547 | 1260g / 2.78 lb | About 87g / 3.1 oz heavier than Leica two-prime kit; surprisingly close in bag weight. |
| Sony a7R VI + 24/1.4 GM + 35/1.8 | 713 + 445 + 280 | 1438g / 3.17 lb | About 265g / 9.3 oz heavier than Leica kit; best two-prime answer for shallow DOF plus resolution. |
| Sony a7R VI + 24/2.8 G + 40/2.5 G | 713 + 162 + 173 | 1048g / 2.31 lb | Lighter than Leica kit, but not as shallow-DOF-oriented and 40mm may be too tight. |

### Mounted / in-hand weight

| Mounted kit | Calculation | Total | Interpretation |
| --- | --- | ---: | --- |
| Leica M10 + 28/2.8 Elmarit | 660 + 175 | 835g / 1.84 lb | Very light and flat in hand. |
| Leica M10 + 35/1.4 Summilux | 660 + 338 | 998g / 2.20 lb | Similar scale weight to Sony a7R VI + 35/1.8. |
| Sony a7R VI + 35/1.8 | 713 + 280 | 993g / 2.19 lb | Essentially the same weight as M10 + 35 Summilux, but bulkier due to grip/body depth. |
| Sony a7R VI + 40/2.5 G | 713 + 173 | 886g / 1.95 lb | Lighter than M10 + 35 Summilux, but tighter and slower. |
| Sony a7R VI + 24/1.4 GM | 713 + 445 | 1158g / 2.55 lb | Heavier in hand but still far lighter than old 24-70 GM style kit. |
| Sony a7R VI + 16-35/2.8 GM II | 713 + 547 | 1260g / 2.78 lb | Good bag-weight efficiency, but clearly larger and heavier in hand than M10 + 28. |

## Expected winner logic

A high-scoring answer should say something close to this:

1. The Leica kit still wins on compactness, flatness, and shooting romance, especially M10 + 28/2.8 mounted.
2. The Sony kit is not much heavier in bag weight if the single lens is the FE 16-35mm f/2.8 GM II: 1260g versus 1173g for the Leica two-prime kit.
3. The Sony FE 16-35mm f/2.8 GM II is the most viable light, high-resolution, full-frame travel zoom option because it uses the whole sensor, reaches true 16mm, has f/2.8, and has strong across-frame MTF.
4. The ideal two-prime Sony kit for the user's taste is FE 24mm f/1.4 GM plus FE 35mm f/1.8. It is heavier than the Leica kit by about 265g, but gives fast apertures, shallow DOF, AF, IBIS, video, and full 66.8MP files.
5. The tiny FE 24/2.8 G plus FE 40/2.5 G option is an interesting ultralight Sony-as-Leica carry kit, but it is not the best answer for shallow depth of field or a 35mm-default shooter.
6. Sigma DC lenses are not primary recommendations on a7R VI because they are APS-C lenses and throw away full-frame field of view and sensor area.

## Stabilization note

Do not reward answers that imply the discussed Sony lenses provide OSS unless they are careful. The important stabilization advantage here is the a7R VI body's five-axis IBIS. The Sony 16-35/2.8 GM II and 24/2.8 G list image stabilization as body-integrated, not lens optical stabilization.
