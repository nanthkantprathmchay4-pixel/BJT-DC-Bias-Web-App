# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web App หลายไฟล์ที่คำนวณ DC Operating Point ของ BJT Common-Emitter Voltage-Divider Bias พร้อม validation, region warning และ automated tests ภายในคาบ Lab 02

**Architecture:** Flask รับ `POST /` แล้วเรียก `dc_bias.validate()` → `dc_bias.calculate()` ซึ่งเป็นฟังก์ชันบริสุทธิ์ที่ไม่รู้จัก HTTP, จากนั้นเรนเดอร์ `templates/index.html` หน้าเดียวที่แสดงฟอร์มและผลลัพธ์พร้อมกัน ไม่มี JavaScript

**Tech Stack:** Python 3.15.2, Flask 3.1.3, Jinja2, `unittest` (stdlib), HTML/CSS

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Python 3.15.2, Flask 3.1.3 — `requirements.txt` มีเพียง `Flask`
- ใช้ `unittest` จาก stdlib เท่านั้น ห้ามเพิ่ม pytest
- ห้ามใช้ JavaScript ฝั่ง client ทั้งหมดเรนเดอร์ฝั่ง server
- สมการทั้งหมดอยู่ใน `dc_bias.py` เท่านั้น ห้ามคำนวณในเทมเพลต และห้ามใส่เลขผลลัพธ์ตายตัวในเทมเพลต
- `dc_bias.py` ห้าม import `flask`
- ตัวต้านทานรับเป็น **kΩ** จากฟอร์ม แล้วแปลงเป็น Ω ภายใน `validate()`
- รูปแบบตัวเลข: ทศนิยม 3 ตำแหน่ง; กระแส `>= 1 mA` → mA, ต่ำกว่า → µA; ความต้านทาน `>= 1000 Ω` → kΩ, ต่ำกว่า → Ω
- เกณฑ์ Saturation: `VCE <= 0.3 V`; เกณฑ์ Cutoff: `VTH <= VBE`
- รันคำสั่งทั้งหมดจาก root ของ repo
- **ห้าม agent รัน `git commit` / `git push`** — ผู้ใช้ commit ผ่าน GitHub Desktop เท่านั้น
- ภาษา UI ไทย ศัพท์เทคนิคอังกฤษ

## Review Focus

1. **ช่องกรอกที่มีช่องว่างหรือตัวคั่นหลักพัน** (`" 12 "`, `"1,000"`) — ผู้ใช้พิมพ์ตามสัญชาตญาณ ต้องได้ข้อความ error ที่อ่านรู้เรื่อง ไม่ใช่ 500 (ทดสอบใน Task 2)
2. **POST ที่ไม่มีฟิลด์เลย** (กด submit ฟอร์มว่าง หรือ request ที่ตัดฟิลด์ออก) — ต้องเห็น error ครบทุกช่อง ไม่ล้ม (ทดสอบใน Task 2 และ Task 5)
3. **ค่าที่ทำให้ตัวส่วนเป็นศูนย์หรือติดลบ** (เช่น `β` ติดลบจน `RTH+(β+1)RE <= 0`) — validation ต้องกันก่อนถึง `calculate()` (ทดสอบใน Task 2)
4. **ค่ามากผิดปกติ** (`VCC = 1e9`) — ต้องไม่ crash และไม่แสดง `inf`/`nan` อย่างเงียบ ๆ (ทดสอบใน Task 5)
5. **β เป็นทศนิยม** (`2.5`) — สมการต้องใช้ค่าได้ตามปกติ ไม่ปัดเป็นจำนวนเต็ม (ทดสอบใน Task 2)

---

### Task 1: โครงโปรเจกต์ + ฟังก์ชันคำนวณ

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `dc_bias.py`
- Create: `tests/test_dc_bias.py`

**Interfaces:**
- Produces:
  - `BiasInput(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float)` — dataclass, ตัวต้านทานหน่วย Ω
  - `BiasResult(vth, rth, ib, ic, ie, vb, ve, vc, vce: float, region: str, warnings: list[str])` — dataclass
  - `calculate(p: BiasInput) -> BiasResult`
  - ค่าคงที่ `SATURATION_VCE_LIMIT = 0.3`

