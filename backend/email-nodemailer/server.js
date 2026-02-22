/**
 * Email service using Nodemailer only.
 * API: POST /send { to, subject, template, context }
 * Compatible with backend Python EMAIL_SERVICE_URL.
 */
require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });
const express = require('express');
const nodemailer = require('nodemailer');

const app = express();
app.use(express.json());

const PORT = process.env.EMAIL_SERVICE_PORT || process.env.PORT || 3025;

// SMTP from env (same as backend/.env)
const transportOptions = {
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: parseInt(process.env.SMTP_PORT || '587', 10),
  secure: process.env.SMTP_SECURE === 'true',
};
if (process.env.SMTP_USER) {
  transportOptions.auth = {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASSWORD || '',
  };
}

const transporter = nodemailer.createTransport(transportOptions);
const fromEmail = process.env.FROM_EMAIL || '"AI Travel Agent" <noreply@example.com>';

// แจ้งเตือนถ้ายังใช้ค่า placeholder ใน backend/.env (ส่งอีเมลจะไม่สำเร็จจนกว่าจะแทนที่ด้วยค่าจริง)
const isPlaceholder = !process.env.SMTP_USER || /your-email|your-app-password|noreply@example\.com/i.test(process.env.SMTP_USER + (process.env.SMTP_PASSWORD || '') + (process.env.FROM_EMAIL || ''));
if (isPlaceholder) {
  console.warn('[email-nodemailer] ⚠️  SMTP ยังใช้ค่า placeholder ใน backend/.env — แทนที่ SMTP_USER, SMTP_PASSWORD, FROM_EMAIL ด้วยค่าจริง (Gmail ใช้ App Password) แล้ว restart บริการนี้');
}

// Better Auth UI style (Vercel variant): siteName, heading, content, action button, baseUrl
// Ref: https://better-auth-ui.com/components/email-template
const SITE_NAME = process.env.SITE_NAME || 'AI Travel Agent';
const BASE_URL = process.env.FRONTEND_URL || process.env.BASE_URL || '';

function renderVerifyEmail(ctx) {
  const userName = (ctx && ctx.userName) || 'คุณ';
  const linkUrl = (ctx && ctx.linkUrl) || '#';
  return `<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ยืนยันอีเมล - ${escapeHtml(SITE_NAME)}</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #fafafa; color: #171717; padding: 40px 24px; line-height: 1.6; }
    .wrapper { max-width: 480px; margin: 0 auto; }
    .card { background: #fff; border-radius: 8px; padding: 32px 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .site-name { font-size: 14px; font-weight: 600; color: #737373; margin-bottom: 24px; letter-spacing: -0.01em; }
    .heading { font-size: 24px; font-weight: 600; margin: 0 0 24px; letter-spacing: -0.02em; color: #171717; }
    .content { font-size: 15px; color: #525252; margin: 0 0 24px; }
    .content p { margin: 0 0 12px; }
    .content p:last-child { margin-bottom: 0; }
    .btn-wrap { text-align: center; margin: 28px 0; }
    .btn { display: inline-block; padding: 12px 24px; background: #171717; color: #fff !important; text-decoration: none; font-size: 14px; font-weight: 500; border-radius: 6px; }
    .link-fallback { font-size: 13px; color: #737373; word-break: break-all; margin-top: 16px; }
    .link-fallback a { color: #0066cc; }
    .footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e5e5; font-size: 12px; color: #a3a3a3; text-align: center; }
    .footer a { color: #737373; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card">
      <div class="site-name">${escapeHtml(SITE_NAME)}</div>
      <h1 class="heading">ยืนยันอีเมล</h1>
      <div class="content">
        <p>สวัสดีค่ะ ${escapeHtml(userName)}</p>
        <p>กรุณากดปุ่มด้านล่างเพื่อยืนยันอีเมลของคุณ (ลิงก์ใช้ได้ 24 ชั่วโมง)</p>
      </div>
      <div class="btn-wrap">
        <a href="${escapeAttr(linkUrl)}" class="btn">ยืนยันอีเมล</a>
      </div>
      <p class="link-fallback">หากปุ่มไม่ทำงาน คัดลอกลิงก์นี้: <a href="${escapeAttr(linkUrl)}">${escapeHtml(linkUrl)}</a></p>
    </div>
    <div class="footer">
      ${BASE_URL ? `<a href="${escapeAttr(BASE_URL)}">${escapeHtml(SITE_NAME)}</a>` : escapeHtml(SITE_NAME)}
    </div>
  </div>
</body>
</html>`;
}

