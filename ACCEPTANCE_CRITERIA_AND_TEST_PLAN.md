# DIT 716 Module 2 — Acceptance Criteria and Test Plan

## ฐานของตารางและขอบเขต

ตารางนี้อิงข้อกำหนด Module 2 ใน `Course_Syllabus.pdf` หน้า 1–2 และ rubric รายวิชาในหน้า 4–5 โดยตรง ประกอบกับรายละเอียดการออกแบบใน `DIT716_Module2_Agent_Memory_Map.docx` หัวข้อ 7 แยกเกณฑ์ทางการ 4 ข้อออกจาก acceptance checks ที่เราแตกย่อยสำหรับตรวจโค้ด

Module 2 มีน้ำหนัก 15% ของคะแนนรวมรายวิชา; น้ำหนักย่อย 25% / 35% / 25% / 15% ในตารางด้านล่างเป็นสัดส่วนภายใน Module 2 ตาม rubric

สถานะ `ผ่าน (prototype)` หมายถึงมีโค้ดและการทดสอบรองรับตาม fixtures ปัจจุบัน ไม่ได้หมายถึงผ่านการตรวจรับจากผู้สอนหรือผ่านการประเมินกับข้อมูลจริง การทำ mapping นี้ไม่ใช่การให้คะแนนหรือคาดการณ์เกรด

## เกณฑ์ทางการของ Module 2 และสถานะหลักฐาน

| เกณฑ์ตาม syllabus | น้ำหนักใน Module 2 | สิ่งที่ระดับ 4 ระบุว่าควรมี | หลักฐานในงานปัจจุบัน | สถานะ/ช่องว่าง |
|---|---:|---|---|---|
| Memory-Map Design Rigor | 25% | ให้เหตุผลการเลือก taxonomy ให้สัมพันธ์กับโดเมน พร้อม storage layer, TTL และ access policy พร้อม rationale | `DIT716_Module2_Agent_Memory_Map.docx`: แยก M1–M5, storage, retention/TTL, access map, write/retrieve/summarize/forget workflow และ domain rationale | **มีหลักฐานด้านการออกแบบ** — สมมติฐานและ retention ยังเป็นค่าที่เสนอ; ควรทบทวนกับ supervisor/data owner ก่อนอ้างใช้จริง |
| Prototype Implementation Quality | 35% | LTM prototype ทำงานได้ (vector DB + summarization), documented, reproducible และมี engineering practice ที่ดี | `ltm.py`, `demo.py`, `agents/memory_writer.py`, 16 unit tests, README, runbook และ GitHub Pages demo; SQLite vector index 384D hash features และ source-linked summary template | **ทำงานได้ในขอบเขตสาธิต** — ต้องอธิบายความต่างจากสถาปัตยกรรมที่เสนอใน memory map (PostgreSQL/pgvector); hash-vector เป็น lexical baseline ไม่ใช่ trained semantic embedding |
| Retrieval / Forgetting Policy Experiment | 25% | เปรียบเทียบ policy แบบควบคุม เช่น active/passive และ TTL/no-TTL พร้อม quantitative results และ interpretation | `experiment.py` เปรียบเทียบ P0–P3 ด้วย frozen corpus/query set; CSV aggregate และ per-query; `results/experiment_report.md` | **มีผล pilot** — 6 query cases เป็น synthetic/hand-labeled จึงยังไม่รองรับข้อสรุปทั่วไปหรือ field validity |
| Documentation & Reflection | 15% | อธิบาย design trade-offs (retrieval accuracy, latency, privacy) และสะท้อนผลอย่างมีวิจารณญาณ | memory map, `README.md`, `DEMO_RUNBOOK.md`, `results/experiment_report.md`, case-level CSV | **หลักฐานมี แต่ควรตรวจแพ็กเกจส่งงาน** — ชี้ trade-off และกรณี Q2/Q4; สรุปข้อจำกัดและอธิบายว่าไม่ใช่ผลจริงทางอุทกวิทยา |

## ตารางเกณฑ์งานและหลักฐาน

