# Lab 03 — Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed Bias และ Emitter Bias ให้เว็บ Flask เดิม โดยผลของ Voltage Divider ต้องเหมือน commit `39ebe16` ทุกตำแหน่ง และตรวจ A1–A5 บนเบราว์เซอร์จริง

**Architecture:** `dc_bias.py` ถือสมการทั้งสามโหมดเป็นฟังก์ชันแยก (`calculate`, `calculate_fixed`, `calculate_emitter`) ที่คืน `BiasResult` ร่วมกัน, `validate(form, mode)` ตรวจเฉพาะช่องของโหมดนั้น, `app.py` เลือกฟังก์ชันด้วย `if/elif` ตาม `mode` แล้วประกอบ `fields`/`steps` ให้เทมเพลตเดียวที่วนแสดงช่องจากรายการที่ส่งเข้ามา (ไม่มี JavaScript)

**Tech Stack:** Python 3.15.2, Flask 3.1.3, Jinja2, `unittest` (stdlib), HTML/CSS, Playwright MCP (`@playwright/mcp@0.0.85`)

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-bias-modes-design.md`

## Global Constraints

- ค่าคงที่ที่ใช้ร่วมทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
- เกณฑ์ Saturation ของ Lab 03: `VCE ≤ 0.2 V` (แทน 0.3 เดิม) และเตือนเมื่อ `IB ≤ 0 V`
- อินพุตผิด → error ต่อช่อง; อินพุตถูกแต่แบบจำลองใช้ไม่ได้ → warning (ห้ามแก้สมการ Cutoff/Saturation)
- `dc_bias.py` ห้าม import Flask; `templates/index.html` ห้ามคำนวณและห้ามฝังเลขผลลัพธ์
- ตัวต้านทานบนฟอร์มเป็น **kΩ** แปลงเป็น Ω ครั้งเดียวใน `validate()` → `RB = 1 MΩ` กรอกเป็น `1000`
- แสดงผล 3 ตำแหน่งทศนิยม; กระแส ≥ 1 mA เป็น mA, ต่ำกว่าเป็น µA
- ห้ามใช้ JavaScript ฝั่ง client
- `validate(form)` ที่เรียกด้วยอาร์กิวเมนต์เดียวต้องยังทำงานแบบ Divider ได้ (เทสต์เดิม 39 ตัวห้ามแก้)
- commit ผ่าน **GitHub Desktop เท่านั้น** — agent ไม่รัน `git commit` / `git push`
- Playwright MCP เรียกผ่าน `cmd /c npx` (ทดสอบแล้วว่า `spawn("npx")` บน Windows ล้มด้วย `ENOENT`)

## Review Focus

1. **POST ที่ไม่มีฟิลด์ `mode`** (client/เทสต์จาก Lab 2) → ต้องคำนวณ Divider ตามปกติ ไม่ใช่ error
2. **โหมด Fixed แต่ฟอร์มยังส่ง `r1`/`r2`/`re` มาด้วย** (ค่าขยะหรือ `0`) → ต้องเพิกเฉยทั้งหมด ไม่ error และไม่ทำให้ผลเปลี่ยน (A2)
3. **`mode` เป็นค่าที่ไม่รู้จัก** (`mode=xyz`) → ต้องแจ้ง error ไม่เดาเป็น Divider
4. **`RB` กรอก `1000` kΩ** → ต้องได้ 1 MΩ จริง; **`RB = 0`** → error ไม่ล้ม และไม่มีผลรอบก่อนค้าง (A5)
5. **ผลลัพธ์/ข้อความ error ต้องระบุโหมดที่เลือก** และเมื่อส่งฟอร์มผิดต้องไม่มีบล็อกผลลัพธ์ของรอบก่อนเหลืออยู่

---

### Task 1: ฟังก์ชันคำนวณสองโหมดใหม่ + เกณฑ์ 0.2 V

**Files:**
- Modify: `dc_bias.py` (ค่าคงที่บรรทัด 12–30, `BiasResult` บรรทัด 44–56, ต่อท้าย `calculate`)
- Test: `tests/test_fixed.py`, `tests/test_emitter.py`

**Interfaces:**
- Produces:
  - `FixedBiasInput(vcc: float, rb: float, rc: float, beta: float, vbe: float)`
  - `EmitterBiasInput(vcc: float, rb: float, rc: float, re: float, beta: float, vbe: float)`
  - `BiasResult(ib, ic, ie, vb, ve, vc, vce, region, warnings, vth: float | None = None, rth: float | None = None)` — `vth`/`rth` ย้ายไปท้ายและมีค่าเริ่มต้น เพื่อให้สองโหมดใหม่ไม่ต้องใส่ค่าที่ไม่มีความหมาย (ทุกจุดที่สร้างใช้ keyword ทั้งหมด)
  - `calculate_fixed(p: FixedBiasInput) -> BiasResult`
  - `calculate_emitter(p: EmitterBiasInput) -> BiasResult`
  - `SATURATION_VCE_LIMIT = 0.2`

- [ ] **Step 1: เขียน failing test `tests/test_fixed.py`**

ค่าอ้างอิง A2 (RB = 1 MΩ): `ib=1.13e-05`, `ic=0.00113`, `ie=0.0011413`, `vb=0.7`, `ve=0.0`, `vc=9.514`, `vce=9.514`
ใช้ `delta=1e-9` กับกระแส และ `delta=1e-6` กับแรงดัน

```python
import unittest
from dc_bias import FixedBiasInput, calculate_fixed

