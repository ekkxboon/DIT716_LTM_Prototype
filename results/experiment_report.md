# Module 2 retrieval / forgetting pilot — observed results

## Question and protocol

Does active retrieval recover more of the independently fixture-labeled relevant memory than one passive lookup, and what case-level effects does a 180-day episodic retrieval TTL have? This is a controlled software-policy demonstration, not an evaluation of hydrological diagnosis quality.

The prototype compares the four conditions specified in the Module 2 memory-map design. All arms use the same 15-row synthetic training memory snapshot, six held-out query fixtures, relevance labels, station/basin scope, role, decision time, top-1 per retrieval call, and deterministic hash-vector method. Active arms add the pre-specified missing-context/contradiction follow-ups (up to two). The 180-day TTL is the only age-policy difference; scope, availability, approval, validity, and source-revocation rules remain enabled in all arms. Evaluator labels are stored separately in `evaluation_labels.json` and are not loaded by the memory gateway.

Precision and recall are micro-aggregated over unique returned memory IDs per query case. A returned item is a true positive only if it belongs to that case’s gold relevance set. The detailed IDs and per-case scores are in `policy_case_results.csv`; aggregate counts and call/token estimates are in `policy_results.csv`.

## Aggregate result

| Condition | Retrieval | Episode TTL | Precision | Recall | Calls / case | Estimated context tokens | Forbidden returns |
|---|---|---:|---:|---:|---:|---:|---:|
| P0 | Passive | None | 0.833 | 0.714 | 1.00 | 147 | 0 |
| P1 | Active | None | 0.750 | 0.857 | 1.50 | 225 | 0 |
| P2 | Passive | 180 days | 0.833 | 0.714 | 1.00 | 165 | 0 |
| P3 | Active | 180 days | 0.750 | 0.857 | 1.50 | 243 | 0 |

The active schedule raised fixture recall from 0.714 to 0.857 (+0.143) and reduced precision from 0.833 to 0.750 (-0.083), while increasing retrieval calls by 50% (6 to 9 total). This reflects the intended coverage/cost trade-off in these fixtures, not a general benefit of active retrieval.

The aggregate 180-day comparison is unchanged, but the per-case result is not: P0 retrieves the 240-day-old relevant episode EP-005 for Q4, while P2 excludes it and returns an irrelevant newer match. For Q2, P0’s top result is an irrelevant old analogy, while TTL allows a relevant neighboring-gauge episode to rank first. These opposing substitutions cancel in aggregate recall. This demonstrates why per-case results and rare-event coverage matter when choosing a TTL; it does not validate 180 days.

The availability policy also excluded the delayed maintenance summary EP-004 at the earlier decision time in all conditions. Across the run, the service returned zero pending, expired, revoked, wrong-scope, or not-yet-available items in the tested retrievals. Separate unit tests verify source revocation removes dependent vectors, and TTL cleanup removes expired vectors while keeping the archive inaccessible to agent roles.

## Interpretation and limits

- The fixtures show that active retrieval can fill a missing-context slot, with extra calls and some additional non-relevant returns.
- TTL is not equivalent to deletion. In this prototype it blocks serving, deletes the derived vector, and retains the canonical record behind steward-only archive access.
- A short TTL may erase useful rare-event analogies; review-based renewal or explicit rare-event coverage needs evaluation before deployment.
- All 15 memory rows and all six held-out query cases are synthetic and hand-authored. The six cases are too few for inferential statistics or confidence claims; no confidence intervals are reported.
- The signed feature-hash vectors are deterministic lexical baselines, not learned hydrological embeddings. The measured sub-millisecond local latency is not deployment evidence.
- No agent, LLM, real station data, or operational system was used. Results assess retrieval-policy plumbing only, not diagnostic accuracy, summary truth, or agentic value.

## Reproduction

From this folder run:

```bash
python3 experiment.py
python3 -m unittest -v
```
