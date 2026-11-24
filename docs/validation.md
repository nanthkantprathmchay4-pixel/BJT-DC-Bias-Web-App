# Validation Log — BJT DC Bias Web App

## 1. การคำนวณมือเทียบค่าจากโปรแกรม

ค่าอินพุต: `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`,
`RE = 1 kΩ`, `β = 100`, `VBE = 0.70 V`

| ปริมาณ | สมการ | แทนค่า | คำนวณมือ | โปรแกรมแสดง |
|---|---|---|---|---|
| VTH | VCC·R2/(R1+R2) | 12·22000/122000 | 2.163934 V | 2.164 V |
| RTH | R1·R2/(R1+R2) | 100000·22000/122000 | 18032.787 Ω | 18.033 kΩ |
| IB | (VTH−VBE)/(RTH+(β+1)RE) | (2.163934−0.7)/(18032.787+101000) | 12.2986 µA | 12.299 µA |
| IC | β·IB | 100·12.2986 µA | 1.22986 mA | 1.230 mA |
| IE | (β+1)·IB | 101·12.2986 µA | 1.24216 mA | 1.242 mA |
| VE | IE·RE | 1.24216 mA·1000 Ω | 1.24216 V | 1.242 V |
| VB | VE+VBE | 1.24216+0.70 | 1.94216 V | 1.942 V |
| VC | VCC−IC·RC | 12−1.22986 mA·2200 Ω | 9.29431 V | 9.294 V |
| VCE | VC−VE | 9.29431−1.24216 | 8.05216 V | 8.052 V |

ผลต่างทั้งหมดอยู่ในระดับการปัดเศษทศนิยม 3 ตำแหน่งที่หน้าเว็บแสดง
Operating Region: **Active Region** (ไม่มี warning)

## 2. ผลการทดสอบอัตโนมัติ

```
$ .venv\Scripts\python.exe -m unittest discover -s tests -v
...
Ran 65 tests in 0.053s

OK
```

| ไฟล์ | จำนวน test | สิ่งที่ตรวจ |
|---|---|---|
| `tests/test_dc_bias.py` | 7 | ค่าอ้างอิง Divider, Cutoff, Saturation (เกณฑ์ 0.2 V), ช่วง 0.2–0.3 V ยังเป็น Active |
| `tests/test_fixed.py` | 3 | ค่า A2 (IB/IC/VB/VE/VC/VCE), Region |
| `tests/test_emitter.py` | 5 | ค่า A3/A4, ความสัมพันธ์ `RE`↑ → `IC`↓/`VCE`↓, Region |
| `tests/test_validation.py` | 24 | ฟิลด์ว่าง, ไม่ใช่ตัวเลข, `nan`/`inf`/ค่าล้น, ค่าติดลบ/ศูนย์, VBE เกินช่วง, β ทศนิยม, การแปลง kΩ, validation ตามโหมด, โหมดไม่รู้จัก, `parse_mode` |
| `tests/test_formatting.py` | 6 | การเลือกหน่วย mA/µA และ Ω/kΩ, ขอบเขต 1 mA |
| `tests/test_web.py` | 20 | GET/POST ตามโหมด, error, warning, ไม่มีผลรอบก่อนค้าง, หมายเหตุเกณฑ์ 0.2 V |

## 3. การทดสอบข้อมูลเข้าไม่ถูกต้อง

| สถานการณ์ | ผลที่ได้ |
|---|---|
| `β = 0` | แสดง `β ต้องมากกว่า 0` ใต้ช่อง β และไม่คำนวณ |
| ส่งฟอร์มว่าง | แสดง `กรุณากรอกค่านี้` ครบทั้ง 7 ช่อง |
| `R1 = 1,000` | แสดง `ต้องเป็นตัวเลข` (ไม่รับตัวคั่นหลักพัน) |
| `VBE = 12` เมื่อ `VCC = 12` | แสดง `VBE ต้องอยู่ระหว่าง 0 ถึง VCC` |
| `VCC = 1000000000` | ยังตอบ HTTP 200 ไม่มี traceback |
| `VCC = nan`, `VCC = inf` | แสดง `ต้องเป็นตัวเลข` ไม่แสดง `nan V` / `inf V` |
| `β = 1e400` | แสดง `ต้องเป็นตัวเลข` (ค่าล้นช่วง floating point) |
| `RC = 1e308` kΩ | แสดง `ค่ามากเกินไป` (แปลงเป็น Ω แล้วล้น) |