- [ ] **Step 1: เขียน failing test**

สร้าง `tests/test_dc_bias.py`:

```python
import unittest

from dc_bias import BiasInput, calculate

REFERENCE = BiasInput(
    vcc=12, r1=100_000, r2=22_000, rc=2_200, re=1_000, beta=100, vbe=0.7
)


class ReferenceCaseTest(unittest.TestCase):
    def setUp(self):
        self.r = calculate(REFERENCE)

    def test_intermediate_values(self):
        self.assertAlmostEqual(self.r.vth, 2.163934, delta=1e-6)
        self.assertAlmostEqual(self.r.rth, 18032.787, delta=1e-3)

    def test_currents(self):
        self.assertAlmostEqual(self.r.ib, 12.298581463e-6, delta=1e-9)
        self.assertAlmostEqual(self.r.ic, 1.2298581463e-3, delta=1e-9)
        self.assertAlmostEqual(self.r.ie, 1.242156727763e-3, delta=1e-9)

    def test_voltages(self):
        self.assertAlmostEqual(self.r.ve, 1.242156727763, delta=1e-6)
        self.assertAlmostEqual(self.r.vb, 1.942156727763, delta=1e-6)
        self.assertAlmostEqual(self.r.vc, 9.29431207814, delta=1e-6)
        self.assertAlmostEqual(self.r.vce, 8.052155350377, delta=1e-6)

    def test_region_is_active_without_warnings(self):
        self.assertEqual(self.r.region, "active")
        self.assertEqual(self.r.warnings, [])


class RegionTest(unittest.TestCase):
    def test_cutoff_when_vth_not_above_vbe(self):
        p = BiasInput(
            vcc=12, r1=100_000, r2=5_000, rc=2_200, re=1_000, beta=100, vbe=0.7
        )
        r = calculate(p)
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ie, 0.0)
        self.assertAlmostEqual(r.vb, 0.571429, delta=1e-6)
        self.assertAlmostEqual(r.vc, 12.0, delta=1e-9)
        self.assertTrue(r.warnings)

    def test_saturation_when_vce_low(self):
        p = BiasInput(
            vcc=12, r1=100_000, r2=22_000, rc=8_700, re=1_000, beta=100, vbe=0.7
        )
        r = calculate(p)
        self.assertEqual(r.region, "saturation")
        self.assertAlmostEqual(r.vce, 0.0581, delta=1e-3)
        self.assertTrue(r.warnings)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: เขียน `dc_bias.py`**

ใช้ `@dataclass(frozen=True)` กับ `BiasInput` และ `BiasResult` ตาม Interfaces
ลำดับการคำนวณ: `vth` → `rth` → `ib` → `ic` → `ie` → `ve` → `vb` → `vc` → `vce`

ตรรกะ region:
- ถ้า `vth <= p.vbe` → `region="cutoff"`, `ib=ic=ie=0.0`, `ve=0.0`, `vb=vth`, `vc=p.vcc`, `vce=p.vcc`, `warnings` มีข้อความ `"วงจรอยู่ในช่วง Cutoff — แบบจำลอง Forward-Active ใช้ไม่ได้"`
- ถ้า `vce <= SATURATION_VCE_LIMIT` → `region="saturation"`, คงค่าที่คำนวณได้, `warnings` มีข้อความ `"VCE ต่ำกว่า 0.3 V — ใกล้หรือเข้าสู่ Saturation ค่าที่ได้ไม่น่าเชื่อถือ"`
- อื่น ๆ → `region="active"`, `warnings=[]`

- [ ] **Step 4: สร้างไฟล์ประกอบ**

`requirements.txt`:
```
Flask==3.1.3
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
```

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS 6 tests

- [ ] **Step 6: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์ที่ต้องเข้า commit: `requirements.txt`, `.gitignore`, `dc_bias.py`, `tests/test_dc_bias.py`
ข้อความแนะนำ: `Add DC bias calculation core with tests`

---

### Task 2: Validation และการแปลงหน่วย

**Files:**
- Modify: `dc_bias.py`
- Create: `tests/test_validation.py`

**Interfaces:**
- Consumes: `BiasInput` จาก Task 1
- Produces: `validate(form: Mapping[str, str]) -> tuple[BiasInput | None, dict[str, str]]`
  - key ของ `form` และ key ของ error dict คือ `"vcc"`, `"r1"`, `"r2"`, `"rc"`, `"re"`, `"beta"`, `"vbe"`
  - ค่า `r1`, `r2`, `rc`, `re` ในฟอร์มเป็น kΩ → คูณ 1 000 ก่อนใส่ `BiasInput`
  - คืน `(None, errors)` ถ้ามี error อย่างน้อยหนึ่งรายการ

- [ ] **Step 1: เขียน failing test**

สร้าง `tests/test_validation.py`:

```python
import unittest

