# DIT 716 Module 2 — Simplified Governed LTM Prototype

A runnable, dependency-free teaching prototype for the Module 2 mini-project. It demonstrates a SQLite-backed vector index for approved summaries, deterministic source-linked summarization, role-gated promotion, policy-filtered retrieval, TTL expiry, source-revocation propagation, and a four-arm retrieval experiment.

## Interactive browser demo / GitHub Pages

The [`web/`](web/index.html) folder is a static walkthrough inspired by the browser-based demonstration format in the reference link. Visitors can run the C1–C4 scenario trace, inspect memory fixtures, simulate review/forget actions, and view the recorded policy and poisoning-test results. It is a client-side teaching simulation; it does not execute the Python/SQLite backend in the browser or connect to live station data. Changes made in the memory screen are stored in that browser's local storage only.

Expected Pages URL after the first successful deployment: [https://ekkxboon.github.io/HydroGuard-Agent/](https://ekkxboon.github.io/HydroGuard-Agent/).

Build and preview the exact Pages artifact locally:

```bash
python3 scripts/build_pages.py
python3 -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. The builder packages only `web/`, `fixtures.json`, and aggregate `policy_results.csv`. It intentionally excludes `evaluation_labels.json`, the case-level CSV containing `gold_ids`, Python source, and the SQLite runtime. The evaluator labels and case-level CSV stay local and are ignored by Git because this repository is public. The `.github/workflows/pages.yml` workflow re-runs the Python tests, checks browser JavaScript syntax, builds this allow-listed bundle, and deploys it on pushes to `main` or by manual workflow dispatch. In a clean public clone, the one evaluator-dependent experiment test is skipped; local project copies containing `evaluation_labels.json` run the complete experiment test. In the GitHub repository, enable Pages with **GitHub Actions** as the build/deployment source. A deployment URL requires this package to be pushed to a GitHub repository with Pages enabled.

## Run the demo

Requires Python 3.10+ and only the Python standard library.

```bash
cd DIT716_LTM_Prototype
python3 demo.py
```

See [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) for the Thai walkthrough, expected outputs, discussion points, and limitations.
See [ACCEPTANCE_CRITERIA_AND_TEST_PLAN.md](ACCEPTANCE_CRITERIA_AND_TEST_PLAN.md) for the requirement-to-evidence matrix and test plan, mapped to the Module 2 criteria and weights in `Course_Syllabus.pdf` (pp. 1–5).

## Run the agent vertical slice

The multi-case prototype separates the role functions and their data contracts. A1 checks signal morphology, A2 retrieves policy-filtered memory analogies while keeping current evidence separate, A3 drafts a diagnosis, and A4 validates evidence lineage and escalates unsupported claims. All agents are deterministic Python functions; the unsafe A3 branch is enabled only by a test flag.

```bash
python3 -m orchestrator
```

The runner executes four synthetic cases: C1 stage rise with rainfall and neighbor-gauge context; C2 repeated flatline; C3 unexplained spike; and C4 missing/delayed packets with a maintenance note unavailable at decision time. C1 and C2 produce traceable hypotheses, while C3 and C4 abstain for human review. A4 does not certify the true cause. C4's future note is withheld by A2.

The A3 memory writer accepts only a traceable, non-abstained result. It creates a pending episode without a vector. The tests demonstrate that A3 cannot approve it; a reviewer must approve before exact-ID retrieval is allowed. This test uses an in-memory database and a simulated reviewer identity.

Run all agent and LTM checks from this directory:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest -v test_ltm
```

The suite also includes four adversarial tests in `tests/test_poisoning.py`: instruction-like text retrieved as memory context, mismatched source/evidence lineage, a revoked poisoned record queried by similarity and exact ID, and an unsafe diagnosis that must not be promoted. These validate the deterministic prototype's boundaries; they do not establish resistance to prompt injection in an LLM.

This is a four-case teaching demonstration, not a validated hydrological system. Scenarios are synthetic, memory records are analogies rather than current-event evidence, and no LLM or live station data is used.

Run the checks:

```bash
python3 -m unittest -v
```

Reproduce the controlled retrieval experiment and CSV:

```bash
python3 experiment.py
```

The demo creates its temporary SQLite database in the system temp directory. The experiment writes aggregate metrics to `results/policy_results.csv` and per-query outcomes to `results/policy_case_results.csv`.

## What it implements

- **Vector + summary:** a deterministic signed feature-hash embedding (384 dimensions, tokens and adjacent token pairs) indexes approved episode summaries in SQLite. Retrieval uses exact cosine ranking across the eligible records. The vector is a small local baseline, not a trained semantic embedding.
- **Canonical records and derived index:** SQLite episode/source rows remain authoritative; vectors are derived and deleted on expiration or revocation. A production design could replace the index with pgvector without changing the policy contract.
- **Write / summarize:** the prototype creates a structured, source-linked *pending* episode summary. It checks that cited evidence IDs exist in the evidence ledger and descend from a declared active source. It records morphology and a candidate hypothesis explicitly as unadjudicated. A human reviewer must approve before vectorization.
- **Retrieve:** scope (basin/station), role, split, corpus snapshot, status, source validity, availability time, observation validity, review deadline, and optional age TTL are checked before similarity ranking. Audit rows store IDs and policy decisions, not query text.
- **Forget:** 180-day expiry removes an episode from the serving index while keeping the record in a restricted archive. Steward revocation immediately blocks a source and removes dependent summaries/vectors from serving. It does not claim raw source erasure or backup erasure.
- **Memory taxonomy:** the fixture distinguishes episodic records, one semantic record, and a profile record. This focused mini-project implements episodic vector retrieval; working state/cache, a relational knowledge graph, and personal profile lifecycle remain out of the executable scope. Profile records are deliberately not vectorized or served because the prototype has no authenticated user identity.

## Controlled experiment

Four conditions follow the Module 2 design: P0 passive/no episode TTL; P1 active/no TTL; P2 passive/180-day TTL; P3 active/180-day TTL. Each condition uses the same frozen corpus, six held-out query fixtures, relevance labels, top-1 per query, source permissions, embedding method, and decision time. Active retrieval runs the initial query and up to two pre-specified follow-ups representing missing-evidence/contradiction triggers. TTL only changes episode age eligibility; other policy checks remain on in every condition. `fixtures.json` is the agent-readable synthetic memory corpus; `evaluation_labels.json` is a separate evaluator-only file containing query relevance labels and follow-up protocol. The retrieval service never loads the label file. The corpus includes deliberately old, delayed, cross-scope, pending, and revocable examples.

The experiment is a software-policy demonstration, not a hydrological field study. Relevance labels are hand-authored fixture labels, the corpus is tiny, and hashed lexical vectors do not model domain semantics. The evaluation-label file is kept outside the memory store and is only loaded by the experiment runner. Latency on this tiny corpus is not a meaningful deployment comparison. The aggregate CSV can hide case-level substitutions (for example, TTL can remove an old relevant episode while another condition becomes a better match); inspect the per-query CSV too. The generated CSVs are measured results for these fixtures only; it must not be presented as evidence of field accuracy or as a validated TTL choice.

## Demo talking points

1. An agent can propose a source-linked summary, but the proposal has no serving vector until a reviewer approves it.
2. A 240-day-old episode is visible in the no-TTL arm and excluded in the 180-day arm; TTL affects retrieval, not authorization or revocation.
3. A maintenance record unavailable at the query decision time stays excluded even when its event time is earlier.
4. A cross-basin item, pending episode, personal profile, and evaluator-only test truth are not returned to the diagnostic role.
5. After steward revocation, the dependent vector is deleted from the serving index; the restricted archive remains unavailable to agents.
6. Active retrieval trades additional calls/context for coverage; examine the measured results and discuss the limitations rather than claiming that active is universally better.

## Limitations and next production steps

This is a single-process CLI prototype, not an authenticated multi-user service. Role names are test inputs, SQLite file access is not protected from its host, source approvals are simulated, summaries use deterministic templates rather than an LLM, and hashes are lexical rather than semantic embeddings. Production work would require real credential-derived identity, database access controls, transactional migrations, embedding/model pinning, validated relevance labels, cache/backup revocation tests, data-owner retention approval, and human review.
