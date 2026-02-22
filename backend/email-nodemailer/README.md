# Email Service (Nodemailer)

บริการส่งอีเมลด้วย [Nodemailer](https://www.npmjs.com/package/nodemailer) สำหรับ AI Travel Agent — ใช้ส่งอีเมลยืนยันตัวตนและเปลี่ยนอีเมล

## การติดตั้ง

```bash
cd backend/email-nodemailer
npm install
```

## ตั้งค่า SMTP

บริการอ่านตัวแปรจาก `backend/.env` (โฟลเดอร์ถัดไป)

ใน `backend/.env` กำหนดค่าตัวอย่าง:

```env
# URL ให้ Python backend เรียกส่งอีเมล (พอร์ตตรงกับ EMAIL_SERVICE_PORT ด้านล่าง)
EMAIL_SERVICE_URL=http://localhost:3025

# SMTP (เช่น Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL="AI Travel Agent" <your-email@gmail.com>
```

- **Gmail:** ใช้ [App Password](https://support.google.com/accounts/answer/185833) ไม่ใช้รหัสผ่านปกติ
- **Outlook:** ใช้ `smtp-mail.outlook.com`, port 587

## รันบริการ

```bash
npm start
```

รันที่พอร์ต **3025** (หรือ `EMAIL_SERVICE_PORT` / `PORT` จาก env)

จากนั้นในแอปเมื่อกด "ส่งอีเมลยืนยัน" backend จะเรียก `POST http://localhost:3025/send` และ Nodemailer จะส่งอีเมลจริง

## API

- `POST /send` — รับ `{ to, subject, template, context }`
  - `template`: `verify-email` หรือ `verify-email-change`
  - `context`: `userName`, `linkUrl` (และ `newEmail` สำหรับเปลี่ยนอีเมล)
- `GET /health` — ตรวจสอบว่า service ทำงาน