from dc_bias import validate

VALID = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


class ValidInputTest(unittest.TestCase):
    def test_returns_bias_input_with_ohms(self):
        bias_input, errors = validate(VALID)
        self.assertEqual(errors, {})
        self.assertIsNotNone(bias_input)
        self.assertEqual(bias_input.r1, 100_000.0)
        self.assertEqual(bias_input.rc, 2_200.0)

    def test_strips_surrounding_whitespace(self):
        bias_input, errors = validate({**VALID, "vcc": " 12 "})
        self.assertEqual(errors, {})
        self.assertEqual(bias_input.vcc, 12.0)

    def test_accepts_fractional_beta(self):
        bias_input, errors = validate({**VALID, "beta": "2.5"})
        self.assertEqual(errors, {})
        self.assertEqual(bias_input.beta, 2.5)


class InvalidInputTest(unittest.TestCase):
    def test_missing_field(self):
        form = dict(VALID)
        del form["re"]
        bias_input, errors = validate(form)
        self.assertIsNone(bias_input)
        self.assertEqual(errors["re"], "กรุณากรอกค่านี้")

    def test_non_numeric(self):
        bias_input, errors = validate({**VALID, "vcc": "abc"})
        self.assertIsNone(bias_input)
        self.assertEqual(errors["vcc"], "ต้องเป็นตัวเลข")

    def test_thousands_separator_is_rejected_as_non_numeric(self):
        bias_input, errors = validate({**VALID, "r1": "1,000"})
        self.assertIsNone(bias_input)
        self.assertEqual(errors["r1"], "ต้องเป็นตัวเลข")

    def test_zero_or_negative_resistance(self):
        _, errors = validate({**VALID, "r1": "-1"})
        self.assertEqual(errors["r1"], "ความต้านทานต้องมากกว่า 0")
        _, errors = validate({**VALID, "r2": "0"})
        self.assertEqual(errors["r2"], "ความต้านทานต้องมากกว่า 0")

    def test_zero_beta(self):
        _, errors = validate({**VALID, "beta": "0"})
        self.assertEqual(errors["beta"], "β ต้องมากกว่า 0")

    def test_non_positive_vcc(self):
        _, errors = validate({**VALID, "vcc": "0"})
        self.assertEqual(errors["vcc"], "VCC ต้องมากกว่า 0")

    def test_vbe_out_of_range(self):
        _, errors = validate({**VALID, "vbe": "12"})
        self.assertEqual(errors["vbe"], "VBE ต้องอยู่ระหว่าง 0 ถึง VCC")

    def test_beta_below_minus_one_is_blocked(self):
        _, errors = validate({**VALID, "beta": "-5"})
        self.assertIn("beta", errors)

    def test_all_missing_reports_every_field(self):
        _, errors = validate({})
        self.assertEqual(len(errors), 7)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest tests.test_validation -v` (หรือ `python -m unittest discover -s tests -v`)
Expected: FAIL — `ImportError: cannot import name 'validate'`

- [ ] **Step 3: เพิ่ม `validate()` ใน `dc_bias.py`**

กติกาที่ต้องใช้ (คงข้อความ error ตามนี้เป๊ะ):
- ค่าไม่ผ่าน `strip()` แล้วว่าง → `"กรุณากรอกค่านี้"`
- แปลง `float()` ไม่ได้ (รวมถึง `"1,000"`) → `"ต้องเป็นตัวเลข"`
- `vcc <= 0` → `"VCC ต้องมากกว่า 0"`
- ตัวต้านทาน `<= 0` → `"ความต้านทานต้องมากกว่า 0"`
- `beta <= 0` → `"β ต้องมากกว่า 0"`
- `vbe < 0` หรือ `vbe >= vcc` → `"VBE ต้องอยู่ระหว่าง 0 ถึง VCC"`
- เก็บ error ทุกฟิลด์ (ไม่หยุดที่ตัวแรก) แล้วคืน `(None, errors)` ถ้ามี error
- ถ้า `vcc` แปลงเป็นตัวเลขไม่ได้ ให้ข้ามการตรวจช่วง `VBE` (ไม่ให้เกิด `TypeError`/`KeyError`)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุก test (6 + 11)

- [ ] **Step 5: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์: `dc_bias.py`, `tests/test_validation.py`
ข้อความแนะนำ: `Add input validation and unit conversion`

---

### Task 3: ตัวช่วยจัดรูปแบบตัวเลขและหน่วย

**Files:**
- Create: `formatting.py`
- Create: `tests/test_formatting.py`

**Interfaces:**
- Produces:
  - `fmt_voltage(volts: float) -> str` → `"1.942 V"`
  - `fmt_current(amps: float) -> str` → `"1.230 mA"` หรือ `"12.299 µA"`
  - `fmt_resistance(ohms: float) -> str` → `"18.033 kΩ"` หรือ `"820.000 Ω"`

- [ ] **Step 1: เขียน failing test**

สร้าง `tests/test_formatting.py`:

```python
import unittest

