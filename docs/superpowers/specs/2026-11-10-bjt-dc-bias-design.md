# BJT DC Bias Web App — Design

- **วันที่:** 2026-11-10
- **รายวิชา:** ENG29 2121 Computer Programming for Electrical Engineers (2/2569)
- **Lab:** 02 — First DC Bias Web App
- **สถานะ:** รออนุมัติ

---

## 1. Intent และเหตุผล

นักศึกษาต้องส่ง Web Application จริงที่คำนวณ DC Operating Point ของวงจร NPN BJT
แบบ Voltage-Divider Bias ภายในคาบเดียว โดยต้องแสดงให้เห็นว่าแยก
Frontend / Backend / Engineering Logic / Tests ออกจากกันได้จริง ไม่ใช่ HTML
ไฟล์เดียวที่ฝังตัวเลขไว้

เหตุผลเชิงการเรียนรู้: ให้เห็นเส้นทางของข้อมูลจากฟอร์ม → HTTP Request →
Python → HTML Response และให้ตรวจสอบผลลัพธ์ทางวิศวกรรมได้ด้วยการคำนวณอิสระ

---

## 2. Goals

| ID | เป้าหมาย | ตรวจได้อย่างไร |
|----|----------|----------------|
| G1 | เปิด `http://127.0.0.1:5000/` เห็นฟอร์มกรอกค่า | เปิด browser ได้ HTTP 200 |
| G2 | รับ `VCC, R1, R2, RC, RE, β, VBE` | กรอกครบแล้ว submit ผ่าน |
| G3 | Python Backend คำนวณ `VB, VE, VC, VCE, IC` (และ `IB, IE`) | ตัวเลขเปลี่ยนตามอินพุต ไม่ใช่ค่าคงที่ |
| G4 | แสดงผลพร้อมหน่วย (V, mA, µA, Ω, kΩ) | เห็นหน่วยทุกค่า |
| G5 | แสดงตารางขั้นตอนคำนวณ `VTH, RTH, IB, IE` | เห็นค่ากลางพร้อมสูตร |
| G6 | Validation: ค่าผิด/ไม่ครบ/ไม่ใช่ตัวเลข → ข้อความอ่านรู้เรื่อง หน้าไม่ล้ม | กรอก 0 หรือ `abc` แล้วเห็น error |
| G7 | แจ้ง Operating Region: Active / Cutoff / Saturation | ค่าที่ทำให้อิ่มตัวแล้วเห็น warning |
| G8 | Automated tests: ≥3 ข้อตรวจสมการ + ≥1 ข้อผ่าน Flask test client | `python -m unittest discover -s tests -v` ผ่านทั้งหมด |
| G9 | README ทำให้ clone แล้วรันได้ | ทำตาม README บนเครื่องสะอาดได้ |
| G10 | Commit/Push ผ่าน GitHub Desktop | เห็น commit ใน GitHub |

---

## 3. Non-goals (ไม่ทำใน Lab นี้)

- AC small-signal, Gain, Bode plot
- Transient / Signal generator / Overlay animation
- Bias type อื่น (Fixed, Emitter, Collector feedback)
- SPICE / ngspice integration
- FET
- JavaScript ฝั่ง client (ไม่ใช้ `fetch`, ไม่มี framework)
- ฐานข้อมูล, ระบบ login, การ deploy ขึ้น cloud

---

## 4. Anti-goals (ทำงานได้แต่ถือว่าล้มเหลว)

- ตัวเลขผลลัพธ์ถูกเขียนตายไว้ใน HTML หรือในเทมเพลต
- สมการไปอยู่ใน `templates/index.html` แทนที่จะอยู่ใน `dc_bias.py`
- มีการคำนวณซ้ำสองที่ (ทั้งใน Python และในเทมเพลต) แล้วไม่ตรงกัน
- Test ที่ assert ผ่านตลอดโดยไม่ตรวจค่าจริง (เช่น `assertTrue(True)`)
- เปิดไฟล์ `index.html` ตรง ๆ ด้วย `file://` แล้วอ้างว่ารันได้
- Commit ไฟล์ `.venv/` หรือไฟล์ที่มี credential

---

## 5. Constraints

