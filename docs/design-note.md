# Design Note — BJT DC Bias Web App

## สรุปการตัดสินใจ

แอปพลิเคชันนี้เป็น Flask Web App แบบ **server-rendered** หน้าเดียว
ผู้ใช้เลือกโหมดวงจรจากแถบลิงก์แล้วกรอกค่าที่ `/` และกดปุ่ม ระบบส่ง `POST /`
ไปให้ Flask อ่าน `mode` → `dc_bias.validate(form, mode)` → ฟังก์ชันของโหมดนั้น
(`calculate()` / `calculate_fixed()` / `calculate_emitter()`) จากนั้นเรนเดอร์
`templates/index.html` กลับมาพร้อมผลลัพธ์ ไม่มีการใช้ JavaScript

## ทำไมเลือก server-rendered

พิจารณา 3 ทาง ได้แก่

1. **Flask + Jinja server-rendered** — เลือกใช้
2. Flask JSON API + `fetch()` — ไม่เลือก
3. แยกสองเทมเพลต (`index.html` + `result.html`) — ไม่เลือก

เหตุผลที่เลือกแบบที่ 1 เพราะโจทย์กำหนดให้ Server เป็นผู้คำนวณและแสดงผลใน HTML
จำนวนชั้นที่ต้องเขียนและ debug น้อยที่สุด (ไม่มี JavaScript เลย) และทดสอบได้ด้วย
Flask test client โดยตรง ทางเลือกที่ 2 เพิ่มความซับซ้อนฝั่ง client โดยไม่ได้คะแนน
เพิ่มจากเกณฑ์ตรวจรับ ส่วนทางเลือกที่ 3 ต้องดูแล markup ของฟอร์มซ้ำสองที่

## การแยกความรับผิดชอบ

| ไฟล์ | หน้าที่ | สิ่งที่ต้องไม่ทำ |
|---|---|---|
| `dc_bias.py` | สมการ DC bias, validation, การตัดสิน region | import Flask, รู้จัก HTML |
| `formatting.py` | แปลงตัวเลขเป็นสตริงพร้อมหน่วย | คำนวณฟิสิกส์ |
| `app.py` | HTTP route, ประกอบ context ให้เทมเพลต | เก็บสมการ |
| `templates/index.html` | แสดงฟอร์มและผลลัพธ์ | คำนวณ, hardcode ผลลัพธ์ |
| `tests/` | ตรวจสมการและ HTTP | แก้ไข production code |

## เส้นทางข้อมูล

```
Browser (form + hidden mode) --POST--> Flask index()
                                          |
                                          v
                                  dc_bias.parse_mode()  --> ไม่รู้จัก --> error
                                          |
                                          v
                     dc_bias.validate(form, mode)  --> errors --> render ฟอร์ม + error
                                          |
                                          v (ผ่าน)
             if/elif ตามโหมด: calculate() / calculate_fixed() / calculate_emitter()
                                          |
                                          v (BiasResult)
                            formatting.fmt_*()  --> สตริงพร้อมหน่วย
                                          |
                                          v
                     templates/index.html --> HTML response --> Browser
```

## ทำไมเลือกฟังก์ชันแยกต่อโหมด

ทางเลือกที่พิจารณา

1. **ฟังก์ชันแยกต่อโหมด + `if/elif` ใน `app.py`** — เลือกใช้
2. ฟังก์ชันเดียวที่รับ `mode` แล้วแตกกิ่งข้างใน — ไม่เลือก
3. คลาส/subclass ต่อโหมด — ไม่เลือก

เหตุผล: สมการ `IB` ของสามโหมดไม่เหมือนกัน (Divider มี `VTH`/`RTH`, Fixed ไม่มี `RE`,
Emitter มี `(β+1)·RE` อยู่ในตัวส่วน) การแยกเป็นฟังก์ชันทำให้แต่ละสมการอ่านได้ตรงกับ
ตำรา ตรวจทีละโหมดได้ด้วย unit test ของตัวเอง และ `BiasResult` ที่ใช้ร่วมกันทำให้
เทมเพลตมีทางเดียวในการแสดงผล ทางเลือกที่ 2 ทำให้ร่างกายฟังก์ชันเต็มไปด้วยเงื่อนไข
ที่ผสม `VTH` กับ `RB` ไว้ด้วยกัน ส่วนทางเลือกที่ 3 เพิ่มโครงสร้างมากเกินกว่าขนาดงาน

`validate(form, mode)` ตรวจเฉพาะช่องที่โหมดนั้นใช้ (`MODE_FIELDS`) เพื่อให้ค่าที่ค้าง
มาจากโหมดก่อนหน้าไม่กลายเป็น error และ `parse_mode()` คืน `None` เมื่อเจอค่าที่ไม่รู้จัก
แทนที่จะเดาเป็น Divider — ผู้เรียกต้องแสดง error เอง

## การตัดสินใจเรื่อง region

- Divider: `VTH <= VBE` → Cutoff: รายงาน `IC = IE = 0`, `VB = VTH`, `VC = VCC`
  ไม่รายงานค่าติดลบที่เกิดจากสูตร Forward-Active
- Fixed/Emitter: `IB <= 0` → Cutoff พร้อม warning
- `VCE <= 0.2 V` → Saturation warning แต่ยังรายงานค่าที่คำนวณได้
  พร้อมระบุว่าไม่น่าเชื่อถือ
- กรณีอื่น → Active

เกณฑ์ `0.2 V` เป็นเพียงเกณฑ์เตือน ไม่ใช่การแก้สมการใน Saturation Region จริง
(Lab 02 เคยใช้ `0.3 V` — Lab 03 กำหนดใหม่เป็น `0.2 V`)

## สิ่งที่เรียนรู้จากกรณี A4

การเพิ่ม `RE` จาก `1 kΩ` เป็น `2 kΩ` ในโหมด Emitter ทำให้ `IB` และ `IC` ลดลง
ตามที่คาด แต่ `VCE` **ลดลง** จาก `8.705 V` เป็น `8.033 V` ไม่ใช่เพิ่มขึ้น
เพราะ `VE = IE · RE` เพิ่มขึ้นประมาณ `0.86 V` ขณะที่ `IC · RC` ลดลงเพียง `0.19 V`
ถ้าเพิ่ม `RE` ต่อจน `IC → 0` ค่า `VCE` จะกลับขึ้นไปใกล้ `VCC` — ความสัมพันธ์นี้
จึงไม่เป็นเส้นตรง และไม่ควรสรุปทิศทางจากความรู้สึก

## สิ่งที่ตัดออกและเหตุผล

AC analysis, Transient, Bode plot, DC Load Line, การต่อ SPICE/ngspice,
JavaScript และฐานข้อมูล — ทั้งหมดอยู่นอกขอบเขตของ Lab 02/03 และจะเพิ่มในสัปดาห์ถัดไป
การใส่เข้าไปจะทำให้งานไม่จบในคาบและเพิ่มจุดที่พังตอนสาธิต