## 4. การทดสอบ Operating Region

| อินพุต | Region ที่แสดง | Warning |
|---|---|---|
| ค่าอ้างอิง | Active Region | ไม่มี |
| `RC = 8.7 kΩ` | Saturation | `VCE ต่ำกว่า 0.2 V — ใกล้หรือเข้าสู่ Saturation ค่าที่ได้ไม่น่าเชื่อถือ` |
| `R2 = 5 kΩ` | Cutoff | `วงจรอยู่ในช่วง Cutoff — แบบจำลอง Forward-Active ใช้ไม่ได้` |

## 5. ข้อจำกัดที่ยังเหลือ

- แบบจำลองนี้ไม่ใช่ SPICE และไม่ได้แก้สมการ Saturation Region
- เกณฑ์ Saturation ใช้ `VCE ≤ 0.2 V` ตาม Lab 03 (Lab 02 เดิมใช้ `0.3 V`) เป็นเพียงการเตือน — ไม่ได้แก้สมการใหม่
- ไม่ตรวจว่าค่าที่กรอกเป็นค่าที่มีขายจริงในท้องตลาด

---

# Lab 03

## 6. Baseline ก่อนแก้โค้ด (A1 · Voltage Divider)

บันทึกเมื่อ 2026-11-17 · commit `39ebe16` · working tree สะอาด (ยังไม่มี Lab 03)

**วิธีรัน**

```powershell
.venv\Scripts\python.exe -m flask --app app run --port 5000
```

เปิด `http://127.0.0.1:5000/` ด้วย OpenCode Browser (`browser_navigate` → `browser_snapshot`
→ `browser_click` ปุ่ม Calculate DC Bias → `browser_snapshot` อีกครั้ง)

**อินพุต** (ค่าตั้งต้นของฟอร์มตรงกับ A1 พอดี ไม่ต้องแก้ช่องใด)

| ช่อง | ค่า | หน่วยบนฟอร์ม |
|---|---|---|
| VCC | 12 | V |
| β | 100 | — |
| R1 | 100 | kΩ |
| R2 | 22 | kΩ |
| RC | 2.2 | kΩ |
| RE | 1 | kΩ |
| VBE | 0.7 | V |

**ผลที่เห็นจริงบนหน้าเว็บ** (อ่านจาก snapshot ไม่ได้อ่านจากโค้ด)

| ปริมาณ | ค่าที่แสดง | หน่วย |
|---|---|---|
| VB | 1.942 | V |
| VE | 1.242 | V |
| VC | 9.294 | V |
| VCE | 8.052 | V |
| IC | 1.230 | mA |
| VTH | 2.164 | V |
| RTH | 18.033 | kΩ |
| IB | 12.299 | µA |
| IE | 1.242 | mA |
| Operating Region | Active Region | — |
| Warning | ไม่มี | — |

**สรุป** ผลตรงกับค่าอ้างอิงอิสระในข้อ 1 ทุกตำแหน่ง (ผลต่าง ≤ 0.001)
จึงใช้เป็น baseline ของ A1 ได้ — หลังเพิ่ม Fixed/Emitter แล้ว A1 ต้องยังได้ค่าเหล่านี้เมื่อกรอกค่าเดิม

**หลักฐาน** ข้อความที่อ่านได้จากหน้าเว็บหลังส่งฟอร์ม:
`Active Region · VB 1.942 V · VE 1.242 V · VC 9.294 V · VCE 8.052 V · IC 1.230 mA`
ภาพหน้าจอ: `docs/evidence/a1-divider.png` (เก็บด้วย Playwright MCP ตอนตรวจ A1 รอบ Lab 03 — ยืนยันค่าตรง baseline ทุกตำแหน่ง)

## 7. สถานะเครื่องมือสำหรับ Lab 03