- **Python:** 3.15.2 (เครื่องผู้พัฒนา), **Flask:** 3.1.3
- **Test framework:** `unittest` จาก stdlib เท่านั้น (ไม่เพิ่ม pytest)
- **Dependency:** มีเพียง Flask ใน `requirements.txt`
- **Template:** เทมเพลตเดียว (`templates/index.html`) ตามแนวทางที่เลือก
- **ไม่มี JavaScript** ทั้งหมดเรนเดอร์ฝั่ง server
- **ภาษา UI:** ไทยเป็นหลัก ศัพท์เทคนิคคงเป็นอังกฤษ (VCC, VBE, Active Region)
- **หน่วยตัวต้านทาน:** รับเป็น **kΩ** ตามเอกสาร Lab แล้วแปลงเป็น Ω ภายใน
- **รันที่:** `127.0.0.1:5000` เท่านั้น ไม่ expose สู่เครือข่าย

---

## 6. Approaches ที่พิจารณา

### 6.1 Flask + Jinja Server-Rendered — **เลือกใช้**

```
GET  /   → render index.html (results = None)
POST /   → parse → validate → calculate → render index.html (results + steps)
```

- ข้อดี: ตรงกับถ้อยคำโจทย์ "Server เรียก Python คำนวณและแสดงผลใน HTML",
  ไม่มี JS ให้พัง, ทดสอบด้วย Flask test client ได้ตรง ๆ, โค้ดน้อยที่สุด
- ข้อเสีย: กด refresh หลัง POST จะถูกถาม resubmit

### 6.2 Flask JSON API + `fetch()` — ไม่เลือก

ต้องเขียน `app.js` เพิ่ม, ทดสอบ DOM ไม่ได้ด้วย test client, เสี่ยงกว่าเมื่อเวลาเหลือน้อย
และไม่ได้คะแนนเพิ่มจาก rubric

### 6.3 แยกสองเทมเพลต (`index.html` + `result.html`) — ไม่เลือก

ต้องดูแล markup ฟอร์มซ้ำสองที่ เพื่อให้คำนวณซ้ำได้จากหน้าผลลัพธ์

---

## 7. โครงสร้างไฟล์

```
BJT DC Bias Web App/
├── app.py                  # Flask routes + form parsing + error mapping
├── dc_bias.py              # สมการล้วน ไม่ import flask
├── templates/
│   └── index.html          # ฟอร์ม + results + steps table + warnings
├── static/
│   └── style.css
├── tests/
│   ├── test_dc_bias.py     # unit tests ทางวิศวกรรม
│   └── test_web.py         # Flask test client
├── requirements.txt
├── README.md
├── .gitignore
├── AGENTS.md
└── docs/
    ├── design-note.md
    ├── validation.md
    ├── reflection.md
    └── superpowers/specs/2026-11-10-bjt-dc-bias-design.md
```

`tests/` ต้อง import `dc_bias` ได้ จึงรันคำสั่งจาก root ของโปรเจกต์เสมอ
(`python -m unittest discover -s tests -v`) — root จะถูกเพิ่มเข้า `sys.path` ให้เอง

---

## 8. Data Model (`dc_bias.py`)

```python
@dataclass(frozen=True)
class BiasInput:
    vcc: float      # V
    r1: float       # Ω
    r2: float       # Ω
    rc: float       # Ω
    re: float       # Ω
    beta: float     # -
    vbe: float      # V

@dataclass(frozen=True)
class BiasResult:
    vth: float      # V
    rth: float      # Ω
    ib: float       # A
    ic: float       # A
    ie: float       # A
    vb: float       # V
    ve: float       # V
    vc: float       # V
    vce: float      # V
    region: str     # "active" | "cutoff" | "saturation"
    warnings: list[str]
```

ฟังก์ชันสาธารณะ:

| ฟังก์ชัน | หน้าที่ |
|---|---|
| `calculate(p: BiasInput) -> BiasResult` | คำนวณทั้งหมด + ตัดสิน region |
| `validate(form: dict[str, str]) -> tuple[BiasInput \| None, dict[str, str]]` | แปลงหน่วย kΩ→Ω, ตรวจความถูกต้อง, คืน error รายฟิลด์ |

`dc_bias.py` **ห้าม** import `flask` และห้ามรู้จัก HTML

---

## 9. สมการ (Forward-Active Approximation, β และ VBE คงที่)

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) · RE)
IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

---

## 10. Operating Region และ Warning

| เงื่อนไข | region | สิ่งที่แสดง |
|---|---|---|
| `VTH <= VBE` | `cutoff` | IC=IE=0, VE=0, VB=VTH, VC=VCC, VCE=VCC + warning ว่าแบบจำลอง Forward-Active ใช้ไม่ได้ |
| `VCE <= 0.3 V` | `saturation` | แสดงค่าที่คำนวณได้ + warning ว่าอยู่ใกล้/เข้า Saturation ค่าไม่น่าเชื่อถือ |
| อื่น ๆ | `active` | แสดงผลปกติ ไม่มี warning |