A2 = FixedBiasInput(vcc=12, rb=1_000_000, rc=2_200, beta=100, vbe=0.7)

class FixedBiasReferenceTest(unittest.TestCase):
    def setUp(self):
        self.r = calculate_fixed(A2)

    def test_currents(self):
        self.assertAlmostEqual(self.r.ib, 1.13e-05, delta=1e-9)
        self.assertAlmostEqual(self.r.ic, 0.00113, delta=1e-9)
        self.assertAlmostEqual(self.r.ie, 0.0011413, delta=1e-9)

    def test_voltages(self):
        self.assertAlmostEqual(self.r.ve, 0.0, delta=1e-12)
        self.assertAlmostEqual(self.r.vb, 0.7, delta=1e-9)
        self.assertAlmostEqual(self.r.vc, 9.514, delta=1e-6)
        self.assertAlmostEqual(self.r.vce, 9.514, delta=1e-6)

    def test_region_is_active_without_warnings(self):
        self.assertEqual(self.r.region, "active")
        self.assertEqual(self.r.warnings, [])
```

- [ ] **Step 2: เขียน failing test `tests/test_emitter.py`**

A3 (RB=1 MΩ, RE=1 kΩ): `ib=1.0263396911898274e-05`, `ic=0.0010263396911898274`, `ie=0.0010366030881017257`, `vb=1.7366030881017256`, `ve=1.0366030881017256`, `vc=9.742052679382379`, `vce=8.705449591280653`
A4 (RB=1 MΩ, RE=2 kΩ): `ic=0.0009400998336106491`, `vce=8.03277870216306`

เขียน 4 เทสต์: ค่าอ้างอิง A3, ค่าอ้างอิง A4, `A4.ic < A3.ic` และ `A4.vce > A3.vce` (ทิศทางที่ต้องทำนายก่อนรัน), region active ทั้งสองกรณี

- [ ] **Step 3: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `ImportError: cannot import name 'FixedBiasInput'`

- [ ] **Step 4: เพิ่มค่าคงที่และ dataclass**

- `SATURATION_VCE_LIMIT = 0.2`
- `SATURATION_WARNING = "VCE ต่ำกว่า 0.2 V — ใกล้หรือเข้าสู่ Saturation ค่าที่ได้ไม่น่าเชื่อถือ"`
- `MODES = ("divider", "fixed", "emitter")`
- `MODE_FIELDS = {"divider": ("vcc", "beta", "r1", "r2", "rc", "re", "vbe"), "fixed": ("vcc", "beta", "rb", "rc", "vbe"), "emitter": ("vcc", "beta", "rb", "rc", "re", "vbe")}`
- `RESISTOR_FIELDS = ("r1", "r2", "rc", "re", "rb")` (แทนค่าตัวอย่าง 5 ตัวของเดิม)
- `UNKNOWN_MODE_MESSAGE = "ไม่รู้จักโหมดวงจรที่เลือก"`
- `FixedBiasInput` และ `EmitterBiasInput` เป็น `@dataclass(frozen=True)`
- ย้าย `vth`/`rth` ไปท้าย `BiasResult` พร้อม `= None`

- [ ] **Step 5: เขียน `calculate_fixed` และ `calculate_emitter`**

ทั้งคู่: `ic = β·ib`, `ie = (β+1)·ib`, `vc = vcc − ic·rc`, `vce = vc − ve`
`calculate_fixed`: `ib = (vcc − vbe) / rb`, `ve = 0.0`, `vb = ve + vbe`
`calculate_emitter`: `ib = (vcc − vbe) / (rb + (β+1)·re)`, `ve = ie·re`, `vb = ve + vbe`
region: `ib <= 0` → `cutoff` + `CUTOFF_WARNING`; `vce <= SATURATION_VCE_LIMIT` → `saturation` + `SATURATION_WARNING`; อื่น ๆ → `active`
ทั้งสองฟังก์ชันปล่อย `vth`/`rth` เป็น `None`

- [ ] **Step 6: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: 39 + 7 tests PASS

- [ ] **Step 7: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop (checkpoint ไม่บังคับ)**

ไฟล์: `dc_bias.py`, `tests/test_fixed.py`, `tests/test_emitter.py`

---

### Task 2: `parse_mode` และ `validate()` ตามโหมด

**Files:**
- Modify: `dc_bias.py` (`validate` บรรทัด 116–181)
- Test: `tests/test_validation.py` (เพิ่มคลาสท้ายไฟล์)

**Interfaces:**
- Consumes: `MODES`, `MODE_FIELDS`, `RESISTOR_FIELDS`, `UNKNOWN_MODE_MESSAGE`, `FixedBiasInput`, `EmitterBiasInput` จาก Task 1
- Produces:
  - `parse_mode(raw: str | None) -> str | None` — `None`/`""` → `"divider"`; ค่าที่อยู่ใน `MODES` → ค่านั้น; อื่น ๆ → `None`
  - `validate(form: Mapping[str, str], mode: str = "divider") -> tuple[FixedBiasInput | EmitterBiasInput | BiasInput | None, dict[str, str]]`
  - `mode` ที่ไม่รู้จัก → `(None, {"mode": UNKNOWN_MODE_MESSAGE})`

- [ ] **Step 1: เพิ่ม failing test**

เพิ่มคลาส `ModeValidationTest` ใน `tests/test_validation.py` — 6 เทสต์:

```python
class ModeValidationTest(unittest.TestCase):
    FIXED = {"mode": "fixed", "vcc": "12", "beta": "100", "rb": "1000", "rc": "2.2", "vbe": "0.7"}

    def test_missing_mode_defaults_to_divider(self):
        bias_input, errors = validate(VALID)
        self.assertEqual(errors, {})
        self.assertIsInstance(bias_input, BiasInput)

    def test_fixed_converts_rb_to_ohms(self):
        bias_input, errors = validate(self.FIXED, "fixed")
        self.assertEqual(errors, {})
        self.assertEqual(bias_input.rb, 1_000_000.0)

    def test_fixed_ignores_divider_fields(self):
        form = {**self.FIXED, "r1": "abc", "r2": "0", "re": ""}
        bias_input, errors = validate(form, "fixed")
        self.assertEqual(errors, {})

    def test_fixed_requires_rb(self):
        form = dict(self.FIXED); del form["rb"]
        bias_input, errors = validate(form, "fixed")
        self.assertIsNone(bias_input)
        self.assertEqual(errors["rb"], "กรุณากรอกค่านี้")

    def test_fixed_zero_rb_is_rejected(self):
        _, errors = validate({**self.FIXED, "rb": "0"}, "fixed")
        self.assertEqual(errors["rb"], "ความต้านทานต้องมากกว่า 0")

    def test_emitter_requires_re(self):
        form = {**self.FIXED, "mode": "emitter"}
        _, errors = validate(form, "emitter")
        self.assertEqual(errors["re"], "กรุณากรอกค่านี้")

    def test_unknown_mode_reports_error(self):
        bias_input, errors = validate(self.FIXED, "xyz")
        self.assertIsNone(bias_input)
        self.assertEqual(errors, {"mode": "ไม่รู้จักโหมดวงจรที่เลือก"})

    def test_parse_mode(self):
        self.assertEqual(parse_mode(None), "divider")
        self.assertEqual(parse_mode(""), "divider")
        self.assertEqual(parse_mode("emitter"), "emitter")
        self.assertIsNone(parse_mode("xyz"))
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_validation -v`
Expected: `ImportError: cannot import name 'parse_mode'`

- [ ] **Step 3: เขียน `parse_mode`**

คืน `"divider"` เมื่อ `raw` เป็น `None` หรือสตริงว่าง; คืน `raw` เมื่ออยู่ใน `MODES`; มิฉะนั้น `None`

- [ ] **Step 4: ปรับ `validate` ให้รับ `mode`**

- `mode` ไม่อยู่ใน `MODES` → `return None, {"mode": UNKNOWN_MODE_MESSAGE}` ก่อนทำงานอื่น
- วน `MODE_FIELDS[mode]` แทน `FIELDS` คงข้อความ error เดิมทุกข้อ
- ตรวจ `RESISTOR_FIELDS` เฉพาะตัวที่อยู่ในโหมดนั้น
- แปลง kΩ→Ω และตรวจ `isfinite` เฉพาะช่องตัวต้านทานของโหมดนั้น
- คืน `FixedBiasInput` / `EmitterBiasInput` / `BiasInput` ตาม `mode`

- [ ] **Step 5: รันทั้ง suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: ทุก test PASS (39 เดิมห้ามแดง)

- [ ] **Step 6: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop (checkpoint ไม่บังคับ)**

---

### Task 3: `app.py` เลือกโหมดและประกอบ context

**Files:**
- Modify: `app.py` ทั้งไฟล์ (76 บรรทัด)
- Test: `tests/test_web.py` (เพิ่มคลาสท้ายไฟล์)

**Interfaces:**
- Consumes: `parse_mode`, `validate`, `calculate`, `calculate_fixed`, `calculate_emitter`, `MODE_FIELDS`, `MODES` จาก Task 1–2; `fmt_*` จาก Task 3 ของ Lab 2
- Produces (ให้เทมเพลตใน Task 4):
  - `MODE_LABELS = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
  - `DEFAULT_FORMS` (dict ต่อโหมด) — `fixed`/`emitter` ใช้ `rb = "1000"` (1 MΩ) เพื่อให้กรอก A2–A4 ได้ทันที
  - `FIELD_LABELS = {"vcc": "VCC (V)", "beta": "β", "rb": "RB (kΩ)", "r1": "R1 (kΩ)", "r2": "R2 (kΩ)", "rc": "RC (kΩ)", "re": "RE (kΩ)", "vbe": "VBE (V)"}`
  - `FORMULAS["IB"]` เป็น dict ต่อโหมด
  - `fields = [{"name", "label", "value", "error"}]`, `steps = [(name, formula, value)]`
  - context: `mode`, `mode_label`, `mode_options` (`[(key, label)]`), `fields`, `results`, `steps`, `region`, `region_key`, `warnings`, `mode_error`