| ชั้น | สถานะ | หมายเหตุ |
|---|---|---|
| Flask server | OK | Flask 3.1.3 บน `.venv` (Python 3.15.2) — ตัวเก่าที่แย่ง port 5000 ถูกปิดแล้ว |
| เปิดเว็บ + อ่านฟอร์มได้ | OK | OpenCode Browser + Playwright MCP |
| Node.js / `npx` | OK | ติดตั้ง LTS แล้ว: `node v24.20.0`, `npm 11.19.0` |
| Playwright MCP | OK | `✓ playwright connected` (`opencode-cli.exe mcp list`) — ใช้จริงตรวจ A1–A5 |
| Google Chrome | พบ + ใช้จริง | `C:\Program Files\Google\Chrome\Application\chrome.exe` (MCP ใช้ `--browser chrome --isolated`) |
| Microsoft Edge | พบ | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |

ตามใบงานข้อ MCP: ใช้ **Playwright MCP จริง** ตรวจ A1–A5 (ไม่ใช้ `NOT RUN`)
หลังแก้ `opencode.json` ต้อง restart service ก่อนจึงโหลด MCP:
`& "$env:APPDATA\ai.opencode.desktop\cli\2.2.6-x64\opencode-cli.exe" service restart`

**ตรวจว่าเอเจนต์ใช้ MCP ได้จริง (ใบงานข้อ MCP):** เปิดเว็บด้วย
`tools.playwright.browser_navigate` แล้วอ่าน `tools.playwright.browser_snapshot`
ได้ Page Title `BJT DC Bias Calculator` และช่องจริงอย่างน้อย 2 ช่อง:
`VCC (V)`, `RB (kΩ)`, `RC (kΩ)` (โหมด fixed) — ไม่ใช่ค่าที่เดาจากโค้ด

## 8. ตารางตรวจ A1–A5

ค่าที่ใช้ร่วมทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
เกณฑ์ผ่าน: `IC` คลาดเคลื่อน ≤ 0.01 mA (หรือ ≤ 10 µA) และ `VCE` ≤ 0.02 V
ตัวต้านทานบนฟอร์มเป็น **kΩ** — `RB = 1 MΩ` กรอก `1000`

| ID | เลือกโหมด + อินพุต | คาดหมาย | เห็นจริง | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| A1 | `divider` · R1=100, R2=22, RC=2.2, RE=1 | VB 1.942 V · VE 1.242 V · VC 9.294 V · VCE 8.052 V · IC 1.230 mA (ตรง baseline §6) | Active · VB 1.942 V · VE 1.242 V · VC 9.294 V · VCE 8.052 V · IC 1.230 mA · VTH 2.164 V · RTH 18.033 kΩ · IB 12.299 µA · IE 1.242 mA — ตรง §6 ทุกตำแหน่ง | Playwright MCP · `browser_snapshot` · `docs/evidence/a1-divider.png` | PASS |
| A2 | `fixed` · RB=1000, RC=2.2 | IB 11.300 µA · IC 1.130 mA · VB 0.700 V · VE 0.000 V · VC=VCE 9.514 V | Active · IB 11.300 µA · IC 1.130 mA · IE 1.141 mA · VB 0.700 V · VE 0.000 V · VC 9.514 V · VCE 9.514 V | Playwright MCP · `browser_snapshot` · `docs/evidence/a2-fixed.png` | PASS |
| A3 | `emitter` · RB=1000, RC=2.2, RE=1 | IB 10.263 µA · IC 1.026 mA · VE 1.037 V · VB 1.737 V · VC 9.742 V · VCE 8.705 V | Active · IB 10.263 µA · IC 1.026 mA · IE 1.037 mA · VB 1.737 V · VE 1.037 V · VC 9.742 V · VCE 8.705 V | Playwright MCP · `browser_snapshot` | PASS |
| A4 | `emitter` · RB=1000, RC=2.2, **RE=2** | IB 9.401 µA · IC **940.100 µA** (↓) · VE 1.899 V · VC 9.932 V · VCE **8.033 V** (↓) | Active · IB 9.401 µA · IC 940.100 µA · IE 949.501 µA · VB 2.599 V · VE 1.899 V · VC 9.932 V · VCE 8.033 V | Playwright MCP · `browser_type` เปลี่ยน RE → `browser_snapshot` | PASS |
| A5 | `fixed` · **RB=0** | ข้อความ `ความต้านทานต้องมากกว่า 0` ที่ช่อง RB, ไม่มีบล็อกผลลัพธ์, ไม่มีค่าของรอบก่อนค้าง | error `ความต้านทานต้องมากกว่า 0` อยู่ใต้ช่อง RB · ไม่มี `ขั้นตอนการคำนวณ` · ไม่มีผล/ค่าค้างจากรอบก่อน | Playwright MCP · `browser_type` · `browser_snapshot` · `docs/evidence/a5-invalid-rb.png` | PASS |

