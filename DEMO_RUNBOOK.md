# DIT 716 Mini-project Demo Runbook

**เวลาแนะนำ:** 8–10 นาที  
**สิ่งที่สาธิต:** agent pipeline A1–A4, governed LTM (vector + summary), human approval, policy-filtered retrieval, forgetting และการทดลอง P0–P3

## เป้าหมายการสาธิต

ให้ผู้ชมเห็นว่า mini-project ใช้ memory อย่างไรและควบคุมการนำ memory กลับมาใช้อย่างไร โดยแยก **หลักฐานของเหตุการณ์ปัจจุบัน** ออกจาก **memory analogy** และแสดง trade-off ของ retrieval policy กับ TTL

ระบบนี้เป็น prototype แบบ deterministic ใช้สถานการณ์สังเคราะห์และ Python standard library เท่านั้น ไม่มี LLM, API หรือข้อมูลสถานีจริง ผลที่เห็นเป็นการทดสอบ software policy ไม่ใช่การยืนยันความแม่นยำทางอุทกวิทยา

## เตรียมก่อนเริ่ม

เปิด Terminal แล้วเข้าโฟลเดอร์ prototype:

```bash
cd /Users/xboon/Documents/DIT_716/DIT716_LTM_Prototype
python3 --version
```

ต้องใช้ Python 3.10 ขึ้นไป ไม่มี dependency ภายนอกที่ต้องติดตั้ง ไฟล์ diagram ที่แสดงลำดับการพูดอยู่ที่ `../DIT716_MiniProject_Demo_Process_Flow.drawio` เปิดไว้เป็นภาพประกอบได้

ก่อนเริ่ม ให้ย้ำกับผู้ชมว่า fixtures, relevance labels และ reviewer identity เป็นข้อมูลจำลอง และ agent ใน demo เป็น role functions ที่มีสัญญา input/output ไม่ใช่ autonomous LLM agents

## ลำดับการ demo

### 1. เดิน agent pipeline C1–C4 (ประมาณ 2 นาที)

รัน:

```bash
python3 -m orchestrator
```

อธิบาย flow ตามลำดับ:

1. **A1 Data Quality** วัดรูปแบบสัญญาณ เช่น spike, flatline และ missingness โดยไม่ระบุเจตนาหรือสาเหตุ
2. **A2 Hydrology Context** แยก context ที่พร้อมใช้ ณ decision time ออกจาก memory analogies ที่ gateway อนุญาตให้ค้นคืน
3. **A3 Diagnostic** เสนอ candidate cause และคงทางเลือกไว้
4. **A4 Verifier** ตรวจ evidence IDs, case, เวลา และข้อจำกัดของ claim; A4 ตรวจ traceability แต่ไม่ได้รับรองสาเหตุจริง

ชี้ผลลัพธ์สำคัญที่ควรเห็น:

| กรณี | สิ่งที่สังเกต | ผลใน demo |
|---|---|---|
| C1 | ระดับน้ำเพิ่ม พร้อมฝนและ upstream gauge | เสนอ genuine hydrological event เป็น hypothesis ที่ trace ได้ |
| C2 | ค่าระดับน้ำซ้ำต่อเนื่อง ขณะที่ gauge ข้างเคียงเปลี่ยน | เสนอ sensor/data-quality fault เป็น candidate ไม่ฟันธง |
| C3 | spike ไม่มีบริบท corroborating | abstain และส่งให้คนตรวจ |
| C4 | packet ขาด/มาช้า และ maintenance note มาหลัง decision time | ใช้ได้เฉพาะ packet evidence; กัก note ในอนาคตและ abstain |

เน้นว่า C1/C2 ยังเป็นสมมติฐาน ส่วน C3/C4 แสดงการ abstain เมื่อข้อมูลไม่พอ

### 2. สาธิต retrieval และ human approval (ประมาณ 2 นาที)

รัน demo หลัก:

```bash
python3 demo.py
```

ในส่วน `1) Passive semantic retrieval` ชี้ว่า query เรื่อง flatline ได้ `EP-001` และ policy นับรายการที่ยังไม่พร้อมใช้ไว้ใน `not_yet_available` โดยไม่ส่งให้ agent

ในส่วน `2) Propose → approve → retrieve` อธิบาย state transition:

- summary ใหม่เริ่มที่ `pending` และยังไม่มี vector เพิ่ม (จำนวน vectors จึงยังเป็น 13)
- การอนุมัติด้วย role ของ agent ถูกปฏิเสธ
- เมื่อ reviewer อนุมัติ จึงสร้าง vector (เพิ่มเป็น 14) และ exact/source-linked retrieval คืน `EP-DEMO`

การเขียนจาก agent pipeline ใช้ `propose_verified_episode` ซึ่งยอมรับเฉพาะผลที่ A4 ตรวจผ่านและไม่ abstain; acceptance test ยืนยันว่า A3 อนุมัติรายการของตนเองไม่ได้