from formatting import fmt_current, fmt_resistance, fmt_voltage


class FormatTest(unittest.TestCase):
    def test_voltage(self):
        self.assertEqual(fmt_voltage(1.942156), "1.942 V")
        self.assertEqual(fmt_voltage(12.0), "12.000 V")

    def test_current_uses_milliamp_above_one_milliamp(self):
        self.assertEqual(fmt_current(1.22986e-3), "1.230 mA")

    def test_current_uses_microamp_below_one_milliamp(self):
        self.assertEqual(fmt_current(12.2986e-6), "12.299 µA")

    def test_current_boundary_is_one_millamp(self):
        self.assertEqual(fmt_current(1e-3), "1.000 mA")

    def test_resistance_uses_kilo_ohm_above_one_thousand(self):
        self.assertEqual(fmt_resistance(18032.787), "18.033 kΩ")

    def test_resistance_uses_ohm_below_one_thousand(self):
        self.assertEqual(fmt_resistance(820.0), "820.000 Ω")
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'formatting'`

- [ ] **Step 3: เขียน `formatting.py`**

ใช้ `f"{value:.3f} <unit>"` ในทุกฟังก์ชัน และเปรียบเทียบขอบด้วย `>= 1e-3` (กระแส) และ `>= 1000` (ความต้านทาน)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุก test

- [ ] **Step 5: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์: `formatting.py`, `tests/test_formatting.py`
ข้อความแนะนำ: `Add unit formatting helpers`

---

### Task 4: Flask app และหน้า GET

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `BiasInput`, `calculate`, `validate` (Task 1–2), `fmt_*` (Task 3)
- Produces:
  - `app` — Flask instance ใน `app.py` (ชื่อตัวแปร `app`)
  - route `GET /` และ `POST /` ในฟังก์ชัน `index()`
  - ค่าคงที่ `DEFAULT_FORM = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"}`

- [ ] **Step 1: เขียน failing test**

สร้าง `tests/test_web.py`:

