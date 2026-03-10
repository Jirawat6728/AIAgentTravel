import React, { useState, useEffect, useRef } from 'react';
import Swal from 'sweetalert2';
import { formatCardNumber, getCardType, validateCardNumber } from '../../utils/cardUtils';
import { loadOmiseScript, createTokenAsync } from '../../utils/omiseLoader';
import { CardBrandLogo } from '../settings/SettingsPage';
import './UserProfileEditPage.css';
import '../settings/SettingsPage.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';

/** แปลง YYYY-MM-DD (จาก API) เป็น DD/MM/YYYY สำหรับแสดง/กรอก */
function formatYyyyMmDdToDdMmYyyy(yyyyMmDd) {
  if (!yyyyMmDd || typeof yyyyMmDd !== 'string') return '';
  const m = yyyyMmDd.trim().match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!m) return yyyyMmDd;
  const [, y, mo, d] = m;
  return `${d.padStart(2, '0')}/${mo.padStart(2, '0')}/${y}`;
}

/** แปลงข้อความ DD/MM/YYYY หรือ D/M/YYYY เป็น YYYY-MM-DD (สำหรับส่ง API) คืน '' ถ้าไม่สมบูรณ์หรือไม่ถูกต้อง */
function parseDdMmYyyyToYyyyMmDd(input) {
  if (!input || typeof input !== 'string') return '';
  const s = input.trim().replace(/\s/g, '');
  const parts = s.split(/[/-]/);
  if (parts.length !== 3) return '';
  let [d, m, y] = parts;
  d = d.padStart(2, '0');
  m = m.padStart(2, '0');
  if (y.length === 2) y = parseInt(y, 10) >= 50 ? `19${y}` : `20${y}`;
  if (y.length !== 4) return '';
  const yyyy = parseInt(y, 10), mm = parseInt(m, 10), dd = parseInt(d, 10);
  if (isNaN(yyyy) || isNaN(mm) || isNaN(dd)) return '';
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return '';
  const date = new Date(yyyy, mm - 1, dd);
  if (date.getFullYear() !== yyyy || date.getMonth() !== mm - 1 || date.getDate() !== dd) return '';
  return `${yyyy}-${m}-${d}`;
}

