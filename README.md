# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
NPN แบบ Common-Emitter รองรับสามวงจรไบอัส และมี **Lab 4 CE Amplifier Simulator**
(ngspice `.op/.ac/.tran`) สำหรับวงจร CE Voltage Divider อ้างอิง

| โหมด/หน้า | วงจร | ช่องที่ใช้ในฟอร์ม |
|---|---|---|
| `divider` | Voltage Divider Bias | `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` |
| `fixed` | Fixed Bias (RB จาก VCC ไปเบส, อิมิตเตอร์ลงกราวด์) | `VCC`, `RB`, `RC`, `β`, `VBE` |
| `emitter` | Emitter Bias (RB จาก VCC ไปเบส + RE ที่อิมิตเตอร์) | `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` |
| `/simulator` | CE Voltage Divider Amplifier (SPICE) | `VCC`, `R1`, `R2`, `RC`, `RE`, `RL`, `Cin`, `Cout`, `β`, `VBE`, `Vin`, `Freq`, `Analysis` |

พัฒนาเป็นส่วนหนึ่งของรายวิชา ENG29 2121 (Lab 02 วงจร Voltage Divider,
Lab 03 เพิ่ม Fixed Bias และ Emitter Bias พร้อมตรวจผลผ่านเบราว์เซอร์,
Lab 04 เพิ่ม CE Amplifier Simulator ด้วย ngspice จริง)

## ค่าที่รับและแสดงผล

| ข้อมูลเข้า | ข้อมูลออก |
|---|---|
| `VCC` (V), `RB`/`R1`/`R2`/`RC`/`RE` (**kΩ**), `β`, `VBE` (V) | `VB`, `VE`, `VC`, `VCE` (V) และ `IC` (mA/µA) |
| | ค่าขั้นตอน `VTH`, `RTH` (Divider), `IB`, `IE` และสถานะ Operating Region |

> ตัวต้านทานทุกช่องเป็น **kΩ** เช่น `RB = 1 MΩ` ให้กรอก `1000`

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/> แล้วเลือกโหมดจากแถบด้านบน
(ลิงก์ `/?mode=divider`, `/?mode=fixed`, `/?mode=emitter`) หรือเปิด
`/simulator` สำหรับ Lab 4 CE Amplifier Simulator

> ต้องรันผ่าน Flask Server เท่านั้น การเปิด `templates/index.html` ด้วย
> `file://` จะไม่ได้ผลลัพธ์ เพราะไม่มีการคำนวณฝั่ง Python

## Lab 4: ngspice setup

Lab 4 simulator ใช้ **ngspice จริง** ผ่าน `subprocess` (ไม่ใช่ mock). ติดตั้ง ngspice แล้วตั้งค่าให้ resolver หาได้อย่างใดอย่างหนึ่ง:

1. ตั้ง environment variable `NGSPICE_EXE` เป็น path เต็มของ executable (แนะนำ `ngspice_con.exe` บน Windows)
2. หรือใส่ `ngspice_con.exe` / `ngspice.exe` ใน `PATH`
3. หรือติดตั้ง portable ngspice ที่ path มาตรฐานที่ resolver ตรวจ เช่น `%LOCALAPPDATA%\Programs\ngspice-47\Spice64\bin\ngspice_con.exe`

ตัวอย่าง (PowerShell):

```powershell
$env:NGSPICE_EXE="C:\Users\<you>\AppData\Local\Programs\ngspice-47\Spice64\bin\ngspice_con.exe"
python -m flask --app app run --debug
```

เวอร์ชันที่ตรวจจริงในการพัฒนา/validation: **ngspice-47** (`ngspice_con.exe`, compiled with KLU Direct Linear Solver).

### โมเดล BJT ที่ใช้

Simulator ใช้โมเดล NPN ชื่อ `2N3904` (ค่าใน netlist ไม่ถูกซ่อน):

```spice
.model Q2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259 Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1 Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75 Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
```

### วิธีรันและตรวจ Lab 4

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m flask --app app run --debug
# เปิด http://127.0.0.1:5000/simulator
```

บนหน้า `/simulator` เลือก analysis (`DC .op`, `AC .ac`, `Transient .tran`) กรอกพารามิเตอร์ แล้วกด Run Simulation. ผล SPICE และกราฟ SVG สร้างจาก ngspice จริง; กรณี `.op` จะแสดงตารางเปรียบเทียบ SPICE กับ Analytical reference (สูตร divider) โดยระบุ provenance แยกกันชัดเจน.

## ตัวอย่างผลลัพธ์

ค่าที่ใช้ร่วม: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`

| กรณี | โหมด + อินพุต | `IC` | `VCE` |
|---|---|---|---|
| A2 | `fixed`, `RB = 1000` (1 MΩ) | 1.130 mA | 9.514 V |
| A3 | `emitter`, `RB = 1000`, `RE = 1` | 1.026 mA | 8.705 V |
| A4 | `emitter`, `RB = 1000`, `RE = 2` | 940.100 µA | 8.033 V |