**หมายเหตุ A4 — ทำนายผิดตอนร่างแผน.** ร่างแรกคาดว่า `RE` เพิ่มแล้ว `VCE` จะเพิ่ม
แต่ค่าจริงลดลง (`8.705 → 8.033 V`) เพราะ `VE = IE · RE` เพิ่มขึ้น +0.86 V
ขณะที่ `IC · RC` ลดลงเพียง −0.19 V ถ้า `RE` ใหญ่ขึ้นอีกจน `IC → 0` ค่า `VCE`
จะกลับไปใกล้ `VCC` — ความสัมพันธ์นี้ไม่เป็นเส้นตรง

**หมายเหตุหน่วย.** A4 มี `IC = 0.9401 mA` ซึ่งต่ำกว่า 1 mA ตามกติกาของโปรเจกต์
จึงต้องแสดงเป็น `940.100 µA` ไม่ใช่ `0.940 mA`

**หลักฐานภาพหน้าจอ** `docs/evidence/a1-divider.png`, `docs/evidence/a2-fixed.png`,
`docs/evidence/a5-invalid-rb.png` (เก็บด้วย `browser_take_screenshot` ของ Playwright MCP)

**วิธีรันที่ใช้ทุกรอบ**

```powershell
.venv\Scripts\python.exe -m flask --app app run --port 5000
```

แล้วใช้ Playwright MCP: `browser_navigate` → `http://127.0.0.1:5000/?mode=<โหมด>`
→ `browser_type` (ถ้าปรับค่า) → `browser_click` ปุ่ม Calculate DC Bias → `browser_snapshot`
อ่านค่าจาก snapshot ทุกครั้งหลังเปลี่ยนโหมดหรือส่งฟอร์ม (ห้ามใช้ค่าของรอบก่อนหน้า)

---

# Lab 04

## 9. สภาพแวดล้อมและการรันจริง

- วันที่ตรวจ: 2026-11-24
- Branch: `lab4-ce-amplifier-simulator`
- Python venv: `.venv\Scripts\python.exe`
- Flask: `python -m flask --app app run --debug` (ตรวจ B1–B8 ที่ `http://127.0.0.1:5174`)
- ngspice: **ngspice-47** (`ngspice_con.exe`, Compiled with KLU Direct Linear Solver)
- ngspice path ที่ใช้จริง: `%LOCALAPPDATA%\Programs\ngspice-47\Spice64\bin\ngspice_con.exe`
- Model: `Q2N3904 NPN` (พารามิเตอร์ตาม `spice_engine.py` / README)

## 10. ผลทดสอบอัตโนมัติ (หลังเพิ่ม Lab 4)

```
$ .venv\Scripts\python.exe -m unittest discover -s tests -v
...
Ran 85 tests in 0.239s

OK
```

เพิ่มชุดทดสอบ Lab 4: `tests/test_spice_engine.py`, `tests/test_plot_svg.py`, `tests/test_web_simulator.py` และยังคงผ่าน regression ชุด Lab 3 เดิมครบ

## 11. ตารางตรวจ B1–B8 (Browser จริงผ่าน Playwright)

หมายเหตุ: ค่า SPICE มาจาก ngspice .op/.ac/.tran จริงของวงจร CE Voltage Divider reference; ค่า Analytical reference ใน `.op` คำนวณจากสูตร divider เดียวกันเพื่อเปรียบเทียบ (คนละ provenance)

