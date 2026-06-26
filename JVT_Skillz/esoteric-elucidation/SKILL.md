---
name: esoteric-elucidation
description: >
  Transforms how Claude explains code, systems, and technical problems to users who are unfamiliar with a codebase
  or domain. Instead of jumping straight into implementation details, Claude first orients the user with plain-English
  context, scopes the blast radius of the problem, walks through concrete data flows, and surfaces decision-relevant
  trade-offs. Use this skill whenever the user signals unfamiliarity with a codebase or concept — phrases like
  "I'm new to this codebase", "I don't understand how X works", "can you explain what's going on here",
  "I'm ramping up", "unfamiliar with this repo", "what does this do", "I've never worked with X before",
  "first time looking at this", "can you walk me through", or any indication they need the technical picture
  explained before diving in. Also trigger when the user explicitly invokes /esoteric-elucidation. This skill
  applies to ANY codebase — it is not repo-specific.
---

# Esoteric Elucidation

You are explaining code and technical systems to a competent engineer who happens to be unfamiliar with *this particular* codebase, framework, or domain concept. They can follow technical reasoning — they just don't have the map yet. Your job is to give them the map before handing them the compass.

The core failure mode this skill prevents: dumping a wall of file paths, function names, and dependency chains on someone who doesn't yet know what the system *does* or why any of those things matter. That's like giving someone driving directions using street names in a city they've never visited. Instead, start with "you're going from the airport to downtown" — then the street names make sense.

## Before you explain anything: gather context

Read the relevant code first. Trace imports, check directory structure, look at tests, read config files. The user is asking because they *can't* easily do this themselves (or it would take them much longer). Your explanation must be grounded in the actual codebase — not hypothetical examples or generic framework descriptions.

Spend the time upfront to understand before you speak. A thorough 30-second investigation beats a fast but disorienting answer.

## The Explanation Flow

Follow these four steps in order. Do not skip or compress the first two steps — they are the entire point.

### Step 1: Orient

Open with a plain-English paragraph that answers three questions:

1. **What is this thing?** — Describe the system, module, or component in terms of what it *does*, not how it's implemented. ("This is the service that processes incoming webhook events from Stripe and updates user subscription records.")
2. **Why does it exist?** — What role does it play in the broader system? What would break or be missing without it?
3. **What's the question/problem?** — Restate the user's question or the problem at hand in plain terms, confirming you understood what they're asking about.

This paragraph should be readable by someone who has never opened the repo. No file paths, no function names, no framework jargon yet.

### Step 2: Scope the Blast Radius

Now connect the plain-English picture to the actual codebase. Explain:

- **What parts of the system are involved?** — Name the specific files and modules, but explain what each one does as you introduce it. Never drop a path without context. Instead of "see `src/workers/stripe_handler.ts`", write "the webhook processing logic lives in `src/workers/stripe_handler.ts`, which is responsible for validating incoming Stripe events and dispatching them to the right handler function."
- **What are the upstream and downstream dependencies?** — What feeds into this component? What consumes its output? If the user changes something here, what else might be affected?
- **How deep do they need to go?** — Be honest about scope. If understanding this problem requires knowing how three other subsystems work, say so upfront. If it's self-contained, say that too. This helps the user calibrate how much time and attention to budget.

Think of this step as drawing a box around the problem on a whiteboard — showing what's inside, what's connected, and where the edges are.

### Step 3: Walk Through the Mechanics

Now get technical. Lead with **concrete execution flow**, not abstract architecture:

- **Data flow first.** Walk through what actually happens at runtime, step by step. For example: "When a user clicks 'Subscribe', here's the chain of events: (1) The frontend calls `POST /api/subscribe` (2) The route handler in `routes/billing.ts:47` validates the session... (3) It calls `createSubscription()` in `services/stripe.ts:112`..." This grounding in real execution paths makes the architecture tangible.

- **Use the actual code.** Reference real files, real functions, real line numbers from the codebase. Simplify where needed (you don't have to walk through every conditional branch), but always point at the real thing.

- **Explain framework conventions inline.** If the codebase uses something like Next.js file-based routing, middleware chains, dependency injection, or ORM conventions, explain the convention when you first reference it. Don't assume the user knows that `pages/api/foo.ts` automatically becomes an API route, or that `@Injectable()` means something specific in NestJS.

- **Use analogies sparingly.** Analogies work well for genuinely abstract concepts (event sourcing, consensus algorithms, CRDTs, reactive streams). For concrete code flow, the code itself is the best explanation — an analogy just adds a layer of indirection. When you do use an analogy, follow it immediately with the concrete technical version so the user has both.

### Step 4: Surface Decision Context

Finally, give the user what they need to make good choices:

- **Trade-offs in the current design.** Why was it built this way? What are the known costs? ("This uses polling instead of webhooks because the upstream API didn't support webhooks when this was built. The trade-off is higher latency but simpler error handling.")
- **Gotchas and invariants.** Are there non-obvious constraints? Things that look safe to change but aren't? Implicit ordering dependencies? ("The `processEvent` function must be idempotent — it's called with at-least-once delivery, so duplicate calls are expected.")
- **Considerations for changes.** If the user is about to modify something, what should they keep in mind? What tests cover this area? Are there migration concerns?

## Calibration

**Do:**
- Write explanations that logically build on each other — each step should make the next one easier to follow
- Use section headers so the user can scan and re-find information
- Reference files with `path/to/file:line_number` format for easy navigation
- Describe data flows in numbered steps when the sequence matters
- Be thorough but respect the user's time — cover what matters, skip what doesn't

**Don't:**
- Assume the user is a beginner — they're an engineer, just an unfamiliar one
- Be hand-wavy or use vague abstractions ("it basically handles the thing") — every claim should be specific enough that the user could verify it by looking at the code
- Front-load jargon before establishing context — the Orient step exists for a reason
- Use hypothetical or generic examples when the real codebase is right there
- Over-explain things the user clearly already understands (read their question carefully for signals about their existing knowledge level)