## การรันทดสอบ

```powershell
python -m unittest discover -s tests -v
```

## โครงสร้างโปรเจกต์

```
app.py                    Flask routes, Lab 3 modes + Lab 4 /simulator
dc_bias.py                สมการ DC bias ต่อโหมด + validation (ไม่รู้จัก Flask)
formatting.py             จัดรูปแบบตัวเลขและหน่วย (V, mA, µA, Ω, kΩ)
spice_engine.py           ngspice adapter: netlist, subprocess, wrdata parse
plot_svg.py               สร้างกราฟ SVG ฝั่ง server (Bode/Transient)
templates/index.html      ฟอร์มและผลลัพธ์ Lab 3 (Jinja, ไม่มี JavaScript)
templates/simulator.html  ฟอร์มและผลลัพธ์ Lab 4 simulator
static/style.css          การจัดหน้าจอ
tests/test_dc_bias.py     ทดสอบสมการ Divider และ Operating Region
tests/test_fixed.py       ทดสอบสมการ Fixed Bias (A2)
tests/test_emitter.py     ทดสอบสมการ Emitter Bias (A3, A4)
tests/test_validation.py  ทดสอบการตรวจข้อมูลเข้าและการแปลงหน่วย
tests/test_formatting.py  ทดสอบรูปแบบตัวเลข
tests/test_web.py         ทดสอบ HTTP route Lab 3 ด้วย Flask test client
tests/test_web_simulator.py ทดสอบ HTTP route /simulator
tests/test_spice_engine.py  ทดสอบ netlist/parse/run/real ngspice smoke
tests/test_plot_svg.py    ทดสอบ SVG plot
opencode.json             ตั้งค่า Playwright MCP สำหรับตรวจผลผ่านเบราว์เซอร์
docs/                     design note, validation log, reflection, evidence
```

## แบบจำลองที่ใช้

Forward-Active Approximation โดยถือ `β` และ `VBE` คงที่ ใช้ร่วมทั้งสามโหมด

```
IC  = β · IB          IE = (β + 1) · IB
VE  = IE · RE         VB = VE + VBE
VC  = VCC − IC · RC   VCE = VC − VE
```

แต่ละโหมดต่างกันที่สมการ `IB`

```
Divider: VTH = VCC · R2 / (R1 + R2)     RTH = R1 · R2 / (R1 + R2)
         IB  = (VTH − VBE) / (RTH + (β + 1) · RE)

Fixed:   IB  = (VCC − VBE) / RB          และ VE = 0

Emitter: IB  = (VCC − VBE) / (RB + (β + 1) · RE)
```

## ข้อจำกัด

### Lab 3 DC Bias Calculator
- ไม่ใช่ SPICE/ngspice — แบบจำลอง Forward-Active โดยถือ `β` และ `VBE` คงที่ ไม่ได้แก้สมการแบบไม่เชิงเส้น
- ถ้า `IB ≤ 0` วงจรอยู่ที่ **Cutoff** และแบบจำลอง Forward-Active ใช้ไม่ได้
- ถ้า `VCE ≤ 0.2 V` จะแสดง **Saturation warning** แต่ยังรายงานค่าที่คำนวณได้
  โดยไม่แก้สมการใหม่ใน Saturation Region
- `VCE` ไม่ได้แปรผกผันกับ `RE` แบบเส้นตรงเสมอ: ในย่านนี้ `RE` เพิ่มทำให้ `VE`
  เพิ่มมากกว่าที่ `IC · RC` ลดลง (`VCE` จึงลด) แต่ถ้า `RE` ใหญ่มากจน `IC → 0`
  ค่า `VCE` จะกลับขึ้นไปใกล้ `VCC`
- โหมด `fixed` และ `emitter` ไม่ใช้ `R1`/`R2` (และ `fixed` ไม่ใช้ `RE`)
  ค่าที่ส่งมาในช่องเหล่านั้นจะถูกเพิกเฉย

### Lab 4 CE Amplifier Simulator
- ใช้ ngspice จริงสำหรับ `.op/.ac/.tran` แต่จำกัดที่ **วงจร CE Voltage Divider reference เดียว** (ไม่มี CE bypass capacitor, ไม่มี topology อื่น)
- ค่า SPICE ขึ้นกับโมเดล 2N3904 และ netlist ที่สร้างจริง; ค่า Analytical reference เป็นสูตร divider แบบ ideal เพื่อเปรียบเทียบ ไม่ใช่ค่าเดียวกันโดยนิยาม
- ถ้า ngspice ไม่พบ, timeout, exit code ไม่ใช่ 0, หรือ output ว่าง/parse ไม่ได้/มีค่า non-finite ระบบจะแสดงสถานะ error และไม่แสดงกราฟ/ผลสำเร็จเก่าค้าง
- กราฟเป็น SVG ที่สร้างฝั่ง server (ไม่มี Chart.js/JS charting library)