| ID | กรณี | คาดหมาย/เกณฑ์ | เห็นจริง (จาก browser) | วิธีตรวจ | สถานะ | หลักฐาน |
|---|---|---|---|---|---|---|
| B1 | Regression A1-equivalent (Lab 3 divider) | ค่า A1 เดิม: Active, VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA | Active Region, VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA | Playwright เปิด `/?mode=divider`, กรอกค่า A1, กด Calculate | PASS | `docs/evidence/lab4/b1-divider.png` |
| B2 | DC SPICE `.op` (default) | status OK, แสดงค่า SPICE และ Analytical reference แยกคอลัมน์ | status OK. SPICE: VB 2.004 V, VE 1.333 V, VC 9.087 V, VCE 7.754 V, IC 1.324 mA. Reference: VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA, Active Region | Playwright เปิด `/simulator`, analysis=op, Run Simulation | PASS | `docs/evidence/lab4/b2-op.png` |
| B3 | เปลี่ยน RE 1kΩ → 2kΩ (`.op`) | ค่าต้องเปลี่ยนจาก B2; IC ควรลดลงเมื่อ RE เพิ่ม (ในย่านนี้) | status OK. SPICE: VB 2.073 V, VE 1.419 V, VC 10.450 V, VCE 9.032 V, IC 704.369 µA. Reference: VB 2.044 V, VE 1.344 V, VC 10.536 V, VCE 9.192 V, IC 665.326 µA. IC ลดลงจาก B2 | Playwright เปลี่ยน RE=2, Run Simulation | PASS | `docs/evidence/lab4/b3-re-change.png` |
| B4 | AC `.ac` (default) | status OK, มีกราฟ Bode SVG | status OK, hasSvg=1 (กราฟ Bode magnitude/phase แสดงบนหน้า) | Playwright เลือก AC, Run Simulation | PASS | `docs/evidence/lab4/b4-ac.png` |
| B5 | Transient `.tran` 10mV peak, 1kHz | status OK, มีกราฟ transient SVG | status OK, hasSvg=1, Vin=10 mV peak, Freq=1000 Hz | Playwright เลือก Tran, vin_mvp=10, freq_hz=1000, Run Simulation | PASS | `docs/evidence/lab4/b5-tran.png` |
| B6 | Source change (Tran 20mV peak, 2kHz) | ผลกราฟ/การรันต้องเปลี่ยนตาม input ใหม่; status OK | status OK, hasSvg=1, vin=20, freq=2000 (ค่าฟอร์มเปลี่ยนและรันใหม่สำเร็จ) | Playwright เปลี่ยน vin_mvp=20, freq_hz=2000, Run Simulation | PASS | `docs/evidence/lab4/b6-source-change.png` |
| B7 | Invalid/fail | input ไม่ถูกต้องต้องแสดง error ชัดเจน และไม่มีสถานะสำเร็จค้าง | RE=0 แสดงข้อความ `ความต้านทานต้องมากกว่า 0`, status ERROR, `status-ok` count = 0 | Playwright ตั้ง RE=0, Run Simulation | PASS | `docs/evidence/lab4/b7-invalid.png` |
| B8 | Desktop + 390px UI | ที่ 390px หน้า simulator ใช้งานได้, ไม่มี horizontal scroll หลัก | viewport 390x844, hasHScroll=false, รัน op สำเร็จและแสดงตารางผลลัพธ์ | Playwright resize 390x844, เปิด `/simulator`, Run Simulation | PASS | `docs/evidence/lab4/b8-mobile.png` |

## 12. หมายเหตุ Lab 4

- ค่า SPICE และ Analytical reference ใน B2/B3 ใกล้เคียงแต่ไม่เท่ากัน เพราะ SPICE ใช้โมเดล 2N3904 แบบไม่เชิงเส้น ส่วน reference ใช้สมการ divider ideal (β, VBE คงที่) — UI แสดง provenance แยกคอลัมน์
- กรณี error/invalid ต้องไม่แสดงกราฟหรือสถานะสำเร็จค้าง (ยืนยันโดย B7 และ unit tests `test_web_simulator.py`, `test_spice_engine.py`)
- Lab 4 ไม่ได้เพิ่ม CE bypass capacitor และไม่ขยาย topology นอกเหนือ CE Voltage Divider reference

