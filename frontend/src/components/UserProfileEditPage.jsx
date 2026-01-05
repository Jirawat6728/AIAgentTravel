import React, { useState, useEffect } from 'react';
import './UserProfileEditPage.css';

export default function UserProfileEditPage({ user, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    dob: '',
    gender: '',
    passport_no: '',
    passport_expiry: '',
    nationality: 'TH',
    address_line1: '',
    address_line2: '',
    city: '',
    province: '',
    postal_code: '',
    country: 'TH',
  });

  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      const fullName = (user.name || '').trim();
      const parts = fullName.split(/\s+/).filter(Boolean);
      const first_name = parts[0] || '';
      const last_name = parts.slice(1).join(' ') || '';

      setFormData({
        first_name: user.first_name || first_name,
        last_name: user.last_name || last_name,
        email: user.email || '',
        phone: user.phone || '',
        dob: user.dob || '',
        gender: user.gender || '',
        passport_no: user.passport_no || '',
        passport_expiry: user.passport_expiry || '',
        nationality: user.nationality || 'TH',
        address_line1: user.address_line1 || '',
        address_line2: user.address_line2 || '',
        city: user.city || '',
        province: user.province || '',
        postal_code: user.postal_code || '',
        country: user.country || 'TH',
      });
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validate = () => {
    const newErrors = {};

    // Required fields
    if (!formData.first_name.trim()) {
      newErrors.first_name = 'กรุณากรอกชื่อ';
    }
    if (!formData.last_name.trim()) {
      newErrors.last_name = 'กรุณากรอกนามสกุล';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'กรุณากรอกอีเมล';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'รูปแบบอีเมลไม่ถูกต้อง';
    }
    if (!formData.phone.trim()) {
      newErrors.phone = 'กรุณากรอกเบอร์โทร';
    } else if (!/^[0-9]{9,10}$/.test(formData.phone.replace(/[-\s]/g, ''))) {
      newErrors.phone = 'รูปแบบเบอร์โทรไม่ถูกต้อง (9-10 หลัก)';
    }

    // Optional but recommended
    if (formData.dob && !/^\d{4}-\d{2}-\d{2}$/.test(formData.dob)) {
      newErrors.dob = 'รูปแบบวันเกิดไม่ถูกต้อง (YYYY-MM-DD)';
    }
    if (formData.passport_no && formData.passport_no.length < 6) {
      newErrors.passport_no = 'เลขพาสปอร์ตต้องมีอย่างน้อย 6 ตัวอักษร';
    }
    if (formData.passport_expiry && !/^\d{4}-\d{2}-\d{2}$/.test(formData.passport_expiry)) {
      newErrors.passport_expiry = 'รูปแบบวันหมดอายุไม่ถูกต้อง (YYYY-MM-DD)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(formData);
    } catch (error) {
      console.error('Error saving profile:', error);
      alert('เกิดข้อผิดพลาดในการบันทึกข้อมูล: ' + (error.message || 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  const countries = [
    { code: 'TH', name: 'ไทย' },
    { code: 'US', name: 'สหรัฐอเมริกา' },
    { code: 'GB', name: 'สหราชอาณาจักร' },
    { code: 'JP', name: 'ญี่ปุ่น' },
    { code: 'KR', name: 'เกาหลีใต้' },
    { code: 'CN', name: 'จีน' },
    { code: 'SG', name: 'สิงคโปร์' },
    { code: 'MY', name: 'มาเลเซีย' },
    { code: 'ID', name: 'อินโดนีเซีย' },
    { code: 'VN', name: 'เวียดนาม' },
    { code: 'PH', name: 'ฟิลิปปินส์' },
    { code: 'AU', name: 'ออสเตรเลีย' },
  ];

  const provinces = [
    'กรุงเทพมหานคร', 'เชียงใหม่', 'ภูเก็ต', 'พัทยา', 'กระบี่', 'เชียงราย',
    'นครราชสีมา', 'ขอนแก่น', 'อุดรธานี', 'สงขลา', 'สุราษฎร์ธานี', 'ระยอง',
  ];

  return (
    <div className="profile-edit-container">
      <div className="profile-edit-card">
        <div className="profile-edit-header">
          <h2>✏️ แก้ไขข้อมูลส่วนตัว</h2>
          <p className="profile-edit-subtitle">
            กรุณากรอกข้อมูลให้ครบถ้วนเพื่อความสะดวกในการจองทริป
          </p>
        </div>

        <form onSubmit={handleSubmit} className="profile-edit-form">
          {/* ข้อมูลพื้นฐาน */}
          <div className="form-section">
            <h3 className="form-section-title">📋 ข้อมูลพื้นฐาน</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="first_name" className="form-label">
                  ชื่อ <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  className={`form-input ${errors.first_name ? 'error' : ''}`}
                  placeholder="ชื่อ"
                />
                {errors.first_name && <span className="error-message">{errors.first_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="last_name" className="form-label">
                  นามสกุล <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  className={`form-input ${errors.last_name ? 'error' : ''}`}
                  placeholder="นามสกุล"
                />
                {errors.last_name && <span className="error-message">{errors.last_name}</span>}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="email" className="form-label">
                  อีเมล <span className="required">*</span>
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className={`form-input ${errors.email ? 'error' : ''}`}
                  placeholder="example@email.com"
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="phone" className="form-label">
                  เบอร์โทรศัพท์ <span className="required">*</span>
                </label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  className={`form-input ${errors.phone ? 'error' : ''}`}
                  placeholder="0812345678"
                />
                {errors.phone && <span className="error-message">{errors.phone}</span>}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="dob" className="form-label">วันเกิด</label>
                <input
                  type="date"
                  id="dob"
                  name="dob"
                  value={formData.dob}
                  onChange={handleChange}
                  className={`form-input ${errors.dob ? 'error' : ''}`}
                />
                {errors.dob && <span className="error-message">{errors.dob}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="gender" className="form-label">เพศ</label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือกเพศ --</option>
                  <option value="M">ชาย</option>
                  <option value="F">หญิง</option>
                  <option value="O">อื่นๆ</option>
                </select>
              </div>
            </div>
          </div>

          {/* ข้อมูลหนังสือเดินทาง */}
          <div className="form-section">
            <h3 className="form-section-title">🛂 ข้อมูลหนังสือเดินทาง (สำหรับเที่ยวบินระหว่างประเทศ)</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="passport_no" className="form-label">เลขหนังสือเดินทาง</label>
                <input
                  type="text"
                  id="passport_no"
                  name="passport_no"
                  value={formData.passport_no}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_no ? 'error' : ''}`}
                  placeholder="A12345678"
                />
                {errors.passport_no && <span className="error-message">{errors.passport_no}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="passport_expiry" className="form-label">วันหมดอายุ</label>
                <input
                  type="date"
                  id="passport_expiry"
                  name="passport_expiry"
                  value={formData.passport_expiry}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_expiry ? 'error' : ''}`}
                />
                {errors.passport_expiry && <span className="error-message">{errors.passport_expiry}</span>}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="nationality" className="form-label">สัญชาติ</label>
              <select
                id="nationality"
                name="nationality"
                value={formData.nationality}
                onChange={handleChange}
                className="form-input"
              >
                {countries.map(country => (
                  <option key={country.code} value={country.code}>{country.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* ที่อยู่ */}
          <div className="form-section">
            <h3 className="form-section-title">📍 ที่อยู่</h3>
            <div className="form-group">
              <label htmlFor="address_line1" className="form-label">ที่อยู่บรรทัดที่ 1</label>
              <input
                type="text"
                id="address_line1"
                name="address_line1"
                value={formData.address_line1}
                onChange={handleChange}
                className="form-input"
                placeholder="เลขที่, หมู่, ถนน"
              />
            </div>

            <div className="form-group">
              <label htmlFor="address_line2" className="form-label">ที่อยู่บรรทัดที่ 2</label>
              <input
                type="text"
                id="address_line2"
                name="address_line2"
                value={formData.address_line2}
                onChange={handleChange}
                className="form-input"
                placeholder="แขวง/ตำบล, เขต/อำเภอ"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="city" className="form-label">จังหวัด</label>
                <select
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือกจังหวัด --</option>
                  {provinces.map(province => (
                    <option key={province} value={province}>{province}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="postal_code" className="form-label">รหัสไปรษณีย์</label>
                <input
                  type="text"
                  id="postal_code"
                  name="postal_code"
                  value={formData.postal_code}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="10110"
                  maxLength="5"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="country" className="form-label">ประเทศ</label>
              <select
                id="country"
                name="country"
                value={formData.country}
                onChange={handleChange}
                className="form-input"
              >
                {countries.map(country => (
                  <option key={country.code} value={country.code}>{country.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Buttons */}
          <div className="form-actions">
            <button
              type="button"
              onClick={onCancel}
              className="btn-cancel"
              disabled={isSaving}
            >
              ยกเลิก
            </button>
            <button
              type="submit"
              className="btn-save"
              disabled={isSaving}
            >
              {isSaving ? 'กำลังบันทึก...' : 'บันทึกข้อมูล'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

