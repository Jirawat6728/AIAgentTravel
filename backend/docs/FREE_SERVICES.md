# บริการที่ฟรี / มี Free Tier ใน AI Travel Agent

สรุปบริการที่ใช้ในโปรเจกต์ และอันไหนฟรีหรือมีโควตาฟรี

---

## ฟรีหรือมี Free Tier ชัดเจน

| บริการ | รายละเอียด | หมายเหตุ |
|--------|------------|----------|
| **Gemini API** | โควตาฟรีจาก Google AI Studio (จำนวน request/วัน หรือ tokens) | ลงทะเบียนที่ [aistudio.google.com](https://aistudio.google.com/apikey) ได้ API key ฟรี มี limit ตามแผน |
| **MongoDB** | MongoDB Atlas ฟรี (M0 cluster) หรือรัน MongoDB เองบนเครื่อง (ฟรีทั้งหมด) | [mongodb.com/atlas](https://www.mongodb.com/atlas) เลือก Free tier |
| **Redis** | รัน Redis เองบนเครื่องฟรี หรือ Redis Cloud มี free tier | โปรเจกต์รองรับ Redis optional ถ้าไม่รันก็ยังใช้ได้ (degraded) |
| **Google OAuth (GOOGLE_CLIENT_ID)** | ใช้ฟรีสำหรับการล็อกอินด้วย Google | สร้าง OAuth client ใน Google Cloud Console ไม่เสียเงินสำหรับการยืนยันตัวตนทั่วไป |
| **Firebase** | แผน Spark (ฟรี) มีโควตาการยืนยันตัวตน อีเมล ฯลฯ | [Firebase pricing](https://firebase.google.com/pricing) – โหมดฟรีเพียงพอสำหรับ dev และ traffic ไม่สูงมาก |
| **Google Maps API** | มีเครดิตฟรีประมาณ $200/เดือน (พอใช้สำหรับ dev และ traffic ปานกลาง) | เปิดบิล Google Cloud แล้วใช้ไม่เกินเครดิต = ไม่ถูกหักเงิน |
| **Amadeus API (Test/Sandbox)** | สภาพแวดล้อม Test/Sandbox ใช้สำหรับพัฒนาได้ฟรี | ใช้ `AMADEUS_*_ENV=test` หรือ sandbox ไม่คิดเงินค้นหา/จองทดสอบ |
| **Omise (Test keys)** | คีย์ Test (skey_test_*, pkey_test_*) ใช้ทดสอบการชำระเงินฟรี | ไม่มีการ charge จริง |
| **อีเมลยืนยัน (Firebase Auth)** | ยืนยันอีเมลผ่าน Firebase sendEmailVerification() ฟรี (อยู่ในแผน Spark) | ไม่ใช้ Nodemailer/SMTP — ฝั่ง Client เรียก Firebase |
| **Backend / Frontend (รันเอง)** | รัน Python + Node + Vite บนเครื่องตัวเองฟรี | ไม่มีค่าใช้บริการเพิ่ม |

---

## ฟรีแบบมีเงื่อนไข / Trial

| บริการ | รายละเอียด | หมายเหตุ |
|--------|------------|----------|
| **Twilio (SMS/OTP)** | มีเครดิต Trial ฟรีเมื่อสมัครใหม่ | หมด trial แล้วคิดเงินต่อข้อความ |
| **Amadeus (Production)** | ใช้สภาพแวดล้อม Production สำหรับค้นหาจริง/จองจริง | มี pricing ตามการใช้งาน ต้องดูที่ Amadeus Developer |
| **Omise (Production)** | ใช้คีย์ Live (skey_live_*, pkey_live_*) สำหรับรับชำระเงินจริง | มีค่าธรรมเนียมต่อรายการตาม Omise |

---

## สรุปสั้นๆ

- **ใช้ฟรีได้เต็มที่ (หรือฟรี tier พอใช้ dev):**  
  Gemini, MongoDB (Atlas Free / local), Redis (local), Google OAuth, Firebase (Spark + อีเมลยืนยัน), Google Maps (ในเครดิตฟรี), Amadeus Test, Omise Test, รันแอปเอง

- **ฟรีช่วง Trial / มี limit:**  
  Twilio (SMS), Google Maps (เกินเครดิตแล้วเสียเงิน)

- **ใช้จริงแล้วมักมีค่าใช้จ่าย:**  
  Amadeus Production, Omise Production (รับชำระเงินจริง)

ถ้าต้องการ “ใช้ฟรีทั้งหมด” แนะนำ: ใช้เฉพาะ Test/Sandbox ของ Amadeus และ Omise, ใช้ Firebase สำหรับยืนยันอีเมล (sendEmailVerification), ไม่เปิด Twilio (หรือใช้แค่ช่วง Trial), และใช้โควตาฟรีของ Gemini / Firebase / Google Maps ภายใน limit ที่แต่ละบริการกำหนด
