import React, { useState, useEffect } from 'react';
import './UserProfileEditPage.css';
import AppHeader from '../../components/common/AppHeader';

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
    // Hotel Booking Preferences (Production-ready for Agoda/Traveloka)
    // Emergency Contact
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relation: '',
    emergency_contact_email: '',
    // Special Requests / Preferences
    hotel_early_checkin: false,
    hotel_late_checkout: false,
    hotel_smoking_preference: '',
    hotel_room_type_preference: '',
    hotel_floor_preference: '',
    hotel_view_preference: '',
    hotel_extra_bed: false,
    hotel_airport_transfer: false,
    hotel_dietary_requirements: '',
    hotel_special_occasion: '',
    hotel_accessibility_needs: false,
    // Check-in Details
    hotel_arrival_time: '',
    hotel_arrival_flight: '',
    hotel_departure_time: '',
    hotel_number_of_guests: 1,
    // Payment Information
    payment_method: '',
    card_holder_name: '',
    card_last_4_digits: '',
    billing_address: '',
    // Tax Invoice Information
    company_name: '',
    tax_id: '',
    invoice_address: '',
    // Loyalty Program
    hotel_loyalty_number: '',
    airline_frequent_flyer: '',
    // Additional Notes
    hotel_booking_notes: '',
  });

  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);
  const [hasVisa, setHasVisa] = useState(false); // State สำหรับตรวจสอบว่ามี visa หรือไม่

  // ✅ Fetch latest user data from backend when component mounts or user changes
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
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
              // Hotel Booking Preferences
              emergency_contact_name: updatedUser.emergency_contact_name || '',
              emergency_contact_phone: updatedUser.emergency_contact_phone || '',
              emergency_contact_relation: updatedUser.emergency_contact_relation || '',
              emergency_contact_email: updatedUser.emergency_contact_email || '',
              hotel_early_checkin: updatedUser.hotel_early_checkin || false,
              hotel_late_checkout: updatedUser.hotel_late_checkout || false,
              hotel_smoking_preference: updatedUser.hotel_smoking_preference || '',
              hotel_room_type_preference: updatedUser.hotel_room_type_preference || '',
              hotel_floor_preference: updatedUser.hotel_floor_preference || '',
              hotel_view_preference: updatedUser.hotel_view_preference || '',
              hotel_extra_bed: updatedUser.hotel_extra_bed || false,
              hotel_airport_transfer: updatedUser.hotel_airport_transfer || false,
              hotel_dietary_requirements: updatedUser.hotel_dietary_requirements || '',
              hotel_special_occasion: updatedUser.hotel_special_occasion || '',
              hotel_accessibility_needs: updatedUser.hotel_accessibility_needs || false,
              hotel_arrival_time: updatedUser.hotel_arrival_time || '',
              hotel_arrival_flight: updatedUser.hotel_arrival_flight || '',
              hotel_departure_time: updatedUser.hotel_departure_time || '',
              hotel_number_of_guests: updatedUser.hotel_number_of_guests || 1,
              payment_method: updatedUser.payment_method || '',
              card_holder_name: updatedUser.card_holder_name || '',
              card_last_4_digits: updatedUser.card_last_4_digits || '',
              company_name: updatedUser.company_name || '',
              tax_id: updatedUser.tax_id || '',
              invoice_address: updatedUser.invoice_address || '',
              hotel_loyalty_number: updatedUser.hotel_loyalty_number || '',
              airline_frequent_flyer: updatedUser.airline_frequent_flyer || '',
              hotel_booking_notes: updatedUser.hotel_booking_notes || '',
            });
            
            // ตรวจสอบว่ามี visa หรือไม่
            const hasVisaData = !!(updatedUser.visa_type || updatedUser.visa_number);
            setHasVisa(hasVisaData);
            
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

  // Initialize form with user data (fallback to prop if backend fetch fails)
  useEffect(() => {
    if (user) {
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
      
      // ตรวจสอบว่ามี visa หรือไม่ (ถ้ามี visa_type หรือ visa_number แสดงว่ามี visa)
      const hasVisaData = !!(user.visa_type || user.visa_number);
      setHasVisa(hasVisaData);
      
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

    // ✅ Optional - First Name (Thai)
    if (formData.first_name_th && formData.first_name_th.trim()) {
      if (!validateThaiName(formData.first_name_th)) {
        newErrors.first_name_th = 'ชื่อต้องเป็นภาษาไทยเท่านั้น';
      } else if (formData.first_name_th.trim().length < 2) {
        newErrors.first_name_th = 'ชื่อต้องมีอย่างน้อย 2 ตัวอักษร';
      } else if (formData.first_name_th.trim().length > 50) {
        newErrors.first_name_th = 'ชื่อต้องไม่เกิน 50 ตัวอักษร';
      }
    }

    // ✅ Optional - Last Name (Thai)
    if (formData.last_name_th && formData.last_name_th.trim()) {
      if (!validateThaiName(formData.last_name_th)) {
        newErrors.last_name_th = 'นามสกุลต้องเป็นภาษาไทยเท่านั้น';
      } else if (formData.last_name_th.trim().length < 2) {
        newErrors.last_name_th = 'นามสกุลต้องมีอย่างน้อย 2 ตัวอักษร';
      } else if (formData.last_name_th.trim().length > 50) {
        newErrors.last_name_th = 'นามสกุลต้องไม่เกิน 50 ตัวอักษร';
      }
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

    // ✅ Date of Birth Validation
    if (formData.dob) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(formData.dob)) {
        newErrors.dob = 'รูปแบบวันเกิดไม่ถูกต้อง (YYYY-MM-DD)';
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
    }

    // ✅ Thai National ID Validation (13 digits with checksum)
    if (formData.national_id && formData.national_id.trim()) {
      const cleanedID = formData.national_id.replace(/[-\s]/g, '');
      if (cleanedID.length !== 13) {
        newErrors.national_id = 'เลขบัตรประชาชนต้องมี 13 หลัก';
      } else if (!/^\d{13}$/.test(cleanedID)) {
        newErrors.national_id = 'เลขบัตรประชาชนต้องเป็นตัวเลขเท่านั้น';
      } else if (!validateThaiNationalID(cleanedID)) {
        newErrors.national_id = 'เลขบัตรประชาชนไม่ถูกต้อง (checksum ไม่ผ่าน)';
      }
    }
    // ✅ Passport validation (Production-ready for international flights)
    const hasPassportInfo = formData.passport_no || formData.passport_expiry;
    
    if (hasPassportInfo) {
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

    // ✅ Visa validation (Production-ready)
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
    if (formData.visa_issue_date && !/^\d{4}-\d{2}-\d{2}$/.test(formData.visa_issue_date)) {
      newErrors.visa_issue_date = 'รูปแบบวันออกวีซ่าไม่ถูกต้อง (YYYY-MM-DD)';
    }
    
    // ✅ Validate visa expiry is after issue date
    if (formData.visa_issue_date && formData.visa_expiry_date) {
      const issueDate = new Date(formData.visa_issue_date);
      const expiryDate = new Date(formData.visa_expiry_date);
      if (isNaN(issueDate.getTime()) || isNaN(expiryDate.getTime())) {
        newErrors.visa_expiry_date = 'วันที่ไม่ถูกต้อง';
      } else if (expiryDate <= issueDate) {
        newErrors.visa_expiry_date = 'วันหมดอายุวีซ่าต้องหลังวันออกวีซ่า';
      }
    }
    
    // ✅ Validate visa expiry is not in the past
    if (formData.visa_expiry_date) {
      const expiryDate = new Date(formData.visa_expiry_date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (isNaN(expiryDate.getTime())) {
        newErrors.visa_expiry_date = 'วันหมดอายุวีซ่าไม่ถูกต้อง';
      } else if (expiryDate < today) {
        newErrors.visa_expiry_date = 'วีซ่าหมดอายุแล้ว กรุณาต่ออายุหรือกรอกวีซ่าใหม่';
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

    // Hotel Booking Notes
    if (formData.hotel_booking_notes && formData.hotel_booking_notes.trim().length > 500) {
      newErrors.hotel_booking_notes = 'หมายเหตุต้องไม่เกิน 500 ตัวอักษร';
    }

    // Card Last 4 Digits
    if (formData.card_last_4_digits && formData.card_last_4_digits.trim()) {
      if (!/^\d{4}$/.test(formData.card_last_4_digits.trim())) {
        newErrors.card_last_4_digits = 'ต้องเป็นตัวเลข 4 หลักเท่านั้น';
      }
    }

    // Hotel Number of Guests
    if (formData.hotel_number_of_guests && (formData.hotel_number_of_guests < 1 || formData.hotel_number_of_guests > 20)) {
      newErrors.hotel_number_of_guests = 'จำนวนผู้เข้าพักต้องอยู่ระหว่าง 1-20 คน';
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


  return (
    <div className="profile-edit-wrapper">
      {/* ✅ Header */}
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
        />
      )}
      
      <div className="profile-edit-container">
        <div className="profile-edit-card">
          <div className="profile-edit-header">
            <button
              type="button"
              onClick={onCancel}
              className="btn-back"
              title="ย้อนกลับ"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="20" height="20">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="profile-edit-header-content">
              <div className="profile-edit-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="32" height="32">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2>แก้ไขข้อมูลส่วนตัว</h2>
              <p className="profile-edit-subtitle">
                กรุณากรอกข้อมูลให้ครบถ้วนเพื่อความสะดวกในการจองทริป
              </p>
            </div>
          </div>

        <form onSubmit={handleSubmit} className="profile-edit-form">
          {/* Profile Image Section */}
          <div className="form-section profile-image-section">
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
                  ชื่อ (ภาษาไทย)
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
                  นามสกุล (ภาษาไทย)
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
              <label htmlFor="national_id" className="form-label">เลขบัตรประจำตัวประชาชน</label>
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
              <small className="form-hint">สำหรับใช้เดินทางภายในประเทศ (ถ้ามี)</small>
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
            
            {/* Passport Number & Type */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="passport_no" className="form-label">
                  เลขหนังสือเดินทาง <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="passport_no"
                  name="passport_no"
                  value={formData.passport_no}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_no ? 'error' : ''}`}
                  placeholder="A12345678"
                  maxLength="20"
                  autoComplete="passport"
                />
                {errors.passport_no && <span className="error-message">{errors.passport_no}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="passport_type" className="form-label">ประเภทหนังสือเดินทาง</label>
                <select
                  id="passport_type"
                  name="passport_type"
                  value={formData.passport_type}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="N">ทั่วไป (Normal)</option>
                  <option value="D">ทางการทูต (Diplomatic)</option>
                  <option value="O">ราชการ (Official)</option>
                  <option value="S">บริการ (Service)</option>
                </select>
              </div>
            </div>

            {/* Issue Date & Expiry Date */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="passport_issue_date" className="form-label">วันออกหนังสือเดินทาง</label>
                <input
                  type="date"
                  id="passport_issue_date"
                  name="passport_issue_date"
                  value={formData.passport_issue_date}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_issue_date ? 'error' : ''}`}
                />
                {errors.passport_issue_date && <span className="error-message">{errors.passport_issue_date}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="passport_expiry" className="form-label">
                  วันหมดอายุ <span className="required">*</span>
                </label>
                <input
                  type="date"
                  id="passport_expiry"
                  name="passport_expiry"
                  value={formData.passport_expiry}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_expiry ? 'error' : ''}`}
                />
                {errors.passport_expiry && <span className="error-message">{errors.passport_expiry}</span>}
                <small className="form-hint">หนังสือเดินทางต้องเหลืออายุอย่างน้อย 6 เดือนก่อนเดินทาง</small>
              </div>
            </div>

            {/* Issuing Country & Nationality */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="passport_issuing_country" className="form-label">ประเทศที่ออกหนังสือเดินทาง</label>
                <select
                  id="passport_issuing_country"
                  name="passport_issuing_country"
                  value={formData.passport_issuing_country}
                  onChange={handleChange}
                  className="form-input"
                >
                  {countries.map(country => (
                    <option key={country.code} value={country.code}>{country.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="nationality" className="form-label">
                  สัญชาติ <span className="required">*</span>
                </label>
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

            {/* Passport Name (English) */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="passport_given_names" className="form-label">
                  ชื่อตามหนังสือเดินทาง (ภาษาอังกฤษ) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="passport_given_names"
                  name="passport_given_names"
                  value={formData.passport_given_names}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_given_names ? 'error' : ''}`}
                  placeholder="First Name and Middle Name"
                  autoComplete="given-name"
                />
                {errors.passport_given_names && <span className="error-message">{errors.passport_given_names}</span>}
                <small className="form-hint">กรุณากรอกตามที่ปรากฏในหนังสือเดินทาง (ภาษาอังกฤษ)</small>
              </div>

              <div className="form-group">
                <label htmlFor="passport_surname" className="form-label">
                  นามสกุลตามหนังสือเดินทาง (ภาษาอังกฤษ) <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="passport_surname"
                  name="passport_surname"
                  value={formData.passport_surname}
                  onChange={handleChange}
                  className={`form-input ${errors.passport_surname ? 'error' : ''}`}
                  placeholder="Last Name / Surname"
                  autoComplete="family-name"
                />
                {errors.passport_surname && <span className="error-message">{errors.passport_surname}</span>}
                <small className="form-hint">กรุณากรอกตามที่ปรากฏในหนังสือเดินทาง (ภาษาอังกฤษ)</small>
              </div>
            </div>

            {/* Place of Birth */}
            <div className="form-group">
              <label htmlFor="place_of_birth" className="form-label">สถานที่เกิด</label>
              <input
                type="text"
                id="place_of_birth"
                name="place_of_birth"
                value={formData.place_of_birth}
                onChange={handleChange}
                className={`form-input ${errors.place_of_birth ? 'error' : ''}`}
                placeholder="กรุงเทพมหานคร, ประเทศไทย"
                autoComplete="birth-place"
                maxLength="100"
              />
              {errors.place_of_birth && <span className="error-message">{errors.place_of_birth}</span>}
              <small className="form-hint">ระบุเมืองและประเทศ เช่น กรุงเทพมหานคร, ประเทศไทย หรือ Bangkok, Thailand</small>
            </div>
          </div>

          {/* ข้อมูลวีซ่า */}
          <div className="form-section">
            <h3 className="form-section-title">🛂 ข้อมูลวีซ่า (สำหรับเที่ยวบินระหว่างประเทศ)</h3>
            
            {/* Checkbox สำหรับเลือกว่ามี Visa หรือไม่ */}
            <div className="form-group" style={{ marginBottom: '20px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '16px', fontWeight: '500' }}>
                  <input
                    type="radio"
                    name="has_visa_option"
                    checked={hasVisa === true}
                    onChange={(e) => e.target.checked && handleHasVisaChange({ target: { checked: true } })}
                    style={{ marginRight: '8px', width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                  <span>มี Visa</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '16px', fontWeight: '500' }}>
                  <input
                    type="radio"
                    name="has_visa_option"
                    checked={hasVisa === false}
                    onChange={(e) => e.target.checked && handleHasVisaChange({ target: { checked: false } })}
                    style={{ marginRight: '8px', width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                  <span>ไม่มี Visa</span>
                </label>
              </div>
              <small className="form-hint" style={{ display: 'block', marginTop: '8px', padding: '8px', background: '#e3f2fd', borderRadius: '6px', color: '#1565c0' }}>
                💡 หากคุณมีวีซ่าที่ถูกต้องสำหรับประเทศปลายทางหรือประเทศที่ต้องผ่านทาง (Transit) กรุณาเลือก "มี Visa" และกรอกข้อมูลด้านล่าง เพื่อให้ระบบตรวจสอบและแจ้งเตือนอัตโนมัติ
              </small>
            </div>

            {/* แสดงฟอร์มข้อมูลวีซ่าเฉพาะเมื่อ hasVisa === true */}
            {hasVisa && (
              <>
                {/* Visa Type & Number */}
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="visa_type" className="form-label">ประเภทวีซ่า</label>
                    <select
                      id="visa_type"
                      name="visa_type"
                      value={formData.visa_type}
                      onChange={handleChange}
                      className="form-input"
                    >
                      <option value="">-- เลือกประเภทวีซ่า --</option>
                      <option value="TOURIST">ท่องเที่ยว (Tourist)</option>
                      <option value="BUSINESS">ธุรกิจ (Business)</option>
                      <option value="STUDENT">นักเรียน/นักศึกษา (Student)</option>
                      <option value="WORK">ทำงาน (Work)</option>
                      <option value="TRANSIT">ผ่านทาง (Transit)</option>
                      <option value="VISA_FREE">Visa-Free Entry</option>
                      <option value="ETA">Electronic Travel Authorization (ETA/eTA)</option>
                      <option value="EVISA">Electronic Visa (eVisa)</option>
                      <option value="OTHER">อื่นๆ (Other)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="visa_number" className="form-label">เลขที่วีซ่า</label>
                    <input
                      type="text"
                      id="visa_number"
                      name="visa_number"
                      value={formData.visa_number}
                      onChange={handleChange}
                      className={`form-input ${errors.visa_number ? 'error' : ''}`}
                      placeholder="V123456789"
                      maxLength="50"
                    />
                    {errors.visa_number && <span className="error-message">{errors.visa_number}</span>}
                  </div>
                </div>

                {/* Visa Issuing Country & Purpose */}
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="visa_issuing_country" className="form-label">ประเทศที่ออกวีซ่า</label>
                    <select
                      id="visa_issuing_country"
                      name="visa_issuing_country"
                      value={formData.visa_issuing_country}
                      onChange={handleChange}
                      className="form-input"
                    >
                      <option value="">-- เลือกประเทศ --</option>
                      {countries.map(country => (
                        <option key={country.code} value={country.code}>{country.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="visa_purpose" className="form-label">วัตถุประสงค์ในการเดินทาง</label>
                    <select
                      id="visa_purpose"
                      name="visa_purpose"
                      value={formData.visa_purpose}
                      onChange={handleChange}
                      className="form-input"
                    >
                      <option value="T">ท่องเที่ยว (Tourism)</option>
                      <option value="B">ธุรกิจ (Business)</option>
                      <option value="S">ศึกษา (Study)</option>
                      <option value="W">ทำงาน (Work)</option>
                      <option value="TR">ผ่านทาง (Transit)</option>
                      <option value="O">อื่นๆ (Other)</option>
                    </select>
                  </div>
                </div>

                {/* Visa Issue Date & Expiry Date */}
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="visa_issue_date" className="form-label">วันออกวีซ่า</label>
                    <input
                      type="date"
                      id="visa_issue_date"
                      name="visa_issue_date"
                      value={formData.visa_issue_date}
                      onChange={handleChange}
                      className={`form-input ${errors.visa_issue_date ? 'error' : ''}`}
                    />
                    {errors.visa_issue_date && <span className="error-message">{errors.visa_issue_date}</span>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="visa_expiry_date" className="form-label">
                      วันหมดอายุวีซ่า <span className="required">*</span> (ถ้ามี)
                    </label>
                    <input
                      type="date"
                      id="visa_expiry_date"
                      name="visa_expiry_date"
                      value={formData.visa_expiry_date}
                      onChange={handleChange}
                      className={`form-input ${errors.visa_expiry_date ? 'error' : ''}`}
                    />
                    {errors.visa_expiry_date && <span className="error-message">{errors.visa_expiry_date}</span>}
                    <small className="form-hint">กรุณาตรวจสอบวันหมดอายุวีซ่าก่อนเดินทาง</small>
                  </div>
                </div>

                {/* Visa Entry Type */}
                <div className="form-group">
                  <label htmlFor="visa_entry_type" className="form-label">ประเภทการเข้าประเทศ</label>
                  <select
                    id="visa_entry_type"
                    name="visa_entry_type"
                    value={formData.visa_entry_type}
                    onChange={handleChange}
                    className="form-input"
                  >
                    <option value="S">ครั้งเดียว (Single Entry)</option>
                    <option value="M">หลายครั้ง (Multiple Entry)</option>
                  </select>
                  <small className="form-hint">Single Entry = เข้าได้ 1 ครั้ง, Multiple Entry = เข้าได้หลายครั้ง</small>
                </div>
              </>
            )}
          </div>

          {/* ที่อยู่ */}
          <div className="form-section">
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

          {/* ข้อมูลสำหรับการจองโรงแรม (Hotel Booking Preferences) */}
          <div className="form-section">
            <h3 className="form-section-title">🏨 ข้อมูลสำหรับการจองโรงแรม</h3>

            {/* Emergency Contact */}
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

            {/* Special Requests / Preferences */}
            <div className="form-section-subtitle" style={{ marginTop: '24px', marginBottom: '12px', fontSize: '16px', fontWeight: '600', color: '#1e40af' }}>
              ⭐ ความต้องการพิเศษ (Special Requests)
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  <input
                    type="checkbox"
                    name="hotel_early_checkin"
                    checked={formData.hotel_early_checkin}
                    onChange={handleChange}
                    style={{ marginRight: '8px' }}
                  />
                  ต้องการ Early Check-in
                </label>
              </div>

              <div className="form-group">
                <label className="form-label">
                  <input
                    type="checkbox"
                    name="hotel_late_checkout"
                    checked={formData.hotel_late_checkout}
                    onChange={handleChange}
                    style={{ marginRight: '8px' }}
                  />
                  ต้องการ Late Check-out
                </label>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="hotel_smoking_preference" className="form-label">ความต้องการเรื่องบุหรี่</label>
                <select
                  id="hotel_smoking_preference"
                  name="hotel_smoking_preference"
                  value={formData.hotel_smoking_preference}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="NON_SMOKING">ไม่สูบบุหรี่ (Non-smoking)</option>
                  <option value="SMOKING">สูบบุหรี่ได้ (Smoking)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="hotel_room_type_preference" className="form-label">ประเภทห้องที่ต้องการ</label>
                <select
                  id="hotel_room_type_preference"
                  name="hotel_room_type_preference"
                  value={formData.hotel_room_type_preference}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="STANDARD">Standard</option>
                  <option value="DELUXE">Deluxe</option>
                  <option value="SUITE">Suite</option>
                  <option value="EXECUTIVE">Executive</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="hotel_floor_preference" className="form-label">ชั้นที่ต้องการ</label>
                <select
                  id="hotel_floor_preference"
                  name="hotel_floor_preference"
                  value={formData.hotel_floor_preference}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="HIGH">ชั้นสูง</option>
                  <option value="LOW">ชั้นต่ำ</option>
                  <option value="ANY">ไม่ระบุ</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="hotel_view_preference" className="form-label">วิวที่ต้องการ</label>
                <select
                  id="hotel_view_preference"
                  name="hotel_view_preference"
                  value={formData.hotel_view_preference}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="SEA">วิวทะเล</option>
                  <option value="CITY">วิวเมือง</option>
                  <option value="GARDEN">วิวสวน</option>
                  <option value="ANY">ไม่ระบุ</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  <input
                    type="checkbox"
                    name="hotel_extra_bed"
                    checked={formData.hotel_extra_bed}
                    onChange={handleChange}
                    style={{ marginRight: '8px' }}
                  />
                  ต้องการเตียงเสริม (Extra Bed/Cot)
                </label>
              </div>

              <div className="form-group">
                <label className="form-label">
                  <input
                    type="checkbox"
                    name="hotel_airport_transfer"
                    checked={formData.hotel_airport_transfer}
                    onChange={handleChange}
                    style={{ marginRight: '8px' }}
                  />
                  ต้องการรถรับส่งสนามบิน
                </label>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="hotel_dietary_requirements" className="form-label">อาหารพิเศษ</label>
                <select
                  id="hotel_dietary_requirements"
                  name="hotel_dietary_requirements"
                  value={formData.hotel_dietary_requirements}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="NONE">ไม่มี</option>
                  <option value="VEGETARIAN">Vegetarian</option>
                  <option value="VEGAN">Vegan</option>
                  <option value="HALAL">Halal</option>
                  <option value="ALLERGIES">มีอาการแพ้ (ระบุในหมายเหตุ)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="hotel_special_occasion" className="form-label">โอกาสพิเศษ</label>
                <select
                  id="hotel_special_occasion"
                  name="hotel_special_occasion"
                  value={formData.hotel_special_occasion}
                  onChange={handleChange}
                  className="form-input"
                >
                  <option value="">-- เลือก --</option>
                  <option value="NONE">ไม่มี</option>
                  <option value="BIRTHDAY">วันเกิด</option>
                  <option value="HONEYMOON">ฮันนีมูน</option>
                  <option value="ANNIVERSARY">วันครบรอบ</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                <input
                  type="checkbox"
                  name="hotel_accessibility_needs"
                  checked={formData.hotel_accessibility_needs}
                  onChange={handleChange}
                  style={{ marginRight: '8px' }}
                />
                ต้องการห้องสำหรับผู้พิการ (Accessibility Needs)
              </label>
            </div>

            
            {/* Tax Invoice Information */}
            <div className="form-section-subtitle" style={{ marginTop: '24px', marginBottom: '12px', fontSize: '16px', fontWeight: '600', color: '#1e40af' }}>
              🧾 ข้อมูลสำหรับออกใบกำกับภาษี
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="company_name" className="form-label">ชื่อบริษัท/องค์กร</label>
                <input
                  type="text"
                  id="company_name"
                  name="company_name"
                  value={formData.company_name}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="สำหรับการจองธุรกิจ"
                  maxLength="100"
                />
              </div>

              <div className="form-group">
                <label htmlFor="tax_id" className="form-label">เลขประจำตัวผู้เสียภาษี</label>
                <input
                  type="text"
                  id="tax_id"
                  name="tax_id"
                  value={formData.tax_id}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="เลขประจำตัวผู้เสียภาษี"
                  maxLength="20"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="invoice_address" className="form-label">ที่อยู่สำหรับออกใบกำกับภาษี</label>
              <input
                type="text"
                id="invoice_address"
                name="invoice_address"
                value={formData.invoice_address}
                onChange={handleChange}
                className="form-input"
                placeholder="ถ้าไม่ใช่ที่อยู่หลัก"
                maxLength="200"
              />
            </div>

            {/* Loyalty Program */}
            <div className="form-section-subtitle" style={{ marginTop: '24px', marginBottom: '12px', fontSize: '16px', fontWeight: '600', color: '#1e40af' }}>
              🎁 โปรแกรมสะสมแต้ม/ไมล์
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="hotel_loyalty_number" className="form-label">เลขสมาชิกโรงแรม</label>
                <input
                  type="text"
                  id="hotel_loyalty_number"
                  name="hotel_loyalty_number"
                  value={formData.hotel_loyalty_number}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="เช่น Marriott Bonvoy, Hilton Honors"
                  maxLength="50"
                />
              </div>

              <div className="form-group">
                <label htmlFor="airline_frequent_flyer" className="form-label">เลขสมาชิกสายการบิน</label>
                <input
                  type="text"
                  id="airline_frequent_flyer"
                  name="airline_frequent_flyer"
                  value={formData.airline_frequent_flyer}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="สำหรับสะสมไมล์"
                  maxLength="50"
                />
              </div>
            </div>

            {/* Additional Notes */}
            <div className="form-group" style={{ marginTop: '24px' }}>
              <label htmlFor="hotel_booking_notes" className="form-label">หมายเหตุเพิ่มเติม</label>
              <textarea
                id="hotel_booking_notes"
                name="hotel_booking_notes"
                value={formData.hotel_booking_notes}
                onChange={handleChange}
                className="form-input"
                placeholder="ระบุความต้องการพิเศษอื่นๆ หรือข้อมูลเพิ่มเติม"
                rows="4"
                maxLength="500"
              />
              <small className="form-hint">สูงสุด 500 ตัวอักษร</small>
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
    </div>
  );
}