/** จัดรูปแบบข้อความที่กรอกให้เป็น dd/mm/yyyy (ใส่ / ขั้นอัตโนมัติ) รับได้ทั้งตัวเลขล้วนหรือมี / อยู่แล้ว */
function formatDobInputWithSlashes(input) {
  if (!input || typeof input !== 'string') return '';
  const digits = input.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)}`;
}

const PROFILE_SECTION_IDS = ['personal', 'passport', 'visa', 'address_emergency', 'family', 'cards'];

export default function UserProfileEditPage({ 
  user, 
  onSave, 
  onCancel,
  onNavigateToHome = null,
  onNavigateToBookings = null,
  onNavigateToAI = null,
  onNavigateToFlights = null,
  onNavigateToHotels = null,
  onNavigateToCarRentals = null,
  onLogout = null,
  onNavigateToProfile = null,
  onNavigateToSettings = null,
  notificationCount = 0,
  notifications = [],
  onMarkNotificationAsRead = null,
  onClearAllNotifications = null,
  onRefreshUser = null
}) {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    first_name_th: '',
    last_name_th: '',
    email: '',
    phone: '',
    dob: '',
    gender: '',
    national_id: '',
    passport_no: '',
    passport_expiry: '',
    nationality: 'TH',
    address_line1: '',
    subDistrict: '', // ตำบล/แขวง
    district: '', // อำเภอ/เขต
    province: '', // จังหวัด
    postal_code: '', // รหัสไปรษณีย์
    country: 'TH', // ประเทศ (default: ประเทศไทย)
    profile_image: '',
    // Emergency Contact
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relation: '',
    emergency_contact_email: '',
    hotel_number_of_guests: 1,
  });

  const [errors, setErrors] = useState({});
  const dobPickerRef = useRef(null);
  const [dobDisplay, setDobDisplay] = useState(''); // แสดงในช่องวันเกิดเป็น dd/mm/yyyy
  const [isSaving, setIsSaving] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);
  const [hasVisa, setHasVisa] = useState(false); // State สำหรับตรวจสอบว่ามี visa หรือไม่
  const [hasPassport, setHasPassport] = useState(null); // true=มี, false=ไม่มี, null=ยังไม่เลือก
  // หนังสือเดินทางหลายเล่ม (Multi-Passport)
  const [passports, setPassports] = useState([]); // [{ id, passport_no, passport_type, ..., status, is_primary }, ...]
  const [editingPassportId, setEditingPassportId] = useState(null); // กำลังแก้ไขเล่มไหน (null = ไม่ได้แก้)
  const [passportForm, setPassportForm] = useState({ passport_no: '', passport_type: 'N', passport_issue_date: '', passport_expiry: '', passport_issuing_country: 'TH', nationality: 'TH', passport_given_names: '', passport_surname: '', place_of_birth: '', status: 'active', is_primary: false });
  const [passportFormErrors, setPassportFormErrors] = useState({});
  const [passportWarnings, setPassportWarnings] = useState([]); // จาก API
  // วีซ่าหลายประเทศ/หลายประเภท (Multi-Visa)
  const [visaRecords, setVisaRecords] = useState([]); // [{ id, country_code, visa_type, expiry_date, entries, linked_passport, ... }, ...]
  const [editingVisaId, setEditingVisaId] = useState(null); // null | 'new' | uuid
  const [visaForm, setVisaForm] = useState({ country_code: '', visa_type: 'B1/B2', visa_number: '', issue_date: '', expiry_date: '', entries: 'Multiple', purpose: 'T', linked_passport: '' });
  const [visaFormErrors, setVisaFormErrors] = useState({});
  const [visaWarnings, setVisaWarnings] = useState([]); // จาก API (linked_passport ไม่ตรงกับพาสปอร์ตปัจจุบัน)
  // ผู้จองร่วม (สมาชิกในครอบครัว) - ช่องกรอกละเอียดเท่าผู้จองหลัก
  const emptyFamilyForm = () => ({
    type: 'adult',
    first_name: '',
    last_name: '',
    first_name_th: '',
    last_name_th: '',
    date_of_birth: '',
    gender: '',
    national_id: '',
    has_passport: false, // true = มีหนังสือเดินทาง, false = ไม่มี
    passport_no: '',
    passport_expiry: '',
    passport_issue_date: '',
    passport_issuing_country: 'TH',
    passport_given_names: '',
    passport_surname: '',
    place_of_birth: '',
    passport_type: 'N',
    nationality: 'TH',
    passports: [], // หนังสือเดินทางหลายเล่ม (pattern เดียวกับผู้จองหลัก)
    visa_records: [], // วีซ่าหลายประเทศ (pattern เดียวกับผู้จองหลัก)
    // ที่อยู่: same_as_main = ตามผู้จองหลัก, own = กรอกเอง (default)
    address_option: 'own',
    address_line1: '',
    subDistrict: '',
    district: '',
    province: '',
    postal_code: '',
    country: 'TH',
  });
  const emptyPassportForm = () => ({ passport_no: '', passport_type: 'N', passport_issue_date: '', passport_expiry: '', passport_issuing_country: 'TH', nationality: 'TH', passport_given_names: '', passport_surname: '', place_of_birth: '', status: 'active', is_primary: false });
  const emptyVisaForm = () => ({ country_code: '', visa_type: 'B1/B2', visa_number: '', issue_date: '', expiry_date: '', entries: 'Multiple', purpose: 'T', linked_passport: '' });
  const [family, setFamily] = useState([]);
  const [editingFamilyId, setEditingFamilyId] = useState(null);
  const [familyForm, setFamilyForm] = useState(emptyFamilyForm());
  const [familyFormErrors, setFamilyFormErrors] = useState({});
  // ผู้จองร่วม: หนังสือเดินทางหลายเล่ม + วีซ่าหลายประเทศ (pattern เดียวกับผู้จองหลัก)
  const [editingFamilyPassportId, setEditingFamilyPassportId] = useState(null); // null | 'new' | id
  const [familyPassportForm, setFamilyPassportForm] = useState(emptyPassportForm());
  const [familyPassportFormErrors, setFamilyPassportFormErrors] = useState({});
  const [editingFamilyVisaId, setEditingFamilyVisaId] = useState(null); // null | 'new' | id
  const [familyVisaForm, setFamilyVisaForm] = useState(emptyVisaForm());
  const [familyVisaFormErrors, setFamilyVisaFormErrors] = useState({});
  const [newMemberIds, setNewMemberIds] = useState(new Set()); // id ของสมาชิกที่เพิ่มใหม่ (ยังไม่อยู่บน server)
  const [familySaving, setFamilySaving] = useState(false); // กำลัง save/delete family
  const [activeSection, setActiveSection] = useState('personal');
  const [showDeletePopup, setShowDeletePopup] = useState(false);

  // บัตรเครดิต/เดบิต (saved cards)
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  const [savedCards, setSavedCards] = useState([]);
  const [primaryCardId, setPrimaryCardId] = useState(null);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [cardsError, setCardsError] = useState(null);
  const [deletingCardId, setDeletingCardId] = useState(null);
  const [settingPrimaryId, setSettingPrimaryId] = useState(null);

  // ✅ Fetch latest user data from backend when component mounts or user changes
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
        const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
          credentials: 'include',
        });
        
        if (res.ok) {
          const data = await res.json();
          if (data.user) {
            // ✅ Update user data from backend (more complete than localStorage)
            const updatedUser = data.user;
            
            // ✅ Update form data with fresh data from backend
            const fullName = (updatedUser.name || updatedUser.full_name || '').trim();
            const parts = fullName.split(/\s+/).filter(Boolean);
            const first_name = parts[0] || '';
            const last_name = parts.slice(1).join(' ') || '';

            const profileImage = updatedUser.profile_image || updatedUser.picture || '';
            setFormData({
              first_name: updatedUser.first_name || first_name,
              last_name: updatedUser.last_name || last_name,
              first_name_th: updatedUser.first_name_th || '',
              last_name_th: updatedUser.last_name_th || '',
              email: updatedUser.email || '',
              phone: updatedUser.phone || '',
              dob: updatedUser.dob || '',
              gender: updatedUser.gender || '',
              national_id: updatedUser.national_id || '',
              passport_no: updatedUser.passport_no || '',
              passport_expiry: updatedUser.passport_expiry || '',
              passport_issue_date: updatedUser.passport_issue_date || '',
              passport_issuing_country: updatedUser.passport_issuing_country || 'TH',
              passport_given_names: updatedUser.passport_given_names || '',
              passport_surname: updatedUser.passport_surname || '',
              place_of_birth: updatedUser.place_of_birth || '',
              passport_type: updatedUser.passport_type || 'N',
              nationality: updatedUser.nationality || 'TH',
              visa_type: updatedUser.visa_type || '',
              visa_number: updatedUser.visa_number || '',
              visa_issuing_country: updatedUser.visa_issuing_country || '',
              visa_issue_date: updatedUser.visa_issue_date || '',
              visa_expiry_date: updatedUser.visa_expiry_date || '',
              visa_entry_type: updatedUser.visa_entry_type || 'S',
              visa_purpose: updatedUser.visa_purpose || 'T',
              address_line1: updatedUser.address_line1 || '',
              city: updatedUser.city || '',
              subDistrict: updatedUser.subDistrict || '',
              district: updatedUser.district || '',
              province: updatedUser.province || '',
              postal_code: updatedUser.postal_code || '',
              country: updatedUser.country || 'TH',
              profile_image: profileImage,
              emergency_contact_name: updatedUser.emergency_contact_name || '',
              emergency_contact_phone: updatedUser.emergency_contact_phone || '',
              emergency_contact_relation: updatedUser.emergency_contact_relation || '',
              emergency_contact_email: updatedUser.emergency_contact_email || '',
              hotel_number_of_guests: updatedUser.hotel_number_of_guests || 1,
            });
            setDobDisplay(formatYyyyMmDdToDdMmYyyy(updatedUser.dob || ''));
            
            // ตรวจสอบว่ามี visa หรือไม่
            const hasVisaData = !!(updatedUser.visa_type || updatedUser.visa_number);
            setHasVisa(hasVisaData);
            // หนังสือเดินทางหลายเล่ม: ใช้ passports จาก API (backend ส่งมาแล้ว หรือแปลงจาก legacy)
            const passportsList = Array.isArray(updatedUser.passports) ? updatedUser.passports : [];
            setPassports(passportsList);
            setPassportWarnings(Array.isArray(updatedUser.passport_warnings) ? updatedUser.passport_warnings : []);
            const hasPassportData = passportsList.length > 0 || !!(updatedUser.passport_no || updatedUser.passport_expiry);
            setHasPassport(hasPassportData ? true : null);
            // วีซ่าหลายประเทศ
            const visaList = Array.isArray(updatedUser.visa_records) ? updatedUser.visa_records : [];
            setVisaRecords(visaList);
            setVisaWarnings(Array.isArray(updatedUser.visa_warnings) ? updatedUser.visa_warnings : []);
            setHasVisa(visaList.length > 0 || !!(updatedUser.visa_type || updatedUser.visa_number));
            
            // ✅ Update localStorage with fresh data
            localStorage.setItem("user_data", JSON.stringify(updatedUser));
            
            console.log('✅ Fetched and updated user data from backend');
          }
        } else {
          console.warn('⚠️ Failed to fetch user data from backend:', res.status);
        }
      } catch (error) {
        console.error('❌ Error fetching user data:', error);
      }
    };
    
    // ✅ Always fetch fresh data from backend when component mounts
    fetchUserData();
  }, [onRefreshUser]); // ✅ Re-run if onRefreshUser changes

  // โหลดรายการบัตรเมื่อเปิดหมวดบัตรเครดิต/เดบิต
  useEffect(() => {
    const uid = user?.user_id || user?.id;
    if (activeSection !== 'cards' || !uid) return;
    setCardsLoading(true);
    setCardsError(null);
    const headers = { 'X-User-ID': uid };
    fetch(`${API_BASE_URL}/api/booking/saved-cards`, { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('โหลดบัตรไม่สำเร็จ'))))
      .then((data) => {
        if (data.ok && Array.isArray(data.cards)) setSavedCards(data.cards);
        if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
      })
      .catch((err) => setCardsError(err.message || 'โหลดบัตรไม่สำเร็จ'))
      .finally(() => setCardsLoading(false));
  }, [activeSection, user?.user_id, user?.id]);

  // แสดง popup กรอกข้อมูลบัตร (ไม่โหลด Omise)
  const handleClickAddCard = () => {
    const currentTheme = typeof theme !== 'undefined' ? theme : 'light';
    Swal.fire({
      title: '💳 เพิ่มบัตรใหม่',
      customClass: { popup: `add-card-popup add-card-popup--${currentTheme}` },
      html: `
        <div style="text-align: left;">
          <div class="add-card-field">
            <label class="add-card-label" for="swal-card-number">หมายเลขบัตร</label>
            <input id="swal-card-number" type="text" class="add-card-input" placeholder="1234 5678 9012 3456" maxlength="19" />
            <div id="swal-card-type-display" class="add-card-type-display" aria-live="polite"></div>
          </div>
          <div class="add-card-field">
            <label class="add-card-label" for="swal-card-name">ชื่อบนบัตร</label>
            <input id="swal-card-name" type="text" class="add-card-input" placeholder="ชื่อ-นามสกุล" />
          </div>
          <div class="add-card-row">
            <div class="add-card-field">
              <label class="add-card-label" for="swal-card-expiry">หมดอายุ (MM/YY)</label>
              <input id="swal-card-expiry" type="text" class="add-card-input" placeholder="MM/YY" maxlength="5" />
            </div>
            <div class="add-card-field">
              <label class="add-card-label" for="swal-card-cvv">CVV</label>
              <input id="swal-card-cvv" type="text" class="add-card-input" placeholder="123" maxlength="4" />
            </div>
          </div>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: 'บันทึก',
      cancelButtonText: 'ยกเลิก',
      width: 440,
      didOpen: () => {
        const container = document.querySelector('.swal2-container');
        if (container) container.setAttribute('data-theme', currentTheme);
        const input = document.getElementById('swal-card-number');
        const display = document.getElementById('swal-card-type-display');
        if (!input || !display) return;
        const logos = {
          visa: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" fill="#fff" rx="2"/><text x="28" y="16" text-anchor="middle" fill="#1A1F71" font-size="12" font-weight="700" font-family="Arial,sans-serif">VISA</text></svg>',
          mastercard: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="12" r="8" fill="#EB001B"/><circle cx="36" cy="12" r="8" fill="#F79E1B"/><path fill="#E85A00" fill-opacity="0.9" d="M28 4a8 8 0 0 1 0 16 8 8 0 0 1 0-16z"/></svg>',
          amex: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#006FCF"/><text x="28" y="9.5" text-anchor="middle" fill="#fff" font-size="5" font-weight="700" font-family="Arial,sans-serif">AMERICAN</text><text x="28" y="17.5" text-anchor="middle" fill="#fff" font-size="5" font-weight="700" font-family="Arial,sans-serif">EXPRESS</text></svg>',
          jcb: '<img src="/images/jcb-logo.png" alt="JCB" class="card-logo-img" width="48" height="22" />',
          discover: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#FF6000"/><text x="28" y="15.5" text-anchor="middle" fill="#fff" font-size="7" font-weight="700" font-family="Arial,sans-serif">Discover</text></svg>',
          diners: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#0079BE"/><text x="28" y="15.5" text-anchor="middle" fill="#fff" font-size="6" font-weight="700" font-family="Arial,sans-serif">Diners Club</text></svg>',
          unionpay: '<img src="/images/unionpay-logo.png" alt="UnionPay" class="card-logo-img" width="48" height="22" />'
        };
        const update = () => {
          const raw = input.value.replace(/\D/g, '');
          input.value = formatCardNumber(input.value);
          input.classList.remove('card-visa', 'card-mastercard', 'card-amex', 'card-jcb', 'card-discover', 'card-diners', 'card-unionpay');
          if (raw.length >= 2) {
            const cardType = getCardType(input.value);
            let html = '';
            if (cardType && logos[cardType]) {
              html = '<span class="card-logo-wrap">' + logos[cardType] + '</span>';
              input.classList.add('card-' + cardType);
            }
            display.innerHTML = html;
            display.className = 'add-card-type-display ' + (cardType ? 'visible' : '');
            if (raw.length >= 13) {
              const v = validateCardNumber(input.value);
              const statusSpan = v.valid ? '<span class="card-logo-valid">✓ ถูกต้อง</span>' : '<span class="card-logo-invalid">' + (v.message || 'ไม่ถูกต้อง') + '</span>';
              display.innerHTML = (cardType && logos[cardType] ? '<span class="card-logo-wrap">' + logos[cardType] + '</span>' : '') + statusSpan;
              display.className = 'add-card-type-display visible ' + (v.valid ? 'valid' : 'invalid');
            }
          } else {
            display.innerHTML = '';
            display.className = 'add-card-type-display';
          }
        };
        input.addEventListener('input', update);
        input.addEventListener('paste', () => setTimeout(update, 0));

        const expiryInput = document.getElementById('swal-card-expiry');
        if (expiryInput) {
          const formatExpiry = (val) => {
            const c = (val || '').replace(/\D/g, '');
            if (c.length >= 2) return c.substring(0, 2) + '/' + c.substring(2, 4);
            return c;
          };
          expiryInput.addEventListener('input', (e) => {
            e.target.value = formatExpiry(e.target.value);
            e.target.setSelectionRange(e.target.value.length, e.target.value.length);
          });
          expiryInput.addEventListener('paste', () => setTimeout(() => { expiryInput.value = formatExpiry(expiryInput.value); }, 0));
        }
      },
      preConfirm: () => {
        const cardNumber = (document.getElementById('swal-card-number')?.value || '').replace(/\s/g, '');
        const cardName = (document.getElementById('swal-card-name')?.value || '').trim();
        const cardExpiry = (document.getElementById('swal-card-expiry')?.value || '').trim();
        const cardCvv = (document.getElementById('swal-card-cvv')?.value || '').replace(/\s/g, '');

        if (!cardNumber) {
          Swal.showValidationMessage('กรุณากรอกหมายเลขบัตร');
          return false;
        }
        if (cardNumber.length < 13) {
          Swal.showValidationMessage('กรุณากรอกหมายเลขบัตรอย่างน้อย 13 หลัก');
          return false;
        }
        const v = validateCardNumber(document.getElementById('swal-card-number')?.value);
        if (!v.valid) {
          Swal.showValidationMessage(v.message || 'เลขบัตรไม่ถูกต้อง');
          return false;
        }

        if (!cardName || cardName.length < 2) {
          Swal.showValidationMessage('กรุณากรอกชื่อบนบัตร (อย่างน้อย 2 ตัวอักษร)');
          return false;
        }

        const parts = cardExpiry.split('/').map((p) => p.trim());
        if (parts.length !== 2 || parts[0].length !== 2 || parts[1].length !== 2) {
          Swal.showValidationMessage('กรุณากรอกวันหมดอายุรูปแบบ MM/YY');
          return false;
        }
        const mm = parseInt(parts[0], 10);
        const yy = parseInt(parts[1], 10);
        if (mm < 1 || mm > 12) {
          Swal.showValidationMessage('เดือนต้องอยู่ระหว่าง 01-12');
          return false;
        }
        const now = new Date();
        const fullYear = 2000 + yy;
        const expDate = new Date(fullYear, mm, 0);
        if (expDate < now) {
          Swal.showValidationMessage('บัตรหมดอายุแล้ว');
          return false;
        }

        if (!cardCvv || !/^\d{3,4}$/.test(cardCvv)) {
          Swal.showValidationMessage('กรุณากรอก CVV ให้ถูกต้อง (3-4 หลัก)');
          return false;
        }

        return { cardNumber, cardName, cardExpiry, cardCvv };
      }
    }).then(async (result) => {
      if (result.isConfirmed && result.value) {
        const { cardNumber, cardName, cardExpiry, cardCvv } = result.value;
        const [mm, yy] = cardExpiry.split('/').map((p) => p.trim());
        const num = cardNumber.replace(/\s/g, '');
        try {
          await loadOmiseScript(API_BASE_URL);
          if (!window.Omise) throw new Error('โหลดระบบบัตรไม่สำเร็จ');
          const configRes = await fetch(`${API_BASE_URL}/api/booking/payment-config`, { credentials: 'include' });
          const configData = configRes.ok ? await configRes.json() : {};
          const pubKey = configData.public_key;
          if (!pubKey) throw new Error('ไม่พบ Omise Public Key');
          window.Omise.setPublicKey(pubKey);
          const card = {
            name: cardName,
            number: num,
            expiration_month: mm,
            expiration_year: '20' + yy,
            security_code: cardCvv,
          };
          const tokenResponse = await createTokenAsync(card);
          const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-User-ID': user?.user_id || user?.id || '' },
            credentials: 'include',
            body: JSON.stringify({ token: tokenResponse.id, email: (user?.email || '').trim() || undefined, name: cardName || undefined })
          });
          const data = await res.json();
          if (data.ok) {
            setSavedCards(data.cards || []);
            if (data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
            Swal.fire({ icon: 'success', title: 'บันทึกสำเร็จ', text: 'บัตรของคุณถูกบันทึกแล้ว', confirmButtonText: 'ตกลง' });
          } else {
            throw new Error(data.detail || data.message || 'บันทึกไม่สำเร็จ');
          }
        } catch (err) {
          Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message || 'บันทึกบัตรไม่สำเร็จ', confirmButtonText: 'ตกลง' });
        }
      }
    });
  };

  // Initialize form with user data (fallback to prop if backend fetch fails)
  useEffect(() => {
    if (user) {
      setDobDisplay(formatYyyyMmDdToDdMmYyyy(user.dob || ''));
      const fullName = (user.name || user.full_name || '').trim();
      const parts = fullName.split(/\s+/).filter(Boolean);
      const first_name = parts[0] || '';
      const last_name = parts.slice(1).join(' ') || '';

      const profileImage = user.profile_image || user.picture || '';
      
      // ✅ Only update if formData is still empty (fallback)
      setFormData(prev => {
        // ✅ Only update empty fields (don't overwrite if already set from backend fetch)
        if (prev.first_name && prev.last_name && prev.email) {
          return prev; // Already populated from backend
        }
        
        return {
          first_name: user.first_name || first_name,
          last_name: user.last_name || last_name,
          first_name_th: user.first_name_th || '',
          last_name_th: user.last_name_th || '',
          email: user.email || '',
          phone: user.phone || '',
          dob: user.dob || '',
          gender: user.gender || '',
          national_id: user.national_id || '',
          passport_no: user.passport_no || '',
          passport_expiry: user.passport_expiry || '',
          passport_issue_date: user.passport_issue_date || '',
          passport_issuing_country: user.passport_issuing_country || 'TH',
          passport_given_names: user.passport_given_names || '',
          passport_surname: user.passport_surname || '',
          place_of_birth: user.place_of_birth || '',
          passport_type: user.passport_type || 'N',
          nationality: user.nationality || 'TH',
          visa_type: user.visa_type || '',
          visa_number: user.visa_number || '',
          visa_issuing_country: user.visa_issuing_country || '',
          visa_issue_date: user.visa_issue_date || '',
          visa_expiry_date: user.visa_expiry_date || '',
          visa_entry_type: user.visa_entry_type || 'S',
          visa_purpose: user.visa_purpose || 'T',
          address_line1: user.address_line1 || '',
          city: user.city || '',
          subDistrict: user.subDistrict || '',
          district: user.district || '',
          province: user.province || '',
          postal_code: user.postal_code || '',
          country: user.country || 'TH',
          profile_image: profileImage,
          // Hotel Booking Preferences
          emergency_contact_name: user.emergency_contact_name || '',
          emergency_contact_phone: user.emergency_contact_phone || '',
          emergency_contact_relation: user.emergency_contact_relation || '',
          emergency_contact_email: user.emergency_contact_email || '',
          hotel_early_checkin: user.hotel_early_checkin || false,
          hotel_late_checkout: user.hotel_late_checkout || false,
          hotel_smoking_preference: user.hotel_smoking_preference || '',
          hotel_room_type_preference: user.hotel_room_type_preference || '',
          hotel_floor_preference: user.hotel_floor_preference || '',
          hotel_view_preference: user.hotel_view_preference || '',
          hotel_extra_bed: user.hotel_extra_bed || false,
          hotel_airport_transfer: user.hotel_airport_transfer || false,
          hotel_dietary_requirements: user.hotel_dietary_requirements || '',
          hotel_special_occasion: user.hotel_special_occasion || '',
          hotel_accessibility_needs: user.hotel_accessibility_needs || false,
          hotel_arrival_time: user.hotel_arrival_time || '',
          hotel_arrival_flight: user.hotel_arrival_flight || '',
          hotel_departure_time: user.hotel_departure_time || '',
          hotel_number_of_guests: user.hotel_number_of_guests || 1,
          payment_method: user.payment_method || '',
          card_holder_name: user.card_holder_name || '',
          card_last_4_digits: user.card_last_4_digits || '',
          company_name: user.company_name || '',
          tax_id: user.tax_id || '',
          invoice_address: user.invoice_address || '',
          hotel_loyalty_number: user.hotel_loyalty_number || '',
          airline_frequent_flyer: user.airline_frequent_flyer || '',
          hotel_booking_notes: user.hotel_booking_notes || '',
        };
      });
      
      // วีซ่าหลายประเทศ: ใช้ visa_records จาก API
      const visaList = Array.isArray(user.visa_records) ? user.visa_records : [];
      setVisaRecords(visaList);
      setVisaWarnings(Array.isArray(user.visa_warnings) ? user.visa_warnings : []);
      const hasVisaData = visaList.length > 0 || !!(user.visa_type || user.visa_number);
      setHasVisa(hasVisaData);
      setFamily(Array.isArray(user.family) ? user.family : []);
      
      // Set preview image
      setPreviewImage(profileImage);
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  // Handler สำหรับ checkbox มี Visa / ไม่มี Visa
  const handleHasVisaChange = (e) => {
    const checked = e.target.checked;
    setHasVisa(checked);
    
    // ถ้าเลือก "ไม่มี Visa" ให้เคลียร์ข้อมูล visa ทั้งหมด
    if (!checked) {
      setFormData(prev => ({
        ...prev,
        visa_type: '',
        visa_number: '',
        visa_issuing_country: '',
        visa_issue_date: '',
        visa_expiry_date: '',
        visa_entry_type: 'S',
        visa_purpose: 'T',
      }));
      // เคลียร์ errors ที่เกี่ยวข้อง
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.visa_type;
        delete newErrors.visa_number;
        delete newErrors.visa_issuing_country;
        delete newErrors.visa_issue_date;
        delete newErrors.visa_expiry_date;
        return newErrors;
      });
    }
  };

  // Handler สำหรับปุ่ม มี / ไม่มี passport
  const handleHasPassportChange = (value) => {
    setHasPassport(value);
    if (value === false) {
      setPassports([]);
      setEditingPassportId(null);
      setPassportForm({ passport_no: '', passport_type: 'N', passport_issue_date: '', passport_expiry: '', passport_issuing_country: 'TH', nationality: 'TH', passport_given_names: '', passport_surname: '', place_of_birth: '', status: 'active', is_primary: false });
      setFormData(prev => ({
        ...prev,
        passport_no: '',
        passport_expiry: '',
        passport_issue_date: '',
        passport_issuing_country: 'TH',
        passport_given_names: '',
        passport_surname: '',
        place_of_birth: '',
        passport_type: 'N',
      }));
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.passport_no;
        delete newErrors.passport_expiry;
        delete newErrors.passport_issue_date;
        delete newErrors.passport_issuing_country;
        delete newErrors.passport_given_names;
        delete newErrors.passport_surname;
        delete newErrors.place_of_birth;
        return newErrors;
      });
    }
  };

  const makePassportId = () => (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `pp_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`);

  const validatePassportForm = (p) => {
    const err = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // เลขหนังสือเดินทาง (บังคับ)
    if (!p.passport_no || !p.passport_no.trim()) {
      err.passport_no = 'กรุณากรอกเลขหนังสือเดินทาง';
    } else {
      const no = p.passport_no.trim();
      if (no.length < 6) err.passport_no = 'เลขหนังสือเดินทางต้องมีอย่างน้อย 6 ตัวอักษร';
      else if (no.length > 20) err.passport_no = 'เลขหนังสือเดินทางต้องไม่เกิน 20 ตัวอักษร';
      else if (!/^[A-Z0-9]+$/i.test(no)) err.passport_no = 'เลขหนังสือเดินทางต้องเป็นตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น';
    }

    // วันออก (ถ้ากรอก ต้องรูปแบบถูก และไม่ใช่วันในอนาคต)
    if (p.passport_issue_date && p.passport_issue_date.trim()) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(p.passport_issue_date.trim())) {
        err.passport_issue_date = 'รูปแบบวันออกไม่ถูกต้อง (YYYY-MM-DD)';
      } else {
        const issue = new Date(p.passport_issue_date);
        if (isNaN(issue.getTime())) err.passport_issue_date = 'วันออกไม่ถูกต้อง';
        else if (issue > today) err.passport_issue_date = 'วันออกไม่สามารถเป็นวันในอนาคตได้';
      }
    }

    // วันหมดอายุ (บังคับเมื่อมีเลขหนังสือเดินทาง)
    if (p.passport_no && p.passport_no.trim()) {
      if (!p.passport_expiry || !p.passport_expiry.trim()) {
        err.passport_expiry = 'กรุณากรอกวันหมดอายุ';
      } else {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(p.passport_expiry.trim())) {
          err.passport_expiry = 'รูปแบบวันหมดอายุไม่ถูกต้อง (YYYY-MM-DD)';
        } else {
          const expiry = new Date(p.passport_expiry);
          if (isNaN(expiry.getTime())) {
            err.passport_expiry = 'วันหมดอายุไม่ถูกต้อง';
          } else {
            if (expiry < today) err.passport_expiry = 'หนังสือเดินทางหมดอายุแล้ว กรุณาเตรียมต่ออายุ';
            else if (p.passport_issue_date && p.passport_issue_date.trim()) {
              const issue = new Date(p.passport_issue_date);
              if (!isNaN(issue.getTime()) && expiry <= issue) err.passport_expiry = 'วันหมดอายุต้องหลังวันออกหนังสือเดินทาง';
              else if (!isNaN(issue.getTime())) {
                const yearsDiff = (expiry - issue) / (1000 * 60 * 60 * 24 * 365);
                if (yearsDiff > 15) err.passport_expiry = 'หนังสือเดินทางไม่ควรมีอายุมากกว่า 15 ปี';
              }
            }
          }
        }
      }
    } else if (p.passport_expiry && p.passport_expiry.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(p.passport_expiry.trim())) {
      err.passport_expiry = 'รูปแบบวันหมดอายุไม่ถูกต้อง (YYYY-MM-DD)';
    }

    // ชื่อตามหนังสือเดินทาง (อังกฤษ) — บังคับเมื่อมีเลขพาสปอร์ต
    if (p.passport_no && p.passport_no.trim()) {
      if (!p.passport_given_names || !p.passport_given_names.trim()) {
        err.passport_given_names = 'กรุณากรอกชื่อตามหนังสือเดินทาง (อังกฤษ)';
      } else {
        const name = p.passport_given_names.trim();
        if (!/^[A-Za-z\s\-'\.]+$/.test(name)) err.passport_given_names = 'ชื่อต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
        else if (name.length < 2) err.passport_given_names = 'ชื่อต้องมีอย่างน้อย 2 ตัวอักษร';
        else if (name.length > 100) err.passport_given_names = 'ชื่อต้องไม่เกิน 100 ตัวอักษร';
      }
    }

    // นามสกุลตามหนังสือเดินทาง (อังกฤษ) — บังคับเมื่อมีเลขพาสปอร์ต
    if (p.passport_no && p.passport_no.trim()) {
      if (!p.passport_surname || !p.passport_surname.trim()) {
        err.passport_surname = 'กรุณากรอกนามสกุลตามหนังสือเดินทาง (อังกฤษ)';
      } else {
        const name = p.passport_surname.trim();
        if (!/^[A-Za-z\s\-'\.]+$/.test(name)) err.passport_surname = 'นามสกุลต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
        else if (name.length < 2) err.passport_surname = 'นามสกุลต้องมีอย่างน้อย 2 ตัวอักษร';
        else if (name.length > 100) err.passport_surname = 'นามสกุลต้องไม่เกิน 100 ตัวอักษร';
      }
    }

    // สถานที่เกิด (ถ้ากรอก จำกัดความยาว)
    if (p.place_of_birth && p.place_of_birth.trim() && p.place_of_birth.trim().length > 150) {
      err.place_of_birth = 'สถานที่เกิดต้องไม่เกิน 150 ตัวอักษร';
    }

    // ประเภท — ต้องเป็น N, O, D, S
    if (p.passport_type && !['N', 'O', 'D', 'S'].includes(p.passport_type)) {
      err.passport_type = 'ประเภทหนังสือเดินทางไม่ถูกต้อง';
    }

    return err;
  };

  const addPassport = () => {
    setPassportFormErrors({});
    setPassportForm(emptyPassportForm());
    setEditingPassportId('new');
  };

  const startEditPassport = (entry) => {
    setPassportFormErrors({});
    setPassportForm({
      passport_no: entry.passport_no || '',
      passport_type: entry.passport_type || 'N',
      passport_issue_date: entry.passport_issue_date || '',
      passport_expiry: entry.passport_expiry || '',
      passport_issuing_country: entry.passport_issuing_country || 'TH',
      nationality: entry.nationality || 'TH',
      passport_given_names: entry.passport_given_names || '',
      passport_surname: entry.passport_surname || '',
      place_of_birth: entry.place_of_birth || '',
      status: entry.status || 'active',
      is_primary: !!entry.is_primary,
    });
    setEditingPassportId(entry.id);
  };

  const savePassportEdit = () => {
    const err = validatePassportForm(passportForm);
    if (Object.keys(err).length > 0) {
      setPassportFormErrors(err);
      return;
    }
    setPassportFormErrors({});
    const entry = {
      id: editingPassportId === 'new' ? makePassportId() : editingPassportId,
      ...passportForm,
      is_primary: passportForm.is_primary || (passports.length === 0 && editingPassportId === 'new'),
    };
    if (editingPassportId === 'new') {
      setPassports(prev => {
        const next = prev.map(p => ({ ...p, is_primary: false }));
        next.push(entry);
        return next;
      });
    } else {
      setPassports(prev => prev.map(p => p.id === editingPassportId ? { ...p, ...entry } : (entry.is_primary ? { ...p, is_primary: false } : p)));
    }
    setEditingPassportId(null);
    setPassportForm(emptyPassportForm());
  };

  const cancelPassportEdit = () => {
    setEditingPassportId(null);
    setPassportForm(emptyPassportForm());
    setPassportFormErrors({});
  };

  const setPrimaryPassport = (id) => {
    setPassports(prev => prev.map(p => ({ ...p, is_primary: p.id === id })));
  };

  const deletePassport = (id) => {
    setPassports(prev => {
      const next = prev.filter(p => p.id !== id);
      const hadPrimary = prev.find(p => p.id === id)?.is_primary;
      if (hadPrimary && next.length > 0 && !next.some(p => p.is_primary)) next[0].is_primary = true;
      return next;
    });
    if (editingPassportId === id) cancelPassportEdit();
  };

  // ── วีซ่าหลายประเทศ (Multi-Visa) ─────────────────────────────────────────
  const makeVisaId = () => (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `visa_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`);

  const validateVisaForm = (f) => {
    const err = {};
    if (!(f.country_code || '').trim()) err.country_code = 'กรุณาเลือกประเทศปลายทาง/ประเทศที่ออกวีซ่า';
    if (!(f.expiry_date || '').trim()) err.expiry_date = 'กรุณากรอกวันหมดอายุวีซ่า';
    else if (!/^\d{4}-\d{2}-\d{2}$/.test(f.expiry_date.trim())) err.expiry_date = 'รูปแบบวันหมดอายุไม่ถูกต้อง (YYYY-MM-DD)';
    if (f.issue_date && f.issue_date.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(f.issue_date.trim())) err.issue_date = 'รูปแบบวันออกวีซ่าไม่ถูกต้อง (YYYY-MM-DD)';
    if (f.issue_date && f.expiry_date) {
      const issue = new Date(f.issue_date);
      const expiry = new Date(f.expiry_date);
      if (!isNaN(issue.getTime()) && !isNaN(expiry.getTime()) && expiry < issue) err.expiry_date = 'วันหมดอายุต้องไม่ก่อนวันออกวีซ่า';
    }
    if (f.visa_number && f.visa_number.trim()) {
      if (f.visa_number.trim().length < 5) err.visa_number = 'เลขที่วีซ่าต้องมีอย่างน้อย 5 ตัวอักษร';
      else if (f.visa_number.trim().length > 50) err.visa_number = 'เลขที่วีซ่าต้องไม่เกิน 50 ตัวอักษร';
      else if (!/^[A-Z0-9\-]+$/i.test(f.visa_number.trim())) err.visa_number = 'เลขที่วีซ่าต้องเป็นตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น';
    }
    return err;
  };

  const addVisa = () => {
    setVisaFormErrors({});
    setVisaForm(emptyVisaForm());
    setEditingVisaId('new');
  };

  const startEditVisa = (entry) => {
    setVisaFormErrors({});
    setVisaForm({
      country_code: entry.country_code || '',
      visa_type: entry.visa_type || 'B1/B2',
      visa_number: entry.visa_number || '',
      issue_date: entry.issue_date || '',
      expiry_date: entry.expiry_date || '',
      entries: (entry.entries || 'Multiple').trim() === 'Single' ? 'Single' : 'Multiple',
      purpose: entry.purpose || 'T',
      linked_passport: entry.linked_passport || '',
    });
    setEditingVisaId(entry.id);
  };

  const saveVisaEdit = () => {
    const err = validateVisaForm(visaForm);
    if (Object.keys(err).length > 0) {
      setVisaFormErrors(err);
      return;
    }
    setVisaFormErrors({});
    const entry = {
      id: editingVisaId === 'new' ? makeVisaId() : editingVisaId,
      country_code: (visaForm.country_code || '').trim(),
      visa_type: (visaForm.visa_type || 'B1/B2').trim(),
      visa_number: visaForm.visa_number ? visaForm.visa_number.trim() : null,
      issue_date: visaForm.issue_date ? visaForm.issue_date.trim() : null,
      expiry_date: (visaForm.expiry_date || '').trim(),
      entries: (visaForm.entries || 'Multiple').trim() === 'Single' ? 'Single' : 'Multiple',
      purpose: (visaForm.purpose || 'T').trim() || 'T',
      linked_passport: visaForm.linked_passport ? visaForm.linked_passport.trim() : null,
    };
    if (editingVisaId === 'new') {
      setVisaRecords(prev => [...prev, entry]);
    } else {
      setVisaRecords(prev => prev.map(v => v.id === editingVisaId ? { ...v, ...entry } : v));
    }
    setEditingVisaId(null);
    setVisaForm(emptyVisaForm());
  };

  const cancelVisaEdit = () => {
    setEditingVisaId(null);
    setVisaForm(emptyVisaForm());
    setVisaFormErrors({});
  };

  const deleteVisa = (id) => {
    setVisaRecords(prev => prev.filter(v => v.id !== id));
    if (editingVisaId === id) cancelVisaEdit();
  };

  // ── ผู้จองร่วม: หนังสือเดินทางหลายเล่ม + วีซ่า (pattern เดียวกับผู้จองหลัก) ─────
  const addFamilyPassport = () => {
    setFamilyPassportFormErrors({});
    setFamilyPassportForm(emptyPassportForm());
    setEditingFamilyPassportId('new');
  };
  const startEditFamilyPassport = (entry) => {
    setFamilyPassportFormErrors({});
    setFamilyPassportForm({
      passport_no: entry.passport_no || '',
      passport_type: entry.passport_type || 'N',
      passport_issue_date: entry.passport_issue_date || '',
      passport_expiry: entry.passport_expiry || '',
      passport_issuing_country: entry.passport_issuing_country || 'TH',
      nationality: entry.nationality || 'TH',
      passport_given_names: entry.passport_given_names || '',
      passport_surname: entry.passport_surname || '',
      place_of_birth: entry.place_of_birth || '',
      status: entry.status || 'active',
      is_primary: !!entry.is_primary,
    });
    setEditingFamilyPassportId(entry.id);
  };
  const saveFamilyPassportEdit = () => {
    const err = validatePassportForm(familyPassportForm);
    if (Object.keys(err).length > 0) {
      setFamilyPassportFormErrors(err);
      return;
    }
    setFamilyPassportFormErrors({});
    const list = familyForm.passports || [];
    const entry = {
      id: editingFamilyPassportId === 'new' ? makePassportId() : editingFamilyPassportId,
      ...familyPassportForm,
      is_primary: familyPassportForm.is_primary || (list.length === 0 && editingFamilyPassportId === 'new'),
    };
    if (editingFamilyPassportId === 'new') {
      setFamilyForm(f => ({ ...f, passports: [...(f.passports || []).map(p => ({ ...p, is_primary: false })), entry] }));
    } else {
      setFamilyForm(f => ({
        ...f,
        passports: (f.passports || []).map(p => p.id === editingFamilyPassportId ? { ...p, ...entry } : (entry.is_primary ? { ...p, is_primary: false } : p)),
      }));
    }
    setEditingFamilyPassportId(null);
    setFamilyPassportForm(emptyPassportForm());
  };
  const cancelFamilyPassportEdit = () => {
    setEditingFamilyPassportId(null);
    setFamilyPassportForm(emptyPassportForm());
    setFamilyPassportFormErrors({});
  };
  const deleteFamilyPassport = (id) => {
    setFamilyForm(f => {
      const next = (f.passports || []).filter(p => p.id !== id);
      const hadPrimary = (f.passports || []).find(p => p.id === id)?.is_primary;
      if (hadPrimary && next.length > 0 && !next.some(p => p.is_primary)) next[0] = { ...next[0], is_primary: true };
      return { ...f, passports: next };
    });
    if (editingFamilyPassportId === id) cancelFamilyPassportEdit();
  };
  const setPrimaryFamilyPassport = (id) => {
    setFamilyForm(f => ({ ...f, passports: (f.passports || []).map(p => ({ ...p, is_primary: p.id === id })) }));
  };

  const addFamilyVisa = () => {
    setFamilyVisaFormErrors({});
    setFamilyVisaForm(emptyVisaForm());
    setEditingFamilyVisaId('new');
  };
  const startEditFamilyVisa = (entry) => {
    setFamilyVisaFormErrors({});
    setFamilyVisaForm({
      country_code: entry.country_code || '',
      visa_type: entry.visa_type || 'B1/B2',
      visa_number: entry.visa_number || '',
      issue_date: entry.issue_date || '',
      expiry_date: entry.expiry_date || '',
      entries: (entry.entries || 'Multiple').trim() === 'Single' ? 'Single' : 'Multiple',
      purpose: entry.purpose || 'T',
      linked_passport: entry.linked_passport || '',
    });
    setEditingFamilyVisaId(entry.id);
  };
  const saveFamilyVisaEdit = () => {
    const err = validateVisaForm(familyVisaForm);
    if (Object.keys(err).length > 0) {
      setFamilyVisaFormErrors(err);
      return;
    }
    setFamilyVisaFormErrors({});
    const entry = {
      id: editingFamilyVisaId === 'new' ? makeVisaId() : editingFamilyVisaId,
      country_code: (familyVisaForm.country_code || '').trim(),
      visa_type: (familyVisaForm.visa_type || 'B1/B2').trim(),
      visa_number: familyVisaForm.visa_number ? familyVisaForm.visa_number.trim() : null,
      issue_date: familyVisaForm.issue_date ? familyVisaForm.issue_date.trim() : null,
      expiry_date: (familyVisaForm.expiry_date || '').trim(),
      entries: (familyVisaForm.entries || 'Multiple').trim() === 'Single' ? 'Single' : 'Multiple',
      purpose: (familyVisaForm.purpose || 'T').trim() || 'T',
      linked_passport: familyVisaForm.linked_passport ? familyVisaForm.linked_passport.trim() : null,
    };
    if (editingFamilyVisaId === 'new') {
      setFamilyForm(f => ({ ...f, visa_records: [...(f.visa_records || []), entry] }));
    } else {
      setFamilyForm(f => ({ ...f, visa_records: (f.visa_records || []).map(v => v.id === editingFamilyVisaId ? { ...v, ...entry } : v) }));
    }
    setEditingFamilyVisaId(null);
    setFamilyVisaForm(emptyVisaForm());
  };
  const cancelFamilyVisaEdit = () => {
    setEditingFamilyVisaId(null);
    setFamilyVisaForm(emptyVisaForm());
    setFamilyVisaFormErrors({});
  };
  const deleteFamilyVisa = (id) => {
    setFamilyForm(f => ({ ...f, visa_records: (f.visa_records || []).filter(v => v.id !== id) }));
    if (editingFamilyVisaId === id) cancelFamilyVisaEdit();
  };

  // ✅ Thai National ID Checksum Validation (Production-ready)
  const validateThaiNationalID = (id) => {
    if (!id || id.length !== 13) return false;
    if (!/^\d{13}$/.test(id)) return false;
    
    // Thai National ID checksum algorithm
    let sum = 0;
    for (let i = 0; i < 12; i++) {
      sum += parseInt(id[i]) * (13 - i);
    }
    const checkDigit = (11 - (sum % 11)) % 10;
    return checkDigit === parseInt(id[12]);
  };

  // ✅ Thai Name Validation (ภาษาไทยเท่านั้น)
  const validateThaiName = (name) => {
    if (!name) return true; // Optional field
    // Thai Unicode range: \u0E00-\u0E7F
    return /^[\u0E00-\u0E7F\s\-\.']+$/.test(name.trim());
  };

  // ✅ Email Validation (Enhanced)
  const validateEmail = (email) => {
    if (!email.trim()) return false;
    // RFC 5322 compliant regex (simplified but robust)
    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    return emailRegex.test(email.trim());
  };

  const validate = () => {
    const newErrors = {};

    // ✅ Required fields - First Name (English)
    if (!formData.first_name.trim()) {
      newErrors.first_name = 'กรุณากรอกชื่อ (ภาษาอังกฤษ)';
    } else if (!/^[A-Za-z\s\-'\.]+$/.test(formData.first_name.trim())) {
      newErrors.first_name = 'ชื่อต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
    } else if (formData.first_name.trim().length < 2) {
      newErrors.first_name = 'ชื่อต้องมีอย่างน้อย 2 ตัวอักษร';
    } else if (formData.first_name.trim().length > 50) {
      newErrors.first_name = 'ชื่อต้องไม่เกิน 50 ตัวอักษร';
    }

    // ✅ Required fields - Last Name (English)
    if (!formData.last_name.trim()) {
      newErrors.last_name = 'กรุณากรอกนามสกุล (ภาษาอังกฤษ)';
    } else if (!/^[A-Za-z\s\-'\.]+$/.test(formData.last_name.trim())) {
      newErrors.last_name = 'นามสกุลต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
    } else if (formData.last_name.trim().length < 2) {
      newErrors.last_name = 'นามสกุลต้องมีอย่างน้อย 2 ตัวอักษร';
    } else if (formData.last_name.trim().length > 50) {
      newErrors.last_name = 'นามสกุลต้องไม่เกิน 50 ตัวอักษร';
    }

    // ✅ Required - First Name (Thai)
    if (!formData.first_name_th || !formData.first_name_th.trim()) {
      newErrors.first_name_th = 'กรุณากรอกชื่อ (ภาษาไทย)';
    } else if (!validateThaiName(formData.first_name_th)) {
      newErrors.first_name_th = 'ชื่อต้องเป็นภาษาไทยเท่านั้น';
    } else if (formData.first_name_th.trim().length < 2) {
      newErrors.first_name_th = 'ชื่อต้องมีอย่างน้อย 2 ตัวอักษร';
    } else if (formData.first_name_th.trim().length > 50) {
      newErrors.first_name_th = 'ชื่อต้องไม่เกิน 50 ตัวอักษร';
    }

    // ✅ Required - Last Name (Thai)
    if (!formData.last_name_th || !formData.last_name_th.trim()) {
      newErrors.last_name_th = 'กรุณากรอกนามสกุล (ภาษาไทย)';
    } else if (!validateThaiName(formData.last_name_th)) {
      newErrors.last_name_th = 'นามสกุลต้องเป็นภาษาไทยเท่านั้น';
    } else if (formData.last_name_th.trim().length < 2) {
      newErrors.last_name_th = 'นามสกุลต้องมีอย่างน้อย 2 ตัวอักษร';
    } else if (formData.last_name_th.trim().length > 50) {
      newErrors.last_name_th = 'นามสกุลต้องไม่เกิน 50 ตัวอักษร';
    }

    // ✅ Email Validation (Enhanced)
    if (!formData.email.trim()) {
      newErrors.email = 'กรุณากรอกอีเมล';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'รูปแบบอีเมลไม่ถูกต้อง (เช่น example@email.com)';
    } else if (formData.email.trim().length > 100) {
      newErrors.email = 'อีเมลต้องไม่เกิน 100 ตัวอักษร';
    }

    // ✅ Phone Validation (Thai format: 9-10 digits)
    if (!formData.phone.trim()) {
      newErrors.phone = 'กรุณากรอกเบอร์โทรศัพท์';
    } else {
      const cleanedPhone = formData.phone.replace(/[-\s()]/g, '');
      if (!/^0[689]\d{8}$|^0[2-9]\d{7,8}$/.test(cleanedPhone)) {
        newErrors.phone = 'รูปแบบเบอร์โทรไม่ถูกต้อง (เช่น 0812345678 หรือ 021234567)';
      }
    }

    // ✅ Required - Date of Birth (formData.dob เก็บเป็น YYYY-MM-DD จาก parse dd/mm/yyyy)
    if (!formData.dob || !formData.dob.trim()) {
      newErrors.dob = 'กรุณากรอกวันเกิด';
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(formData.dob)) {
      newErrors.dob = 'รูปแบบวันเกิดไม่ถูกต้อง (dd/mm/yyyy)';
    } else {
      const birthDate = new Date(formData.dob);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      if (isNaN(birthDate.getTime())) {
        newErrors.dob = 'วันเกิดไม่ถูกต้อง';
      } else if (birthDate > today) {
        newErrors.dob = 'วันเกิดไม่สามารถเป็นวันอนาคตได้';
      } else {
        const age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        const actualAge = monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate()) ? age - 1 : age;
        
        if (actualAge > 120) {
          newErrors.dob = 'อายุไม่ถูกต้อง (เกิน 120 ปี)';
        }
      }
    }

    // ✅ Required - Gender
    if (!formData.gender || !formData.gender.trim()) {
      newErrors.gender = 'กรุณาเลือกเพศ';
    }

    // ✅ Required - Thai National ID (13 digits with checksum)
    if (!formData.national_id || !formData.national_id.trim()) {
      newErrors.national_id = 'กรุณากรอกเลขบัตรประจำตัวประชาชน';
    } else {
      const cleanedID = formData.national_id.replace(/[-\s]/g, '');
      if (cleanedID.length !== 13) {
        newErrors.national_id = 'เลขบัตรประชาชนต้องมี 13 หลัก';
      } else if (!/^\d{13}$/.test(cleanedID)) {
        newErrors.national_id = 'เลขบัตรประชาชนต้องเป็นตัวเลขเท่านั้น';
      } else if (!validateThaiNationalID(cleanedID)) {
        newErrors.national_id = 'เลขบัตรประชาชนไม่ถูกต้อง (checksum ไม่ผ่าน)';
      }
    }
    // ✅ Passport validation — ข้ามเมื่อใช้รายการหลายเล่ม (passports array)
    const hasPassportInfo = formData.passport_no || formData.passport_expiry;
    const useMultiPassport = hasPassport === true && passports.length > 0;
    
    if (!useMultiPassport && hasPassportInfo) {
      // Passport number validation
      if (formData.passport_no) {
        if (formData.passport_no.length < 6) {
          newErrors.passport_no = 'เลขหนังสือเดินทางต้องมีอย่างน้อย 6 ตัวอักษร';
        } else if (!/^[A-Z0-9]+$/i.test(formData.passport_no)) {
          newErrors.passport_no = 'เลขหนังสือเดินทางต้องเป็นตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น';
        }
      }
      
      // Date format validation
      if (formData.passport_expiry && !/^\d{4}-\d{2}-\d{2}$/.test(formData.passport_expiry)) {
        newErrors.passport_expiry = 'รูปแบบวันหมดอายุไม่ถูกต้อง (YYYY-MM-DD)';
      }
      if (formData.passport_issue_date && !/^\d{4}-\d{2}-\d{2}$/.test(formData.passport_issue_date)) {
        newErrors.passport_issue_date = 'รูปแบบวันออกหนังสือเดินทางไม่ถูกต้อง (YYYY-MM-DD)';
      }
      
      // Validate passport expiry is after issue date
      if (formData.passport_issue_date && formData.passport_expiry) {
        const issueDate = new Date(formData.passport_issue_date);
        const expiryDate = new Date(formData.passport_expiry);
        if (expiryDate <= issueDate) {
          newErrors.passport_expiry = 'วันหมดอายุต้องหลังวันออกหนังสือเดินทาง';
        }
        // Passport typically valid for 5-10 years, check reasonable range
        const yearsDiff = (expiryDate - issueDate) / (1000 * 60 * 60 * 24 * 365);
        if (yearsDiff > 15) {
          newErrors.passport_expiry = 'หนังสือเดินทางไม่ควรมีอายุมากกว่า 15 ปี';
        }
      }
      
      // Validate passport expiry is not in the past (allow 6 months grace period for renewal)
      if (formData.passport_expiry) {
        const expiryDate = new Date(formData.passport_expiry);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (expiryDate < today) {
          newErrors.passport_expiry = 'หนังสือเดินทางหมดอายุแล้ว กรุณาเตรียมต่ออายุ';
        } else {
          const sixMonthsFromNow = new Date();
          sixMonthsFromNow.setMonth(sixMonthsFromNow.getMonth() + 6);
          if (expiryDate < sixMonthsFromNow) {
            newErrors.passport_expiry = 'หนังสือเดินทางหมดอายุภายใน 6 เดือน กรุณาเตรียมต่ออายุ';
          }
        }
      }
      
      // Validate passport names (English) - required for international flights
      if (formData.passport_no && !formData.passport_given_names?.trim()) {
        newErrors.passport_given_names = 'กรุณากรอกชื่อตามหนังสือเดินทาง (ภาษาอังกฤษ)';
      } else if (formData.passport_given_names && !/^[A-Za-z\s\-'\.]+$/.test(formData.passport_given_names.trim())) {
        newErrors.passport_given_names = 'ชื่อตามหนังสือเดินทางต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
      }
      
      if (formData.passport_no && !formData.passport_surname?.trim()) {
        newErrors.passport_surname = 'กรุณากรอกนามสกุลตามหนังสือเดินทาง (ภาษาอังกฤษ)';
      } else if (formData.passport_surname && formData.passport_surname.trim()) {
        if (!/^[A-Za-z\s\-'\.]+$/.test(formData.passport_surname.trim())) {
          newErrors.passport_surname = 'นามสกุลตามหนังสือเดินทางต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
        } else if (formData.passport_surname.trim().length < 2) {
          newErrors.passport_surname = 'นามสกุลตามหนังสือเดินทางต้องมีอย่างน้อย 2 ตัวอักษร';
        } else if (formData.passport_surname.trim().length > 100) {
          newErrors.passport_surname = 'นามสกุลตามหนังสือเดินทางต้องไม่เกิน 100 ตัวอักษร';
        }
      }

      // ✅ Place of Birth Validation
      if (formData.place_of_birth && formData.place_of_birth.trim()) {
        if (formData.place_of_birth.trim().length > 100) {
          newErrors.place_of_birth = 'สถานที่เกิดต้องไม่เกิน 100 ตัวอักษร';
        }
      }
    }

    // ✅ Visa validation — ข้ามเมื่อใช้รายการหลายวีซ่า (visaRecords) เพราะ validate ในฟอร์มเพิ่ม/แก้ไขแล้ว
    if (visaRecords.length === 0) {
      if (formData.visa_number && formData.visa_number.trim()) {
        const cleanedVisaNumber = formData.visa_number.trim();
        if (cleanedVisaNumber.length < 5) {
          newErrors.visa_number = 'เลขที่วีซ่าต้องมีอย่างน้อย 5 ตัวอักษร';
        } else if (cleanedVisaNumber.length > 50) {
          newErrors.visa_number = 'เลขที่วีซ่าต้องไม่เกิน 50 ตัวอักษร';
        } else if (!/^[A-Z0-9\-]+$/i.test(cleanedVisaNumber)) {
          newErrors.visa_number = 'เลขที่วีซ่าต้องเป็นตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น';
        }
      }
      if (formData.visa_expiry_date && !/^\d{4}-\d{2}-\d{2}$/.test(formData.visa_expiry_date)) {
        newErrors.visa_expiry_date = 'รูปแบบวันหมดอายุวีซ่าไม่ถูกต้อง (YYYY-MM-DD)';
      }
      if (formData.visa_issue_date && formData.visa_issue_date.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(formData.visa_issue_date)) {
        newErrors.visa_issue_date = 'รูปแบบวันออกวีซ่าไม่ถูกต้อง (YYYY-MM-DD)';
      }
      if (formData.visa_issue_date && formData.visa_expiry_date) {
        const issueDate = new Date(formData.visa_issue_date);
        const expiryDate = new Date(formData.visa_expiry_date);
        if (!isNaN(issueDate.getTime()) && !isNaN(expiryDate.getTime()) && expiryDate <= issueDate) {
          newErrors.visa_expiry_date = 'วันหมดอายุวีซ่าต้องหลังวันออกวีซ่า';
        }
      }
      if (formData.visa_expiry_date) {
        const expiryDate = new Date(formData.visa_expiry_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (!isNaN(expiryDate.getTime()) && expiryDate < today) {
          newErrors.visa_expiry_date = 'วีซ่าหมดอายุแล้ว กรุณาต่ออายุหรือกรอกวีซ่าใหม่';
        }
      }
    }

    // ✅ Address Validation
    if (formData.address_line1 && formData.address_line1.trim().length > 200) {
      newErrors.address_line1 = 'ที่อยู่บรรทัดที่ 1 ต้องไม่เกิน 200 ตัวอักษร';
    }

    // ✅ Location Validation (ตำบล, อำเภอ, จังหวัด)
    if (formData.subDistrict && formData.subDistrict.trim().length > 100) {
      newErrors.subDistrict = 'ตำบล/แขวงต้องไม่เกิน 100 ตัวอักษร';
    }
    if (formData.district && formData.district.trim().length > 100) {
      newErrors.district = 'อำเภอ/เขตต้องไม่เกิน 100 ตัวอักษร';
    }
    if (formData.province && formData.province.trim().length > 100) {
      newErrors.province = 'จังหวัดต้องไม่เกิน 100 ตัวอักษร';
    }

    // ✅ Postal Code Validation (Thai: 5 digits)
    if (formData.postal_code && formData.postal_code.trim()) {
      const cleanedPostalCode = formData.postal_code.replace(/[-\s]/g, '');
      if (formData.country === 'TH' && cleanedPostalCode.length !== 5) {
        newErrors.postal_code = 'รหัสไปรษณีย์ไทยต้องมี 5 หลัก';
      } else if (!/^\d+$/.test(cleanedPostalCode)) {
        newErrors.postal_code = 'รหัสไปรษณีย์ต้องเป็นตัวเลขเท่านั้น';
      } else if (cleanedPostalCode.length > 10) {
        newErrors.postal_code = 'รหัสไปรษณีย์ต้องไม่เกิน 10 หลัก';
      }
    }

    // ✅ Country Validation
    if (!formData.country) {
      newErrors.country = 'กรุณาเลือกประเทศ';
    }

    // ✅ Hotel Booking Preferences Validation
    // Emergency Contact Email
    if (formData.emergency_contact_email && formData.emergency_contact_email.trim()) {
      if (!validateEmail(formData.emergency_contact_email)) {
        newErrors.emergency_contact_email = 'รูปแบบอีเมลไม่ถูกต้อง';
      }
    }

    // Hotel Number of Guests
    if (formData.hotel_number_of_guests && (formData.hotel_number_of_guests < 1 || formData.hotel_number_of_guests > 20)) {
      newErrors.hotel_number_of_guests = 'จำนวนผู้เข้าพักต้องอยู่ระหว่าง 1-20 คน';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /** ตรวจสอบเฉพาะที่อยู่ + ติดต่อฉุกเฉิน — ใช้เมื่อบันทึกจากหมวด "ที่อยู่" โดยไม่บังคับข้อมูลส่วนตัว */
  const validateAddressAndEmergency = () => {
    const newErrors = {};
    if (formData.address_line1 && formData.address_line1.trim().length > 200) {
      newErrors.address_line1 = 'ที่อยู่บรรทัดที่ 1 ต้องไม่เกิน 200 ตัวอักษร';
    }
    if (formData.subDistrict && formData.subDistrict.trim().length > 100) newErrors.subDistrict = 'ตำบล/แขวงต้องไม่เกิน 100 ตัวอักษร';
    if (formData.district && formData.district.trim().length > 100) newErrors.district = 'อำเภอ/เขตต้องไม่เกิน 100 ตัวอักษร';
    if (formData.province && formData.province.trim().length > 100) newErrors.province = 'จังหวัดต้องไม่เกิน 100 ตัวอักษร';
    if (formData.postal_code && formData.postal_code.trim()) {
      const cleaned = formData.postal_code.replace(/[-\s]/g, '');
      if (formData.country === 'TH' && cleaned.length !== 5) newErrors.postal_code = 'รหัสไปรษณีย์ไทยต้องมี 5 หลัก';
      else if (!/^\d+$/.test(cleaned)) newErrors.postal_code = 'รหัสไปรษณีย์ต้องเป็นตัวเลขเท่านั้น';
      else if (cleaned.length > 10) newErrors.postal_code = 'รหัสไปรษณีย์ต้องไม่เกิน 10 หลัก';
    }
    if (!formData.country) newErrors.country = 'กรุณาเลือกประเทศ';
    if (formData.emergency_contact_email && formData.emergency_contact_email.trim() && !validateEmail(formData.emergency_contact_email)) {
      newErrors.emergency_contact_email = 'รูปแบบอีเมลไม่ถูกต้อง';
    }
    if (formData.hotel_number_of_guests && (formData.hotel_number_of_guests < 1 || formData.hotel_number_of_guests > 20)) {
      newErrors.hotel_number_of_guests = 'จำนวนผู้เข้าพักต้องอยู่ระหว่าง 1-20 คน';
    }
    setErrors(prev => ({ ...prev, ...newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const handleOpenDeletePopup = () => {
    setShowDeletePopup(true);
  };

  const handleCloseDeletePopup = () => {
    setShowDeletePopup(false);
  };

  const fetchSavedCards = () => {
    const uid = user?.user_id || user?.id;
    if (!uid) return;
    setCardsLoading(true);
    setCardsError(null);
    const headers = { 'X-User-ID': uid };
    fetch(`${API_BASE_URL}/api/booking/saved-cards`, { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('โหลดบัตรไม่สำเร็จ'))))
      .then((data) => {
        if (data.ok && Array.isArray(data.cards)) setSavedCards(data.cards);
        if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
      })
      .catch((err) => setCardsError(err.message || 'โหลดบัตรไม่สำเร็จ'))
      .finally(() => setCardsLoading(false));
  };

  const handleSetPrimaryCard = async (cardId) => {
    if (!user?.id || !cardId) return;
    setSettingPrimaryId(cardId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards/${encodeURIComponent(cardId)}/set-primary`, {
        method: 'PUT',
        headers: { 'X-User-ID': user?.user_id || user?.id },
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ตั้งบัตรหลักไม่สำเร็จ');
      if (data.ok) setPrimaryCardId(cardId);
    } catch (err) {
      setCardsError(err.message || 'ตั้งบัตรหลักไม่สำเร็จ');
    } finally {
      setSettingPrimaryId(null);
    }
  };

  const handleDeleteCard = async (cardId) => {
    if (!user?.id || !cardId) return;
    setDeletingCardId(cardId);
    try {
      const headers = { 'X-User-ID': user?.user_id || user?.id };
      const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards/${encodeURIComponent(cardId)}`, {
        method: 'DELETE',
        headers,
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ลบบัตรไม่สำเร็จ');
      if (data.ok && data.cards) setSavedCards(data.cards);
      if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
    } catch (err) {
      setCardsError(err.message || 'ลบบัตรไม่สำเร็จ');
    } finally {
      setDeletingCardId(null);
    }
  };

  // ผู้จองร่วม (Family) - เพิ่ม/แก้ไข/ลบ (ช่องกรอกละเอียดเท่าผู้จองหลัก)
  const makeId = () => (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `fm_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`);
  const addFamilyMember = (type) => {
    setFamilyFormErrors({});
    const base = emptyFamilyForm();
    const newMember = { id: makeId(), ...base, type };
    setFamily(prev => [...prev, newMember]);
    setNewMemberIds(prev => new Set(prev).add(newMember.id));
    setFamilyForm({ ...base, type });
    setEditingFamilyId(newMember.id);
  };
  const startEditFamily = (member) => {
    setFamilyFormErrors({});
    setEditingFamilyPassportId(null);
    setEditingFamilyVisaId(null);
    const memberPassports = Array.isArray(member.passports) ? member.passports : [];
    const memberVisaRecords = Array.isArray(member.visa_records) ? member.visa_records : [];
    const hasPassportLegacy = !!(member.passport_no && String(member.passport_no).trim());
    const hasPassport = member.has_passport !== undefined ? !!member.has_passport : (memberPassports.length > 0 || hasPassportLegacy);
    setFamilyForm({
      type: member.type || 'adult',
      first_name: member.first_name || '',
      last_name: member.last_name || '',
      first_name_th: member.first_name_th || '',
      last_name_th: member.last_name_th || '',
      date_of_birth: member.date_of_birth || '',
      gender: member.gender || '',
      national_id: member.national_id || '',
      has_passport: hasPassport,
      passport_no: member.passport_no || '',
      passport_expiry: member.passport_expiry || '',
      passport_issue_date: member.passport_issue_date || '',
      passport_issuing_country: member.passport_issuing_country || 'TH',
      passport_given_names: member.passport_given_names || '',
      passport_surname: member.passport_surname || '',
      place_of_birth: member.place_of_birth || '',
      passport_type: member.passport_type || 'N',
      nationality: member.nationality || 'TH',
      passports: memberPassports,
      visa_records: memberVisaRecords,
      address_option: member.address_option || 'own',
      address_line1: member.address_line1 || '',
      subDistrict: member.subDistrict || '',
      district: member.district || '',
      province: member.province || '',
      postal_code: member.postal_code || '',
      country: member.country || 'TH',
    });
    setEditingFamilyId(member.id);
  };

  const validateFamilyForm = (f) => {
    const err = {};
    if (!f.first_name || !f.first_name.trim()) {
      err.first_name = 'กรุณากรอกชื่อ (อังกฤษ)';
    } else if (!/^[A-Za-z\s\-'\.]+$/.test(f.first_name.trim())) {
      err.first_name = 'ชื่อต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
    } else if (f.first_name.trim().length < 2 || f.first_name.trim().length > 50) {
      err.first_name = 'ชื่อต้องมี 2–50 ตัวอักษร';
    }
    if (!f.last_name || !f.last_name.trim()) {
      err.last_name = 'กรุณากรอกนามสกุล (อังกฤษ)';
    } else if (!/^[A-Za-z\s\-'\.]+$/.test(f.last_name.trim())) {
      err.last_name = 'นามสกุลต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
    } else if (f.last_name.trim().length < 2 || f.last_name.trim().length > 50) {
      err.last_name = 'นามสกุลต้องมี 2–50 ตัวอักษร';
    }
    if (f.first_name_th && f.first_name_th.trim()) {
      if (!validateThaiName(f.first_name_th)) err.first_name_th = 'ชื่อต้องเป็นภาษาไทยเท่านั้น';
      else if (f.first_name_th.trim().length < 2 || f.first_name_th.trim().length > 50) err.first_name_th = 'ชื่อต้องมี 2–50 ตัวอักษร';
    }
    if (f.last_name_th && f.last_name_th.trim()) {
      if (!validateThaiName(f.last_name_th)) err.last_name_th = 'นามสกุลต้องเป็นภาษาไทยเท่านั้น';
      else if (f.last_name_th.trim().length < 2 || f.last_name_th.trim().length > 50) err.last_name_th = 'นามสกุลต้องมี 2–50 ตัวอักษร';
    }
    if (f.date_of_birth && f.date_of_birth.trim()) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date_of_birth.trim())) {
        err.date_of_birth = 'รูปแบบวันเกิดไม่ถูกต้อง (dd/mm/yyyy)';
      } else {
        const birth = new Date(f.date_of_birth);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (isNaN(birth.getTime())) err.date_of_birth = 'วันเกิดไม่ถูกต้อง';
        else if (birth > today) err.date_of_birth = 'วันเกิดไม่สามารถเป็นวันอนาคตได้';
        else {
          const age = today.getFullYear() - birth.getFullYear();
          if (age > 120) err.date_of_birth = 'อายุไม่ถูกต้อง (เกิน 120 ปี)';
        }
      }
    }
    if (f.national_id && f.national_id.trim()) {
      const cleaned = f.national_id.replace(/[-\s]/g, '');
      if (cleaned.length !== 13) err.national_id = 'เลขบัตรประชาชนต้องมี 13 หลัก';
      else if (!/^\d{13}$/.test(cleaned)) err.national_id = 'เลขบัตรประชาชนต้องเป็นตัวเลขเท่านั้น';
      else if (!validateThaiNationalID(cleaned)) err.national_id = 'เลขบัตรประชาชนไม่ถูกต้อง (checksum ไม่ผ่าน)';
    }
    // หนังสือเดินทาง (ผู้จองร่วม): เมื่อเลือก "มี" ต้องมีรายการอย่างน้อย 1 เล่ม (pattern เดียวกับผู้จองหลัก)
    const hasPassport = f.has_passport === true || (f.passport_no && f.passport_no.trim()) || (f.passports && f.passports.length > 0);
    if (hasPassport) {
      const list = f.passports || [];
      if (list.length === 0) {
        err.passports = 'กรุณาเพิ่มหนังสือเดินทางอย่างน้อย 1 เล่ม หรือกด "บันทึก" ที่ฟอร์มเพิ่มหนังสือเดินทาง';
      }
    }
    // ที่อยู่ (เมื่อเลือกกรอกเอง): รหัสไปรษณีย์ไทย 5 หลัก
    if (f.address_option === 'own' && f.postal_code && f.postal_code.trim() && (f.country === 'TH' || !f.country)) {
      const pc = f.postal_code.replace(/[-\s]/g, '');
      if (pc.length !== 5 || !/^\d{5}$/.test(pc)) {
        err.postal_code = 'รหัสไปรษณีย์ไทยต้องเป็นตัวเลข 5 หลัก';
      }
    }
    return err;
  };

  /** ตรวจสอบรายการผู้จองร่วมทั้งหมดก่อนบันทึกโปรไฟล์ */
  const validateFamilyList = (list) => {
    for (let i = 0; i < list.length; i++) {
      const member = list[i];
      const err = validateFamilyForm(member);
      if (Object.keys(err).length > 0) {
        const firstError = Object.values(err)[0];
        return { valid: false, index: i, message: firstError, errors: err };
      }
    }
    return { valid: true };
  };

  const saveFamilyEdit = async () => {
    if (!editingFamilyId) return;
    const err = validateFamilyForm(familyForm);
    if (Object.keys(err).length > 0) {
      setFamilyFormErrors(err);
      return;
    }
    setFamilyFormErrors({});
    const isNew = newMemberIds.has(editingFamilyId);
    const payload = { ...familyForm, id: editingFamilyId };
    setFamilySaving(true);
    try {
      const url = `${API_BASE_URL}/api/auth/family${isNew ? '' : `/${editingFamilyId}`}`;
      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data?.ok) throw new Error(data?.detail || 'บันทึกไม่สำเร็จ');
      setFamily(data.family || []);
      if (isNew) setNewMemberIds(prev => { const s = new Set(prev); s.delete(editingFamilyId); return s; });
      setEditingFamilyId(null);
      setFamilyForm(emptyFamilyForm());
      setEditingFamilyPassportId(null);
      setEditingFamilyVisaId(null);
      if (onRefreshUser) onRefreshUser();
    } catch (e) {
      console.error('Error saving family member:', e);
      setFamilyFormErrors({ _form: e.message || 'บันทึกไม่สำเร็จ' });
      Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: e.message || 'บันทึกไม่สำเร็จ', confirmButtonText: 'ตกลง' });
    } finally {
      setFamilySaving(false);
    }
  };
  const cancelFamilyEdit = () => {
    setFamilyFormErrors({});
    setEditingFamilyPassportId(null);
    setEditingFamilyVisaId(null);
    const id = editingFamilyId;
    setEditingFamilyId(null);
    if (id) {
      const member = family.find(m => m.id === id);
      if (member && !member.first_name && !member.last_name) {
        setFamily(prev => prev.filter(m => m.id !== id));
        setNewMemberIds(prev => { const s = new Set(prev); s.delete(id); return s; });
      }
    }
    setFamilyForm(emptyFamilyForm());
  };
  const deleteFamilyMember = async (id) => {
    const isNew = newMemberIds.has(id);
    if (isNew) {
      setFamily(prev => prev.filter(m => m.id !== id));
      setNewMemberIds(prev => { const s = new Set(prev); s.delete(id); return s; });
      if (editingFamilyId === id) { setEditingFamilyId(null); setFamilyForm(emptyFamilyForm()); }
      return;
    }
    setFamilySaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/family/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      const data = await res.json();
      if (!data?.ok) throw new Error(data?.detail || 'ลบไม่สำเร็จ');
      setFamily(data.family || []);
      if (editingFamilyId === id) { setEditingFamilyId(null); setFamilyForm(emptyFamilyForm()); }
      if (onRefreshUser) onRefreshUser();
    } catch (e) {
      console.error('Error deleting family member:', e);
      Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: e.message || 'ลบไม่สำเร็จ', confirmButtonText: 'ตกลง' });
    } finally {
      setFamilySaving(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // เมื่ออยู่หมวด "ที่อยู่และติดต่อฉุกเฉิน" ให้บันทึกเฉพาะที่อยู่ + ติดต่อฉุกเฉินได้ โดยไม่บังคับข้อมูลส่วนตัว
    if (activeSection === 'address_emergency') {
      if (!validateAddressAndEmergency()) return;
      setIsSaving(true);
      try {
        const payload = {
          address_line1: formData.address_line1 || '',
          subDistrict: formData.subDistrict || '',
          district: formData.district || '',
          province: formData.province || '',
          postal_code: formData.postal_code || '',
          country: formData.country || 'TH',
          emergency_contact_name: formData.emergency_contact_name || '',
          emergency_contact_phone: formData.emergency_contact_phone || '',
          emergency_contact_relation: formData.emergency_contact_relation || '',
          emergency_contact_email: formData.emergency_contact_email || '',
          hotel_number_of_guests: formData.hotel_number_of_guests ?? 1,
        };
        await onSave(payload);
        await Swal.fire({ icon: 'success', title: 'บันทึกสำเร็จ', text: 'บันทึกที่อยู่และติดต่อฉุกเฉินเรียบร้อยแล้ว', confirmButtonText: 'ตกลง' });
      } catch (error) {
        console.error('Error saving address:', error);
        await Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: 'เกิดข้อผิดพลาดในการบันทึก: ' + (error.message || 'Unknown error'), confirmButtonText: 'ตกลง' });
      } finally {
        setIsSaving(false);
      }
      return;
    }

    if (!validate()) {
      return;
    }

    if (hasPassport === true && passports.length === 0) {
      setActiveSection('passport');
      Swal.fire({ icon: 'warning', title: 'กรุณาเพิ่มหนังสือเดินทาง', text: 'คุณเลือก "มี" แต่ยังไม่ได้เพิ่มเล่มใด — กรุณากด "เพิ่มหนังสือเดินทางอีกเล่ม" แล้วกรอกข้อมูล หรือเปลี่ยนเป็น "ไม่มี"', confirmButtonText: 'ตกลง' });
      return;
    }

    // ตรวจสอบข้อมูลผู้จองร่วมทุกคนก่อนบันทึก
    if (family.length > 0) {
      const familyCheck = validateFamilyList(family);
      if (!familyCheck.valid) {
        setActiveSection('family');
        const name = family[familyCheck.index]?.first_name || family[familyCheck.index]?.first_name_th || `รายการที่ ${familyCheck.index + 1}`;
        Swal.fire({
          icon: 'warning',
          title: 'ข้อมูลไม่ครบ',
          text: `ข้อมูลผู้จองร่วมไม่ครบหรือไม่ถูกต้อง (${name}): ${familyCheck.message}\nกรุณากด "แก้ไข" ที่รายการนั้นแล้วกรอกให้ถูกต้อง`,
          confirmButtonText: 'ตกลง'
        });
        return;
      }
    }

    // ถ้ากำลังแก้ไขผู้จองร่วมแต่ยังไม่กดบันทึกใน card นั้น → แจ้งให้บันทึกรายการนั้นก่อน
    if (editingFamilyId) {
      const err = validateFamilyForm(familyForm);
      if (Object.keys(err).length > 0) {
        setFamilyFormErrors(err);
        setActiveSection('family');
        Swal.fire({
          icon: 'warning',
          title: 'กรุณากรอกข้อมูลให้ครบ',
          text: 'กรุณากรอกข้อมูลผู้จองร่วมให้ครบและถูกต้อง แล้วกด "บันทึก" ที่รายการที่กำลังแก้ไขก่อน',
          confirmButtonText: 'ตกลง'
        });
        return;
      }
    }
    
    // ถ้ากำลังแก้ไขวีซ่าแต่ยังไม่กดบันทึก → แจ้งให้บันทึกรายการนั้นก่อน
    if (editingVisaId) {
      const visaErr = validateVisaForm(visaForm);
      if (Object.keys(visaErr).length > 0) {
        setVisaFormErrors(visaErr);
        setActiveSection('visa');
        Swal.fire({
          icon: 'warning',
          title: 'กรุณากรอกข้อมูลวีซ่าให้ครบ',
          text: 'กรุณากรอกข้อมูลวีซ่าให้ครบและถูกต้อง แล้วกด "บันทึก" ที่รายการที่กำลังแก้ไขก่อน',
          confirmButtonText: 'ตกลง',
        });
        return;
      }
    }

    setIsSaving(true);
    try {
      const payload = { ...formData };
      if (hasPassport === true && passports.length > 0) payload.passports = passports;
      payload.visa_records = visaRecords; // ส่งรายการวีซ่าทุกครั้ง (backend จะแทนที่)
      await onSave(payload); // family แยก API; passports ส่งเป็น array เมื่อมีหลายเล่ม
      await Swal.fire({
        icon: 'success',
        title: 'บันทึกสำเร็จ',
        text: 'บันทึกข้อมูลเรียบร้อยแล้ว',
        confirmButtonText: 'ตกลง'
      });
    } catch (error) {
      console.error('Error saving profile:', error);
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: 'เกิดข้อผิดพลาดในการบันทึกข้อมูล: ' + (error.message || 'Unknown error'),
        confirmButtonText: 'ตกลง'
      });
    } finally {
      setIsSaving(false);
    }
  };

  // ✅ Production-ready: Comprehensive country list (ISO 3166-1 Alpha-2)
  const countries = [
    { code: 'TH', name: 'ไทย (Thailand)' },
    { code: 'US', name: 'สหรัฐอเมริกา (United States)' },
    { code: 'GB', name: 'สหราชอาณาจักร (United Kingdom)' },
    { code: 'CA', name: 'แคนาดา (Canada)' },
    { code: 'AU', name: 'ออสเตรเลีย (Australia)' },
    { code: 'NZ', name: 'นิวซีแลนด์ (New Zealand)' },
    { code: 'JP', name: 'ญี่ปุ่น (Japan)' },
    { code: 'KR', name: 'เกาหลีใต้ (South Korea)' },
    { code: 'CN', name: 'จีน (China)' },
    { code: 'HK', name: 'ฮ่องกง (Hong Kong)' },
    { code: 'TW', name: 'ไต้หวัน (Taiwan)' },
    { code: 'SG', name: 'สิงคโปร์ (Singapore)' },
    { code: 'MY', name: 'มาเลเซีย (Malaysia)' },
    { code: 'ID', name: 'อินโดนีเซีย (Indonesia)' },
    { code: 'VN', name: 'เวียดนาม (Vietnam)' },
    { code: 'PH', name: 'ฟิลิปปินส์ (Philippines)' },
    { code: 'MM', name: 'พม่า (Myanmar)' },
    { code: 'KH', name: 'กัมพูชา (Cambodia)' },
    { code: 'LA', name: 'ลาว (Laos)' },
    { code: 'BN', name: 'บรูไน (Brunei)' },
    { code: 'IN', name: 'อินเดีย (India)' },
    { code: 'PK', name: 'ปากีสถาน (Pakistan)' },
    { code: 'BD', name: 'บังกลาเทศ (Bangladesh)' },
    { code: 'LK', name: 'ศรีลังกา (Sri Lanka)' },
    { code: 'DE', name: 'เยอรมนี (Germany)' },
    { code: 'FR', name: 'ฝรั่งเศส (France)' },
    { code: 'IT', name: 'อิตาลี (Italy)' },
    { code: 'ES', name: 'สเปน (Spain)' },
    { code: 'NL', name: 'เนเธอร์แลนด์ (Netherlands)' },
    { code: 'BE', name: 'เบลเยียม (Belgium)' },
    { code: 'CH', name: 'สวิตเซอร์แลนด์ (Switzerland)' },
    { code: 'AT', name: 'ออสเตรีย (Austria)' },
    { code: 'SE', name: 'สวีเดน (Sweden)' },
    { code: 'NO', name: 'นอร์เวย์ (Norway)' },
    { code: 'DK', name: 'เดนมาร์ก (Denmark)' },
    { code: 'FI', name: 'ฟินแลนด์ (Finland)' },
    { code: 'IE', name: 'ไอร์แลนด์ (Ireland)' },
    { code: 'PT', name: 'โปรตุเกส (Portugal)' },
    { code: 'GR', name: 'กรีซ (Greece)' },
    { code: 'TR', name: 'ตุรกี (Turkey)' },
    { code: 'RU', name: 'รัสเซีย (Russia)' },
    { code: 'PL', name: 'โปแลนด์ (Poland)' },
    { code: 'CZ', name: 'สาธารณรัฐเช็ก (Czech Republic)' },
    { code: 'HU', name: 'ฮังการี (Hungary)' },
    { code: 'RO', name: 'โรมาเนีย (Romania)' },
    { code: 'AE', name: 'สหรัฐอาหรับเอมิเรตส์ (United Arab Emirates)' },
    { code: 'SA', name: 'ซาอุดีอาระเบีย (Saudi Arabia)' },
    { code: 'QA', name: 'กาตาร์ (Qatar)' },
    { code: 'KW', name: 'คูเวต (Kuwait)' },
    { code: 'BH', name: 'บาห์เรน (Bahrain)' },
    { code: 'OM', name: 'โอมาน (Oman)' },
    { code: 'IL', name: 'อิสราเอล (Israel)' },
    { code: 'EG', name: 'อียิปต์ (Egypt)' },
    { code: 'ZA', name: 'แอฟริกาใต้ (South Africa)' },
    { code: 'KE', name: 'เคนยา (Kenya)' },
    { code: 'MA', name: 'โมร็อกโก (Morocco)' },
    { code: 'BR', name: 'บราซิล (Brazil)' },
    { code: 'MX', name: 'เม็กซิโก (Mexico)' },
    { code: 'AR', name: 'อาร์เจนตินา (Argentina)' },
    { code: 'CL', name: 'ชิลี (Chile)' },
    { code: 'CO', name: 'โคลอมเบีย (Colombia)' },
    { code: 'PE', name: 'เปรู (Peru)' },
  ];


  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

  const PROFILE_SECTIONS = [
    { id: 'personal', name: t('profile.personalInfo'), icon: '👤' },
    { id: 'passport', name: t('profile.passportInfo'), icon: '🛂' },
    { id: 'visa', name: t('profile.visaInfo'), icon: '🛂' },
    { id: 'address_emergency', name: t('profile.addressEmergency'), icon: '📍' },
    { id: 'family', name: t('profile.coTravelers'), icon: '👨‍👩‍👧‍👦' },
    { id: 'cards', name: t('profile.cards'), icon: '💳' },
  ];

  return (
    <div className="profile-edit-wrapper settings-page">
      {onNavigateToHome && (
        <AppHeader
          activeTab="profile"
          user={user}
          onNavigateToHome={onNavigateToHome}
          onNavigateToBookings={onNavigateToBookings}
          onNavigateToAI={onNavigateToAI}
          onNavigateToFlights={onNavigateToFlights}
          onNavigateToHotels={onNavigateToHotels}
          onNavigateToCarRentals={onNavigateToCarRentals}
          onLogout={onLogout}
          onNavigateToProfile={onNavigateToProfile}
          onNavigateToSettings={onNavigateToSettings}
          notificationCount={notificationCount}
          notifications={notifications}
          onMarkNotificationAsRead={onMarkNotificationAsRead}
          onClearAllNotifications={onClearAllNotifications}
        />
      )}

      <div className="settings-content-area" data-theme={theme} data-font-size={fontSize}>
      <div className="settings-container">
        <aside className="settings-sidebar">
          <h2>แก้ไขโปรไฟล์</h2>
          <nav className="settings-nav">
            {PROFILE_SECTIONS.map((section) => (
              <button
                key={section.id}
                type="button"
                className={`settings-nav-item ${activeSection === section.id ? 'active' : ''}`}
                onClick={() => setActiveSection(section.id)}
              >
                <span className="settings-nav-icon">{section.icon}</span>
                <span>{section.name}</span>
              </button>
            ))}
          </nav>
        </aside>

        <div className="settings-content">
          <div className="profile-edit-content-header">
            <button type="button" onClick={onCancel} className="btn-secondary" style={{ marginBottom: '20px' }}>
              {t('profile.back')}
            </button>
          </div>

          {/* บัตรเครดิต/เดบิต — เพิ่มหรือลบบัตรสำหรับชำระเงินในระบบ */}
          {activeSection === 'cards' && (
            <div className="settings-section settings-section-cards">
              <h3>บัตรเครดิต/เดบิต</h3>
              <p className="settings-cards-desc">จัดการบัตรสำหรับใช้ชำระเงินในระบบ — เพิ่มหรือลบบัตรได้ที่นี่</p>

              {cardsLoading && <p className="settings-cards-loading">กำลังโหลดรายการบัตร...</p>}
              {cardsError && (
                <div className="settings-cards-error">
                  <span>{cardsError}</span>
                  <button type="button" className="btn-secondary" onClick={fetchSavedCards}>โหลดใหม่</button>
                </div>
              )}

              {!cardsLoading && savedCards.length > 0 && (
                <div className="settings-cards-list">
                  <h4>บัตรที่บันทึกไว้</h4>
                  <ul className="settings-cards-grid">
                    {savedCards.map((c) => {
                      const brandKey = (c.brand || 'card').toLowerCase().replace(/\s+/g, '');
                      const cardClass = ['visa','mastercard','amex','americanexpress','jcb','discover','diners','unionpay'].includes(brandKey)
                        ? `settings-card-visual card-${brandKey.replace('americanexpress','amex')}`
                        : 'settings-card-visual card-default';
                      return (
                        <li key={c.card_id || c.id} className="settings-card-item">
                          <div className={`${cardClass} ${primaryCardId === (c.card_id || c.id) ? 'settings-card-primary' : ''}`}>
                            <div className="settings-card-visual-top">
                              {primaryCardId === (c.card_id || c.id) && (
                                <span className="settings-card-primary-badge">บัตรหลัก</span>
                              )}
                            </div>
                            <div className="settings-card-visual-mid">
                              <span className="settings-card-visual-number">•••• •••• •••• {c.last4 || '****'}</span>
                              <span className="settings-card-visual-name">{c.name || '—'}</span>
                            </div>
                            <div className="settings-card-visual-bottom">
                              <span className="settings-card-visual-expiry">หมดอายุ {c.expiry_month || '**'}/{c.expiry_year || '**'}</span>
                              <span className="settings-card-visual-logo"><CardBrandLogo brand={c.brand} /></span>
                            </div>
                          </div>
                          <div className="settings-card-actions">
                            {primaryCardId !== (c.card_id || c.id) && (
                              <button
                                type="button"
                                className="btn-secondary btn-set-primary-card"
                                onClick={() => handleSetPrimaryCard(c.card_id || c.id)}
                                disabled={settingPrimaryId === (c.card_id || c.id)}
                              >
                                {settingPrimaryId === (c.card_id || c.id) ? 'กำลังตั้ง...' : 'ตั้งเป็นหลัก'}
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn-secondary btn-delete-card"
                              onClick={() => {
                                Swal.fire({
                                  title: 'ยืนยันการลบ',
                                  text: 'ต้องการลบบัตรใช่หรือไม่',
                                  icon: 'warning',
                                  showCancelButton: true,
                                  confirmButtonColor: '#d33',
                                  cancelButtonColor: '#3085d6',
                                  confirmButtonText: 'ลบ',
                                  cancelButtonText: 'ยกเลิก',
                                }).then((result) => {
                                  if (result.isConfirmed) handleDeleteCard(c.card_id || c.id);
                                });
                              }}
                              disabled={deletingCardId === (c.card_id || c.id)}
                            >
                              {deletingCardId === (c.card_id || c.id) ? 'กำลังลบ...' : 'ลบ'}
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {!cardsLoading && (
                <div className="settings-cards-add">
                  <h4>เพิ่มบัตรใหม่</h4>
                  <button
                    type="button"
                    className="btn-primary btn-add-card"
                    onClick={handleClickAddCard}
                  >
                    เพิ่มบัตร
                  </button>
                </div>
              )}
            </div>
          )}

        {activeSection !== 'cards' && (
        <form onSubmit={handleSubmit} className="profile-edit-form">
          {/* ข้อมูลส่วนตัว: รูป + ข้อมูลพื้นฐาน + passport + visa */}
          {activeSection === 'personal' && (
          <>
          <div id="section-personal" className="form-section profile-image-section">
            <h3 className="form-section-title">📷 รูปโปรไฟล์</h3>
            <div className="profile-image-container">
              <div className="profile-image-wrapper">
                {previewImage ? (
                  <img 
                    src={previewImage} 
                    alt="Profile" 
                    className="profile-image-preview"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      const placeholder = e.target.nextElementSibling;
                      if (placeholder) {
                        placeholder.style.display = 'flex';
                      }
                    }}
                  />
                ) : null}
                <div className="profile-image-placeholder" style={{ display: previewImage ? 'none' : 'flex' }}>
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="48" height="48">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <div className="profile-image-actions">
                <label htmlFor="profile-image-upload" className="btn-upload-image">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="18" height="18">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {previewImage ? 'เปลี่ยนรูป' : 'เลือกรูป'}
                </label>
                <input
                  type="file"
                  id="profile-image-upload"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      // Validate file size (max 5MB)
                      if (file.size > 5 * 1024 * 1024) {
                        alert('ขนาดไฟล์ต้องไม่เกิน 5MB');
                        return;
                      }
                      // Validate file type
                      if (!file.type.startsWith('image/')) {
                        alert('กรุณาเลือกไฟล์รูปภาพเท่านั้น');
                        return;
                      }
                      
                      // Read file as base64 data URL
                      const reader = new FileReader();
                      reader.onloadend = () => {
                        const base64String = reader.result;
                        setPreviewImage(base64String);
                        setFormData(prev => ({ ...prev, profile_image: base64String }));
                      };
                      reader.readAsDataURL(file);
                    }
                  }}
                />
                {previewImage && (
                  <button
                    type="button"
                    className="btn-delete-image"
                    onClick={() => {
                      setPreviewImage(null);
                      setFormData(prev => ({ ...prev, profile_image: '' }));
                      // Reset file input
                      const fileInput = document.getElementById('profile-image-upload');
                      if (fileInput) {
                        fileInput.value = '';
                      }
                    }}
                  >
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="18" height="18">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    ลบรูป
                  </button>
                )}
              </div>
              <p className="profile-image-hint">รองรับไฟล์ JPG, PNG, GIF ขนาดไม่เกิน 5MB</p>
            </div>
          </div>

          {/* ข้อมูลพื้นฐาน */}
          <div className="form-section">
            <h3 className="form-section-title">📋 ข้อมูลพื้นฐาน</h3>
            {/* ชื่อ-นามสกุล (ภาษาอังกฤษ) */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="first_name" className="form-label">
                  ชื่อ (ภาษาอังกฤษ) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  className={`form-input ${errors.first_name ? 'error' : ''}`}
                  placeholder="First Name"
                />
                {errors.first_name && <span className="error-message">{errors.first_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="last_name" className="form-label">
                  นามสกุล (ภาษาอังกฤษ) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  className={`form-input ${errors.last_name ? 'error' : ''}`}
                  placeholder="Last Name"
                />
                {errors.last_name && <span className="error-message">{errors.last_name}</span>}
              </div>
            </div>

            {/* ชื่อ-นามสกุล (ภาษาไทย) */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="first_name_th" className="form-label">
                  ชื่อ (ภาษาไทย) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="first_name_th"
                  name="first_name_th"
                  value={formData.first_name_th}
                  onChange={handleChange}
                  className={`form-input ${errors.first_name_th ? 'error' : ''}`}
                  placeholder="ชื่อภาษาไทย"
                />
                {errors.first_name_th && <span className="error-message">{errors.first_name_th}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="last_name_th" className="form-label">
                  นามสกุล (ภาษาไทย) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="last_name_th"
                  name="last_name_th"
                  value={formData.last_name_th}
                  onChange={handleChange}
                  className={`form-input ${errors.last_name_th ? 'error' : ''}`}
                  placeholder="นามสกุลภาษาไทย"
                />
                {errors.last_name_th && <span className="error-message">{errors.last_name_th}</span>}
              </div>
            </div>

            {/* บัตรประชาชน (National ID) */}
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label htmlFor="national_id" className="form-label">เลขบัตรประจำตัวประชาชน <span className="required">*</span></label>
              <input
                type="text"
                id="national_id"
                name="national_id"
                value={formData.national_id}
                onChange={handleChange}
                className={`form-input ${errors.national_id ? 'error' : ''}`}
                placeholder="1xxxxxxxxxxxx"
                maxLength="13"
              />
              {errors.national_id && <span className="error-message">{errors.national_id}</span>}
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
                  readOnly
                  disabled
                  className={`form-input ${errors.email ? 'error' : ''}`}
                  placeholder="example@email.com"
                  style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
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
                  readOnly
                  disabled
                  className={`form-input ${errors.phone ? 'error' : ''}`}
                  placeholder="0812345678"
                  style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
                />
                {errors.phone && <span className="error-message">{errors.phone}</span>}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="dob" className="form-label">วันเกิด <span className="required">*</span></label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    type="text"
                    id="dob"
                    name="dob"
                    placeholder="dd/mm/yyyy"
                    value={dobDisplay}
                    onChange={(e) => {
                      const formatted = formatDobInputWithSlashes(e.target.value);
                      setDobDisplay(formatted);
                      const parsed = parseDdMmYyyyToYyyyMmDd(formatted);
                      setFormData(prev => ({ ...prev, dob: parsed }));
                      if (parsed) {
                        const today = new Date(); today.setHours(0, 0, 0, 0);
                        if (new Date(parsed) > today) setErrors(prev => ({ ...prev, dob: 'วันเกิดไม่สามารถเป็นวันอนาคตได้' }));
                        else setErrors(prev => { const next = { ...prev }; delete next.dob; return next; });
                      }
                    }}
                    className={`form-input ${errors.dob ? 'error' : ''}`}
                    style={{ flex: 1 }}
                  />
                  <input
                    ref={dobPickerRef}
                    type="date"
                    aria-hidden="true"
                    tabIndex={-1}
                    max={(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d.toISOString().slice(0, 10); })()}
                    value={formData.dob || ''}
                    onChange={(e) => {
                      const val = e.target.value || '';
                      setFormData(prev => ({ ...prev, dob: val }));
                      setDobDisplay(formatYyyyMmDdToDdMmYyyy(val));
                      if (val) {
                        const today = new Date(); today.setHours(0, 0, 0, 0);
                        if (new Date(val) > today) setErrors(prev => ({ ...prev, dob: 'วันเกิดไม่สามารถเป็นวันอนาคตได้' }));
                        else setErrors(prev => { const next = { ...prev }; delete next.dob; return next; });
                      }
                    }}
                    style={{ position: 'absolute', opacity: 0, width: 0, height: 0, pointerEvents: 'none' }}
                  />
                  <button
                    type="button"
                    title="เลือกวันที่"
                    onClick={() => dobPickerRef.current?.showPicker?.() || dobPickerRef.current?.click?.()}
                    style={{ marginLeft: 8, padding: '8px 10px', background: '#f0f0f0', border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer' }}
                    tabIndex={0}
                  >
                    📅
                  </button>
                </div>
                {errors.dob && <span className="error-message">{errors.dob}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="gender" className="form-label">เพศ <span className="required">*</span></label>
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

          </>
          )}

          {/* ข้อมูลหนังสือเดินทาง - หมวดแยก */}
          {activeSection === 'passport' && (
          <div id="section-passport" className="form-section">
            <h3 className="form-section-title">🛂 ข้อมูลหนังสือเดินทาง (สำหรับเที่ยวบินระหว่างประเทศ)</h3>
            
            {/* ปุ่ม มี / ไม่มี passport */}
            <div className="form-group" style={{ marginBottom: '20px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => handleHasPassportChange(true)}
                  className={`passport-toggle-btn ${hasPassport === true ? 'active' : ''}`}
                  style={{
                    padding: '10px 24px',
                    borderRadius: '8px',
                    border: `2px solid ${hasPassport === true ? '#2563eb' : '#e2e8f0'}`,
                    background: hasPassport === true ? '#2563eb' : '#fff',
                    color: hasPassport === true ? '#fff' : '#64748b',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  มี
                </button>
                <button
                  type="button"
                  onClick={() => handleHasPassportChange(false)}
                  className={`passport-toggle-btn ${hasPassport === false ? 'active' : ''}`}
                  style={{
                    padding: '10px 24px',
                    borderRadius: '8px',
                    border: `2px solid ${hasPassport === false ? '#2563eb' : '#e2e8f0'}`,
                    background: hasPassport === false ? '#2563eb' : '#fff',
                    color: hasPassport === false ? '#fff' : '#64748b',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  ไม่มี
                </button>
              </div>
              {hasPassport === false && (
                <small className="form-hint" style={{ display: 'block', marginTop: '10px', padding: '8px', background: '#fef3c7', borderRadius: '6px', color: '#92400e' }}>
                  💡 เที่ยวบินในประเทศสามารถใช้บัตรประชาชนได้ — เมื่อมีหนังสือเดินทางแล้วสามารถกลับมากรอกได้
                </small>
              )}
            </div>

            {/* หนังสือเดินทางหลายเล่ม: รายการ + เพิ่ม/แก้ไข/ลบ/ใช้เป็นค่าเริ่มต้น */}
            {hasPassport === true && (
            <>
            {passportWarnings.length > 0 && (
              <div style={{ marginBottom: '16px', padding: '12px', background: '#fef3c7', borderRadius: '8px', border: '1px solid #f59e0b' }}>
                <strong style={{ color: '#92400e' }}>⚠️ แจ้งเตือน</strong>
                <ul style={{ margin: '8px 0 0', paddingLeft: '20px', color: '#92400e' }}>
                  {passportWarnings.map((w, i) => (
                    <li key={i}>{w.passport_no ? `${w.passport_no}: ${w.message}` : w.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {passports.length === 0 && !editingPassportId && (
              <p style={{ color: '#6b7280', marginBottom: '12px' }}>ยังไม่มีหนังสือเดินทาง — กดปุ่มด้านล่างเพื่อเพิ่มเล่มแรก</p>
            )}

            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {passports.map((p) => (
                <li key={p.id} style={{ marginBottom: '12px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <span style={{ fontWeight: 600, color: '#111827' }}>{p.passport_no}</span>
                      <span style={{ marginLeft: '8px', fontSize: '12px', color: '#6b7280' }}>
                        {p.passport_type === 'N' && 'ทั่วไป'}
                        {p.passport_type === 'O' && 'ราชการ'}
                        {p.passport_type === 'D' && 'ทูต'}
                        {p.passport_type === 'S' && 'บริการ'}
                        {p.passport_expiry && ` • หมดอายุ ${p.passport_expiry}`}
                      </span>
                      {p.is_primary && (
                        <span style={{ marginLeft: '8px', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#2563eb', color: '#fff' }}>ใช้เป็นค่าเริ่มต้น</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {!p.is_primary && (
                        <button type="button" onClick={() => setPrimaryPassport(p.id)} style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #2563eb', borderRadius: '6px', background: '#eff6ff', color: '#2563eb' }}>ใช้เป็นค่าเริ่มต้น</button>
                      )}
                      <button type="button" onClick={() => startEditPassport(p)} style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', color: '#374151' }}>แก้ไข</button>
                      <button type="button" onClick={() => deletePassport(p.id)} style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #fecaca', borderRadius: '6px', background: '#fef2f2', color: '#dc2626' }}>ลบ</button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>

            {editingPassportId ? (
              <div style={{ marginTop: '16px', padding: '16px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #0ea5e9' }}>
                <h4 style={{ marginTop: 0, marginBottom: '12px' }}>{editingPassportId === 'new' ? 'เพิ่มหนังสือเดินทาง' : 'แก้ไขหนังสือเดินทาง'}</h4>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">เลขหนังสือเดินทาง <span className="required">*</span></label>
                    <input type="text" value={passportForm.passport_no} onChange={(e) => setPassportForm(f => ({ ...f, passport_no: e.target.value }))} className={`form-input ${passportFormErrors.passport_no ? 'error' : ''}`} placeholder="A12345678" maxLength="20" />
                    {passportFormErrors.passport_no && <span className="error-message">{passportFormErrors.passport_no}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">ประเภท</label>
                    <select value={passportForm.passport_type} onChange={(e) => setPassportForm(f => ({ ...f, passport_type: e.target.value }))} className="form-input">
                      <option value="N">ทั่วไป</option><option value="D">ทูต</option><option value="O">ราชการ</option><option value="S">บริการ</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">วันออก</label>
                    <input type="date" value={passportForm.passport_issue_date} onChange={(e) => setPassportForm(f => ({ ...f, passport_issue_date: e.target.value }))} className={`form-input ${passportFormErrors.passport_issue_date ? 'error' : ''}`} />
                    {passportFormErrors.passport_issue_date && <span className="error-message">{passportFormErrors.passport_issue_date}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">วันหมดอายุ <span className="required">*</span></label>
                    <input type="date" value={passportForm.passport_expiry} onChange={(e) => setPassportForm(f => ({ ...f, passport_expiry: e.target.value }))} className={`form-input ${passportFormErrors.passport_expiry ? 'error' : ''}`} />
                    {passportFormErrors.passport_expiry && <span className="error-message">{passportFormErrors.passport_expiry}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">ประเทศที่ออก</label>
                    <select value={passportForm.passport_issuing_country} onChange={(e) => setPassportForm(f => ({ ...f, passport_issuing_country: e.target.value }))} className="form-input">
                      {countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">สัญชาติ</label>
                    <select value={passportForm.nationality} onChange={(e) => setPassportForm(f => ({ ...f, nationality: e.target.value }))} className="form-input">
                      {countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">ชื่อตามเล่ม (อังกฤษ) <span className="required">*</span></label>
                    <input type="text" value={passportForm.passport_given_names} onChange={(e) => setPassportForm(f => ({ ...f, passport_given_names: e.target.value }))} className={`form-input ${passportFormErrors.passport_given_names ? 'error' : ''}`} placeholder="First name" />
                    {passportFormErrors.passport_given_names && <span className="error-message">{passportFormErrors.passport_given_names}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">นามสกุลตามเล่ม (อังกฤษ) <span className="required">*</span></label>
                    <input type="text" value={passportForm.passport_surname} onChange={(e) => setPassportForm(f => ({ ...f, passport_surname: e.target.value }))} className={`form-input ${passportFormErrors.passport_surname ? 'error' : ''}`} placeholder="Last name" />
                    {passportFormErrors.passport_surname && <span className="error-message">{passportFormErrors.passport_surname}</span>}
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">สถานที่เกิด</label>
                  <input type="text" value={passportForm.place_of_birth} onChange={(e) => setPassportForm(f => ({ ...f, place_of_birth: e.target.value }))} className={`form-input ${passportFormErrors.place_of_birth ? 'error' : ''}`} placeholder="เมือง, ประเทศ" maxLength="150" />
                  {passportFormErrors.place_of_birth && <span className="error-message">{passportFormErrors.place_of_birth}</span>}
                </div>
                {editingPassportId === 'new' && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', cursor: 'pointer' }}>
                    <input type="checkbox" checked={passportForm.is_primary} onChange={(e) => setPassportForm(f => ({ ...f, is_primary: e.target.checked }))} />
                    <span>ใช้เป็นค่าเริ่มต้นตอนจอง</span>
                  </label>
                )}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="button" onClick={savePassportEdit} className="btn-primary" style={{ padding: '8px 16px' }}>บันทึก</button>
                  <button type="button" onClick={cancelPassportEdit} className="btn-secondary" style={{ padding: '8px 16px' }}>ยกเลิก</button>
                </div>
              </div>
            ) : (
              <button type="button" onClick={addPassport} style={{ marginTop: '12px', padding: '10px 20px', borderRadius: '8px', border: '1px solid #2563eb', background: '#eff6ff', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}>
                + เพิ่มหนังสือเดินทางอีกเล่ม
              </button>
            )}

            <small className="form-hint" style={{ display: 'block', marginTop: '12px' }}>รองรับหลายเล่ม (หลายสัญชาติ/ประเภท) — เล่มที่ตั้งเป็น &quot;ใช้เป็นค่าเริ่มต้น&quot; จะถูกใช้ตอนจองตั๋ว</small>
            </>
            )}
          </div>
          )}

          {/* ข้อมูลวีซ่า - รายการหลายประเทศ/หลายประเภท (Multi-Visa) */}
          {activeSection === 'visa' && (
          <div id="section-visa" className="form-section">
            <h3 className="form-section-title">🛂 ข้อมูลวีซ่า (สำหรับเที่ยวบินระหว่างประเทศ)</h3>
            <p style={{ color: '#374151', marginBottom: '16px' }}>หนึ่งคนมีวีซ่าได้หลายประเทศ — กรอกแต่ละรายการแล้วผูกกับเล่มพาสปอร์ตที่ลงวีซ่า เพื่อให้ระบบแจ้งเตือนและ AI ใช้ตรวจสอบตอนจอง</p>

            {visaWarnings.length > 0 && (
              <div style={{ marginBottom: '16px', padding: '12px', background: '#fef3c7', borderRadius: '8px', border: '1px solid #f59e0b' }}>
                <strong style={{ color: '#92400e' }}>⚠️ แจ้งเตือน</strong>
                <ul style={{ margin: '8px 0 0', paddingLeft: '20px', color: '#92400e' }}>
                  {visaWarnings.map((w, i) => (
                    <li key={i}>{w.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {visaRecords.length === 0 && !editingVisaId && (
              <p style={{ color: '#6b7280', marginBottom: '12px' }}>ยังไม่มีรายการวีซ่า — กดปุ่มด้านล่างเพื่อเพิ่ม</p>
            )}

            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {visaRecords.map((v) => {
                const countryName = countries.find(c => c.code === v.country_code)?.name || v.country_code;
                const isExpired = v.status === 'Expired' || (v.expiry_date && new Date(v.expiry_date) < new Date());
                return (
                  <li key={v.id} style={{ marginBottom: '12px', padding: '12px', background: isExpired ? '#fef2f2' : '#f9fafb', borderRadius: '8px', border: `1px solid ${isExpired ? '#fecaca' : '#e5e7eb'}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <span style={{ fontWeight: 600, color: '#111827' }}>{countryName}</span>
                        <span style={{ marginLeft: '8px', fontSize: '12px', color: '#6b7280' }}>
                          {v.visa_type} • หมดอายุ {v.expiry_date || '-'} • {v.entries === 'Single' ? 'ครั้งเดียว' : 'หลายครั้ง'}
                          {v.linked_passport && ` • ผูกกับพาสปอร์ต ${v.linked_passport}`}
                        </span>
                        {isExpired && (
                          <span style={{ marginLeft: '8px', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#dc2626', color: '#fff' }}>หมดอายุ</span>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button type="button" onClick={() => startEditVisa(v)} style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', color: '#374151' }}>แก้ไข</button>
                        <button type="button" onClick={() => deleteVisa(v.id)} style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #fecaca', borderRadius: '6px', background: '#fef2f2', color: '#dc2626' }}>ลบ</button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>

            {editingVisaId ? (
              <div style={{ marginTop: '16px', padding: '16px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #0ea5e9' }}>
                <h4 style={{ marginTop: 0, marginBottom: '12px' }}>{editingVisaId === 'new' ? 'เพิ่มวีซ่า' : 'แก้ไขวีซ่า'}</h4>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">ประเทศปลายทาง/ประเทศที่ออกวีซ่า <span className="required">*</span></label>
                    <select value={visaForm.country_code} onChange={(e) => setVisaForm(f => ({ ...f, country_code: e.target.value }))} className={`form-input ${visaFormErrors.country_code ? 'error' : ''}`}>
                      <option value="">-- เลือกประเทศ --</option>
                      {countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}
                    </select>
                    {visaFormErrors.country_code && <span className="error-message">{visaFormErrors.country_code}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">ประเภทวีซ่า</label>
                    <select value={visaForm.visa_type} onChange={(e) => setVisaForm(f => ({ ...f, visa_type: e.target.value }))} className="form-input">
                      <option value="B1/B2">B1/B2 (สหรัฐ)</option>
                      <option value="L">L (จีน ท่องเที่ยว)</option>
                      <option value="TOURIST">ท่องเที่ยว (Tourist)</option>
                      <option value="BUSINESS">ธุรกิจ (Business)</option>
                      <option value="STUDENT">นักเรียน (Student)</option>
                      <option value="WORK">ทำงาน (Work)</option>
                      <option value="TRANSIT">ผ่านทาง (Transit)</option>
                      <option value="EVISA">eVisa</option>
                      <option value="ETA">ETA/eTA</option>
                      <option value="OTHER">อื่นๆ</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">วันหมดอายุ <span className="required">*</span></label>
                    <input type="date" value={visaForm.expiry_date} onChange={(e) => setVisaForm(f => ({ ...f, expiry_date: e.target.value }))} className={`form-input ${visaFormErrors.expiry_date ? 'error' : ''}`} />
                    {visaFormErrors.expiry_date && <span className="error-message">{visaFormErrors.expiry_date}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">วันออกวีซ่า</label>
                    <input type="date" value={visaForm.issue_date} onChange={(e) => setVisaForm(f => ({ ...f, issue_date: e.target.value }))} className={`form-input ${visaFormErrors.issue_date ? 'error' : ''}`} />
                    {visaFormErrors.issue_date && <span className="error-message">{visaFormErrors.issue_date}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">การเข้าประเทศ</label>
                    <select value={visaForm.entries} onChange={(e) => setVisaForm(f => ({ ...f, entries: e.target.value }))} className="form-input">
                      <option value="Single">ครั้งเดียว (Single Entry)</option>
                      <option value="Multiple">หลายครั้ง (Multiple Entry)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">วัตถุประสงค์</label>
                    <select value={visaForm.purpose} onChange={(e) => setVisaForm(f => ({ ...f, purpose: e.target.value }))} className="form-input">
                      <option value="T">ท่องเที่ยว</option>
                      <option value="B">ธุรกิจ</option>
                      <option value="S">ศึกษา</option>
                      <option value="W">ทำงาน</option>
                      <option value="TR">ผ่านทาง</option>
                      <option value="O">อื่นๆ</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">เลขที่วีซ่า (ถ้ามี)</label>
                    <input type="text" value={visaForm.visa_number} onChange={(e) => setVisaForm(f => ({ ...f, visa_number: e.target.value }))} className={`form-input ${visaFormErrors.visa_number ? 'error' : ''}`} placeholder="V123456789" maxLength="50" />
                    {visaFormErrors.visa_number && <span className="error-message">{visaFormErrors.visa_number}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">ผูกกับพาสปอร์ตเล่ม</label>
                    <select value={visaForm.linked_passport} onChange={(e) => setVisaForm(f => ({ ...f, linked_passport: e.target.value }))} className="form-input">
                      <option value="">-- ไม่ระบุ / เล่มอื่น --</option>
                      {passports.filter(p => p.passport_no).map(p => (
                        <option key={p.id} value={p.passport_no}>{p.passport_no}{p.is_primary ? ' (ค่าเริ่มต้น)' : ''}</option>
                      ))}
                    </select>
                    <small className="form-hint">วีซ่าลงในเล่มไหน ให้เลือกเล่มนั้น — ถ้าเป็นเล่มเก่าที่หมดอายุแล้ว ระบบจะเตือนให้พกเล่มนั้นไปด้วย</small>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <button type="button" onClick={saveVisaEdit} className="btn-primary" style={{ padding: '8px 16px' }}>บันทึก</button>
                  <button type="button" onClick={cancelVisaEdit} className="btn-secondary" style={{ padding: '8px 16px' }}>ยกเลิก</button>
                </div>
              </div>
            ) : (
              <button type="button" onClick={addVisa} style={{ marginTop: '12px', padding: '10px 20px', borderRadius: '8px', border: '1px solid #2563eb', background: '#eff6ff', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}>
                + เพิ่มวีซ่า
              </button>
            )}

            <small className="form-hint" style={{ display: 'block', marginTop: '12px' }}>รองรับหลายประเทศ/หลายประเภท — AI จะใช้ข้อมูลนี้ตรวจสอบและแจ้งเตือนเมื่อจองเที่ยวบินระหว่างประเทศหรือมี Transit</small>
          </div>
          )}

          {/* ที่อยู่ + ติดต่อฉุกเฉิน / ผู้จองร่วม (รวมในหมวดเดียวกัน) */}
          {activeSection === 'address_emergency' && (
          <>
          <div id="section-address" className="form-section">
            <h3 className="form-section-title">📍 ที่อยู่</h3>
            <div className="form-group">
              <label htmlFor="address_line1" className="form-label">ที่อยู่ (เลขที่, หมู่, ถนน)</label>
              <input
                type="text"
                id="address_line1"
                name="address_line1"
                value={formData.address_line1}
                onChange={handleChange}
                className={`form-input ${errors.address_line1 ? 'error' : ''}`}
                placeholder="เลขที่, หมู่, ถนน"
                maxLength="200"
              />
              {errors.address_line1 && <span className="error-message">{errors.address_line1}</span>}
            </div>

            {/* ✅ Location Fields: ตำบล -> อำเภอ -> จังหวัด -> รหัสไปรษณีย์ -> ประเทศ */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="subDistrict" className="form-label">ตำบล/แขวง</label>
                <input
                  type="text"
                  id="subDistrict"
                  name="subDistrict"
                  value={formData.subDistrict}
                  onChange={handleChange}
                  className={`form-input ${errors.subDistrict ? 'error' : ''}`}
                  placeholder="ตำบล/แขวง"
                  maxLength="100"
                />
                {errors.subDistrict && <span className="error-message">{errors.subDistrict}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="district" className="form-label">อำเภอ/เขต</label>
                <input
                  type="text"
                  id="district"
                  name="district"
                  value={formData.district}
                  onChange={handleChange}
                  className={`form-input ${errors.district ? 'error' : ''}`}
                  placeholder="อำเภอ/เขต"
                  maxLength="100"
                />
                {errors.district && <span className="error-message">{errors.district}</span>}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="province" className="form-label">จังหวัด</label>
                <input
                  type="text"
                  id="province"
                  name="province"
                  value={formData.province}
                  onChange={handleChange}
                  className={`form-input ${errors.province ? 'error' : ''}`}
                  placeholder="จังหวัด"
                  maxLength="100"
                />
                {errors.province && <span className="error-message">{errors.province}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="postal_code" className="form-label">รหัสไปรษณีย์</label>
                <input
                  type="text"
                  id="postal_code"
                  name="postal_code"
                  value={formData.postal_code}
                  onChange={handleChange}
                  className={`form-input ${errors.postal_code ? 'error' : ''}`}
                  placeholder="10110"
                  maxLength="10"
                />
                {errors.postal_code && <span className="error-message">{errors.postal_code}</span>}
                <small className="form-hint">รหัสไปรษณีย์ไทยต้องมี 5 หลัก</small>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="country" className="form-label">ประเทศ</label>
              <select
                id="country"
                name="country"
                value={formData.country}
                onChange={handleChange}
                className={`form-input ${errors.country ? 'error' : ''}`}
              >
                {countries.map(country => (
                  <option key={country.code} value={country.code}>{country.name}</option>
                ))}
              </select>
              {errors.country && <span className="error-message">{errors.country}</span>}
            </div>

          </div>

          {/* ติดต่อฉุกเฉิน + ผู้จองร่วม (Family) */}
          <div id="section-emergency" className="form-section">
            <div className="form-section-subtitle" style={{ marginTop: '20px', marginBottom: '12px', fontSize: '16px', fontWeight: '600', color: '#1e40af' }}>
              📞 ข้อมูลติดต่อฉุกเฉิน
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="emergency_contact_name" className="form-label">ชื่อผู้ติดต่อฉุกเฉิน</label>
                <input
                  type="text"
                  id="emergency_contact_name"
                  name="emergency_contact_name"
                  value={formData.emergency_contact_name}
                  onChange={handleChange}
                  className={`form-input ${errors.emergency_contact_name ? 'error' : ''}`}
                  placeholder="ชื่อ-นามสกุล"
                  maxLength="100"
                />
                {errors.emergency_contact_name && <span className="error-message">{errors.emergency_contact_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="emergency_contact_phone" className="form-label">เบอร์โทรศัพท์</label>
                <input
                  type="tel"
                  id="emergency_contact_phone"
                  name="emergency_contact_phone"
                  value={formData.emergency_contact_phone}
                  onChange={handleChange}
                  className={`form-input ${errors.emergency_contact_phone ? 'error' : ''}`}
                  placeholder="0812345678"
                  maxLength="20"
                />
                {errors.emergency_contact_phone && <span className="error-message">{errors.emergency_contact_phone}</span>}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="emergency_contact_relation" className="form-label">ความสัมพันธ์</label>
                <select
                  id="emergency_contact_relation"
                  name="emergency_contact_relation"
                  value={formData.emergency_contact_relation}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือกความสัมพันธ์ --</option>
                  <option value="SPOUSE">คู่สมรส</option>
                  <option value="PARENT">บิดา/มารดา</option>
                  <option value="FRIEND">เพื่อน</option>
                  <option value="OTHER">อื่นๆ</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="emergency_contact_email" className="form-label">อีเมล (ถ้ามี)</label>
                <input
                  type="email"
                  id="emergency_contact_email"
                  name="emergency_contact_email"
                  value={formData.emergency_contact_email}
                  onChange={handleChange}
                  className={`form-input ${errors.emergency_contact_email ? 'error' : ''}`}
                  placeholder="contact@example.com"
                  maxLength="100"
                />
                {errors.emergency_contact_email && <span className="error-message">{errors.emergency_contact_email}</span>}
              </div>
            </div>

          </div>
          </>
          )}

          {/* ผู้จองร่วม (สมาชิกในครอบครัว) - หมวดแยก */}
          {activeSection === 'family' && (
          <div id="section-family" className="form-section">
            <h3 className="form-section-title">👨‍👩‍👧‍👦 ผู้จองร่วม (สมาชิกในครอบครัว)</h3>
            <p className="form-hint" style={{ marginBottom: '12px', color: '#6b7280', fontSize: '14px' }}>
              เพิ่มชื่อผู้ใหญ่หรือเด็กที่มักเดินทางด้วย ตอนจองมากกว่า 1 คนจะเลือกจากรายการนี้ได้
            </p>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => addFamilyMember('adult')}
                disabled={!!editingFamilyId}
                title={editingFamilyId ? 'กรุณาบันทึกรายการที่กำลังแก้ไขก่อน' : undefined}
                style={{
                  padding: '8px 16px', borderRadius: '8px', border: '1px solid #3b82f6', background: '#eff6ff', color: '#1d4ed8', fontWeight: 500,
                  opacity: editingFamilyId ? 0.5 : 1, cursor: editingFamilyId ? 'not-allowed' : 'pointer'
                }}
              >
                + เพิ่มผู้ใหญ่
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => addFamilyMember('child')}
                disabled={!!editingFamilyId}
                title={editingFamilyId ? 'กรุณาบันทึกรายการที่กำลังแก้ไขก่อน' : undefined}
                style={{
                  padding: '8px 16px', borderRadius: '8px', border: '1px solid #10b981', background: '#ecfdf5', color: '#059669', fontWeight: 500,
                  opacity: editingFamilyId ? 0.5 : 1, cursor: editingFamilyId ? 'not-allowed' : 'pointer'
                }}
              >
                + เพิ่มเด็ก
              </button>
            </div>
            {family.length === 0 ? (
              <div style={{ padding: '16px', background: '#f9fafb', borderRadius: '8px', color: '#6b7280', fontSize: '14px' }}>
                ยังไม่มีรายชื่อผู้จองร่วม กดปุ่มด้านบนเพื่อเพิ่ม
              </div>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {family.map((member) => (
                    <li key={member.id} style={{ marginBottom: '12px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                      {editingFamilyId === member.id ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                          {/* ชื่อ-นามสกุล (EN/TH) — ประเภทเลือกจากปุ่ม + เพิ่มผู้ใหญ่ / + เพิ่มเด็ก แล้ว */}
                          <div className="form-row" style={{ flexWrap: 'wrap', gap: '12px' }}>
                            <div className="form-group" style={{ minWidth: '120px' }}>
                              <label className="form-label">ชื่อ (อังกฤษ) <span className="required">*</span></label>
                              <input type="text" value={familyForm.first_name} onChange={(e) => setFamilyForm(f => ({ ...f, first_name: e.target.value }))} className={`form-input ${familyFormErrors.first_name ? 'error' : ''}`} placeholder="First name" />
                              {familyFormErrors.first_name && <span className="error-message">{familyFormErrors.first_name}</span>}
                            </div>
                            <div className="form-group" style={{ minWidth: '120px' }}>
                              <label className="form-label">นามสกุล (อังกฤษ) <span className="required">*</span></label>
                              <input type="text" value={familyForm.last_name} onChange={(e) => setFamilyForm(f => ({ ...f, last_name: e.target.value }))} className={`form-input ${familyFormErrors.last_name ? 'error' : ''}`} placeholder="Last name" />
                              {familyFormErrors.last_name && <span className="error-message">{familyFormErrors.last_name}</span>}
                            </div>
                            <div className="form-group" style={{ minWidth: '100px' }}>
                              <label className="form-label">ชื่อ (ไทย)</label>
                              <input type="text" value={familyForm.first_name_th} onChange={(e) => setFamilyForm(f => ({ ...f, first_name_th: e.target.value }))} className={`form-input ${familyFormErrors.first_name_th ? 'error' : ''}`} placeholder="ชื่อไทย" />
                              {familyFormErrors.first_name_th && <span className="error-message">{familyFormErrors.first_name_th}</span>}
                            </div>
                            <div className="form-group" style={{ minWidth: '100px' }}>
                              <label className="form-label">นามสกุล (ไทย)</label>
                              <input type="text" value={familyForm.last_name_th} onChange={(e) => setFamilyForm(f => ({ ...f, last_name_th: e.target.value }))} className={`form-input ${familyFormErrors.last_name_th ? 'error' : ''}`} placeholder="นามสกุลไทย" />
                              {familyFormErrors.last_name_th && <span className="error-message">{familyFormErrors.last_name_th}</span>}
                            </div>
                          </div>
                          {/* วันเกิด + เพศ + เลขบัตรประชาชน */}
                          <div className="form-row" style={{ flexWrap: 'wrap', gap: '12px' }}>
                            <div className="form-group" style={{ minWidth: '140px' }}>
                              <label className="form-label">วันเกิด</label>
                              <input
                                type="text"
                                placeholder="dd/mm/yyyy"
                                value={formatYyyyMmDdToDdMmYyyy(familyForm.date_of_birth)}
                                onChange={(e) => {
                                  const formatted = formatDobInputWithSlashes(e.target.value);
                                  const parsed = parseDdMmYyyyToYyyyMmDd(formatted);
                                  setFamilyForm(f => ({ ...f, date_of_birth: parsed }));
                                }}
                                className={`form-input ${familyFormErrors.date_of_birth ? 'error' : ''}`}
                              />
                              {familyFormErrors.date_of_birth && <span className="error-message">{familyFormErrors.date_of_birth}</span>}
                            </div>
                            <div className="form-group" style={{ minWidth: '100px' }}>
                              <label className="form-label">เพศ</label>
                              <select value={familyForm.gender} onChange={(e) => setFamilyForm(f => ({ ...f, gender: e.target.value }))} className="form-input">
                                <option value="">-- เลือก --</option>
                                <option value="M">ชาย</option>
                                <option value="F">หญิง</option>
                                <option value="O">อื่นๆ</option>
                              </select>
                            </div>
                            <div className="form-group" style={{ minWidth: '160px' }}>
                              <label className="form-label">เลขบัตรประชาชน</label>
                              <input type="text" value={familyForm.national_id} onChange={(e) => setFamilyForm(f => ({ ...f, national_id: e.target.value }))} className={`form-input ${familyFormErrors.national_id ? 'error' : ''}`} placeholder="13 หลัก" maxLength="13" />
                              {familyFormErrors.national_id && <span className="error-message">{familyFormErrors.national_id}</span>}
                            </div>
                          </div>
                          {/* มี/ไม่มี หนังสือเดินทาง */}
                          <div className="form-row" style={{ flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
                            <label className="form-label" style={{ width: '100%', marginBottom: '4px' }}>หนังสือเดินทาง</label>
                            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                                <input
                                  type="radio"
                                  name="family_has_passport"
                                  checked={familyForm.has_passport === true}
                                  onChange={() => setFamilyForm(f => ({ ...f, has_passport: true }))}
                                />
                                <span>มีหนังสือเดินทาง</span>
                              </label>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                                <input
                                  type="radio"
                                  name="family_has_passport"
                                  checked={familyForm.has_passport === false}
                                  onChange={() => {
                                    setFamilyForm(f => ({
                                      ...f,
                                      has_passport: false,
                                      passport_no: '', passport_expiry: '', passport_issue_date: '',
                                      passport_issuing_country: 'TH', passport_given_names: '', passport_surname: '',
                                      place_of_birth: '', passports: [], visa_records: [],
                                    }));
                                    setEditingFamilyPassportId(null);
                                    setEditingFamilyVisaId(null);
                                  }}
                                />
                                <span>ไม่มีหนังสือเดินทาง</span>
                              </label>
                            </div>
                          </div>
                          {familyForm.has_passport && (
                            <>
                          {/* หนังสือเดินทางหลายเล่ม (สำหรับเที่ยวบินระหว่างประเทศ) — pattern เดียวกับผู้จองหลัก */}
                          <div style={{ marginBottom: '12px' }}>
                            <div className="form-label" style={{ marginBottom: '8px' }}>🛂 ข้อมูลหนังสือเดินทาง (สำหรับเที่ยวบินระหว่างประเทศ)</div>
                            {familyFormErrors.passports && <span className="error-message" style={{ display: 'block', marginBottom: '8px' }}>{familyFormErrors.passports}</span>}
                            {(member.passport_warnings || []).length > 0 && editingFamilyId === member.id && (
                              <div style={{ marginBottom: '8px', padding: '8px', background: '#fef3c7', borderRadius: '6px', fontSize: '13px', color: '#92400e' }}>
                                {(member.passport_warnings || []).map((w, i) => <div key={i}>{w.message}</div>)}
                              </div>
                            )}
                            {(familyForm.passports || []).length === 0 && !editingFamilyPassportId && (
                              <p style={{ color: '#6b7280', marginBottom: '8px', fontSize: '14px' }}>ยังไม่มีหนังสือเดินทาง — กดปุ่มด้านล่างเพื่อเพิ่ม</p>
                            )}
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                              {(familyForm.passports || []).map((p) => (
                                <li key={p.id} style={{ marginBottom: '8px', padding: '10px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                                    <span style={{ fontWeight: 600, color: '#111827' }}>{p.passport_no}</span>
                                    <span style={{ fontSize: '12px', color: '#6b7280' }}>{p.passport_expiry && `หมดอายุ ${p.passport_expiry}`} {p.is_primary && ' • ใช้เป็นค่าเริ่มต้น'}</span>
                                    <div style={{ display: 'flex', gap: '6px' }}>
                                      {!p.is_primary && <button type="button" onClick={setPrimaryFamilyPassport.bind(null, p.id)} style={{ padding: '4px 8px', fontSize: '12px', border: '1px solid #2563eb', borderRadius: '6px', background: '#eff6ff', color: '#2563eb' }}>ใช้เป็นค่าเริ่มต้น</button>}
                                      <button type="button" onClick={() => startEditFamilyPassport(p)} style={{ padding: '4px 8px', fontSize: '12px' }}>แก้ไข</button>
                                      <button type="button" onClick={() => deleteFamilyPassport(p.id)} style={{ padding: '4px 8px', fontSize: '12px', color: '#dc2626' }}>ลบ</button>
                                    </div>
                                  </div>
                                </li>
                              ))}
                            </ul>
                            {editingFamilyPassportId ? (
                              <div style={{ marginTop: '12px', padding: '12px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #0ea5e9' }}>
                                <h4 style={{ margin: '0 0 8px', fontSize: '14px' }}>{editingFamilyPassportId === 'new' ? 'เพิ่มหนังสือเดินทาง' : 'แก้ไขหนังสือเดินทาง'}</h4>
                                <div className="form-row">
                                  <div className="form-group"><label className="form-label">เลขหนังสือเดินทาง *</label><input type="text" value={familyPassportForm.passport_no} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_no: e.target.value }))} className={`form-input ${familyPassportFormErrors.passport_no ? 'error' : ''}`} placeholder="A12345678" />{familyPassportFormErrors.passport_no && <span className="error-message">{familyPassportFormErrors.passport_no}</span>}</div>
                                  <div className="form-group"><label className="form-label">ประเภท</label><select value={familyPassportForm.passport_type} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_type: e.target.value }))} className="form-input"><option value="N">ทั่วไป</option><option value="D">ทูต</option><option value="O">ราชการ</option><option value="S">บริการ</option></select></div>
                                </div>
                                <div className="form-row">
                                  <div className="form-group"><label className="form-label">วันออก</label><input type="date" value={familyPassportForm.passport_issue_date} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_issue_date: e.target.value }))} className={`form-input ${familyPassportFormErrors.passport_issue_date ? 'error' : ''}`} />{familyPassportFormErrors.passport_issue_date && <span className="error-message">{familyPassportFormErrors.passport_issue_date}</span>}</div>
                                  <div className="form-group"><label className="form-label">วันหมดอายุ *</label><input type="date" value={familyPassportForm.passport_expiry} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_expiry: e.target.value }))} className={`form-input ${familyPassportFormErrors.passport_expiry ? 'error' : ''}`} />{familyPassportFormErrors.passport_expiry && <span className="error-message">{familyPassportFormErrors.passport_expiry}</span>}</div>
                                </div>
                                <div className="form-row">
                                  <div className="form-group"><label className="form-label">ประเทศที่ออก</label><select value={familyPassportForm.passport_issuing_country} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_issuing_country: e.target.value }))} className="form-input">{countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}</select></div>
                                  <div className="form-group"><label className="form-label">สัญชาติ</label><select value={familyPassportForm.nationality} onChange={(e) => setFamilyPassportForm(f => ({ ...f, nationality: e.target.value }))} className="form-input">{countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}</select></div>
                                </div>
                                <div className="form-row">
                                  <div className="form-group"><label className="form-label">ชื่อตามเล่ม (EN) *</label><input type="text" value={familyPassportForm.passport_given_names} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_given_names: e.target.value }))} className={`form-input ${familyPassportFormErrors.passport_given_names ? 'error' : ''}`} />{familyPassportFormErrors.passport_given_names && <span className="error-message">{familyPassportFormErrors.passport_given_names}</span>}</div>
                                  <div className="form-group"><label className="form-label">นามสกุลตามเล่ม (EN) *</label><input type="text" value={familyPassportForm.passport_surname} onChange={(e) => setFamilyPassportForm(f => ({ ...f, passport_surname: e.target.value }))} className={`form-input ${familyPassportFormErrors.passport_surname ? 'error' : ''}`} />{familyPassportFormErrors.passport_surname && <span className="error-message">{familyPassportFormErrors.passport_surname}</span>}</div>
                                </div>
                                <div className="form-group"><label className="form-label">สถานที่เกิด</label><input type="text" value={familyPassportForm.place_of_birth} onChange={(e) => setFamilyPassportForm(f => ({ ...f, place_of_birth: e.target.value }))} className="form-input" />{familyPassportFormErrors.place_of_birth && <span className="error-message">{familyPassportFormErrors.place_of_birth}</span>}</div>
                                {editingFamilyPassportId === 'new' && <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', cursor: 'pointer' }}><input type="checkbox" checked={familyPassportForm.is_primary} onChange={(e) => setFamilyPassportForm(f => ({ ...f, is_primary: e.target.checked }))} /><span>ใช้เป็นค่าเริ่มต้น</span></label>}
                                <div style={{ display: 'flex', gap: '8px' }}><button type="button" onClick={saveFamilyPassportEdit} className="btn-primary" style={{ padding: '6px 12px' }}>บันทึก</button><button type="button" onClick={cancelFamilyPassportEdit} className="btn-secondary" style={{ padding: '6px 12px' }}>ยกเลิก</button></div>
                              </div>
                            ) : (
                              <button type="button" onClick={addFamilyPassport} style={{ marginTop: '8px', padding: '8px 14px', fontSize: '13px', border: '1px solid #2563eb', borderRadius: '8px', background: '#eff6ff', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}>+ เพิ่มหนังสือเดินทาง</button>
                            )}
                          </div>

                          {/* ข้อมูลวีซ่า (สำหรับเที่ยวบินระหว่างประเทศ) — pattern เดียวกับผู้จองหลัก */}
                          <div style={{ marginBottom: '12px', marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e5e7eb' }}>
                            <div className="form-label" style={{ marginBottom: '8px' }}>🛂 ข้อมูลวีซ่า (สำหรับเที่ยวบินระหว่างประเทศ)</div>
                            {(member.visa_warnings || []).length > 0 && editingFamilyId === member.id && (
                              <div style={{ marginBottom: '8px', padding: '8px', background: '#fef3c7', borderRadius: '6px', fontSize: '13px', color: '#92400e' }}>{(member.visa_warnings || []).map((w, i) => <div key={i}>{w.message}</div>)}</div>
                            )}
                            {(familyForm.visa_records || []).length === 0 && !editingFamilyVisaId && <p style={{ color: '#6b7280', marginBottom: '8px', fontSize: '14px' }}>ยังไม่มีรายการวีซ่า — กดปุ่มด้านล่างเพื่อเพิ่ม</p>}
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                              {(familyForm.visa_records || []).map((v) => {
                                const countryName = countries.find(c => c.code === v.country_code)?.name || v.country_code;
                                const isExpired = v.status === 'Expired' || (v.expiry_date && new Date(v.expiry_date) < new Date());
                                return (
                                  <li key={v.id} style={{ marginBottom: '8px', padding: '10px', background: isExpired ? '#fef2f2' : '#f9fafb', borderRadius: '8px', border: `1px solid ${isExpired ? '#fecaca' : '#e5e7eb'}` }}>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                                      <span style={{ fontWeight: 600, color: '#111827' }}>{countryName}</span>
                                      <span style={{ fontSize: '12px', color: '#6b7280' }}>{v.visa_type} • หมดอายุ {v.expiry_date || '-'} • {v.entries === 'Single' ? 'ครั้งเดียว' : 'หลายครั้ง'}{v.linked_passport && ` • ผูกกับพาสปอร์ต ${v.linked_passport}`}</span>
                                      <div style={{ display: 'flex', gap: '6px' }}><button type="button" onClick={() => startEditFamilyVisa(v)} style={{ padding: '4px 8px', fontSize: '12px' }}>แก้ไข</button><button type="button" onClick={() => deleteFamilyVisa(v.id)} style={{ padding: '4px 8px', fontSize: '12px', color: '#dc2626' }}>ลบ</button></div>
                                    </div>
                                  </li>
                                );
                              })}
                            </ul>
                            {editingFamilyVisaId ? (
                              <div style={{ marginTop: '12px', padding: '12px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #0ea5e9' }}>
                                <h4 style={{ margin: '0 0 8px', fontSize: '14px' }}>{editingFamilyVisaId === 'new' ? 'เพิ่มวีซ่า' : 'แก้ไขวีซ่า'}</h4>
                                <div className="form-row"><div className="form-group"><label className="form-label">ประเทศปลายทาง *</label><select value={familyVisaForm.country_code} onChange={(e) => setFamilyVisaForm(f => ({ ...f, country_code: e.target.value }))} className={`form-input ${familyVisaFormErrors.country_code ? 'error' : ''}`}><option value="">-- เลือกประเทศ --</option>{countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}</select>{familyVisaFormErrors.country_code && <span className="error-message">{familyVisaFormErrors.country_code}</span>}</div><div className="form-group"><label className="form-label">ประเภทวีซ่า</label><select value={familyVisaForm.visa_type} onChange={(e) => setFamilyVisaForm(f => ({ ...f, visa_type: e.target.value }))} className="form-input"><option value="B1/B2">B1/B2</option><option value="L">L</option><option value="TOURIST">ท่องเที่ยว</option><option value="EVISA">eVisa</option><option value="OTHER">อื่นๆ</option></select></div></div>
                                <div className="form-row"><div className="form-group"><label className="form-label">วันหมดอายุ *</label><input type="date" value={familyVisaForm.expiry_date} onChange={(e) => setFamilyVisaForm(f => ({ ...f, expiry_date: e.target.value }))} className={`form-input ${familyVisaFormErrors.expiry_date ? 'error' : ''}`} />{familyVisaFormErrors.expiry_date && <span className="error-message">{familyVisaFormErrors.expiry_date}</span>}</div><div className="form-group"><label className="form-label">วันออก</label><input type="date" value={familyVisaForm.issue_date} onChange={(e) => setFamilyVisaForm(f => ({ ...f, issue_date: e.target.value }))} className={`form-input ${familyVisaFormErrors.issue_date ? 'error' : ''}`} /></div></div>
                                <div className="form-row"><div className="form-group"><label className="form-label">การเข้าประเทศ</label><select value={familyVisaForm.entries} onChange={(e) => setFamilyVisaForm(f => ({ ...f, entries: e.target.value }))} className="form-input"><option value="Single">ครั้งเดียว</option><option value="Multiple">หลายครั้ง</option></select></div><div className="form-group"><label className="form-label">วัตถุประสงค์</label><select value={familyVisaForm.purpose} onChange={(e) => setFamilyVisaForm(f => ({ ...f, purpose: e.target.value }))} className="form-input"><option value="T">ท่องเที่ยว</option><option value="B">ธุรกิจ</option><option value="S">ศึกษา</option><option value="O">อื่นๆ</option></select></div></div>
                                <div className="form-row"><div className="form-group"><label className="form-label">เลขที่วีซ่า (ถ้ามี)</label><input type="text" value={familyVisaForm.visa_number} onChange={(e) => setFamilyVisaForm(f => ({ ...f, visa_number: e.target.value }))} className={`form-input ${familyVisaFormErrors.visa_number ? 'error' : ''}`} placeholder="V123456789" />{familyVisaFormErrors.visa_number && <span className="error-message">{familyVisaFormErrors.visa_number}</span>}</div><div className="form-group"><label className="form-label">ผูกกับพาสปอร์ตเล่ม</label><select value={familyVisaForm.linked_passport} onChange={(e) => setFamilyVisaForm(f => ({ ...f, linked_passport: e.target.value }))} className="form-input"><option value="">-- ไม่ระบุ --</option>{(familyForm.passports || []).filter(p => p.passport_no).map(p => (<option key={p.id} value={p.passport_no}>{p.passport_no}{p.is_primary ? ' (ค่าเริ่มต้น)' : ''}</option>))}</select></div></div>
                                <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}><button type="button" onClick={saveFamilyVisaEdit} className="btn-primary" style={{ padding: '6px 12px' }}>บันทึก</button><button type="button" onClick={cancelFamilyVisaEdit} className="btn-secondary" style={{ padding: '6px 12px' }}>ยกเลิก</button></div>
                              </div>
                            ) : (
                              <button type="button" onClick={addFamilyVisa} style={{ marginTop: '8px', padding: '8px 14px', fontSize: '13px', border: '1px solid #2563eb', borderRadius: '8px', background: '#eff6ff', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}>+ เพิ่มวีซ่า</button>
                            )}
                          </div>
                            </>
                          )}
                          {/* ที่อยู่: default กรอกเอง, มีตัวเลือกติ๊ก "ตามผู้จองหลัก" เท่านั้น */}
                          <div className="form-row" style={{ flexWrap: 'wrap', gap: '16px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
                            <div className="form-group" style={{ width: '100%' }}>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                <input type="checkbox" checked={familyForm.address_option === 'same_as_main'} onChange={(e) => setFamilyForm(f => ({ ...f, address_option: e.target.checked ? 'same_as_main' : 'own' }))} />
                                <span className="form-label" style={{ marginBottom: 0 }}>ใช้ที่อยู่ตามผู้จองหลัก</span>
                              </label>
                              {familyForm.address_option === 'same_as_main' && (
                                <p style={{ marginTop: '8px', fontSize: '13px', color: '#6b7280' }}>
                                  ใช้ที่อยู่เดียวกับผู้จองหลัก{formData.address_line1 || formData.province || formData.postal_code ? ` (${[formData.address_line1, formData.subDistrict, formData.district, formData.province, formData.postal_code].filter(Boolean).join(', ')})` : ''}
                                </p>
                              )}
                            </div>
                            {familyForm.address_option === 'own' && (
                              <>
                                <div className="form-group" style={{ width: '100%' }}>
                                  <label className="form-label">ที่อยู่ (เลขที่, หมู่, ถนน)</label>
                                  <input type="text" value={familyForm.address_line1} onChange={(e) => setFamilyForm(f => ({ ...f, address_line1: e.target.value }))} className="form-input" placeholder="เลขที่, หมู่, ถนน" maxLength="200" />
                                </div>
                                <div className="form-row" style={{ flexWrap: 'wrap', gap: '12px', width: '100%' }}>
                                  <div className="form-group" style={{ minWidth: '120px' }}>
                                    <label className="form-label">ตำบล/แขวง</label>
                                    <input type="text" value={familyForm.subDistrict} onChange={(e) => setFamilyForm(f => ({ ...f, subDistrict: e.target.value }))} className="form-input" placeholder="ตำบล/แขวง" maxLength="100" />
                                  </div>
                                  <div className="form-group" style={{ minWidth: '120px' }}>
                                    <label className="form-label">อำเภอ/เขต</label>
                                    <input type="text" value={familyForm.district} onChange={(e) => setFamilyForm(f => ({ ...f, district: e.target.value }))} className="form-input" placeholder="อำเภอ/เขต" maxLength="100" />
                                  </div>
                                </div>
                                <div className="form-row" style={{ flexWrap: 'wrap', gap: '12px', width: '100%' }}>
                                  <div className="form-group" style={{ minWidth: '120px' }}>
                                    <label className="form-label">จังหวัด</label>
                                    <input type="text" value={familyForm.province} onChange={(e) => setFamilyForm(f => ({ ...f, province: e.target.value }))} className="form-input" placeholder="จังหวัด" maxLength="100" />
                                  </div>
                                  <div className="form-group" style={{ minWidth: '100px' }}>
                                    <label className="form-label">รหัสไปรษณีย์</label>
                                    <input type="text" value={familyForm.postal_code} onChange={(e) => setFamilyForm(f => ({ ...f, postal_code: e.target.value }))} className={`form-input ${familyFormErrors.postal_code ? 'error' : ''}`} placeholder="10110" maxLength="10" />
                                    {familyFormErrors.postal_code && <span className="error-message">{familyFormErrors.postal_code}</span>}
                                  </div>
                                </div>
                                <div className="form-group" style={{ minWidth: '140px' }}>
                                  <label className="form-label">ประเทศ</label>
                                  <select value={familyForm.country} onChange={(e) => setFamilyForm(f => ({ ...f, country: e.target.value }))} className="form-input">
                                    {countries.map(c => (<option key={c.code} value={c.code}>{c.name}</option>))}
                                  </select>
                                </div>
                              </>
                            )}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <button type="button" onClick={saveFamilyEdit} className="btn-primary" style={{ padding: '8px 14px', fontSize: '14px' }} disabled={familySaving}>{familySaving ? 'กำลังบันทึก...' : 'บันทึก'}</button>
                            <button type="button" onClick={cancelFamilyEdit} className="btn-secondary" style={{ padding: '8px 14px', fontSize: '14px' }} disabled={familySaving}>ยกเลิก</button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <span style={{ fontWeight: 600, color: '#111827' }}>
                              {(member.first_name_th && member.last_name_th) ? `${member.first_name_th} ${member.last_name_th}` : (member.first_name || '(ยังไม่ระบุ)') + ' ' + (member.last_name || '')}
                            </span>
                            <span style={{ marginLeft: '8px', fontSize: '12px', padding: '2px 8px', borderRadius: '6px', background: member.type === 'adult' ? '#1d4ed8' : '#059669', color: '#ffffff', fontWeight: 600 }}>
                              {member.type === 'adult' ? 'ผู้ใหญ่' : 'เด็ก'}
                            </span>
                            {(member.date_of_birth || member.passport_no || (member.passports && member.passports.length > 0) || member.has_passport === false || member.national_id || member.address_option || (member.visa_records && member.visa_records.length > 0)) && (
                              <span style={{ marginLeft: '8px', fontSize: '12px', color: '#374151' }}>
                                {member.date_of_birth && `วันเกิด ${member.date_of_birth}`}
                                {(member.passport_no || (member.passports && member.passports.length > 0)) && ` • พาสปอร์ต ${(member.primary_passport || member.passports?.[0] || {}).passport_no || member.passport_no || '-'}`}
                                {member.has_passport === false && !member.passport_no && (!member.passports || member.passports.length === 0) && ` • ไม่มีหนังสือเดินทาง`}
                                {(member.visa_records && member.visa_records.length > 0) && ` • วีซ่า ${member.visa_records.length} ประเทศ`}
                                {member.national_id && ` • บัตรประชาชน`}
                                {member.address_option === 'same_as_main' && ` • ที่อยู่: ตามผู้จองหลัก`}
                                {member.address_option === 'own' && (member.address_line1 || member.province || member.postal_code) && ` • ที่อยู่: กรอกเอง`}
                              </span>
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button type="button" onClick={() => startEditFamily(member)} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', color: '#374151' }}>แก้ไข</button>
                            <button type="button" onClick={() => deleteFamilyMember(member.id)} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #fecaca', borderRadius: '6px', background: '#fef2f2', color: '#dc2626' }}>ลบ</button>
                          </div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
          </div>
          )}

          {/* Buttons - แสดงเมื่ออยู่หมวด ข้อมูลส่วนตัว / ที่อยู่ & ติดต่อฉุกเฉิน / ผู้จองร่วม */}
          {(activeSection === 'personal' || activeSection === 'passport' || activeSection === 'visa' || activeSection === 'address_emergency' || activeSection === 'family') && (
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
          )}
          
          {/* ลบบัญชี - แสดงเมื่ออยู่หมวด ลบบัญชี */}
          {activeSection === 'delete' && (
          <div className="delete-account-section" style={{ marginTop: '40px', paddingTop: '40px', borderTop: '2px solid #e0e0e0' }}>
            <button
              type="button"
              onClick={handleOpenDeletePopup}
              className="btn-delete"
              disabled={isSaving}
              style={{
                backgroundColor: '#d32f2f',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                cursor: isDeleting ? 'not-allowed' : 'pointer',
                opacity: isDeleting ? 0.6 : 1,
                fontWeight: 'bold'
              }}
            >
              ลบบัญชี
            </button>
          </div>
          )}
          
          {/* Delete Account Popup */}
          {showDeletePopup && (
            <div 
              className="delete-account-popup-overlay"
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000
              }}
              onClick={handleCloseDeletePopup}
            >
              <div 
                className="delete-account-popup"
                style={{
                  backgroundColor: 'white',
                  borderRadius: '12px',
                  padding: '32px',
                  maxWidth: '500px',
                  width: '90%',
                  maxHeight: '90vh',
                  overflow: 'auto',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <h3 style={{ color: '#d32f2f', marginBottom: '16px', fontSize: '20px', fontWeight: 'bold' }}>
                  🗑️ ลบบัญชี
                </h3>
                <p style={{ color: '#666', marginBottom: '20px', fontSize: '14px', lineHeight: '1.6' }}>
                  การลบบัญชีจะลบข้อมูลทั้งหมดของคุณอย่างถาวร รวมถึง:
                </p>
                <ul style={{ marginTop: '10px', marginBottom: '20px', paddingLeft: '20px', color: '#666', fontSize: '14px', lineHeight: '1.8' }}>
                  <li>ข้อมูลโปรไฟล์</li>
                  <li>ประวัติการจองทั้งหมด</li>
                  <li>ประวัติการสนทนา</li>
                  <li>ความจำและความชอบ</li>
                  <li>การแจ้งเตือนทั้งหมด</li>
                </ul>
                <div style={{ 
                  backgroundColor: '#fff3cd', 
                  border: '1px solid #ffc107', 
                  borderRadius: '6px', 
                  padding: '12px', 
                  marginBottom: '24px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px'
                }}>
                  <span style={{ color: '#d32f2f', fontSize: '18px' }}>⚠️</span>
                  <strong style={{ color: '#d32f2f', fontSize: '14px' }}>
                    การกระทำนี้ไม่สามารถยกเลิกได้!
                  </strong>
                </div>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={handleCloseDeletePopup}
                    disabled={isDeleting}
                    style={{
                      backgroundColor: '#f5f5f5',
                      color: '#333',
                      border: '1px solid #ddd',
                      padding: '12px 24px',
                      borderRadius: '6px',
                      cursor: isDeleting ? 'not-allowed' : 'pointer',
                      opacity: isDeleting ? 0.6 : 1,
                      fontWeight: '500',
                      fontSize: '14px'
                    }}
                  >
                    ยกเลิก
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmDeleteAccount}
                    disabled={isDeleting}
                    style={{
                      backgroundColor: '#d32f2f',
                      color: 'white',
                      border: 'none',
                      padding: '12px 24px',
                      borderRadius: '6px',
                      cursor: isDeleting ? 'not-allowed' : 'pointer',
                      opacity: isDeleting ? 0.6 : 1,
                      fontWeight: 'bold',
                      fontSize: '14px'
                    }}
                  >
                    {isDeleting ? 'กำลังลบบัญชี...' : 'ยืนยันลบบัญชี'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </form>
        )}
        </div>
      </div>
      </div>
    </div>
  );
}