- [ ] **Step 1: เพิ่ม failing test คลาส `ModeWebTest`**

```python
class ModeWebTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_fixed_shows_rb_and_hides_r1(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertNotIn('name="r1"', body)
        self.assertNotIn('name="re"', body)

    def test_get_emitter_shows_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertIn('name="re"', body)
        self.assertNotIn('name="r1"', body)

    def test_post_fixed_shows_a2_values(self):
        body = self.client.post("/", data={"mode": "fixed", "vcc": "12", "beta": "100",
                                           "rb": "1000", "rc": "2.2", "vbe": "0.7"}).get_data(as_text=True)
        self.assertIn("1.130 mA", body)
        self.assertIn("9.514 V", body)
        self.assertIn("Fixed Bias", body)

    def test_post_emitter_shows_a3_values(self):
        body = self.client.post("/", data={"mode": "emitter", "vcc": "12", "beta": "100",
                                           "rb": "1000", "rc": "2.2", "re": "1", "vbe": "0.7"}).get_data(as_text=True)
        self.assertIn("1.026 mA", body)
        self.assertIn("8.705 V", body)

    def test_post_emitter_re_2k_changes_result(self):
        body = self.client.post("/", data={"mode": "emitter", "vcc": "12", "beta": "100",
                                           "rb": "1000", "rc": "2.2", "re": "2", "vbe": "0.7"}).get_data(as_text=True)
        self.assertIn("0.940 mA", body)
        self.assertIn("8.033 V", body)

    def test_post_fixed_rb_zero_shows_error_and_hides_results(self):
        body = self.client.post("/", data={"mode": "fixed", "vcc": "12", "beta": "100",
                                           "rb": "0", "rc": "2.2", "vbe": "0.7"}).get_data(as_text=True)
        self.assertIn("ความต้านทานต้องมากกว่า 0", body)
        self.assertNotIn("ขั้นตอนการคำนวณ", body)

    def test_post_unknown_mode_shows_error(self):
        body = self.client.post("/", data={"mode": "xyz"}).get_data(as_text=True)
        self.assertIn("ไม่รู้จักโหมดวงจรที่เลือก", body)
        self.assertNotIn("ขั้นตอนการคำนวณ", body)

    def test_get_unknown_mode_shows_error(self):
        body = self.client.get("/?mode=xyz").get_data(as_text=True)
        self.assertIn("ไม่รู้จักโหมดวงจรที่เลือก", body)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v`