`0.3 V` เป็นเกณฑ์เตือน (ไม่ใช่การ solve Saturation Region จริง) — ระบุในหมายเหตุของหน้าเว็บ

---

## 11. Validation Rules

| ฟิลด์ | กติกา | ข้อความเมื่อผิด |
|---|---|---|
| ทุกฟิลด์ | ต้องมีค่า (ไม่ว่าง) | "กรุณากรอกค่านี้" |
| ทุกฟิลด์ | ต้องเป็นตัวเลข (รับทศนิยมได้) | "ต้องเป็นตัวเลข" |
| VCC | `> 0` | "VCC ต้องมากกว่า 0" |
| R1, R2, RC, RE | `> 0` (หน่วย kΩ) | "ความต้านทานต้องมากกว่า 0" |
| β | `> 0` | "β ต้องมากกว่า 0" |
| VBE | `0 <= VBE < VCC` | "VBE ต้องอยู่ระหว่าง 0 ถึง VCC" |

เมื่อมี error: แสดงข้อความใต้ฟิลด์ที่ผิด, คงค่าที่ผู้ใช้กรอกไว้, **ไม่คำนวณ**

---

## 12. หน้าจอ (เทมเพลตเดียว)

```
┌──────────────────────────────────────────────┐
│ BJT DC Bias Calculator                       │
│ Common-Emitter · Voltage Divider             │
├──────────────────────────────────────────────┤
│ VCC [12.0] V      β   [100]                  │
│ R1  [100] kΩ      VBE [0.70] V               │
│ R2  [22]  kΩ                                 │
│ RC  [2.2] kΩ                                 │
│ RE  [1]   kΩ                                 │
│            [ Calculate DC Bias ]             │
├──────────────────────────────────────────────┤
│ ● Active Region                              │
│ ┌──────┬──────┬──────┬──────┬──────┐         │
│ │ VB   │ VE   │ VC   │ VCE  │ IC   │         │
│ │1.942V│1.242V│9.294V│8.052V│1.230mA│        │
│ └──────┴──────┴──────┴──────┴──────┘         │
│ ▸ ขั้นตอนการคำนวณ                            │
│   VTH = 2.164 V    RTH = 18.033 kΩ           │
│   IB  = 12.30 µA   IE  = 1.242 mA            │
├──────────────────────────────────────────────┤
│ ⚠ warning (ถ้ามี)                            │
└──────────────────────────────────────────────┘
```

- ค่า default เติมไว้ในฟอร์ม: `12, 100, 22, 2.2, 1, 100, 0.70` (เป็นค่าเริ่มต้นของอินพุต ไม่ใช่ผลลัพธ์)
- ตัวเลขแสดงทศนิยม 3 ตำแหน่งทุกค่า
- **สัญญาการแปลงหน่วย (เป็นการตัดสินใจของผู้สร้าง):**
  | ปริมาณ | กติกา | ตัวอย่าง |
  |---|---|---|
  | แรงดัน | V เสมอ, 3 ตำแหน่ง | `1.942 V` |
  | กระแส | `>= 1 mA` → mA, ต่ำกว่า → µA (ใช้กับ IB, IC, IE ทุกตัว) | `1.230 mA`, `12.300 µA` |
  | ความต้านทาน | `>= 1000 Ω` → kΩ, ต่ำกว่า → Ω | `18.033 kΩ`, `820.000 Ω` |
- `results` เป็น `None` เมื่อยังไม่ submit → ไม่แสดงบล็อกผลลัพธ์
- ใช้ semantic HTML + `<label for>` ทุกช่อง, `<table>` สำหรับ steps

---

## 13. Tests

### `tests/test_dc_bias.py` (อย่างน้อย 5 ข้อ)

1. **Reference case** — `12 V, 100k, 22k, 2.2k, 1k, β=100, VBE=0.7`
   → `VTH≈2.163934`, `RTH≈18032.787 Ω`, `IB≈12.2986 µA`, `IC≈1.22986 mA`,
   `IE≈1.24216 mA`, `VE≈1.24216`, `VB≈1.94216`, `VC≈9.29431`, `VCE≈8.05216`,
   region `active`, `warnings == []` (tolerance: V ±1e-6, A ±1e-9, Ω ±1e-3)