| ID | เกณฑ์ที่ต้องแสดง | การยอมรับใน prototype | จุดที่ทำงาน/หลักฐาน | สถานะและข้อจำกัด |
|---|---|---|---|---|
| AC-01 | สร้าง memory summary ที่ trace กลับไปยังแหล่งข้อมูลได้ | summary เก็บ morphology, candidate hypothesis, source IDs และ evidence IDs; ระบุว่าเป็น candidate ไม่ใช่ผลยืนยัน | `ltm.py` → `propose_summary`; `test_ltm.py` → `test_proposal_needs_human_approval_before_vectorization`; `tests/test_agent_pipeline.py` → `test_only_verified_candidate_can_be_proposed_and_reviewer_approves` | **ผ่าน (กลไก)** — summary ใช้ deterministic template; ยังไม่ได้ประเมินความถูกต้องเชิงความหมายโดย domain expert |
| AC-02 | ทำ vector index และเรียกคืนตาม similarity | ใช้ SQLite เก็บเวกเตอร์ signed feature-hash 384 มิติ และจัดอันดับด้วย cosine เฉพาะรายการที่ผ่าน policy | `ltm.py` → `embed`, `retrieve`; `demo.py` → passive retrieval | **ผ่าน (กลไก)** — เป็น lexical baseline ไม่ใช่ trained semantic embedding; ห้ามเรียกว่า semantic understanding |
| AC-03 | ป้องกันการค้นคืนที่ผิดสิทธิ์/ผิดขอบเขต/ผิดเวลา | ตรวจ role, station/basin, split, snapshot, status, source validity, availability, observation validity, review due และ TTL ก่อน ranking | `ltm.py` → `_eligible`, `retrieve`, `retrieve_by_id`; `test_ltm.py` → scope/role/availability และ direct-ID tests | **ผ่าน (fixture tests)** — identity/role เป็นค่าจำลอง ไม่ใช่ authentication boundary |
| AC-04 | แสดงวงจร approval ก่อน memory พร้อมให้ค้นคืน | รายการใหม่เริ่ม `pending`, ไม่มี serving vector และ direct read ถูก deny; reviewer จึงอนุมัติให้ vectorize ได้ | `ltm.py` → `propose_summary`, `approve_episode`; `test_ltm.py` และ `test_agent_pipeline.py` | **ผ่าน (กลไก)** — reviewer identity ใน demo เป็น simulated identity |
| AC-05 | ทดสอบ forgetting ด้วย TTL | episode เกิน 180 วันถูกเอาออกจาก serving index และ vector ถูกลบ; record คงอยู่ใน restricted archive | `ltm.py` → `forget_expired`, `archive_record`; `test_ltm.py` → `test_ttl_expires_serving_index_but_keeps_restricted_archive`; `demo.py` ส่วน Forgetting | **ผ่าน (fixture tests)** — TTL เป็นค่าทดสอบ ไม่ใช่ค่าที่ผ่านการ validate สำหรับงานจริง |
| AC-06 | ทดสอบ forgetting/หยุด serving จากการเพิกถอน source | steward เพิกถอน source แล้วบล็อก dependent summaries และลบ vectors ที่เกี่ยวข้องจาก serving; archive ยังจำกัดสิทธิ์ | `ltm.py` → `invalidate_source`; `test_ltm.py` → `test_revocation_cascades_to_summary_and_vector_index`; `demo.py` ส่วน Forgetting | **ผ่าน (fixture tests)** — ไม่ได้ลบ raw source หรือสำเนา backup |
| AC-07 | เปรียบเทียบ retrieval policy อย่างควบคุม | เปรียบเทียบ P0 passive/no-TTL, P1 active/no-TTL, P2 passive/180-day TTL, P3 active/180-day TTL บน corpus/query snapshot เดียวกัน | `experiment.py`; `evaluation_labels.json`; `results/policy_results.csv`; `results/policy_case_results.csv`; `results/experiment_report.md` | **ผ่านใน pilot** — 6 query cases สังเคราะห์และ hand-labeled; ใช้สรุปแนวโน้มใน fixture เท่านั้น ไม่ใช้อนุมานทั่วไป |
| AC-08 | ตรวจว่าการทดลองไม่ส่งรายการผิด policy | evaluator audit ตรวจ returned IDs แยกจาก retrieval service; acceptance threshold ของ fixture run คือ forbidden returns = 0 | `experiment.py` → `_violates_policy`; `test_ltm.py` → reproducibility/zero-forbidden test; `policy_results.csv` | **ผ่านใน fixture run** — ค่า 0 ไม่รับประกันว่าจะไม่มี policy leak เมื่อเพิ่มข้อมูลหรือเปลี่ยนระบบ |
| AC-09 | เชื่อม agent flow กับ LTM โดยไม่สับสน evidence กับ memory | A1–A4 แยกหน้าที่; A2 แยก current evidence/memory analogy และกรอง record ในอนาคต; A4 ตรวจ claim และ abstain/escalate | `agents/`; `orchestrator.py`; `tools/scenarios.py`; `tests/test_agent_pipeline.py` | **ผ่านใน 4 synthetic cases** — agent เป็น deterministic rules; ไม่ใช่ผลวัดความแม่นยำของ LLM หรือ hydrological diagnosis |
| AC-10 | ทำซ้ำการรันและตรวจสอบผลได้ | ใช้ Python standard library, มีคำสั่ง run/test, เก็บ aggregate และ case-level CSV พร้อม runbook | `README.md`; `DEMO_RUNBOOK.md`; commands ในส่วนถัดไป | **ผ่านด้านการทำซ้ำในเครื่อง** — ยังไม่ได้ทดสอบหลาย OS หรือ environment ของผู้สอน |
| AC-11 | ทดสอบ memory poisoning / instruction-like content | Retrieved instructions stay inert; invalid lineage and unsafe claims are not promoted; revoked-source content is excluded from semantic and exact-ID retrieval | `tests/test_poisoning.py` — `test_instruction_like_retrieved_memory_stays_untrusted_analogy`, `test_source_substitution_attack_cannot_create_pending_memory`, `test_revoked_poison_is_excluded_even_for_matching_query_and_exact_id`, `test_unsafe_adversarial_diagnosis_cannot_be_promoted` | **ผ่านใน deterministic prototype** — เป็น adversarial unit tests; ยังไม่ใช่การทดสอบ prompt injection กับ LLM/model จริง |