Expected: FAIL ที่ `test_get_fixed_shows_rb_and_hides_r1`

- [ ] **Step 3: เขียน `app.py` ใหม่**

- `GET`: `mode = parse_mode(request.args.get("mode"))`; ถ้า `None` → `render_template` พร้อม `mode_error` และ `fields=[]`
- `POST`: `mode = parse_mode(request.form.get("mode"))`; ถ้า `None` → เหมือนกัน
- `if/elif` เรียก `calculate` / `calculate_fixed` / `calculate_emitter`
- error จาก `validate` → `fields` ที่มี error, `results=None` เสมอ
- `steps`: divider = VTH/RTH/IB/IE (ค่าเดิม); fixed/emitter = IB/IE
- ผลลัพธ์ยังเป็น dict ของสตริงที่จัดรูปแบบแล้ว (`vb`, `ve`, `vc`, `vce`, `ic`) — โครงเดียวกับ Lab 2

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop (checkpoint ไม่บังคับ)**

---

### Task 4: เทมเพลตและ CSS

**Files:**
- Modify: `templates/index.html` ทั้งไฟล์
- Modify: `static/style.css` (ต่อท้าย)
- Test: `tests/test_web.py` (ทดสอบจาก Task 3 ครอบไว้แล้ว ไม่เพิ่มไฟล์)