2. **Cutoff** — `R1=100k, R2=5k` → `VTH=0.571 V < VBE` → region `cutoff`, `IC==0`
3. **Saturation** — reference แต่ `RC=8.7k` → `VCE≈0.058 V` → region `saturation`, มี warning
4. **Validation: ค่าเป็นศูนย์/ลบ** — `β=0`, `R1=-1` → คืน error, ไม่คำนวณ
5. **Validation: ไม่ใช่ตัวเลข/ว่าง** — `"abc"`, `""` → คืน error รายฟิลด์
6. **Unit conversion** — กรอก `R1=100` (kΩ) ต้องได้ผลเดียวกับ `100_000` Ω

### `tests/test_web.py` (อย่างน้อย 3 ข้อ)

1. `GET /` → 200 และมี `<form`
2. `POST /` ด้วยค่าถูกต้อง → 200 และมีสตริง `1.942` (VB) อยู่ใน response
3. `POST /` ด้วย `β=0` → 200, มีข้อความ error, ไม่มี `Traceback`
4. `POST /` ที่ทำให้เกิด saturation → มีข้อความ warning

---

## 14. วิธีรัน (จะเขียนลง README)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
# เปิด http://127.0.0.1:5000/
python -m unittest discover -s tests -v
```

---

## 15. Git / GitHub Desktop

- `.gitignore`: `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`
- Commit ผ่าน **GitHub Desktop** เท่านั้น (ผู้ใช้กดเอง) — agent ไม่รัน `git commit`
- ครั้งแรกต้อง **Publish repository** จาก GitHub Desktop เพราะยังไม่มี remote
- ข้อความ commit แนะนำ: `Add Flask DC bias calculator with tests`

---

## 16. เอกสารประกอบ (ตกลงกับเจ้าของงานแล้ว)

| ไฟล์ | ใครเขียน | ต้องมีอะไร |
|---|---|---|
| `AGENTS.md` | AI ร่าง | กติกาโปรเจกต์: สมการต้องอยู่ใน `dc_bias.py` เท่านั้น, ห้ามใส่ตัวเลขผลลัพธ์ในเทมเพลต, รัน test ก่อน commit, ภาษา UI, กติกาหน่วย |
| `docs/design-note.md` | AI ร่าง | เหตุผลที่เลือก server-rendered, โครงสร้างไฟล์, data flow, ขอบเขตที่ตัดออก และเหตุผล |
| `docs/validation.md` | AI ร่าง | **ตารางคำนวณมือ** แทนค่าทีละขั้นของ reference case เทียบค่าที่โปรแกรมให้ + ผลรัน `unittest` + ผลทดสอบ invalid input และ region warning |
| `docs/reflection.md` | AI ร่างเป็น baseline | สิ่งที่เรียนรู้, ปัญหาที่เจอ, จะทำอะไรต่างถ้ามีเวลา, ตอบคำถามรายบุคคล 4 ข้อท้ายเอกสาร Lab (เจ้าของงานแก้ให้เป็นเสียงของตัวเองก่อนส่ง) |

**ค่าอ้างอิงสำหรับ `validation.md` (คำนวณมือ):**

| ขั้น | สมการ | แทนค่า | ผล |
|---|---|---|---|
| VTH | VCC·R2/(R1+R2) | 12·22000/(100000+22000) | 2.1639 V |
| RTH | R1·R2/(R1+R2) | 100000·22000/122000 | 18032.79 Ω |
| IB | (VTH−VBE)/(RTH+(β+1)RE) | (2.1639−0.7)/(18032.79+101·1000) | 12.299 µA |
| IC | β·IB | 100·12.299µ | 1.2299 mA |
| IE | (β+1)·IB | 101·12.299µ | 1.2422 mA |
| VE | IE·RE | 1.2422m·1000 | 1.2422 V |
| VB | VE+VBE | 1.2422+0.7 | 1.9422 V |
| VC | VCC−IC·RC | 12−1.2299m·2200 | 9.2942 V |
| VCE | VC−VE | 9.2942−1.2422 | 8.0521 V |

---

## 17. สิ่งที่เหลือให้ผู้สร้างตัดสินใจเอง

- ถ้อยคำภาษาไทยของ label/ข้อความ error (ให้อ่านง่ายและสั้น)
- โทนสีและรายละเอียด CSS
- รูปแบบการจัดวางตาราง steps (กี่คอลัมน์)
- จะเพิ่ม docstring/comment มากน้อยเพียงใด
