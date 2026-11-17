# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
NPN แบบ Common-Emitter รองรับสามวงจรไบอัส

| โหมด | วงจร | ช่องที่ใช้ในฟอร์ม |
|---|---|---|
| `divider` | Voltage Divider Bias | `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` |
| `fixed` | Fixed Bias (RB จาก VCC ไปเบส, อิมิตเตอร์ลงกราวด์) | `VCC`, `RB`, `RC`, `β`, `VBE` |
| `emitter` | Emitter Bias (RB จาก VCC ไปเบส + RE ที่อิมิตเตอร์) | `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` |

พัฒนาเป็นส่วนหนึ่งของรายวิชา ENG29 2121 (Lab 02 วงจร Voltage Divider,
Lab 03 เพิ่ม Fixed Bias และ Emitter Bias พร้อมตรวจผลผ่านเบราว์เซอร์)

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
(ลิงก์ `/?mode=divider`, `/?mode=fixed`, `/?mode=emitter`)

> ต้องรันผ่าน Flask Server เท่านั้น การเปิด `templates/index.html` ด้วย
> `file://` จะไม่ได้ผลลัพธ์ เพราะไม่มีการคำนวณฝั่ง Python

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
app.py                  Flask routes, เลือกฟังก์ชันตามโหมด, ประกอบ context
dc_bias.py              สมการ DC bias ต่อโหมด + validation (ไม่รู้จัก Flask)
formatting.py           จัดรูปแบบตัวเลขและหน่วย (V, mA, µA, Ω, kΩ)
templates/index.html    ฟอร์มและผลลัพธ์ (Jinja, ไม่มี JavaScript)
static/style.css        การจัดหน้าจอ
tests/test_dc_bias.py   ทดสอบสมการ Divider และ Operating Region
tests/test_fixed.py     ทดสอบสมการ Fixed Bias (A2)
tests/test_emitter.py   ทดสอบสมการ Emitter Bias (A3, A4)
tests/test_validation.py ทดสอบการตรวจข้อมูลเข้าและการแปลงหน่วย
tests/test_formatting.py ทดสอบรูปแบบตัวเลข
tests/test_web.py       ทดสอบ HTTP route ด้วย Flask test client
opencode.json           ตั้งค่า Playwright MCP สำหรับตรวจผลผ่านเบราว์เซอร์
docs/                   design note, validation log, reflection
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

- ไม่ใช่ SPICE/ngspice — ไม่ได้แก้สมการแบบไม่เชิงเส้น
- ถ้า `IB ≤ 0` วงจรอยู่ที่ **Cutoff** และแบบจำลอง Forward-Active ใช้ไม่ได้
- ถ้า `VCE ≤ 0.2 V` จะแสดง **Saturation warning** แต่ยังรายงานค่าที่คำนวณได้
  โดยไม่แก้สมการใหม่ใน Saturation Region
- `VCE` ไม่ได้แปรผกผันกับ `RE` แบบเส้นตรงเสมอ: ในย่านนี้ `RE` เพิ่มทำให้ `VE`
  เพิ่มมากกว่าที่ `IC · RC` ลดลง (`VCE` จึงลด) แต่ถ้า `RE` ใหญ่มากจน `IC → 0`
  ค่า `VCE` จะกลับขึ้นไปใกล้ `VCC`
- โหมด `fixed` และ `emitter` ไม่ใช้ `R1`/`R2` (และ `fixed` ไม่ใช้ `RE`)
  ค่าที่ส่งมาในช่องเหล่านั้นจะถูกเพิกเฉย
- ไม่รองรับ AC, Transient, Bode plot หรือ DC Load Line ในเวอร์ชันนี้