**Interfaces:**
- Consumes: context จาก Task 3
- Produces: markup ที่มี `name=` ตรงกับ `MODE_FIELDS` และ `<label for>` ตรงกับ `id` ทุกช่อง เพื่อให้ browser tool หา element เจอ

- [ ] **Step 1: แก้ header และเพิ่มแถบโหมด**

`<p class="subtitle">Common-Emitter · Fixed · Emitter · Voltage Divider</p>`
`<nav class="modes">` วน `mode_options` เป็นลิงก์ `/?mode={{ key }}` พร้อม `aria-current="page"` เมื่อเป็นโหมดปัจจุบัน

- [ ] **Step 2: เปลี่ยนฟอร์มให้วน `fields`**

`<form class="card" method="post" action="/">` + `<input type="hidden" name="mode" value="{{ mode }}">` แล้ว `{% for f in fields %}` สร้าง `<label for="{{ f.name }}">{{ f.label }}</label>`, `<input id="{{ f.name }}" name="{{ f.name }}" ... value="{{ f.value }}">`, `{% if f.error %}<p class="error">{{ f.error }}</p>{% endif %}`

- [ ] **Step 3: ผลลัพธ์ระบุโหมด + แก้หมายเหตุเป็น 0.2 V**

- หัวบล็อกผล: `<h2>ผลลัพธ์ · {{ mode_label }}</h2>`
- การ์ด VB/VE/VC/VCE/IC คงเดิม
- หมายเหตุท้าย: `แบบจำลอง Forward-Active: β และ VBE คงที่ · เกณฑ์เตือน Saturation ที่ VCE ≤ 0.2 V`
- แสดง `mode_error` เป็น `<p class="warning">` เมื่อไม่มีฟอร์ม