```python
import unittest

from app import app


class GetFormTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("<form", body)

    def test_get_has_every_named_input(self):
        body = self.client.get("/").get_data(as_text=True)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', body)

    def test_get_prefills_defaults(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="12"', body)
        self.assertIn('value="100"', body)

    def test_get_has_no_results_block(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("ขั้นตอนการคำนวณ", body)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: เขียน `app.py`**

`app = Flask(__name__)`; `@app.route("/", methods=["GET", "POST"])` ฟังก์ชัน `index()`:
- `GET` → `render_template("index.html", form=DEFAULT_FORM, errors={}, results=None)`
- `POST` (Task 5 จะเติม logic) → ชั่วคราวให้คืน `render_template` แบบเดียวกับ GET

- [ ] **Step 4: เขียน `templates/index.html`**

- `<form method="post" action="/">` มี 7 ช่อง พร้อม `<label for="...">` และ `name="..."` ตรงกับ key
- ทุกช่องมี `value="{{ form.<key> }}"` และแสดงหน่วยข้างช่อง (V, kΩ)
- ปุ่ม `<button type="submit">Calculate DC Bias</button>`
- `{% if results %}` แสดงบล็อกผลลัพธ์ (จะเติมใน Task 5)
- `{% if errors %}` แสดงรายการ error
- ลิงก์ `static/style.css` ด้วย `url_for`

- [ ] **Step 5: เขียน `static/style.css`**

จัดกลางหน้า, ฟอร์มเป็น grid 2 คอลัมน์บนจอกว้าง, ป้าย Region เป็น badge, ตาราง steps มีเส้นคั่น — ไม่ต้องสวยที่สุด ขอให้อ่านง่ายและ responsive

- [ ] **Step 6: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุก test

- [ ] **Step 7: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์: `app.py`, `templates/index.html`, `static/style.css`, `tests/test_web.py`
ข้อความแนะนำ: `Add Flask app with input form`

---

### Task 5: POST คำนวณและแสดงผลลัพธ์

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: `validate`, `calculate`, `fmt_voltage`, `fmt_current`, `fmt_resistance`
- Produces: `render_template` ที่ส่ง `results` (dict พร้อมสตริงที่จัดรูปแบบแล้ว), `region`, `warnings`, `steps`, `errors`, `form`

- [ ] **Step 1: เพิ่ม failing tests ต่อท้าย `tests/test_web.py`**

```python
VALID_POST = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


class CalculatePostTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_post_shows_results(self):
        body = self.client.post("/", data=VALID_POST).get_data(as_text=True)
        self.assertIn("1.942", body)          # VB
        self.assertIn("1.230 mA", body)       # IC
        self.assertIn("Active Region", body)

    def test_valid_post_shows_steps(self):
        body = self.client.post("/", data=VALID_POST).get_data(as_text=True)
        self.assertIn("ขั้นตอนการคำนวณ", body)
        self.assertIn("2.164", body)          # VTH

    def test_invalid_input_shows_error_without_traceback(self):
        body = self.client.post(
            "/", data={**VALID_POST, "beta": "0"}
        ).get_data(as_text=True)
        self.assertIn("β ต้องมากกว่า 0", body)
        self.assertNotIn("Traceback", body)

    def test_empty_post_reports_missing_fields(self):
        body = self.client.post("/", data={}).get_data(as_text=True)
        self.assertIn("กรุณากรอกค่านี้", body)

    def test_saturation_shows_warning(self):
        body = self.client.post(
            "/", data={**VALID_POST, "rc": "8.7"}
        ).get_data(as_text=True)
        self.assertIn("Saturation", body)

    def test_huge_values_do_not_crash(self):
        resp = self.client.post("/", data={**VALID_POST, "vcc": "1000000000"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Traceback", resp.get_data(as_text=True))
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL ที่ `test_valid_post_shows_results` เป็นต้น

- [ ] **Step 3: เติม logic ใน `app.py`**

ใน `POST`:
1. `bias_input, errors = validate(request.form)`
2. ถ้า `errors` ไม่ว่าง → `render_template(..., form=request.form, errors=errors, results=None)`
3. ถ้าผ่าน → `result = calculate(bias_input)`
4. สร้าง dict สำหรับเทมเพลต:
   - `results = {"vb": fmt_voltage(result.vb), ...}` ครบ `vb, ve, vc, vce, ic`
   - `steps = [("VTH", "VCC · R2 / (R1 + R2)", fmt_voltage(result.vth)), ("RTH", ..., fmt_resistance(result.rth)), ("IB", ..., fmt_current(result.ib)), ("IE", ..., fmt_current(result.ie))]`
   - `region = result.region`, `warnings = result.warnings`
5. `render_template(..., form=request.form, errors={}, results=results, steps=steps, region=region, warnings=warnings)`

- [ ] **Step 4: เติมบล็อกผลลัพธ์ใน `templates/index.html`**

- badge แสดง `Active Region` / `Cutoff` / `Saturation` ตาม `region`
- การ์ด 5 ใบ: VB, VE, VC, VCE, IC จาก `results`
- ตาราง `ขั้นตอนการคำนวณ` วนจาก `steps` แสดงชื่อ, สูตร, ค่า
- `{% for w in warnings %}<p class="warning">{{ w }}</p>{% endfor %}`
- หมายเหตุใต้ผลลัพธ์: "แบบจำลอง Forward-Active: β และ VBE คงที่, เกณฑ์เตือน Saturation ที่ VCE ≤ 0.3 V"

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุก test (ทั้งหมด ≥ 20)

- [ ] **Step 6: ตรวจด้วยตาจริง**

Run: `python -m flask --app app run --debug`
เปิด `http://127.0.0.1:5000/` กรอกค่าตัวอย่าง กด Calculate — ต้องเห็น VB 1.942 V, IC 1.230 mA, badge Active Region
จากนั้นแก้ `β` เป็น `0` แล้วกดซ้ำ — ต้องเห็นข้อความ error และหน้าไม่พัง

- [ ] **Step 7: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์: `app.py`, `templates/index.html`, `tests/test_web.py`
ข้อความแนะนำ: `Render DC bias results in Flask template`

---

### Task 6: เอกสารประกอบและ README

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1–5

- [ ] **Step 1: เขียน `README.md`**

ต้องมี: ชื่อโปรเจกต์, สิ่งที่คำนวณได้, วิธีติดตั้ง (venv + pip), วิธีรัน, วิธีรัน test, โครงสร้างไฟล์, สมมติฐานของแบบจำลอง, ข้อจำกัด (ไม่ใช่ SPICE, Saturation เป็นเพียงเกณฑ์เตือน)

- [ ] **Step 2: เขียน `AGENTS.md`**

ต้องมีกติกา: สมการอยู่ใน `dc_bias.py` เท่านั้น, ห้าม hardcode ผลลัพธ์ในเทมเพลต, ห้ามใช้ JavaScript, รัน `python -m unittest discover -s tests -v` ก่อน commit, commit ผ่าน GitHub Desktop, รูปแบบหน่วย 3 ตำแหน่ง

- [ ] **Step 3: เขียน `docs/design-note.md`**

สรุป: ทำไมเลือก server-rendered ไม่เลือก JSON API, โครงสร้างไฟล์และหน้าที่, data flow, สิ่งที่ตัดออกและเหตุผล

- [ ] **Step 4: เขียน `docs/validation.md`**

- ตารางคำนวณมือของ reference case (จาก design doc §16) เทียบค่าที่โปรแกรมให้
- ผลรัน `python -m unittest discover -s tests -v`
- ผลทดสอบ invalid input และ region warning

- [ ] **Step 5: เขียน `docs/reflection.md`**

โครง 4 หัวข้อ: สิ่งที่เรียนรู้, ปัญหาที่เจอและวิธีแก้, จะทำอะไรต่างถ้ามีเวลา, คำตอบคำถามรายบุคคล 4 ข้อท้ายเอกสาร Lab (เหตุใดเปิด `index.html` ตรง ๆ ไม่เท่ากับรัน Flask / ฟอร์มส่งข้อมูลไป Python อย่างไร / แก้สมการใน `dc_bias.py` ต้องแก้ HTML ไหม / ทำไมผลนอก region ที่แบบจำลองใช้ไม่ได้ต้องมี warning) — เขียนเป็น baseline ให้เจ้าของงานแก้เป็นเสียงของตัวเอง

- [ ] **Step 6: รันชุดทดสอบทั้งหมดอีกครั้ง**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุก test, ไม่มี error/failure

- [ ] **Step 7: หยุด — ให้ผู้ใช้ commit ผ่าน GitHub Desktop**

ไฟล์: `README.md`, `AGENTS.md`, `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`
ข้อความแนะนำ: `Add README, agent rules and lab documentation`

---

## หลังจบ Plan

1. ผู้ใช้กด **Publish repository** ใน GitHub Desktop (ยังไม่มี remote)
2. ผู้ใช้กด **Push origin**
3. คัดลอก Commit SHA ล่าสุดส่ง Moodle พร้อม Repository URL
