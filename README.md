# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
NPN แบบ Common-Emitter ที่ใช้ **Voltage-Divider Bias**
พัฒนาเป็นส่วนหนึ่งของรายวิชา ENG29 2121 (Lab 02)

## ค่าที่รับและแสดงผล

| ข้อมูลเข้า | ข้อมูลออก |
|---|---|
| `VCC` (V), `R1`/`R2`/`RC`/`RE` (kΩ), `β`, `VBE` (V) | `VB`, `VE`, `VC`, `VCE` (V) และ `IC` (mA/µA) |
| | ค่าขั้นตอน `VTH`, `RTH`, `IB`, `IE` และสถานะ Operating Region |

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

> ต้องรันผ่าน Flask Server เท่านั้น การเปิด `templates/index.html` ด้วย
> `file://` จะไม่ได้ผลลัพธ์ เพราะไม่มีการคำนวณฝั่ง Python

## การรันทดสอบ

```powershell
python -m unittest discover -s tests -v
```

## โครงสร้างโปรเจกต์

```
app.py                  Flask routes และการประกอบผลลัพธ์สำหรับเทมเพลต
dc_bias.py              สมการ DC bias + validation (ไม่รู้จัก Flask)
formatting.py           จัดรูปแบบตัวเลขและหน่วย (V, mA, µA, Ω, kΩ)
templates/index.html    ฟอร์มและผลลัพธ์ (Jinja, ไม่มี JavaScript)
static/style.css        การจัดหน้าจอ
tests/test_dc_bias.py   ทดสอบสมการและ Operating Region
tests/test_validation.py ทดสอบการตรวจข้อมูลเข้าและการแปลงหน่วย
tests/test_formatting.py ทดสอบรูปแบบตัวเลข
tests/test_web.py       ทดสอบ HTTP route ด้วย Flask test client
docs/                   design note, validation log, reflection
```

## แบบจำลองที่ใช้

Forward-Active Approximation โดยถือ `β` และ `VBE` คงที่

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) · RE)
IC  = β · IB          IE = (β + 1) · IB
VE  = IE · RE         VB = VE + VBE
VC  = VCC − IC · RC   VCE = VC − VE
```

## ข้อจำกัด

- ไม่ใช่ SPICE/ngspice — ไม่ได้แก้สมการแบบไม่เชิงเส้น
- ถ้า `VTH ≤ VBE` วงจรอยู่ที่ **Cutoff** และแบบจำลอง Forward-Active ใช้ไม่ได้
- ถ้า `VCE ≤ 0.3 V` จะแสดง **Saturation warning** แต่ยังรายงานค่าที่คำนวณได้
  โดยไม่แก้สมการใหม่ใน Saturation Region
- ไม่รองรับ AC, Transient, Bode plot หรือ Bias แบบอื่นในเวอร์ชันนี้