- [ ] **Step 4: เพิ่ม CSS ของแถบโหมด**

`.modes` เป็นแถวปุ่มมน, `.modes a` สีน้ำเงิน, `.modes a[aria-current="page"]` พื้นเข้มตัวอักษรขาว — อย่างอื่นปล่อยตามสไตล์เดิม

- [ ] **Step 5: รัน suite + เปิดดูด้วยตา**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS ทุกตัว

- [ ] **Step 6: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop (checkpoint ไม่บังคับ)**

---

### Task 5: เอกสารให้ตรงกับสามโหมด

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/design-note.md`
- Modify: `docs/validation.md`

**Interfaces:**
- Consumes: ค่าที่ผ่านการยืนยันจาก Task 1–4

- [ ] **Step 1: `README.md`** — เพิ่มตารางสามโหมด (ช่องที่ใช้, สมการ IB), ตัวอย่าง A2–A4, ระบุ `RB` เป็น kΩ, และเปลี่ยนเกณฑ์ Saturation เป็น 0.2 V
- [ ] **Step 2: `AGENTS.md`** — เพิ่มกติกา: สมการต่อโหมดแยกฟังก์ชัน, `validate(form, mode)` รับเฉพาะช่องของโหมด, ห้ามเดาโหมดจากค่าที่ไม่รู้จัก, เกณฑ์ 0.2 V
- [ ] **Step 3: `docs/design-note.md`** — เพิ่มหัวข้อ "ทำไมเลือกฟังก์ชันแยกต่อโหมด" และอัปเดตเกณฑ์ 0.2 V
- [ ] **Step 4: `docs/validation.md`** — เติมตาราง A1–A5 (คอลัมน์: กรณี, เลือกโหมด+อินพุต, คาดหมาย, เห็นจริง, วิธีตรวจ, สถานะ) โดย A1 เทียบกับ baseline §6 ที่บันทึกไว้แล้ว; ช่อง "วิธีตรวจ" ต้องเป็นชื่อเครื่องมือจริงที่ใช้
- [ ] **Step 5: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop (checkpoint ไม่บังคับ)**

---

### Task 6: ตรวจ A1–A5 ด้วย Playwright MCP

**Files:**
- Modify: `docs/validation.md` (ผลจริง + หลักฐาน)

**Interfaces:**
- Consumes: `opencode.json` ที่มี `mcp.servers.playwright` (มีอยู่แล้ว, `cmd /c npx -y @playwright/mcp@latest --browser chrome --isolated`), Flask ที่รันบน `http://127.0.0.1:5000/`

- [ ] **Step 1: รีสตาร์ต OpenCode Desktop** ให้โหลด `opencode.json` และ PATH ของ Node ใหม่ จากนั้นตรวจว่า MCP `playwright` ขึ้นสถานะเชื่อมต่อ
- [ ] **Step 2: ตรวจ 3 ชั้นตามใบงาน**

