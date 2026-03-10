import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import Swal from 'sweetalert2';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import { AIRLINE_NAMES, AIRLINE_DOMAINS } from '../../data/airlineNames';
import { formatPriceInThb } from '../../utils/currency';
import './FlightsPage.css';

export default function FlightsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToHome = null, onNavigateToProfile = null, onNavigateToSettings = null, notificationCount = 0, notifications = [], onMarkNotificationAsRead = null, onClearAllNotifications = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [returnDate, setReturnDate] = useState('');
  const [seatType, setSeatType] = useState('ECONOMY');
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [infantsWithSeat, setInfantsWithSeat] = useState(0);
  const [infantsOnLap, setInfantsOnLap] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [flights, setFlights] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [originError, setOriginError] = useState('');
  const [destinationError, setDestinationError] = useState('');
  // index ของการ์ดที่โลโก้โหลดไม่สำเร็จ → แสดง fallback ข้อความ (ใช้ state เพื่อไม่หายหลัง re-render)
  const [logoShowFallback, setLogoShowFallback] = useState(() => new Set());
  const [passengerDropdownOpen, setPassengerDropdownOpen] = useState(false);
  const passengerDropdownRef = useRef(null);
  const passengerPanelRef = useRef(null);
  const passengerTriggerRef = useRef(null);
  const [passengerPanelPosition, setPassengerPanelPosition] = useState(null);

  const [seatDropdownOpen, setSeatDropdownOpen] = useState(false);
  const seatDropdownRef = useRef(null);
  const seatTriggerRef = useRef(null);
  const seatPanelRef = useRef(null);
  const [seatPanelPosition, setSeatPanelPosition] = useState(null);

  const PASSENGER_PANEL_WIDTH = 280;
  const SEAT_PANEL_WIDTH = 220;
  const updatePassengerPanelPosition = useCallback(() => {
    if (!passengerTriggerRef.current) return;
    const rect = passengerTriggerRef.current.getBoundingClientRect();
    const padding = 12;
    let left = rect.left;
    if (left + PASSENGER_PANEL_WIDTH > window.innerWidth - padding) {
      left = Math.max(padding, window.innerWidth - PASSENGER_PANEL_WIDTH - padding);
    }
    setPassengerPanelPosition({
      top: rect.bottom + 8,
      left,
      width: PASSENGER_PANEL_WIDTH,
    });
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      const inTrigger = passengerDropdownRef.current?.contains(e.target);
      const inPanel = passengerPanelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setPassengerDropdownOpen(false);
    };
    if (passengerDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [passengerDropdownOpen]);

  useEffect(() => {
    if (!passengerDropdownOpen) {
      setPassengerPanelPosition(null);
      return;
    }
    updatePassengerPanelPosition();
    const onScrollOrResize = () => updatePassengerPanelPosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [passengerDropdownOpen, updatePassengerPanelPosition]);

  const updateSeatPanelPosition = useCallback(() => {
    if (!seatTriggerRef.current) return;
    const rect = seatTriggerRef.current.getBoundingClientRect();
    const padding = 12;
    let left = rect.left;
    if (left + SEAT_PANEL_WIDTH > window.innerWidth - padding) {
      left = Math.max(padding, window.innerWidth - SEAT_PANEL_WIDTH - padding);
    }
    setSeatPanelPosition({
      top: rect.bottom + 8,
      left,
      width: SEAT_PANEL_WIDTH,
    });
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      const inTrigger = seatDropdownRef.current?.contains(e.target);
      const inPanel = seatPanelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setSeatDropdownOpen(false);
    };
    if (seatDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [seatDropdownOpen]);

  useEffect(() => {
    if (!seatDropdownOpen) {
      setSeatPanelPosition(null);
      return;
    }
    updateSeatPanelPosition();
    const onScrollOrResize = () => updateSeatPanelPosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [seatDropdownOpen, updateSeatPanelPosition]);

  const CABIN_OPTIONS = [
    { value: 'ECONOMY', labelKey: 'flights.cabinEconomy' },
    { value: 'PREMIUM_ECONOMY', labelKey: 'flights.cabinPremiumEconomy' },
    { value: 'BUSINESS', labelKey: 'flights.cabinBusiness' },
    { value: 'FIRST', labelKey: 'flights.cabinFirst' },
  ];

  const IATA_CITY = {
    BKK: 'กรุงเทพ (สุวรรณภูมิ)', DMK: 'กรุงเทพ (ดอนเมือง)',
    CNX: 'เชียงใหม่', CEI: 'เชียงราย', HKT: 'ภูเก็ต', HDY: 'หาดใหญ่',
    KBV: 'กระบี่', USM: 'สมุย', UTH: 'อุดรธานี', UBP: 'อุบลราชธานี',
    KKC: 'ขอนแก่น', NST: 'นครศรีธรรมราช', NAK: 'นครราชสีมา',
    SNO: 'สกลนคร', URT: 'สุราษฎร์ธานี', THS: 'สุโขทัย',
    TST: 'ตรัง', NAW: 'นราธิวาส', LOE: 'เลย', LPT: 'ลำปาง',
    PRH: 'แพร่', NNT: 'น่าน', HHQ: 'หัวหิน', PHS: 'พิษณุโลก',
    ROI: 'ร้อยเอ็ด', MAQ: 'แม่สอด', RGN: 'ย่างกุ้ง',
    NRT: 'โตเกียว (นาริตะ)', HND: 'โตเกียว (ฮาเนดะ)',
    KIX: 'โอซาก้า', ICN: 'โซล (อินชอน)', GMP: 'โซล (กิมโป)',
    SIN: 'สิงคโปร์', KUL: 'กัวลาลัมเปอร์', HKG: 'ฮ่องกง',
    TPE: 'ไทเป', PEK: 'ปักกิ่ง', PVG: 'เซี่ยงไฮ้',
    SGN: 'โฮจิมินห์', HAN: 'ฮานอย', DAD: 'ดานัง',
    REP: 'เสียมเรียบ', PNH: 'พนมเปญ',
    VTE: 'เวียงจันทน์', LPQ: 'หลวงพระบาง',
    MNL: 'มะนิลา', CEB: 'เซบู', DPS: 'บาหลี', CGK: 'จาการ์ตา',
    DEL: 'นิวเดลี', BOM: 'มุมไบ', CCU: 'โกลกาตา',
    SYD: 'ซิดนีย์', MEL: 'เมลเบิร์น', AKL: 'โอ๊คแลนด์',
    LHR: 'ลอนดอน', CDG: 'ปารีส', FRA: 'แฟรงก์เฟิร์ต',
    AMS: 'อัมสเตอร์ดัม', FCO: 'โรม', BCN: 'บาร์เซโลนา',
    IST: 'อิสตันบูล', DXB: 'ดูไบ', DOH: 'โดฮา',
    JFK: 'นิวยอร์ก', LAX: 'ลอสแอนเจลิส', SFO: 'ซานฟรานซิสโก',
    ORD: 'ชิคาโก',
  };
  const getCityName = (iata) => IATA_CITY[iata] || iata;

  const getAirlineName = (iata) => (iata && AIRLINE_NAMES[String(iata).toUpperCase()]) || iata || '';
  const getClearbitLogoUrl = (iataCode) => {
    const domain = AIRLINE_DOMAINS[String(iataCode).toUpperCase()];
    if (!domain) return null;
    return `https://logo.clearbit.com/${domain}`;
  };
  // Duffel CDN: 600+ สายการบิน, SVG (ตาม https://duffel.com/docs/api/airlines/schema)
  const getDuffelLogoUrl = (iataCode) => {
    const code = String(iataCode || '').toUpperCase();
    if (!code || code.length !== 2) return null;
    return `https://assets.duffel.com/img/airlines/for-light-background/full-color-logo/${code}.svg`;
  };
  // Google Favicon เป็น fallback สุดท้ายก่อนข้อความ (เมื่อ Kiwi/Duffel/Clearbit โหลดไม่ได้)
  const getGoogleFaviconUrl = (iataCode) => {
    const domain = AIRLINE_DOMAINS[String(iataCode).toUpperCase()];
    if (!domain) return null;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  };

  // คืน "บินตรง" หรือ "หยุดพัก x ครั้งที่ IATA1, IATA2" ตาม segments
  const getStopInfo = (itinerary) => {
    const segs = itinerary?.segments || [];
    if (segs.length <= 1) return 'บินตรง';
    const stops = segs.slice(0, -1).map((s) => s.arrival?.iataCode).filter(Boolean);
    const iataList = [...new Set(stops)].join(', ');
    return `หยุดพัก ${stops.length} ครั้งที่ ${iataList}`;
  };

  // แปลง duration แบบ ISO 8601 (PT1H10M) เป็นข้อความอ่านง่าย
  const formatDuration = (isoDuration) => {
    if (!isoDuration || typeof isoDuration !== 'string') return '';
    const m = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!m) return isoDuration;
    const hours = parseInt(m[1] || '0', 10);
    const mins = parseInt(m[2] || '0', 10);
    const parts = [];
    if (hours) parts.push(`${hours} ชม.`);
    if (mins) parts.push(`${mins} นาที`);
    return parts.length ? parts.join(' ') : '—';
  };

  // คืนค่าชั้นโดยสารภาษาไทย (ตรงกับ PlanChoiceCardFlights)
  const getCabinDisplay = (cabin) => {
    if (!cabin) return '';
    const c = String(cabin).toUpperCase();
    if (c === 'ECONOMY') return 'Economy';
    if (c === 'PREMIUM_ECONOMY') return 'Premium Economy';
    if (c === 'BUSINESS') return 'Business';
    if (c === 'FIRST') return 'First';
    return cabin;
  };

  // แสดง Sweet Alert รายละเอียดเที่ยวบินแบบ PlanChoiceCard (ราคา ชั้นโดยสาร กระเป๋า วันที่ Fare rules)
  const showFlightDetailsAlert = (f) => {
    const isRoundTrip = f.itineraries && f.itineraries.length >= 2;
    const priceTotal = parseFloat(f.price?.total || f.price?.grandTotal || 0);
    const currency = f.price?.currency || 'THB';

    // ดึงจาก Amadeus travelerPricings (ถ้ามี)
    const travelerPricings = f.travelerPricings || [];
    const firstTraveler = travelerPricings[0] || {};
    const fareDetails = firstTraveler.fareDetailsBySegment || [];
    const firstFare = fareDetails[0] || {};
    const cabinFromApi = firstFare.cabin;
    const cabinDisplay = getCabinDisplay(cabinFromApi || seatType) || getCabinDisplay(seatType);
    const includedBags = firstFare.includedCheckedBags || {};
    let baggageText = 'ไม่รวม';
    if (includedBags.weight != null) {
      baggageText = `${includedBags.weight} ${includedBags.weightUnit || 'KG'}`;
    } else if (includedBags.quantity != null) {
      baggageText = `${includedBags.quantity} ใบ`;
    }
    const pricingOpts = f.pricingOptions || {};
    const refundable = pricingOpts.refundableFare;
    const noRestriction = pricingOpts.noRestrictionFare;

    // วันที่เดินทางจาก segment แรก
    const firstSeg = f.itineraries?.[0]?.segments?.[0];
    const depAt = firstSeg?.departure?.at;
    let travelDateStr = '';
    if (depAt) {
      try {
        const d = new Date(depAt);
        travelDateStr = d.toLocaleDateString('th-TH', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
      } catch (e) {}
    }
    if (isRoundTrip && f.itineraries?.[1]?.segments?.[0]?.departure?.at) {
      try {
        const d = new Date(f.itineraries[1].segments[0].departure.at);
        travelDateStr += ` → กลับ ${d.toLocaleDateString('th-TH', { weekday: 'short', month: 'short', day: 'numeric' })}`;
      } catch (e) {}
    }

    let html = '<div style="text-align: left; max-height: 70vh; overflow-y: auto;">';

    const renderItinerary = (itinerary, label, color) => {
      const segs = itinerary?.segments || [];
      const duration = formatDuration(itinerary?.duration);
      const stopInfo = getStopInfo(itinerary);
      let block = `<p style="margin:0 0 0.4rem 0; font-weight: 600; color: ${color};">${label}</p>`;
      block += `<p style="margin:0 0 0.3rem 0; font-size: 0.9em; color: #666;">${stopInfo}${duration ? ` • ระยะเวลา ${duration}` : ''}</p>`;
      segs.forEach((seg) => {
        const dep = seg.departure?.at ? formatTime(seg.departure.at) : '--:--';
        const arr = seg.arrival?.at ? formatTime(seg.arrival.at) : '--:--';
        const from = getCityName(seg.departure?.iataCode) || seg.departure?.iataCode || '';
        const to = getCityName(seg.arrival?.iataCode) || seg.arrival?.iataCode || '';
        const airline = getAirlineName(seg.carrierCode) || seg.carrierCode || '';
        const flightNum = `${seg.carrierCode || ''} ${seg.number || ''}`.trim();
        const aircraft = seg.aircraft?.code ? ` • เครื่องบิน ${seg.aircraft.code}` : '';
        block += `<div style="margin: 0.5rem 0; padding: 0.5rem; background: #f5f5f5; border-radius: 6px; font-size: 0.9em;">`;
        block += `<strong>${airline} ${flightNum}</strong>${aircraft}<br/>`;
        block += `${dep} → ${arr}<br/>`;
        block += `${from} (${seg.departure?.iataCode || ''}) → ${to} (${seg.arrival?.iataCode || ''})`;
        block += `</div>`;
      });
      return block;
    };

    html += renderItinerary(f.itineraries?.[0], '✈ ขาไป', '#1565c0');
    if (isRoundTrip && f.itineraries?.[1]) {
      html += `<hr style="border:none; border-top:1px solid #eee; margin:0.8rem 0;"/>`;
      html += renderItinerary(f.itineraries[1], '✈ ขากลับ', '#c62828');
    }

    // ── บล็อกรายละเอียดแบบ PlanChoiceCard ──
    html += `<hr style="border:none; border-top:1px solid #eee; margin:0.8rem 0;"/>`;
    html += `<p style="margin:0 0 0.4rem 0; font-weight: 600; font-size: 0.95rem;">💰 ราคา</p>`;
    html += `<p style="margin:0 0 0.5rem 0; font-size: 1.05rem;">ราคารวม <strong style="color: #c62828;">${formatPriceInThb(priceTotal, currency)}</strong></p>`;
    if (f.price?.base && parseFloat(f.price.base) > 0) {
      html += `<p style="margin:0; font-size: 0.9em; color: #666;">ราคาฐาน ${formatPriceInThb(parseFloat(f.price.base), currency)}</p>`;
    }
    if (travelDateStr) {
      html += `<p style="margin:0.6rem 0 0; font-weight: 600; font-size: 0.95rem;">📅 วันที่เดินทาง</p>`;
      html += `<p style="margin:0; font-size: 0.9em;">${travelDateStr}</p>`;
    }
    if (cabinDisplay) {
      html += `<p style="margin:0.6rem 0 0; font-weight: 600; font-size: 0.95rem;">🪑 ชั้นโดยสาร</p>`;
      html += `<p style="margin:0; font-size: 0.9em;">${cabinDisplay}</p>`;
    }
    html += `<p style="margin:0.6rem 0 0; font-weight: 600; font-size: 0.95rem;">🧳 กระเป๋า</p>`;
    html += `<p style="margin:0; font-size: 0.9em;">กระเป๋าโหลด: ${baggageText}</p>`;
    html += `<p style="margin:0; font-size: 0.9em;">กระเป๋าถือขึ้นเครื่อง: 1 กระเป๋า (7 kg) ตามมาตรฐานสายการบิน</p>`;
    html += `<p style="margin:0.6rem 0 0; font-weight: 600; font-size: 0.95rem;">📋 เงื่อนไขค่าโดยสาร</p>`;
    if (refundable !== undefined) {
      html += `<p style="margin:0; font-size: 0.9em;">${refundable ? '✅ คืนเงินได้' : '❌ คืนเงินไม่ได้'}</p>`;
    } else {
      html += `<p style="margin:0; font-size: 0.9em;">ตรวจสอบกับสายการบิน</p>`;
    }
    if (noRestriction !== undefined) {
      html += `<p style="margin:0.2rem 0 0; font-size: 0.9em;">${noRestriction ? '✅ เลื่อนวันได้ (ตามเงื่อนไข)' : '❌ เลื่อนวันได้ตามนโยบายสายการบิน'}</p>`;
    }
    html += `<p style="margin:0.6rem 0 0; font-size: 0.85rem; color: #888;">🍽️ อาหาร: ตามชั้นโดยสาร / ซื้อบนเครื่อง • 📶 WiFi/ปลั๊ก: ตรวจสอบบนเครื่อง</p>`;
    html += '</div>';

    Swal.fire({
      title: 'รายละเอียดเที่ยวบิน',
      html,
      width: 560,
      showCloseButton: true,
      showConfirmButton: true,
      confirmButtonText: t('flights.ok') || 'ตกลง',
      confirmButtonColor: '#1565c0',
    });
  };

  // วันที่น้อยที่สุดที่เลือกได้ = วันนี้; สูงสุด = อีก 2 ปี (รองรับจองระยะไกล/ข้ามปี)
  const todayStr = React.useMemo(() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }, []);
  // รองรับการค้นหาได้ 11 เดือนนับจากวันนี้ (สอดคล้องกับ backend / Amadeus)
  const maxDateStr = React.useMemo(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 11);
    return d.toISOString().slice(0, 10);
  }, []);

  /** ข้อมูลผู้โดยสารที่ validate แล้ว สำหรับส่ง API / ใช้กับ AI
   * - adults 1-9, children/infants 0-9, อย่างน้อย 1 ผู้ใหญ่
   * - โครงสร้าง: adults, children_2_11, infants_with_seat, infants_on_lap, total, valid
   */
  const passengersForAI = React.useMemo(() => {
    const a = Math.min(9, Math.max(1, Number(adults) || 1));
    const c = Math.min(9, Math.max(0, Number(children) || 0));
    const iw = Math.min(9, Math.max(0, Number(infantsWithSeat) || 0));
    const il = Math.min(9, Math.max(0, Number(infantsOnLap) || 0));
    const total = a + c + iw + il;
    const valid = a >= 1 && total >= 1;
    return {
      adults: a,
      children_2_11: c,
      infants_with_seat: iw,
      infants_on_lap: il,
      total,
      valid,
      /** สำหรับ API search: { adults, children, infants } */
      forSearch: () => ({
        adults: a,
        children: c,
        infants: iw + il,
      }),
    };
  }, [adults, children, infantsWithSeat, infantsOnLap]);

  // ฟังก์ชันแปลงเวลาให้อ่านง่าย
  const formatTime = (isoStr) => {
    if (!isoStr) return '--:--';
    return new Date(isoStr).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  // ปกติค่า origin/destination สำหรับเปรียบเทียบ (trim + ไม่สนใจตัวพิมพ์)
  const normalizeLocation = (v) => (v || '').trim().toLowerCase();

  // --- 1. ค้นหา: ใช้พารามิเตอร์ departure_date ตามรูป image_61207d ---
  const handleSearch = async (e) => {
    e.preventDefault();
    const originTrim = (origin || '').trim();
    const destTrim = (destination || '').trim();

    setOriginError('');
    setDestinationError('');

    let hasError = false;
    if (!originTrim) {
      setOriginError(t('flights.errOriginRequired'));
      hasError = true;
    }
    if (!destTrim) {
      setDestinationError(t('flights.errDestRequired'));
      hasError = true;
    }
    if (originTrim && destTrim && normalizeLocation(originTrim) === normalizeLocation(destTrim)) {
      setOriginError(t('flights.errSameOriginDest'));
      setDestinationError(t('flights.errSameOriginDest'));
      hasError = true;
    }
    if (hasError) return;

    if (!date) {
      Swal.fire({ icon: 'warning', text: t('flights.errFillAll'), toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (date < todayStr) {
      Swal.fire({ icon: 'warning', text: t('flights.errPastDate'), toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (returnDate && returnDate < date) {
      Swal.fire({ icon: 'warning', text: t('flights.errReturnBeforeDepart'), toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    setHasSearched(true);
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
      // Backend รองรับชื่อเมือง (เช่น กรุงเทพ โตเกียว) และรหัส IATA (BKK, NRT) — จะแปลงชื่อเมืองเป็นรหัสให้
      const params = new URLSearchParams({ origin: originTrim, destination: destTrim, departure_date: date });
      if (returnDate) params.set('return_date', returnDate);
      const p = passengersForAI.forSearch();
      params.set('adults', String(p.adults));
      if (p.children > 0) params.set('children', String(p.children));
      if (p.infants > 0) params.set('infants', String(p.infants));
      if (seatType && seatType !== 'ECONOMY') params.set('cabin_class', seatType);

      const response = await fetch(`${baseUrl}/api/mcp/search/flights?${params.toString()}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });

      const resData = await response.json();
      if (!response.ok) {
        const errMsg = typeof resData.detail === 'string'
          ? resData.detail
          : (resData.detail?.[0]?.msg || resData.detail?.msg);
        throw new Error(errMsg || "ค้นหาไม่สำเร็จ");
      }

      // ดึงจากฟิลด์ flights ตามที่สำเร็จใน image_612c1a.jpg (รูปแบบ Amadeus: itineraries, price)
      setFlights(resData.flights || []);
      setLogoShowFallback(new Set());
    } catch (err) {
      Swal.fire({ icon: 'error', text: err.message, toast: true, position: 'top', showConfirmButton: false, timer: 3000 });
    } finally {
      setIsLoading(false);
    }
  };

  // --- 2. จอง: ใช้ /api/booking/create ให้ตรงกับ AITravelChat (ไม่ใช้ MCP save_booking ที่ไม่มีใน backend) ---
  const handleBooking = async (f) => {
    if (!user) {
      const { isConfirmed } = await Swal.fire({
        icon: 'warning',
        title: 'กรุณาเข้าสู่ระบบ',
        text: 'กรุณา Login ก่อนจองเที่ยวบิน',
        showCancelButton: true,
        confirmButtonText: 'เข้าสู่ระบบ',
        cancelButtonText: 'ยกเลิก'
      });
      if (isConfirmed) onSignIn?.();
      return;
    }

    const isRoundTrip = f.itineraries && f.itineraries.length >= 2;
    const outSeg = f.itineraries[0].segments[0];
    const outDepTime = formatTime(outSeg.departure?.at);
    const outArrTime = formatTime(outSeg.arrival?.at);

    let confirmHtml = `<div style="text-align: left;">
      <p style="margin: 0 0 0.3rem 0; font-weight: 600; color: #1565c0;">✈ ขาไป</p>
      <p style="margin: 0 0 0.2rem 0;">เที่ยวบิน <strong>${outSeg.carrierCode} ${outSeg.number}</strong></p>
      <p style="margin: 0 0 0.5rem 0; color: #666;">${outDepTime} → ${outArrTime}</p>`;

    if (isRoundTrip) {
      const retSeg = f.itineraries[1].segments[0];
      const retDepTime = formatTime(retSeg.departure?.at);
      const retArrTime = formatTime(retSeg.arrival?.at);
      confirmHtml += `<hr style="border: none; border-top: 1px solid #eee; margin: 0.5rem 0;" />
        <p style="margin: 0 0 0.3rem 0; font-weight: 600; color: #c62828;">✈ ขากลับ</p>
        <p style="margin: 0 0 0.2rem 0;">เที่ยวบิน <strong>${retSeg.carrierCode} ${retSeg.number}</strong></p>
        <p style="margin: 0 0 0.5rem 0; color: #666;">${retDepTime} → ${retArrTime}</p>`;
    }

    confirmHtml += `<hr style="border: none; border-top: 1px solid #eee; margin: 0.5rem 0;" />
      <p style="margin: 0; font-size: 1.1rem;">ราคารวม <strong style="color: #c62828;">${formatPriceInThb(parseFloat(f.price?.total || 0), f.price?.currency)}</strong></p>
    </div>`;

    const { isConfirmed } = await Swal.fire({
      icon: 'question',
      title: isRoundTrip ? 'ยืนยันจอง (ไป-กลับ)' : 'ยืนยันจอง (เที่ยวเดียว)',
      html: confirmHtml,
      showCancelButton: true,
      confirmButtonText: 'ยืนยันจอง',
      cancelButtonText: 'ยกเลิก',
      confirmButtonColor: '#c62828'
    });
    if (!isConfirmed) return;

    setIsLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
      const userId = user?.user_id || user?.id;
      const tripId = `flight-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

      const outboundData = [{
        selected_option: {
          raw_data: f,
          price_amount: parseFloat(f.price?.total) || 0,
          currency: f.price?.currency || "THB"
        }
      }];

      const inboundData = isRoundTrip ? [{
        selected_option: {
          raw_data: f,
          price_amount: parseFloat(f.price?.total) || 0,
          currency: f.price?.currency || "THB"
        }
      }] : [];

      const plan = {
        travel: {
          flights: {
            outbound: outboundData,
            inbound: inboundData
          }
        }
      };
      const firstSeg = f.itineraries?.[0]?.segments?.[0] || {};
      const lastSeg = f.itineraries?.[0]?.segments?.slice(-1)[0] || {};
      const travelSlots = {
        origin_city: origin,
        destination_city: destination,
        departure_date: date,
        ...(isRoundTrip && returnDate ? { return_date: returnDate } : {}),
        ...passengersForAI.forSearch(),
        flights: [{
          selected_option: {
            raw_data: f,
            price_amount: parseFloat(f.price?.total) || 0,
            currency: f.price?.currency || "THB",
            display_name: `${firstSeg.carrierCode || ''}${firstSeg.number || ''}`
          }
        }],
        source: 'flight_search',
        airline_code: firstSeg.carrierCode || '',
        flight_number: `${firstSeg.carrierCode || ''}${firstSeg.number || ''}`,
        departure_iata: firstSeg.departure?.iataCode || '',
        arrival_iata: lastSeg.arrival?.iataCode || '',
        trip_type: isRoundTrip ? 'round_trip' : 'one_way'
      };
      const payload = {
        trip_id: tripId,
        chat_id: null,
        user_id: userId,
        plan,
        travel_slots: travelSlots,
        total_price: parseFloat(f.price?.total) || 0,
        currency: f.price?.currency || "THB",
        mode: "normal"
      };

      const response = await fetch(`${baseUrl}/api/booking/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userId ? { 'X-User-ID': userId } : {})
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data?.booking_id) {
        await Swal.fire({
          icon: 'success',
          title: 'จองสำเร็จ',
          text: 'ข้อมูลบันทึกลงระบบเรียบร้อยแล้ว คุณสามารถชำระเงินได้ที่ การจองของฉัน',
          confirmButtonText: 'ไปที่การจองของฉัน',
          confirmButtonColor: '#1565c0'
        });
        onNavigateToBookings?.();
      } else {
        const errMsg = typeof data?.detail === 'string' ? data.detail : (data?.detail?.[0]?.msg || data?.message);
        await Swal.fire({
          icon: 'error',
          title: 'บันทึกไม่สำเร็จ',
          text: errMsg || 'Invalid request format',
          confirmButtonText: 'ตกลง'
        });
      }
    } catch (err) {
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: err.message,
        confirmButtonText: 'ตกลง'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flights-page" data-theme={theme}>
      <AppHeader
        activeTab="flights"
        theme={theme}
        user={user}
        onTabChange={(tab) => {
          if (tab === 'bookings') onNavigateToBookings?.();
          else if (tab === 'ai') onNavigateToAI?.();
          else if (tab === 'hotels') onNavigateToHotels?.();
          else if (tab === 'car-rentals') onNavigateToCarRentals?.();
        }}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onNavigateToHome={onNavigateToHome}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        notificationCount={notificationCount}
        notifications={notifications}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
        onClearAllNotifications={onClearAllNotifications}
        isConnected={true}
      />
      <div className="flights-content" data-theme={theme} data-font-size={fontSize}>
        <div className="flights-search-container">
          <form className="flights-search-form" onSubmit={handleSearch}>
            <div className="flights-field-wrap">
              <label className="flights-field-label" htmlFor="flights-origin">{t('flights.origin')}</label>
              <input
                id="flights-origin"
                type="text"
                className={`flights-input ${originError ? 'flights-input-error' : ''}`}
                placeholder={t('flights.origin')}
                value={origin}
                onChange={(e) => { setOrigin(e.target.value); setOriginError(''); }}
                aria-label={t('flights.origin')}
                aria-invalid={!!originError}
                aria-describedby={originError ? 'flights-origin-error' : undefined}
              />
              {originError && <span id="flights-origin-error" className="flights-field-error" role="alert">{originError}</span>}
            </div>
            <div className="flights-field-wrap">
              <label className="flights-field-label" htmlFor="flights-destination">{t('flights.destination')}</label>
              <input
                id="flights-destination"
                type="text"
                className={`flights-input ${destinationError ? 'flights-input-error' : ''}`}
                placeholder={t('flights.destination')}
                value={destination}
                onChange={(e) => { setDestination(e.target.value); setDestinationError(''); }}
                aria-label={t('flights.destination')}
                aria-invalid={!!destinationError}
                aria-describedby={destinationError ? 'flights-dest-error' : undefined}
              />
              {destinationError && <span id="flights-dest-error" className="flights-field-error" role="alert">{destinationError}</span>}
            </div>
            <div className="flights-date-field-wrap">
              <label className="flights-field-label" htmlFor="flights-date">{t('flights.date')}</label>
              <div className="flights-input-date-wrap" aria-label={t('flights.date')}>
                <input
                  id="flights-date"
                  type="date"
                  value={date}
                  onChange={(e) => {
                    const next = e.target.value;
                    setDate(next);
                    if (returnDate && next && returnDate < next) setReturnDate('');
                  }}
                  min={todayStr}
                  max={maxDateStr}
                  aria-label={t('flights.date')}
                  title={t('flights.date')}
                />
                <span className="flights-calendar-icon" aria-hidden="true"></span>
              </div>
            </div>
            <div className="flights-date-field-wrap">
              <label className="flights-field-label" htmlFor="flights-return-date">{t('flights.returnDate')}</label>
              <div className="flights-input-date-wrap" aria-label={t('flights.returnDate')}>
                <input
                  id="flights-return-date"
                  type="date"
                  value={returnDate}
                  onChange={(e) => setReturnDate(e.target.value)}
                  min={date || todayStr}
                  max={maxDateStr}
                  placeholder={t('flights.returnDate')}
                  aria-label={t('flights.returnDate')}
                  title={t('flights.returnDate')}
                />
                <span className="flights-calendar-icon" aria-hidden="true"></span>
              </div>
            </div>
            <div className="flights-field-wrap flights-option-field flights-seat-dropdown-wrap" ref={seatDropdownRef}>
              <label className="flights-field-label" id="flights-seat-type-label">{t('flights.seatType')}</label>
              <div
                ref={seatTriggerRef}
                className="flights-seat-trigger"
                onClick={() => setSeatDropdownOpen((o) => !o)}
                role="combobox"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSeatDropdownOpen((o) => !o);
                  }
                  if (e.key === 'Escape') setSeatDropdownOpen(false);
                }}
                aria-expanded={seatDropdownOpen}
                aria-haspopup="listbox"
                aria-labelledby="flights-seat-type-label"
                aria-activedescendant={seatDropdownOpen ? `flights-seat-option-${seatType}` : undefined}
              >
                <span className="flights-seat-trigger-text">{t(CABIN_OPTIONS.find((o) => o.value === seatType)?.labelKey || 'flights.cabinEconomy')}</span>
                <span className={`flights-seat-trigger-arrow ${seatDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
              </div>
              {seatDropdownOpen && seatPanelPosition && createPortal(
                <div
                  ref={seatPanelRef}
                  className="flights-seat-dropdown-panel"
                  data-theme={theme}
                  role="listbox"
                  aria-labelledby="flights-seat-type-label"
                  style={{
                    position: 'fixed',
                    top: seatPanelPosition.top,
                    left: seatPanelPosition.left,
                    width: seatPanelPosition.width,
                    minWidth: seatPanelPosition.width,
                    maxWidth: seatPanelPosition.width,
                  }}
                >
                  {CABIN_OPTIONS.map((opt) => (
                    <div
                      key={opt.value}
                      id={`flights-seat-option-${opt.value}`}
                      role="option"
                      aria-selected={seatType === opt.value}
                      className={`flights-seat-option ${seatType === opt.value ? 'selected' : ''}`}
                      onClick={() => {
                        setSeatType(opt.value);
                        setSeatDropdownOpen(false);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSeatType(opt.value);
                          setSeatDropdownOpen(false);
                        }
                      }}
                    >
                      {t(opt.labelKey)}
                    </div>
                  ))}
                </div>,
                document.body
              )}
            </div>
            <div className="flights-field-wrap flights-option-field flights-passenger-dropdown-wrap" ref={passengerDropdownRef}>
                <label className="flights-field-label">{t('flights.passengerCounts')}</label>
                <div
                  ref={passengerTriggerRef}
                  className="flights-passenger-trigger"
                  onClick={() => setPassengerDropdownOpen((o) => !o)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setPassengerDropdownOpen((o) => !o); } }}
                  aria-expanded={passengerDropdownOpen}
                  aria-haspopup="true"
                >
                  <span className="flights-passenger-trigger-icon" aria-hidden="true">👤</span>
                  <span className="flights-passenger-trigger-count">{passengersForAI.total} {t('flights.persons')}</span>
                  <span className={`flights-passenger-trigger-arrow ${passengerDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
                </div>
                {passengerDropdownOpen && passengerPanelPosition && createPortal(
                  <div
                    ref={passengerPanelRef}
                    className="flights-passenger-dropdown-panel"
                    data-theme={theme}
                    role="dialog"
                    aria-label={t('flights.passengerCounts')}
                    style={{
                      position: 'fixed',
                      top: passengerPanelPosition.top,
                      left: passengerPanelPosition.left,
                      width: passengerPanelPosition.width,
                      minWidth: passengerPanelPosition.width,
                      maxWidth: passengerPanelPosition.width,
                      marginTop: 0,
                    }}
                  >
                    <div className="flights-passenger-dropdown-row">
                      <div className="flights-passenger-dropdown-label">{t('flights.adults')}</div>
                      <div className="flights-passenger-dropdown-controls">
                        <button type="button" className="flights-passenger-btn" onClick={() => setAdults((a) => Math.max(1, a - 1))} aria-label={t('flights.adults') + ' -'}>−</button>
                        <span className="flights-passenger-dropdown-value">{adults}</span>
                        <button type="button" className="flights-passenger-btn" onClick={() => setAdults((a) => Math.min(9, a + 1))} aria-label={t('flights.adults') + ' +'}>+</button>
                      </div>
                    </div>
                    <div className="flights-passenger-dropdown-row">
                      <div className="flights-passenger-dropdown-label">
                        {t('flights.children')}
                        <span className="flights-passenger-dropdown-sublabel"> {t('flights.childAgeRange')}</span>
                      </div>
                      <div className="flights-passenger-dropdown-controls">
                        <button type="button" className="flights-passenger-btn" onClick={() => setChildren((c) => Math.max(0, c - 1))} aria-label={t('flights.children') + ' -'}>−</button>
                        <span className="flights-passenger-dropdown-value">{children}</span>
                        <button type="button" className="flights-passenger-btn" onClick={() => setChildren((c) => Math.min(9, c + 1))} aria-label={t('flights.children') + ' +'}>+</button>
                      </div>
                    </div>
                    <div className="flights-passenger-dropdown-row">
                      <div className="flights-passenger-dropdown-label">
                        {t('flights.infantsWithSeat')}
                      </div>
                      <div className="flights-passenger-dropdown-controls">
                        <button type="button" className="flights-passenger-btn" onClick={() => setInfantsWithSeat((i) => Math.max(0, i - 1))} aria-label={t('flights.infantsWithSeat') + ' -'}>−</button>
                        <span className="flights-passenger-dropdown-value">{infantsWithSeat}</span>
                        <button type="button" className="flights-passenger-btn" onClick={() => setInfantsWithSeat((i) => Math.min(9, i + 1))} aria-label={t('flights.infantsWithSeat') + ' +'}>+</button>
                      </div>
                    </div>
                    <div className="flights-passenger-dropdown-row">
                      <div className="flights-passenger-dropdown-label">{t('flights.infantsOnLap')}</div>
                      <div className="flights-passenger-dropdown-controls">
                        <button type="button" className="flights-passenger-btn" onClick={() => setInfantsOnLap((i) => Math.max(0, i - 1))} aria-label={t('flights.infantsOnLap') + ' -'}>−</button>
                        <span className="flights-passenger-dropdown-value">{infantsOnLap}</span>
                        <button type="button" className="flights-passenger-btn" onClick={() => setInfantsOnLap((i) => Math.min(9, i + 1))} aria-label={t('flights.infantsOnLap') + ' +'}>+</button>
                      </div>
                    </div>
                  </div>,
                  document.body
                )}
              </div>
            <div className="flights-btn-wrap">
              <span className="flights-field-label flights-field-label-invisible" aria-hidden="true">&#8203;</span>
              <button type="submit" className="flights-btn-search" disabled={isLoading}>
                {isLoading ? t('flights.searching') : t('flights.search')}
              </button>
            </div>
          </form>

          <div className="flights-results">
            {hasSearched && !isLoading && flights.length === 0 && (
              <div className="flights-no-data" role="status">{t('flights.noData')}</div>
            )}
            {flights.map((f, i) => {
              const outSegs = f.itineraries?.[0]?.segments || [];
              const outFirst = outSegs[0];
              const outLast = outSegs[outSegs.length - 1];
              const isRoundTrip = f.itineraries && f.itineraries.length >= 2;
              const retSegs = isRoundTrip ? (f.itineraries[1]?.segments || []) : [];
              const retFirst = retSegs[0];
              const retLast = retSegs[retSegs.length - 1];
              return (
                <div key={i} className="flights-result-card">
                  <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                    {outFirst?.carrierCode && (() => {
                      const code = outFirst.carrierCode;
                      const kiwiUrl = `https://images.kiwi.com/airlines/64/${String(code).toUpperCase()}.png`;
                      const duffelUrl = getDuffelLogoUrl(code);
                      const clearbitUrl = getClearbitLogoUrl(code);
                      const googleFaviconUrl = getGoogleFaviconUrl(code);
                      const showFallback = logoShowFallback.has(i);
                      // ใช้ Duffel ก่อน (ตาม https://duffel.com/blog/.../airline-logos-in-our-flights-api) แล้ว fallback ตามลำดับ
                      const initialSrc = duffelUrl || kiwiUrl;
                      return (
                      <div className="flight-airline-logo-wrap" title={`สายการบิน ${outFirst.carrierCode}`}>
                        {!showFallback && (
                        <img
                          src={initialSrc}
                          alt={outFirst.carrierCode}
                          className="flight-airline-logo-img"
                          onError={(e) => {
                            const img = e.target;
                            const fallback = img.nextElementSibling;
                            const src = (img.src || '').toLowerCase();
                            const isDuffel = src.includes('assets.duffel.com');
                            const isKiwi = src.includes('images.kiwi.com');
                            const isClearbit = src.includes('logo.clearbit.com');
                            const isGoogle = src.includes('google.com/s2/favicons');
                            if (isDuffel && kiwiUrl) {
                              img.src = kiwiUrl;
                              return;
                            }
                            if (isKiwi && clearbitUrl) {
                              img.src = clearbitUrl;
                              return;
                            }
                            if (isClearbit && googleFaviconUrl) {
                              img.src = googleFaviconUrl;
                              return;
                            }
                            setLogoShowFallback((prev) => new Set(prev).add(i));
                            if (fallback) {
                              img.style.display = 'none';
                              fallback.style.display = 'inline-flex';
                            }
                          }}
                        />
                        )}
                        <span className="flight-airline-logo-fallback" style={{ display: showFallback ? 'inline-flex' : 'none' }}>✈️ {outFirst.carrierCode}</span>
                      </div>
                      );
                    })()}
                    <div style={{ minWidth: 0 }}>
                    {isRoundTrip && <div className="flight-trip-label" style={{ fontSize: '0.75rem', fontWeight: 600, color: '#1565c0', marginBottom: 2 }}>✈ ขาไป</div>}
                    <div className="flight-code" style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {outFirst?.carrierCode && getAirlineName(outFirst.carrierCode) && (
                        <span style={{ fontSize: '0.85em', fontWeight: 500, color: 'var(--flight-route-color, #78909c)', opacity: 0.95 }}>{getAirlineName(outFirst.carrierCode)}</span>
                      )}
                      <span>{outFirst?.carrierCode} {outFirst?.number}</span>
                    </div>
                    <div className="flight-times">
                      {formatTime(outFirst?.departure?.at)} ➔ {formatTime(outLast?.arrival?.at)}
                    </div>
                    <div className="flight-route">
                      {getCityName(outFirst?.departure?.iataCode)} ({outFirst?.departure?.iataCode}) → {getCityName(outLast?.arrival?.iataCode)} ({outLast?.arrival?.iataCode})
                    </div>
                    {isRoundTrip && retFirst && (
                      <>
                        <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.15)', margin: '0.5rem 0' }} />
                        <div className="flight-trip-label" style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ef5350', marginBottom: 2 }}>✈ ขากลับ</div>
                        <div className="flight-code" style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {retFirst.carrierCode && getAirlineName(retFirst.carrierCode) && (
                            <span style={{ fontSize: '0.85em', fontWeight: 500, color: 'var(--flight-route-color, #78909c)', opacity: 0.95 }}>{getAirlineName(retFirst.carrierCode)}</span>
                          )}
                          <span>{retFirst.carrierCode} {retFirst.number}</span>
                        </div>
                        <div className="flight-times">
                          {formatTime(retFirst.departure?.at)} ➔ {formatTime(retLast?.arrival?.at)}
                        </div>
                        <div className="flight-route">
                          {getCityName(retFirst.departure?.iataCode)} ({retFirst.departure?.iataCode}) → {getCityName(retLast?.arrival?.iataCode)} ({retLast?.arrival?.iataCode})
                        </div>
                      </>
                    )}
                    </div>
                  </div>
                  <div className="flight-stop-info-center">
                    {isRoundTrip && retFirst
                      ? <><div>{getStopInfo(f.itineraries?.[0])}</div><div>{getStopInfo(f.itineraries?.[1])}</div></>
                      : getStopInfo(f.itineraries?.[0])}
                  </div>
                  <div className="flight-price-wrap">
                    <div className="flight-price">{formatPriceInThb(parseFloat(f.price.total), f.price.currency)}</div>
                    {isRoundTrip && <div style={{ fontSize: '0.7rem', opacity: 0.7, textAlign: 'right', marginBottom: 4 }}>ไป-กลับ</div>}
                    {!isRoundTrip && <div style={{ fontSize: '0.7rem', opacity: 0.7, textAlign: 'right', marginBottom: 4 }}>เที่ยวเดียว</div>}
                    <button type="button" className="flights-btn-detail" onClick={(e) => { e.stopPropagation(); showFlightDetailsAlert(f); }} title={t('flights.showMoreDetails')}>
                      {t('flights.showMoreDetails')}
                    </button>
                    <button type="button" className="flights-btn-book" onClick={() => handleBooking(f)}>
                      {t('flights.bookNow')}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}