function renderVerifyEmailChange(ctx) {
  const userName = (ctx && ctx.userName) || 'คุณ';
  const newEmail = (ctx && ctx.newEmail) || '';
  const linkUrl = (ctx && ctx.linkUrl) || '#';
  return `<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ยืนยันการเปลี่ยนอีเมล - ${escapeHtml(SITE_NAME)}</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #fafafa; color: #171717; padding: 40px 24px; line-height: 1.6; }
    .wrapper { max-width: 480px; margin: 0 auto; }
    .card { background: #fff; border-radius: 8px; padding: 32px 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .site-name { font-size: 14px; font-weight: 600; color: #737373; margin-bottom: 24px; letter-spacing: -0.01em; }
    .heading { font-size: 24px; font-weight: 600; margin: 0 0 24px; letter-spacing: -0.02em; color: #171717; }
    .content { font-size: 15px; color: #525252; margin: 0 0 24px; }
    .content p { margin: 0 0 12px; }
    .email-badge { display: inline-block; padding: 4px 10px; background: #f5f5f5; border-radius: 4px; font-weight: 500; color: #171717; }
    .btn-wrap { text-align: center; margin: 28px 0; }
    .btn { display: inline-block; padding: 12px 24px; background: #171717; color: #fff !important; text-decoration: none; font-size: 14px; font-weight: 500; border-radius: 6px; }
    .link-fallback { font-size: 13px; color: #737373; word-break: break-all; margin-top: 16px; }
    .link-fallback a { color: #0066cc; }
    .footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e5e5; font-size: 12px; color: #a3a3a3; text-align: center; }
    .footer a { color: #737373; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card">
      <div class="site-name">${escapeHtml(SITE_NAME)}</div>
      <h1 class="heading">ยืนยันการเปลี่ยนอีเมล</h1>
      <div class="content">
        <p>สวัสดีค่ะ ${escapeHtml(userName)}</p>
        <p>คุณได้ขอเปลี่ยนอีเมลเป็น <span class="email-badge">${escapeHtml(newEmail)}</span></p>
        <p>กรุณากดปุ่มด้านล่างเพื่อยืนยัน (ลิงก์ใช้ได้ 24 ชั่วโมง)</p>
      </div>
      <div class="btn-wrap">
        <a href="${escapeAttr(linkUrl)}" class="btn">ยืนยันอีเมลใหม่</a>
      </div>
      <p class="link-fallback">หากปุ่มไม่ทำงาน คัดลอกลิงก์นี้: <a href="${escapeAttr(linkUrl)}">${escapeHtml(linkUrl)}</a></p>
    </div>
    <div class="footer">
      ${BASE_URL ? `<a href="${escapeAttr(BASE_URL)}">${escapeHtml(SITE_NAME)}</a>` : escapeHtml(SITE_NAME)}
    </div>
  </div>
</body>
</html>`;
}

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function escapeAttr(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

app.post('/send', async (req, res) => {
  const { to, subject, template, context } = req.body || {};
  if (!to || !subject) {
    return res.status(400).json({ ok: false, message: 'to and subject are required' });
  }
  let html;
  if (template === 'verify-email' && context) {
    html = renderVerifyEmail(context);
  } else if (template === 'verify-email-change' && context) {
    html = renderVerifyEmailChange(context);
  } else if (template && context) {
    return res.status(400).json({ ok: false, message: 'Unknown template: ' + template });
  } else {
    return res.status(400).json({ ok: false, message: 'Provide template and context' });
  }
  try {
    await transporter.sendMail({
      from: fromEmail,
      to,
      subject,
      html,
    });
    res.json({ ok: true });
  } catch (err) {
    console.error('Nodemailer send error:', err);
    res.status(500).json({ ok: false, message: err.message || String(err) });
  }
});

app.get('/health', (req, res) => {
  res.json({
    ok: true,
    service: 'email-nodemailer',
    smtp_configured: !isPlaceholder,
    port: PORT,
  });
});

app.listen(PORT, () => {
  console.log(`Email service (Nodemailer) running on http://localhost:${PORT}`);
});
