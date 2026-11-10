# Design Note — BJT DC Bias Web App

## สรุปการตัดสินใจ

แอปพลิเคชันนี้เป็น Flask Web App แบบ **server-rendered** หน้าเดียว
ผู้ใช้กรอกค่าที่ `/` แล้วกดปุ่ม ระบบส่ง `POST /` ไปให้ Flask เรียก
`dc_bias.validate()` และ `dc_bias.calculate()` จากนั้นเรนเดอร์
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
Browser (form) --POST--> Flask index()
                            |
                            v
                    dc_bias.validate()  --> errors --> render ฟอร์ม + error
                            |
                            v (ผ่าน)
                    dc_bias.calculate() --> BiasResult
                            |
                            v
                    formatting.fmt_*()  --> สตริงพร้อมหน่วย
                            |
                            v
                    templates/index.html --> HTML response --> Browser
```

## การตัดสินใจเรื่อง region

- `VTH <= VBE` → Cutoff: รายงาน `IC = IE = 0`, `VB = VTH`, `VC = VCC`
  ไม่รายงานค่าติดลบที่เกิดจากสูตร Forward-Active
- `VCE <= 0.3 V` → Saturation warning แต่ยังรายงานค่าที่คำนวณได้
  พร้อมระบุว่าไม่น่าเชื่อถือ
- กรณีอื่น → Active

เกณฑ์ `0.3 V` เป็นเพียงเกณฑ์เตือน ไม่ใช่การแก้สมการใน Saturation Region จริง

## สิ่งที่ตัดออกและเหตุผล

AC analysis, Transient, Bode plot, Bias แบบอื่น, การต่อ SPICE/ngspice,
JavaScript และฐานข้อมูล — ทั้งหมดอยู่นอกขอบเขตของ Lab 02 และจะเพิ่มในสัปดาห์ถัดไป
การใส่เข้าไปจะทำให้งานไม่จบในคาบและเพิ่มจุดที่พังตอนสาธิต