## แผนทดสอบและผลล่าสุด

| Test ID | สิ่งที่ทดสอบ | วิธีรัน/หลักฐาน | เกณฑ์ผ่าน | ผลล่าสุด |
|---|---|---|---|---|
| T-01 | A1–A4 ทำงานกับ C1–C4; C4 ไม่เปิดเผย maintenance record ก่อนเวลา | `python3 -m unittest discover -s tests -v` — `test_all_four_cases_have_expected_candidates_and_time_filtering` | Candidate/abstain ตรง expected fixture; C4 current evidence มี packet เท่านั้นและ maintenance อยู่ใน withheld | **ผ่าน** |
| T-02 | A4 ลด malicious claim และตรวจ evidence ข้าม case/อนาคต | ชุดเดียวกัน — `test_a4_downgrades_injected_malicious_claim`, `test_a4_rejects_cross_case_and_future_evidence` | ไม่มีการ publish adjudicated outcome; unsupported intent ถูก downgrade; invalid references ถูก flag | **ผ่าน** |
| T-03 | A3 เสนอ memory ได้เฉพาะผลที่ A4 traceable; approval ต้องเป็น reviewer | ชุดเดียวกัน — `test_only_verified_candidate_can_be_proposed_and_reviewer_approves` | pending ไม่มี vector/ค้นคืนไม่ได้; A3 approve ไม่ได้; reviewer approve แล้ว exact-ID retrieval allow | **ผ่าน** |
| T-04 | Retrieval จำกัด scope, role, status, availability และชนิด memory | `python3 -m unittest -v test_ltm` — `test_scope_split_status_availability_and_role_are_enforced`, `test_exact_id_reads_share_policy_and_profile_is_not_embedded` | รายการที่ผิด policy ไม่ถูกคืน; exact-ID lookup ใช้ policy เดียวกัน | **ผ่าน** |
| T-05 | TTL และ archive permissions | `python3 -m unittest -v test_ltm` — `test_ttl_expires_serving_index_but_keeps_restricted_archive` | expired item ไม่มีใน serving; archive deny agent และ allow steward | **ผ่าน** |
| T-06 | Source revocation cascade | `python3 -m unittest -v test_ltm` — `test_revocation_cascades_to_summary_and_vector_index` | dependent vector หายจาก serving; steward-only archive ยังคง; agent ไม่เพิกถอน source ได้ | **ผ่าน** |
| T-07 | P0–P3 ทำซ้ำได้และไม่มี forbidden return ใน fixtures | `python3 -m unittest -v test_ltm` — `test_four_arm_policy_experiment_is_reproducible_and_zero_forbidden` | ผล metric ทำซ้ำได้และ forbidden retrievals = 0 ใน fixture | **ผ่าน** |
| T-08 | Guided demo สร้าง state transitions/CSV ตามลำดับ | `python3 demo.py` | เห็น retrieval, pending → reviewer approval → vector, TTL, revocation, P0–P3 และ CSV paths | **ผ่านจากการ dry run** |
| T-09 | ขยาย external validity ของ retrieval labels | เพิ่ม cases ให้ครอบคลุม category และให้ผู้ตรวจ domain ทบทวน relevance labels ก่อนใช้ข้อมูลจริง | มี protocol, rationale ของ label, held-out queries และรายงาน per-query; ห้ามตั้ง threshold หลังเห็นผล | **ค้าง** |
| T-10 | ตรวจความจำเป็นของ semantic embeddings ตาม rubric | ยืนยันก่อนว่ารายวิชาต้องการ semantic retrieval จริงหรือเพียง vector index + policy; หากต้องการ ให้ pin model/version และทดสอบเทียบ lexical baseline | เลือกด้วยข้อกำหนดและ held-out evaluation; ไม่อ้างว่า hash vectors เป็น semantic model | **ตัดสินใจตาม rubric/ผู้สอน** |
| T-11 | Retrieved instruction-like summary ไม่เปลี่ยน diagnosis | `python3 -m unittest discover -s tests -v` — `test_instruction_like_retrieved_memory_stays_untrusted_analogy` (จำลอง post-approval tampering กับ canonical summary/vector) | EP-008 ถูกดึงเป็น analogy แต่ไม่กลายเป็น current evidence; A3 ยังคง abstain และ A4 escalate | **ผ่าน** |
| T-12 | ป้องกัน source/evidence substitution และ unsafe promotion | ชุดเดียวกัน — `test_source_substitution_attack_cannot_create_pending_memory`, `test_unsafe_adversarial_diagnosis_cannot_be_promoted` | lineage mismatch ถูก reject ก่อนสร้าง episode/vector; malicious draft ไม่ถูก promote | **ผ่าน** |
| T-13 | Revocation มีผลเหนือ semantic similarity และ exact-ID lookup | ชุดเดียวกัน — `test_revoked_poison_is_excluded_even_for_matching_query_and_exact_id` | หลัง revoke รายการหายจาก vector serving; semantic และ direct-ID retrieval deny | **ผ่าน** |
| T-14 | Build bundle สำหรับ Pages และไม่เผยแพร่ evaluator labels/Python runtime | `python3 -m unittest discover -s tests -v` — `test_static_bundle_has_demo_data_but_excludes_evaluator_labels` | artifact มี browser UI + fixture/aggregate metrics แต่ไม่มี `evaluation_labels.json`, case-level CSV ที่มี `gold_ids` หรือไฟล์ Python | **ผ่าน** |

