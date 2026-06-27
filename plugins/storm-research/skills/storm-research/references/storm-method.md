# STORM method — faithful reference

STORM = **S**ynthesis of **T**opic **O**utlines through **R**etrieval and **M**ulti-perspective
question asking (Stanford OVAL, [paper](https://arxiv.org/abs/2402.14207),
[repo](https://github.com/stanford-oval/storm)). It generates cited, Wikipedia-style long-form by
doing the research *before* the writing. This skill reimplements the method natively; the four
modules below are the contract.

## The two stages and four modules

**Pre-writing stage**

1. **Knowledge curation.** Discover multiple *perspectives* on the topic, then for each perspective
   simulate a multi-turn conversation between a *writer* (asks questions) and an *expert* (answers,
   grounded in web search). Save claim-level evidence. This is where breadth and grounding come from.
2. **Outline generation.** Produce a *naive* outline from the model's prior knowledge, then a
   *refined* outline informed by the curated evidence. The refined outline is authoritative.

**Writing stage**

3. **Article generation.** Write the article section by section, each section grounded in the
   retrieved evidence, with inline citations.
4. **Article polishing.** Add a lead/summary section, remove duplicated content, smooth transitions,
   finalize citations.

The original pipeline emits staged files (`conversation_log.json`, `raw_search_results.json`,
`storm_gen_outline.txt`, `url_to_info.json`, `storm_gen_article.txt`,
`storm_gen_article_polished.txt`). We mirror that staging with friendlier names — see
`output-contracts.md`.

## Perspective discovery

STORM seeds research with *perspectives* because a single point of view misses "unknown unknowns."
A perspective is a persona/lens with its own information needs.

- Derive **3–6** perspectives that are genuinely distinct (different stakeholders, mechanisms,
  timelines, controversies, applications, or disciplinary lenses) — not rephrasings of each other.
- Optionally **seed** discovery by surveying existing overview/encyclopedia articles on the topic
  (or close topics) and extracting the recurring themes and the kinds of experts who write about it.
- For a contested or multi-stakeholder topic, deliberately include opposing perspectives.
- Each perspective carries 3–5 **key questions** it would investigate first.

## The simulated research conversation (per perspective)

This is the heart of knowledge curation. Each perspective runs its own conversation:

1. **Ask** the most important open question for this perspective.
2. **Retrieve**: run web searches, fetch the most promising sources, read them.
3. **Emit evidence notes** — one atomic note per discrete factual claim, each anchored to a source
   actually fetched (URL + title + supporting snippet).
4. **Gap check**: what did the answer leave open or raise?
5. **Follow up** (bounded — up to 2 follow-ups) on the most important gaps, repeating retrieval.
6. Record any questions that could not be resolved from available sources as `open_questions`.

Keep notes atomic (one claim each) so they can be re-sliced per outline section later. Record
disagreement between sources rather than averaging it — mark such notes `contested: true`.

### Research-subagent prompt template (copy, fill the `<...>`)

> You are a researcher investigating **<topic>** from the perspective of **<perspective.name>**
> (focus: <perspective.focus>). First load web tools: call ToolSearch with
> `select:WebSearch,WebFetch`, then use them.
>
> Run a grounded research conversation: (1) ask your most important question; (2) answer it ONLY
> from web search + fetched pages, emitting one evidence note per discrete claim; (3) inspect gaps
> and ask up to **<max_followups, default 2>** follow-up questions, repeating retrieval each time.
> <If recency matters:> Prefer sources dated on/after <recency_cutoff>.
>
> Rules: never assert a source-specific fact without a URL you actually fetched. Prefer primary /
> authoritative sources. If two sources disagree, record both and set `contested: true` — do not
> average them. If you cannot ground a claim, drop it.
>
> Return ONLY this JSON (no prose around it):
> ```json
> {
>   "perspective_id": "<perspective.id>",
>   "conversation": [{"role":"writer|expert","text":"...","queries":["..."]}],
>   "evidence_notes": [{
>     "claim":"single atomic factual claim",
>     "source_url":"https://...","source_title":"...","snippet":"quote/paraphrase from the page",
>     "date_if_available":"YYYY-MM-DD or ''","perspective":"<perspective.id>",
>     "confidence":"high|medium|low","contested":false
>   }],
>   "open_questions": ["questions you could not resolve from available sources"]
> }
> ```

## Outline: naive then refined

- **Naive outline**: sections you'd expect from prior knowledge alone. Fast, ungrounded — it exists
  to be improved and to expose your priors.
- **Refined outline**: reconcile the naive outline with the evidence pool. Merge/split/reorder so
  that **every section is supported by evidence** and **every perspective is represented somewhere**.
  Tag each section with the perspectives and candidate `source_ids` that feed it, and an
  `evidence_strength` of strong/moderate/thin. Drop sections the evidence cannot support; add
  sections the evidence demands.

**Perspective→section coverage rule:** before drafting, confirm each discovered perspective maps to
at least one refined-outline section. If one does not, either fold its concerns into an existing
section or add a section — do not silently drop a perspective.

## Drafting and polishing

- Draft **section by section**, each grounded only in its assigned evidence slice, with inline
  `[S#]` markers keyed to the canonical source ids. No source-specific sentence without a marker.
- Present `contested` claims even-handedly ("X reports… while Y finds…").
- Thin section → write briefly and state the limitation; never pad with unsourced generalities.
- **Polish** adds the lead/summary, removes cross-section duplication, smooths transitions, and
  compiles the Open Questions & Uncertainty section. Polishing introduces **no new claims or
  citations** — it only reorganizes and tightens what drafting produced.

### Section-drafting subagent prompt template

> Write the article section **"<heading>"** (intent: <intent>). Use ONLY the evidence notes below
> — do not search for or add new facts. End every sentence carrying a source-specific fact with its
> citation marker like `[S3]`, using the provided ids. When notes conflict (`contested:true`),
> present both sides. If the evidence is thin, write a short section and say so. Plain encyclopedic
> register; no filler.
>
> Evidence notes (JSON): <slice of evidence_pool for this section>
>
> Return ONLY: `{"heading":"...","markdown":"## <heading>\n...with [S#] markers...",
> "citations_used":["S3","S7"],"uncertainty_notes":["weak/contested/unverifiable points"]}`

## Fidelity vs deep-research (don't blur them)

`deep-research` is claim-first and adversarial: fan out searches on one question, verify, answer.
`storm-research` is perspective-first and outline-first: it models *viewpoints*, gathers a reusable
evidence pool, and produces a *sectioned long-form article* whose signature properties are
**perspective balance**, **evidence-first drafting** (no claim without a note), and **explicit
uncertainty**. Keep those three properties — they are why someone picks this over deep-research.
