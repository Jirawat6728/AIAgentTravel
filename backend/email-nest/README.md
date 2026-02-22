# Email Service (NestJS + Nodemailer + Mailer)

ส่งอีเมลยืนยันด้วย **Nodemailer** ผ่าน **NestJS Mailer** พร้อมเทมเพลต Handlebars ให้อีเมลสวยและเป็นรูปแบบเดียวกัน

## ความต้องการ

- Node.js 18+
- ตั้งค่า SMTP ใน `backend/.env` (ใช้ไฟล์ env ร่วมกับ backend หลัก)

## ติดตั้งและรัน

```bash
cd backend/email-nest
npm install
npm run build
npm run start
```

หรือรันโหมดพัฒนา (auto-reload):

```bash
npm run start:dev
```

บริการจะรันที่ **http://localhost:3001** (หรือค่า `EMAIL_SERVICE_PORT` / `PORT` ใน env)

## Environment

อ่านจาก `backend/.env` อัตโนมัติ (เมื่อรันจาก `email-nest`):

| ตัวแปร | ความหมาย |
|--------|----------|
| `SMTP_HOST` | เซิร์ฟเวอร์ SMTP (เช่น smtp.gmail.com, smtp-mail.outlook.com) |
| `SMTP_PORT` | พอร์ต (587 หรือ 465) |
| `SMTP_SECURE` | true ถ้าใช้พอร์ต 465 |
| `SMTP_USER` | อีเมลที่ใช้ส่ง |
| `SMTP_PASSWORD` | รหัสผ่านหรือ App Password |
| `FROM_EMAIL` | ชื่อ/อีเมลผู้ส่ง (เช่น "AI Travel Agent" <noreply@example.com>) |

Backend หลัก (Python) ตั้ง `EMAIL_SERVICE_URL=http://localhost:3001` เพื่อเรียกบริการนี้

## API

### POST /send

รองรับสองรูปแบบ:

1. **เทมเพลตสวย (แนะนำ)** — ส่ง `template` + `context`:
   - `verify-email`: ยืนยันอีเมลหลังสมัคร (context: `userName`, `linkUrl`)
   - `verify-email-change`: ยืนยันการเปลี่ยนอีเมล (context: `userName`, `newEmail`, `linkUrl`)

2. **HTML ธรรมดา** — ส่ง `html` จะถูกห่อด้วย layout สวย (`wrap-html`)

ตัวอย่าง body:
```json
{
  "to": "user@example.com",
  "subject": "ยืนยันอีเมล - AI Travel Agent",
  "template": "verify-email",
  "context": { "userName": "คุณ", "linkUrl": "https://..." }
}
```

## เทมเพลต

- `src/mail/templates/verify-email.hbs` — หน้าตาอีเมลยืนยัน (หัวข้อ สี ปุ่ม)
- `src/mail/templates/verify-email-change.hbs` — หน้าตาอีเมลยืนยันเปลี่ยนอีเมล
- `src/mail/templates/wrap-html.hbs` — ใช้ห่อ HTML ที่ส่งมาให้เป็นรูปแบบเดียวกับระบบ

แก้ไขไฟล์ `.hbs` แล้ว build ใหม่ หรือใช้ `npm run start:dev` เพื่อพัฒนา