ใน local package ที่มี evaluator labels ทดสอบได้ **16 unit tests** (agent 5, poisoning/adversarial 4, LTM 6, Pages packaging 1) ครบทั้งหมด; public repository จะรัน 15 tests และ skip การทดลอง 1 test ที่ต้องใช้ `evaluation_labels.json` ซึ่งเก็บไว้ local โดยเจตนา ผลเหล่านี้เป็นหลักฐานสำหรับ deterministic prototype นี้ ไม่ใช่การประเมินทางสถิติของระบบทั่วไปหรือหลักฐานความทนทานต่อ LLM prompt injection

## การสร้างหลักฐานผลการทดลองใหม่

รันจากโฟลเดอร์ `DIT716_LTM_Prototype`:

```bash
python3 -m orchestrator
python3 demo.py
python3 -m unittest discover -s tests -v
python3 -m unittest -v test_ltm
```

หรือสร้างผล retrieval experiment โดยตรง:

```bash
python3 experiment.py
```

ไฟล์ผลอยู่ที่ `results/policy_results.csv` (aggregate) และ `results/policy_case_results.csv` (ราย query) ค่า pilot ล่าสุด:

| Condition | Precision | Recall | Calls/query | Forbidden returns |
|---|---:|---:|---:|---:|
| P0 | 0.833 | 0.714 | 1.00 | 0 |
| P1 | 0.750 | 0.857 | 1.50 | 0 |
| P2 | 0.833 | 0.714 | 1.00 | 0 |
| P3 | 0.750 | 0.857 | 1.50 | 0 |

รายงาน trade-off และ substitution ระดับ query จาก `results/experiment_report.md` และ `results/policy_case_results.csv`; อย่าสรุปว่า active หรือ TTL ดีกว่าโดยทั่วไปจาก 6 queries นี้

## งานที่แนะนำก่อนส่ง prototype

1. หากเพิ่ม LLM หรือ embedding service ให้เพิ่ม prompt-injection tests, adversarial paraphrase และ source-integrity tests ใน model/service boundary; การทดสอบปัจจุบันยืนยันเฉพาะ deterministic pipeline และ policy gateway
2. ให้ supervisor/data owner ทบทวน assumptions ใน memory map, โดยเฉพาะ taxonomy, scope, TTL, review, revocation, retention
3. ให้ผู้สอน/ผู้รู้โดเมนตรวจ scenario และ relevance labels; ขยาย held-out queries ก่อนนำ metric ไปกล่าวอ้าง
4. ยืนยันจาก rubric/ผู้สอนว่าต้องการ trained semantic embedding หรือไม่; ถ้าไม่ ให้คง hash-vector baseline พร้อมเปิดเผยข้อจำกัด
5. ทำ clean run จาก environment ที่จะใช้ส่งงาน แล้วเก็บ run outputs และ CSV รุ่นสุดท้ายไว้พร้อม code, runbook และ diagram