1. Flask: เปิด `http://127.0.0.1:5000/` ด้วยมือได้
2. MCP: `playwright` เชื่อมต่อ
3. เอเจนต์ใช้ได้จริง: สั่งให้เปิดเว็บและอ่าน snapshot แล้วรายงานชื่อหน้า + ชื่อช่องอย่างน้อย 2 ช่อง พร้อมระบุเครื่องมือ

- [ ] **Step 3: รัน A1–A5**

| ID | โหมด | อินพุต (หน่วยบนฟอร์ม) | คาดหมาย |
|---|---|---|---|
| A1 | Divider | R1=100, R2=22, RC=2.2, RE=1 | IC 1.230 mA · VCE 8.052 V |
| A2 | Fixed | RB=1000, RC=2.2 | IC 1.130 mA · VCE 9.514 V |
| A3 | Emitter | RB=1000, RC=2.2, RE=1 | IC 1.026 mA · VCE 8.705 V |
| A4 | Emitter | RB=1000, RC=2.2, **RE=2** | IC 0.940 mA ↓ · VCE 8.033 V ↑ |
| A5 | Fixed | RB=0 | ข้อความให้แก้ RB, ไม่มีผลค้าง |

ทุกกรณี `VCC=12`, `β=100`, `VBE=0.7`; เกณฑ์: IC ±0.01 mA, VCE ±0.02 V
อ่านผลใหม่ทุกครั้งหลังเปลี่ยนโหมดหรือส่งฟอร์ม ห้ามใช้ผลรอบก่อน

- [ ] **Step 4: เก็บหลักฐาน** — ข้อความที่อ่านได้จากหน้าเว็บอย่างน้อยหนึ่งกรณี และ screenshot อย่างน้อยหนึ่งภาพ
- [ ] **Step 5: บันทึกลง `docs/validation.md`** — เติม "เห็นจริง" + "สถานะ" (PASS/FAIL/NOT RUN) + ชื่อเครื่องมือจริง
- [ ] **Step 6: ถ้า MCP ใช้ไม่ได้** — บันทึก `Playwright MCP = NOT RUN` พร้อมข้อความ error จริง แล้วใช้ OpenCode Browser ตรวจ A1–A5 แทน โดยระบุวิธีจริงว่า `OpenCode Browser`
- [ ] **Step 7: หยุด — ให้ผู้ใช้ commit + push ผ่าน GitHub Desktop**

หลัง push: คัดลอก Commit SHA และ Repository URL ส่ง Moodle พร้อมตาราง A1–A5

---

## Self-Review

- **Spec coverage:** ครบทุกหัวข้อของ spec §6 (6.1 สมการ → Task 1; 6.2 `dc_bias` → Task 1–2; 6.3 `app.py` → Task 3; 6.4 เทมเพลต → Task 4; 6.5 เทสต์ → Task 1–3; 6.6 เอกสาร → Task 5–6)
- **Review Focus:** ทั้ง 5 ข้อมี test รองรับ (ข้อ 1 → `test_missing_mode_defaults_to_divider`; ข้อ 2 → `test_fixed_ignores_divider_fields`; ข้อ 3 → `test_unknown_mode_reports_error` + `test_get_unknown_mode_shows_error`; ข้อ 4 → `test_fixed_converts_rb_to_ohms` + `test_post_fixed_rb_zero_shows_error_and_hides_results`; ข้อ 5 → `test_post_fixed_shows_a2_values` + `test_post_fixed_rb_zero_shows_error_and_hides_results`)
- **Type consistency:** `BiasResult` ใช้ร่วมทั้งสามฟังก์ชัน; `validate` คืนชนิดอินพุตตาม `mode` และ `app.py` จับคู่กับฟังก์ชันเดียวกัน
- **Proportion:** แผนสั้นกว่าโค้ดที่ต้องเขียน และไม่มี step ที่ตัดสินใจแทนไม่ได้