### 3. สาธิต forgetting: TTL และ revocation (ประมาณ 2 นาที)

ส่วน `3) Forgetting checks` ใน `demo.py` ใช้ฐานข้อมูลชั่วคราว:

- **TTL:** episode เกิน 180 วันถูกถอด vector จาก serving index และเปลี่ยนเป็น `expired`; record ยังอยู่ใน restricted archive
- **สิทธิ์ archive:** role ของ agent อ่าน archive ไม่ได้ แต่ steward อ่านได้
- **Source revocation:** steward เพิกถอน `SRC-115`; dependent record ถูก block และ vector ถูกลบจาก serving index
- หลัง revocation อาจยังเห็น memory อื่นที่ถูกต้องในผลค้นคืน เช่น `EP-001`; ประเด็นที่ต้องตรวจคือ `EP-015` ที่พึ่งพา `SRC-115` ไม่ปรากฏแล้ว

prototype นี้ไม่อ้างว่าลบ raw source หรือ backup

### 4. อธิบายผล retrieval experiment P0–P3 (ประมาณ 2–3 นาที)

ส่วน `4) Four-condition experiment` รัน query fixtures 6 รายการ บน frozen corpus เดียวกัน:

| เงื่อนไข | Retrieval | TTL | Precision | Recall | Calls/query | Forbidden |
|---|---|---:|---:|---:|---:|---:|
| P0 | Passive | ปิด | 0.833 | 0.714 | 1.00 | 0 |
| P1 | Active | ปิด | 0.750 | 0.857 | 1.50 | 0 |
| P2 | Passive | 180 วัน | 0.833 | 0.714 | 1.00 | 0 |
| P3 | Active | 180 วัน | 0.750 | 0.857 | 1.50 | 0 |

ชวนอภิปราย trade-off แทนการประกาศผู้ชนะ:

- Active retrieval เพิ่ม recall ใน fixture นี้ แต่ลด precision และเพิ่ม calls/query
- TTL ไม่ได้ช่วยทุกกรณี: Q4 ต้องการ `EP-005` ซึ่งเก่ากว่า 180 วัน จึงถูกแทนด้วยผลอื่นที่ไม่เกี่ยวข้อง; ใน Q2 TTL กลับช่วยให้ได้ relevant result
- `forbidden=0` เป็นผลบน fixture audit ชุดเล็ก ไม่ใช่หลักประกันว่า policy จะไม่รั่วในระบบจริง

ไฟล์ผลลัพธ์อยู่ที่ `results/policy_results.csv` และ `results/policy_case_results.csv` ควรเปิด case-level CSV เพื่อดูว่า aggregate metrics ซ่อนความต่างของ query ใดบ้าง

## ตรวจความพร้อมและรันซ้ำ

ชุดทดสอบ agent:

```bash
python3 -m unittest discover -s tests -v
```

ชุดทดสอบ LTM policy:

```bash
python3 -m unittest -v test_ltm
```

ชุด poisoning/adversarial ครอบคลุม instruction-like memory, การสวม source/evidence lineage, การเรียกคืนหลัง revoke และการกัน unsafe diagnosis จากการ promote:

```bash
python3 -m unittest -v tests.test_poisoning
```

ใน local package ที่มี evaluator labels ผ่านทั้งหมด **16 tests** (agent 5, poisoning/adversarial 4, LTM 6, Pages build 1); public repository จะ skip test experiment 1 รายการเพราะไม่นำ labels/case-level gold IDs ขึ้น GitHub โดยเจตนา ผลยืนยันขอบเขตของ deterministic prototype เท่านั้น ยังไม่ได้ทดสอบ LLM prompt injection หากต้องการสร้าง CSV ใหม่โดยตรง:

```bash
python3 experiment.py
```

`demo.py` สร้าง SQLite database ใน temporary directory และลบทิ้งเมื่อจบ ส่วน `experiment.py` สร้างผล CSV ใน `results/`

## คำถามอภิปรายและข้อจำกัด

1. เมื่อ A2 พบ memory ที่คล้ายกัน แต่ไม่มี current evidence ควรให้ A3 ใช้ memory นั้นในระดับใด?
2. จะตั้ง TTL อย่างไรเมื่อ episode เก่าอาจยังเกี่ยวข้อง แต่ข้อมูลใหม่ก็อาจดีกว่า?
3. ควรเพิ่มการตรวจใดก่อนใช้ LLM กับ A3: evidence faithfulness, calibration, abstention quality หรือ reviewer workload?

ตัวเลข retrieval ใช้ relevance labels ที่เขียนไว้สำหรับ fixture 6 queries; vector เป็น deterministic lexical hash 384 มิติ ไม่ใช่ trained semantic embedding; agent cases สี่รายการเป็น synthetic; reviewer และ role เป็นค่าจำลองใน single-process prototype ดังนั้นห้ามนำ precision/recall หรือผล agent ไปอ้างเป็น field accuracy หรือผลทั่วไป
