import React, { useState, useMemo } from 'react';
import './PlanChoiceCard.css'; // ใช้คลาสจากไฟล์หลักร่วมกันได้

function formatMoney(value, currency = 'THB') {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return `${currency} ${value.toLocaleString('th-TH')}`;
}

// ✅ แปลง airport code เป็นชื่อสนามบินเต็ม
function getAirportName(code) {
  if (!code) return '';
  
  const airportNames = {
    // Thailand
    'BKK': 'ท่าอากาศยานสุวรรณภูมิ',
    'DMK': 'ท่าอากาศยานดอนเมือง',
    'CNX': 'ท่าอากาศยานเชียงใหม่',
    'HKT': 'ท่าอากาศยานภูเก็ต',
    'USM': 'ท่าอากาศยานสมุย',
    'KBV': 'ท่าอากาศยานกระบี่',
    // China
    'TAO': 'ท่าอากาศยานชิงเต่า (Qingdao Liuting International Airport)',
    'PEK': 'ท่าอากาศยานปักกิ่ง (Beijing Capital International Airport)',
    'PVG': 'ท่าอากาศยานเซี่ยงไฮ้ผู่ตง (Shanghai Pudong International Airport)',
    'CAN': 'ท่าอากาศยานกวางโจว (Guangzhou Baiyun International Airport)',
    // Korea
    'ICN': 'ท่าอากาศยานนานาชาติอินชอน (Incheon International Airport)',
    'GMP': 'ท่าอากาศยานกิมโป (Gimpo International Airport)',
    // Japan
    'NRT': 'ท่าอากาศยานนาริตะ (Narita International Airport)',
    'HND': 'ท่าอากาศยานฮาเนดะ (Haneda Airport)',
    'KIX': 'ท่าอากาศยานคันไซ (Kansai International Airport)',
    // Singapore
    'SIN': 'ท่าอากาศยานชางงี (Changi Airport)',
    // Malaysia
    'KUL': 'ท่าอากาศยานกัวลาลัมเปอร์ (Kuala Lumpur International Airport)',
    // Vietnam
    'SGN': 'ท่าอากาศยานโฮจิมินห์ (Tan Son Nhat International Airport)',
    'HAN': 'ท่าอากาศยานฮานอย (Noi Bai International Airport)',
    // Taiwan
    'TPE': 'ท่าอากาศยานไต้หวัน (Taiwan Taoyuan International Airport)',
    // Hong Kong
    'HKG': 'ท่าอากาศยานฮ่องกง (Hong Kong International Airport)',
  };
  
  return airportNames[code.toUpperCase()] || code;
}

// ✅ คำนวณ layover time (เวลารอคอยระหว่าง segments)
function calculateLayoverTime(prevSegment, nextSegment) {
  if (!prevSegment || !nextSegment) return null;
  
  const prevArrival = prevSegment.arrive_at || prevSegment.depart_at;
  const nextDeparture = nextSegment.depart_at || nextSegment.depart_at;
  
  if (!prevArrival || !nextDeparture) return null;
  
  try {
    const prevTime = new Date(prevArrival);
    const nextTime = new Date(nextDeparture);
    const diffMs = nextTime.getTime() - prevTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (diffHours < 0 || diffMinutes < 0) return null; // Invalid time
    
    if (diffHours > 0) {
      return `${diffHours}ชม ${diffMinutes}นาที`;
    } else {
      return `${diffMinutes}นาที`;
    }
  } catch (e) {
  }
}

// ✅ คำนวณราคาต่อ segment (แบ่งตามสัดส่วน duration)
function calculateSegmentPrice(totalPrice, segmentDuration, totalDuration) {
  if (!totalPrice || !segmentDuration || !totalDuration || totalDuration === 0) {
  }
  
  try {
    // Parse ISO 8601 duration (e.g., "PT4H25M")
    const parseDuration = (durationStr) => {
      if (!durationStr || typeof durationStr !== 'string' || !durationStr.startsWith('PT')) return 0;
      let hours = 0;
      let minutes = 0;
      const hourMatch = durationStr.match(/(\d+)H/);
      const minuteMatch = durationStr.match(/(\d+)M/);
      if (hourMatch) hours = parseInt(hourMatch[1]);
      if (minuteMatch) minutes = parseInt(minuteMatch[1]);
      return hours * 3600 + minutes * 60; // Return seconds
    };
    
    const segSeconds = parseDuration(segmentDuration);
    const totalSeconds = parseDuration(totalDuration);
    
    if (segSeconds === 0 || totalSeconds === 0) return null;
    
    const segmentPrice = (totalPrice * segSeconds) / totalSeconds;
    return Math.round(segmentPrice);
  } catch (e) {
  }
}

// ✅ ดึง airline logo จาก CDN หรือ Google - หลายแหล่งข้อมูล
function getAirlineLogoUrl(carrierCode, attempt = 1) {
  if (!carrierCode) return null;
  
  const code = carrierCode.toUpperCase();
  
  // ใช้หลายแหล่งข้อมูลตามลำดับความน่าจะเป็น
  switch (attempt) {
    case 1:
      // Skyscanner CDN (มี airline logos มากที่สุด)
      return `https://logos.skyscnr.com/images/airlines/favicon/${code}.png`;
    case 2:
      // Avicon.io API (fallback 1)
      return `https://avicon.io/api/airlines/${code}`;
    case 3:
      // AirlineCodes.info (fallback 2)
      return `https://www.airlinecodes.info/airline-logos/${code}.png`;
    case 4:
      // ContentSquare CDN (fallback 3)
      return `https://d1yjjnpx0p53s8.cloudfront.net/images/airlines/${code}.png`;
    case 5:
      // Travelpayouts (fallback 4)
      return `https://pics.avs.io/200/200/${code}.png`;
    default:
      return null;
  }
}

// ✅ Component สำหรับแสดง airline logo พร้อม fallback หลายแหล่งข้อมูล
function AirlineLogo({ carrierCode, size = 40, style = {} }) {
  const [logoAttempt, setLogoAttempt] = React.useState(1);
  const [logoError, setLogoError] = React.useState(false);
  const [currentUrl, setCurrentUrl] = React.useState(null);
  
  React.useEffect(() => {
    if (carrierCode) {
      setLogoAttempt(1);
      setLogoError(false);
      setCurrentUrl(getAirlineLogoUrl(carrierCode, 1));
    }
  }, [carrierCode]);
  
  const handleImageError = () => {
    // ลอง fallback URLs ตามลำดับ (1-5)
    if (logoAttempt < 5) {
      const nextAttempt = logoAttempt + 1;
      setLogoAttempt(nextAttempt);
      setCurrentUrl(getAirlineLogoUrl(carrierCode, nextAttempt));
    } else {
      // ถ้าทุก URL ล้มเหลว ให้แสดง carrier code แทน
      setLogoError(true);
    }
  };
  
  // ถ้าไม่มี logo หรือ error ให้แสดง carrier code แทน
  if (!carrierCode || logoError || !currentUrl) {
    return (
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '6px',
        background: 'rgba(255, 255, 255, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: `${Math.max(10, size * 0.35)}px`,
        fontWeight: '600',
        color: '#fff',
        ...style
      }}>
        {carrierCode || 'N/A'}
      </div>
    );
  }
  
  return (
    <img
      src={currentUrl}
      alt={`${carrierCode} logo`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '6px',
        objectFit: 'contain',
        background: 'rgba(255, 255, 255, 0.05)',
        padding: '4px',
        ...style
      }}
      onError={handleImageError}
      onLoad={() => {
        // Reset error state เมื่อโหลดสำเร็จ
        if (logoError) setLogoError(false);
      }}
    />
  );
}

// ✅ แปลง airline IATA code เป็นชื่อเต็ม
function getAirlineName(code) {
  if (!code) return 'Unknown';
  
  const airlineNames = {
    'TG': 'Thai Airways',
    'FD': 'Thai AirAsia',
    'SL': 'Thai Lion Air',
    'PG': 'Bangkok Airways',
    'VZ': 'Thai Vietjet Air',
    'WE': 'Thai Smile',
    'XJ': 'Thai AirAsia X',
    'DD': 'Nok Air',
    'Z2': 'AirAsia Philippines',
    'AK': 'AirAsia',
    'D7': 'AirAsia X',
    'QZ': 'Indonesia AirAsia',
    'JT': 'Lion Air',
    'SJ': 'Sriwijaya Air',
    'GA': 'Garuda Indonesia',
    'SQ': 'Singapore Airlines',
    'MI': 'SilkAir',
    'TR': 'Scoot',
    '3K': 'Jetstar Asia',
    'QF': 'Qantas',
    'JQ': 'Jetstar',
    'MH': 'Malaysia Airlines',
    'OD': 'Malindo Air',
    'VN': 'Vietnam Airlines',
    'VJ': 'Vietjet Air',
    'BL': 'Jetstar Pacific',
    'CX': 'Cathay Pacific',
    'KA': 'Cathay Dragon',
    'HX': 'Hong Kong Airlines',
    'UO': 'Hong Kong Express',
    'JL': 'Japan Airlines',
    'NH': 'All Nippon Airways',
    'MM': 'Peach Aviation',
    'GK': 'Jetstar Japan',
    'KE': 'Korean Air',
    'OZ': 'Asiana Airlines',
    'TW': "T'way Air",
    '7C': 'Jeju Air',
    'ZE': 'Eastar Jet',
    'CA': 'Air China',
    'CZ': 'China Southern Airlines',
    'MU': 'China Eastern Airlines',
    '3U': 'Sichuan Airlines',
    '9C': 'Spring Airlines',
    'HO': 'Juneyao Airlines',
    'FM': 'Shanghai Airlines',
    'MF': 'Xiamen Airlines',
  };
  
  return airlineNames[code.toUpperCase()] || code;
}

// ✅ แปลง aircraft code เป็นชื่อเต็ม
function getAircraftName(code) {
  if (!code) return 'Unknown';
  
  const aircraftNames = {
    '737': 'Boeing 737',
    '738': 'Boeing 737-800',
    '739': 'Boeing 737-900',
    '73H': 'Boeing 737-800',
    '73M': 'Boeing 737 MAX',
    '320': 'Airbus A320',
    '321': 'Airbus A321',
    '32A': 'Airbus A320',
    '32B': 'Airbus A321',
    '32N': 'Airbus A320neo',
    '32Q': 'Airbus A321neo',
    '330': 'Airbus A330',
    '332': 'Airbus A330-200',
    '333': 'Airbus A330-300',
    '350': 'Airbus A350',
    '351': 'Airbus A350-1000',
    '359': 'Airbus A350-900',
    '380': 'Airbus A380',
    '777': 'Boeing 777',
    '77W': 'Boeing 777-300ER',
    '787': 'Boeing 787',
    '788': 'Boeing 787-8',
    '789': 'Boeing 787-9',
    '78X': 'Boeing 787-10',
    'AT7': 'ATR 72',
    'ATR': 'ATR 72',
    'CRJ': 'Bombardier CRJ',
    'E90': 'Embraer E190',
    'E95': 'Embraer E195',
  };
  
  return aircraftNames[code.toUpperCase()] || `เครื่องบิน ${code}`;
}

// ✅ แปลง ISO 8601 duration (PT1H15M) เป็นข้อความอ่านง่าย
function formatDuration(durationStr) {
  if (!durationStr || typeof durationStr !== 'string') return '';
  
  // Parse ISO 8601 duration (e.g., "PT4H25M" = 4 hours 25 minutes)
  if (durationStr.startsWith('PT')) {
    let hours = 0;
    let minutes = 0;
    
    try {
      if (durationStr.includes('H')) {
        const hoursPart = durationStr.split('H')[0].replace('PT', '');
        hours = parseInt(hoursPart) || 0;
        const remaining = durationStr.split('H')[1] || '';
        if (remaining.includes('M')) {
          const minutesPart = remaining.split('M')[0];
          minutes = parseInt(minutesPart) || 0;
        }
      } else {
        const remaining = durationStr.replace('PT', '');
        if (remaining.includes('M')) {
          const minutesPart = remaining.split('M')[0];
          minutes = parseInt(minutesPart) || 0;
        }
      }
      
      // Format as readable Thai text
      const parts = [];
      if (hours > 0) {
        parts.push(`${hours}ชม`);
      }
      if (minutes > 0) {
        parts.push(`${minutes}นาที`);
      }
      
      return parts.length > 0 ? parts.join(' ') : 'ไม่ระบุ';
    } catch (e) {
      return durationStr; // Return original if parsing fails
    }
  }
  
  return durationStr; // Return original if not ISO 8601 format
}

// ✅ คำนวณ CO2 emissions (จาก distance ใน km)
function calculateCO2e(distanceKm) {
  if (!distanceKm || distanceKm <= 0) return 0;
  // Rough estimate: ~220 kg CO2e per 1000 km for economy class
  const estimatedCO2 = Math.round(distanceKm * 0.22); // ~220g per km average
  return estimatedCO2;
}

// ✅ หา flight type (บินตรง หรือ ต่อเครื่อง)
function getFlightType(segments) {
  if (!segments || segments.length === 0) return 'บินตรง';
  return segments.length > 1 ? 'ต่อเครื่อง' : 'บินตรง';
}

// ✅ Format arrival time with +1 for next day
function getArrivalTimeDisplay(arriveAt, arrivePlus) {
  if (!arriveAt) return '';
  
  let timeStr = '';
  if (typeof arriveAt === 'string' && arriveAt.includes('T')) {
    const timePart = arriveAt.split('T')[1]?.split(':').slice(0, 2).join(':') || '';
    timeStr = timePart;
  } else if (typeof arriveAt === 'string') {
    timeStr = arriveAt;
  }
  
  if (arrivePlus) {
    return `${timeStr} ${arrivePlus}`;
  }
  
  return timeStr;
}

function getFirstSegment(flight) {
  return flight?.segments?.length ? flight.segments[0] : null;
}

function getLastSegment(flight) {
  return flight?.segments?.length ? flight.segments[flight.segments.length - 1] : null;
}

function stopsLabel(flight) {
  const n = flight?.segments?.length || 0;
  if (!n) return null;
  const stops = Math.max(0, n - 1);
  return stops === 0 ? 'Non-stop' : `${stops} stop`;
}

function carriersLabel(flight) {
  const segs = flight?.segments || [];
  if (!segs.length) return null;
  const carriers = [];
  for (const s of segs) {
    const c = s?.carrier;
    if (c && !carriers.includes(c)) carriers.push(c);
  }
  return carriers.length ? carriers.join(', ') : null;
}

export default function PlanChoiceCard({ choice, onSelect }) {
  const [showItinerary, setShowItinerary] = useState(false);
  const [showFlightDetails, setShowFlightDetails] = useState(false);
  
  
  const {
    id,
    label,
    description,
    tags,
    recommended,
    flight,
    flight_details, // ✅ ข้อมูลรายละเอียดไฟท์บิน
    hotel,
    car, // ✅ รถเช่า
    transport,
    currency,
    total_price,
    total_price_text,
    price_breakdown,
    title, // เผื่อ backend ส่ง title มา (เช่น "🟢 ช้อยส์ 1 (แนะนำ) ...")
    ground_transport, // ✅ ข้อมูลการเดินทาง/ขนส่ง
    itinerary, // ✅ ข้อมูล itinerary
    is_fastest, // ✅ เร็วสุดสะดวกสุด
    is_day_trip, // ✅ 1 วันไปกลับ
    display_text, // ✅ ข้อความที่ backend สร้างไว้แล้ว (สำหรับ slot-based workflow)
    slot, // ✅ slot type (flight, hotel, etc.)
  } = choice || {};
  

  const displayCurrency =
    (price_breakdown && price_breakdown.currency) ||
    currency ||
    flight?.currency ||
    hotel?.currency ||
    'THB';

  const displayTotalPrice =
    typeof total_price === 'number'
      ? `${displayCurrency} ${total_price.toLocaleString('th-TH')}`
      : (total_price_text || null);

  // ===== Flight computed fields (from Amadeus structure) =====
  const firstSeg = getFirstSegment(flight);
  const lastSeg = getLastSegment(flight);
  

  const flightRoute =
    firstSeg && lastSeg
      ? `${firstSeg.from} → ${lastSeg.to}`
      : null;

  const flightTime =
    firstSeg && lastSeg
      ? `${firstSeg.depart_time || ''} → ${lastSeg.arrive_time || ''}${lastSeg.arrive_plus ? ` ${lastSeg.arrive_plus}` : ''}`.trim()
      : null;

  const flightStops = stopsLabel(flight);
  const flightCarriers = carriersLabel(flight);
  const flightPrice = formatMoney(
    typeof flight?.price_total === 'number' ? flight.price_total : null,
    flight?.currency || displayCurrency
  );
  
  // ✅ คำนวณเวลาเดินทางทั้งหมด (รวม layover times)
  let totalJourneyTime = null;
  if (firstSeg && lastSeg && flight?.segments && flight.segments.length > 0) {
    try {
      // วิธีที่ 1: ถ้ามี depart_at และ arrive_at ที่ถูกต้อง
      const firstDepart = firstSeg.depart_at || firstSeg.depart_time;
      let lastArrive = lastSeg.arrive_at || lastSeg.arrive_time;
      
      // ✅ Handle arrive_plus (เช่น +1, +2 วัน)
      if (lastArrive && lastSeg.arrive_plus) {
        try {
          const arriveDate = new Date(lastArrive);
          const plusMatch = String(lastSeg.arrive_plus).match(/\+(\d+)/);
          if (plusMatch) {
            const plusDays = parseInt(plusMatch[1]) || 0;
            arriveDate.setDate(arriveDate.getDate() + plusDays);
            lastArrive = arriveDate.toISOString();
          }
        } catch (e) {
          // ถ้า parse ไม่ได้ใช้ค่าเดิม
        }
      }
      
      
      // วิธีที่ 2: คำนวณจาก duration + layover (ถ้าไม่มี depart_at/arrive_at)
      if (!firstDepart || !lastArrive) {
        // คำนวณจาก duration ของแต่ละ segment + layover times
        let totalSeconds = 0;
        
        // Parse duration ของแต่ละ segment
        const parseDuration = (durationStr) => {
          if (!durationStr || typeof durationStr !== 'string' || !durationStr.startsWith('PT')) return 0;
          let hours = 0, minutes = 0;
          const hourMatch = durationStr.match(/(\d+)H/);
          const minuteMatch = durationStr.match(/(\d+)M/);
          if (hourMatch) hours = parseInt(hourMatch[1]);
          if (minuteMatch) minutes = parseInt(minuteMatch[1]);
          return hours * 3600 + minutes * 60; // Return seconds
        };
        
        // รวม duration ของทุก segments
        for (const seg of flight.segments) {
          if (seg.duration) {
            totalSeconds += parseDuration(seg.duration);
          }
        }
        
        // รวม layover times
        for (let i = 0; i < flight.segments.length - 1; i++) {
          const prevSeg = flight.segments[i];
          const nextSeg = flight.segments[i + 1];
          const layover = calculateLayoverTime(prevSeg, nextSeg);
          if (layover) {
            // Parse layover string เช่น "5ชม 30นาที"
            const hourMatch = layover.match(/(\d+)ชม/);
            const minuteMatch = layover.match(/(\d+)นาที/);
            if (hourMatch) totalSeconds += parseInt(hourMatch[1]) * 3600;
            if (minuteMatch) totalSeconds += parseInt(minuteMatch[1]) * 60;
          }
        }
        
        if (totalSeconds > 0) {
          const totalHours = Math.floor(totalSeconds / 3600);
          const totalMinutes = Math.floor((totalSeconds % 3600) / 60);
          
          if (totalHours > 0) {
            totalJourneyTime = `${totalHours}ชม ${totalMinutes}นาที`;
          } else {
            totalJourneyTime = `${totalMinutes}นาที`;
          }
        }
      } else {
        // วิธีที่ 1: ใช้ depart_at และ arrive_at
        const firstTime = new Date(firstDepart);
        const lastTime = new Date(lastArrive);
        
        // ตรวจสอบว่า parse ได้ถูกต้อง
        if (!isNaN(firstTime.getTime()) && !isNaN(lastTime.getTime())) {
          const diffMs = lastTime.getTime() - firstTime.getTime();
          
          
          if (diffMs > 0) {
            const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
            const totalMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            
            if (totalHours > 0) {
              totalJourneyTime = `${totalHours}ชม ${totalMinutes}นาที`;
            } else {
              totalJourneyTime = `${totalMinutes}นาที`;
            }
          }
        }
      }
      
      if (totalJourneyTime) {
      }
    } catch (e) {
      // ถ้าคำนวณไม่ได้ก็ไม่แสดง
    }
  }
  

  // ===== Hotel computed fields (from Amadeus structure) =====
  const hotelName = hotel?.hotelName || null;
  const hotelNights = hotel?.nights != null ? hotel.nights : null;
  const hotelBoard = hotel?.boardType || null;
  const hotelPrice = formatMoney(
    typeof hotel?.price_total === 'number' ? hotel.price_total : null,
    hotel?.currency || displayCurrency
  );

  // ===== Transport (your legacy structure) =====
  const transportMode = transport?.mode || null;
  const transportNote = transport?.note || null;

  // ===== Price breakdown =====
  const breakdownFlight =
    typeof price_breakdown?.flight_total === 'number'
      ? formatMoney(price_breakdown.flight_total, displayCurrency)
      : null;

  const breakdownHotel =
    typeof price_breakdown?.hotel_total === 'number'
      ? formatMoney(price_breakdown.hotel_total, displayCurrency)
      : null;

  // Extract transport info (transport already destructured from choice above)
  const transportType = transport?.type || null;
  const transportData = transport?.data || null;
  
  const breakdownTransport =
    typeof price_breakdown?.transport_total === 'number'
      ? formatMoney(price_breakdown.transport_total, displayCurrency)
      : null;

  return (
    <div className={`plan-card ${recommended ? 'plan-card-recommended' : ''}`}>
      {/* Header */}
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">
            {/* ถ้ามี title จาก backend ให้ใช้ title เลย */}
            {title
              ? title
              : `ช้อยส์ ${id}${label ? ` — ${label}` : ''}`
            }
          </span>
          {/* ✅ แสดง recommended tag ถ้า recommended และไม่มีใน tags */}
          {recommended && (!tags || !tags.includes('แนะนำ')) && (
            <span className="plan-card-tag">แนะนำ</span>
          )}
          {/* ✅ แสดง tag "บินตรง" ถ้าเป็น non-stop และไม่มีใน tags */}
          {(choice?.is_non_stop || (flight && flightStops === 'Non-stop')) && flight && (!tags || !tags.includes('บินตรง')) && (
            <span className="plan-card-tag" style={{ 
              background: 'rgba(227, 242, 253, 0.3)', 
              color: '#1976d2',
              marginLeft: '6px',
              fontSize: '13px',
              padding: '3px 10px',
              backdropFilter: 'blur(4px)'
            }}>
              ✈️ บินตรง
            </span>
          )}
        </div>

        {tags && Array.isArray(tags) && tags.length > 0 && (
          <div className="plan-card-tags">
            {/* ✅ กรอง tags ไม่ให้ซ้ำกัน และกรอง "แนะนำ" และ "บินตรง" ออกถ้าแสดงใน header แล้ว */}
            {[...new Set(tags)]
              .filter(tag => {
                // กรอง "แนะนำ" ถ้าแสดงใน header แล้ว
                if (tag === 'แนะนำ' && recommended) return false;
                // กรอง "บินตรง" ถ้าแสดงใน header แล้ว
                if (tag === 'บินตรง' && (choice?.is_non_stop || (flight && flightStops === 'Non-stop'))) return false;
                return true;
              })
              .map((tag, idx) => (
                <span key={idx} className="plan-tag-pill">
                  {tag}
                </span>
              ))}
          </div>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="plan-card-desc">{description}</p>
      )}

      {/* Flight Section - แสดงรายละเอียด segments ก่อน */}
      {flight && flight.segments && flight.segments.length > 0 && (
        <div className="plan-card-section">
          {/* #region agent log */}
          {/* #endregion */}
          
          <div className="plan-card-section-title">✈️ รายละเอียดเที่ยวบิน</div>
            <div className="plan-card-section-body">
              {/* Header - Airline, Times, Route, Type */}
              {firstSeg && lastSeg && (
                <div style={{
                  marginBottom: '16px',
                  padding: '12px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.15)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
                    {/* Left: Airline Info */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '120px' }}>
                      <AirlineLogo 
                        carrierCode={firstSeg.carrier} 
                        size={40}
                      />
                      <div>
                        <div style={{ fontSize: '14px', fontWeight: '600' }}>{getAirlineName(firstSeg.carrier)}</div>
                        <div style={{ fontSize: '12px', opacity: 0.7 }}>{firstSeg.carrier}{firstSeg.flight_number || ''}</div>
                      </div>
                    </div>

                    {/* Center: Flight Times & Details */}
                    <div style={{ flex: 1, minWidth: '200px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '16px', fontWeight: '600' }}>{firstSeg.depart_time || 'N/A'}</span>
                        <span style={{ opacity: 0.6 }}>–</span>
                        <span style={{ fontSize: '16px', fontWeight: '600' }}>
                          {getArrivalTimeDisplay(lastSeg.arrive_at, lastSeg.arrive_plus) || lastSeg.arrive_time || 'N/A'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '13px', opacity: 0.8 }}>
                        {totalJourneyTime && <span>⏱️ {totalJourneyTime}</span>}
                        {flightRoute && <span>•</span>}
                        {flightRoute && <span>📍 {flightRoute}</span>}
                        {flightStops && <span>•</span>}
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '500',
                          background: flightStops === 'Non-stop' ? 'rgba(74, 222, 128, 0.2)' : 'rgba(255, 193, 7, 0.2)',
                          color: flightStops === 'Non-stop' ? '#4ade80' : '#ffc107'
                        }}>
                          {getFlightType(flight.segments) === 'บินตรง' ? '✈️ บินตรง' : '🔀 ต่อเครื่อง'}
                        </span>
                      </div>
                      {/* Connection details */}
                      {flight.segments.length > 1 && (
                        <div style={{ marginTop: '6px', fontSize: '12px', opacity: 0.7 }}>
                          {flight.segments.slice(0, -1).map((seg, idx) => {
                            const nextSeg = flight.segments[idx + 1];
                            const layover = calculateLayoverTime(seg, nextSeg);
                            return layover ? (
                              <span key={idx} style={{ marginRight: '8px' }}>
                                {seg.to ? `รอที่ ${seg.to}` : 'รอต่อเครื่อง'} ({layover})
                              </span>
                            ) : null;
                          })}
                        </div>
                      )}
                      {/* CO2 Emissions */}
                      {firstSeg.from && lastSeg.to && (
                        <div style={{ marginTop: '6px', fontSize: '12px', opacity: 0.7 }}>
                          <span>🌱 CO2e: ~{calculateCO2e(flightRoute ? 1500 : 0)} กก. (ประมาณการ)</span>
                        </div>
                      )}
                    </div>

                    {/* Right: Price */}
                    <div style={{ textAlign: 'right', minWidth: '100px' }}>
                      {flightPrice && (
                        <div style={{ fontSize: '18px', fontWeight: '700', marginBottom: '4px' }}>
                          {flightPrice}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
                {/* #region agent log */}
                {/* #endregion */}
                  
                {/* แสดงทุก segments */}
                {flight.segments && flight.segments.length > 0 ? (
                  <>
                    {flight.segments.map((seg, idx) => {
                    // คำนวณราคาต่อ segment (แบ่งตามสัดส่วน duration)
                    const totalFlightPrice = typeof flight?.price_total === 'number' ? flight.price_total : null;
                    let segmentPrice = null;
                    
                    if (totalFlightPrice && seg.duration) {
                      // Parse duration ของ segment
                      const parseDuration = (durationStr) => {
                        if (!durationStr || typeof durationStr !== 'string' || !durationStr.startsWith('PT')) return 0;
                        let hours = 0, minutes = 0;
                        const hourMatch = durationStr.match(/(\d+)H/);
                        const minuteMatch = durationStr.match(/(\d+)M/);
                        if (hourMatch) hours = parseInt(hourMatch[1]);
                        if (minuteMatch) minutes = parseInt(minuteMatch[1]);
                        return hours * 3600 + minutes * 60; // Return seconds
                      };
                      
                      // คำนวณ total duration ของทุก segments
                      const totalDuration = flight.segments?.reduce((sum, s) => {
                        return sum + parseDuration(s.duration || '');
                      }, 0) || 0;
                      
                      const segDurationStr = seg.duration;
                      const segSeconds = parseDuration(segDurationStr);
                      
                      if (totalDuration > 0) {
                        segmentPrice = Math.round((totalFlightPrice * segSeconds) / totalDuration);
                      }
                    }
                    
                    // คำนวณ layover time (ถ้ามี segment ถัดไป)
                    const nextSegment = idx < flight.segments.length - 1 ? flight.segments[idx + 1] : null;
                    const layoverTime = calculateLayoverTime(seg, nextSegment);
                    
                    
                    return (
                    <div key={idx} style={{ marginBottom: idx < flight.segments.length - 1 ? '12px' : '0' }}>
                      <div style={{ fontWeight: '600', marginBottom: '6px', fontSize: '16px', lineHeight: '1.4', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>
                          {seg.direction === 'ขาไป' ? '🛫' : seg.direction === 'ขากลับ' ? '🛬' : '✈️'}
                        </span>
                        <span>
                          {seg.direction 
                            ? seg.direction 
                            : (idx === 0 ? 'ขาไป' : (idx === 1 && flight.segments.length === 2 ? 'ขากลับ' : `ไฟลท์ ${idx + 1}`))
                          }
                        </span>
                      </div>
                  <div style={{ fontSize: '16px', marginBottom: '4px', lineHeight: '1.5' }}>
                    สายการบิน: {getAirlineName(seg.carrier)}
                    {seg.carrier && seg.flight_number ? ` • ${seg.carrier}${seg.flight_number}` : seg.flight_number ? ` • ${seg.flight_number}` : ''}
                    {/* ✅ แสดง Operating Carrier ถ้ามี */}
                    {seg.operating && seg.operating !== seg.carrier && (
                       <span style={{ fontSize: '14px', fontStyle: 'italic', marginLeft: '6px', opacity: 0.8 }}>
                         (Operated by {getAirlineName(seg.operating)})
                       </span>
                    )}
                  </div>
                  <div className="plan-card-small">
                    เส้นทาง: {seg.from || '-'} → {seg.to || '-'}
                    {/* ✅ แสดง Terminal ถ้ามี */}
                    {seg.departure_terminal && (
                      <span style={{ marginLeft: '4px' }}>
                        (Term {seg.departure_terminal})
                      </span>
                    )}
                    {seg.arrival_terminal && (
                        <span style={{ marginLeft: '4px' }}>
                            → (Term {seg.arrival_terminal})
                        </span>
                    )}
                  </div>
                  <div className="plan-card-small">
                    ออก: {seg.depart_time || '-'} → ถึง: {seg.arrive_time || '-'}{seg.arrive_plus ? ` ${seg.arrive_plus}` : ''}
                  </div>
                  {seg.aircraft_code && (
                    <div className="plan-card-small">
                      เครื่อง: {getAircraftName(seg.aircraft_code)}
                    </div>
                  )}
                  {seg.duration && (
                    <div className="plan-card-small">
                      ระยะเวลา: {formatDuration(seg.duration)}
                    </div>
                  )}
                        {/* #region agent log */}
                        {/* #endregion */}
                        {/* ✅ แสดงเวลารอคอยต่อเครื่อง พร้อมชื่อสนามบินเต็ม */}
                        {layoverTime && (
                          <div className="plan-card-small" style={{ 
                            fontSize: '16px', 
                            color: 'rgba(255, 215, 0, 0.95)',
                            marginTop: '6px',
                            padding: '4px 8px',
                            background: 'rgba(255, 215, 0, 0.2)',
                            borderRadius: '4px',
                            display: 'inline-block',
                            fontWeight: '500'
                          }}>
                            <div>
                              ⏱️ รอคอยต่อเครื่อง: {layoverTime}
                            </div>
                            {seg.to && (
                              <div style={{ 
                                fontSize: '14px', 
                                marginTop: '4px',
                                opacity: 0.9
                              }}>
                                ที่ {getAirportName(seg.to)}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                    })}
                  </>
            ) : (
              <div>มีข้อมูลเที่ยวบิน (แต่ไม่พบ segment)</div>
            )}

                {/* ✅ สรุปข้อมูลที่ท้ายรายละเอียด segments */}
                <div style={{ 
                  marginTop: '16px', 
                  paddingTop: '12px', 
                  borderTop: '1px solid rgba(255, 255, 255, 0.25)'
                }}>
                  {/* Stops และ Airlines */}
                  {(flightStops || flightCarriers) && (
                    <div className="plan-card-small" style={{ marginBottom: '8px', fontSize: '16px', lineHeight: '1.6' }}>
              {flightStops && <span style={{ fontWeight: '500' }}>{flightStops}</span>}
              {flightCarriers && <span style={{ fontWeight: '500' }}> • {flightCarriers}</span>}
            </div>
                  )}
            
                  {/* Cabin และ Baggage และ Visa Warning */}
            {(flight?.cabin || flight?.baggage || flight?.visa_warning) && (
                    <div className="plan-card-small" style={{ marginBottom: '6px', fontSize: '16px', lineHeight: '1.6' }}>
                {flight?.cabin && <div style={{ marginBottom: '4px' }}>ชั้นโดยสาร: {flight.cabin}</div>}
                {flight?.baggage && <div>กระเป๋าโหลด: {flight.baggage}</div>}
                {/* ⚠️ Transit Visa Warning - Production-ready */}
                {flight?.visa_warning && (
                  <div style={{
                    marginTop: '8px',
                    padding: '10px 12px',
                    background: 'rgba(255, 77, 79, 0.15)',
                    border: '1px solid rgba(255, 77, 79, 0.4)',
                    borderRadius: '6px',
                    color: '#ff4d4f',
                    fontWeight: '600',
                    fontSize: '15px',
                    lineHeight: '1.5'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '18px' }}>⚠️</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '700', marginBottom: '4px' }}>คำเตือนเรื่องวีซ่า (Visa Warning)</div>
                        <div>{flight.visa_warning}</div>
                        <div style={{ 
                          marginTop: '6px', 
                          fontSize: '13px', 
                          fontWeight: '400',
                          color: 'rgba(255, 77, 79, 0.9)',
                          lineHeight: '1.4'
                        }}>
                          💡 <strong>แนะนำ:</strong> กรุณาตรวจสอบความต้องการวีซ่าสำหรับประเทศปลายทางและประเทศที่ต้องผ่านทาง (Transit) 
                          ก่อนทำการจอง หากคุณมีวีซ่าที่ถูกต้องแล้ว กรุณาอัพเดทข้อมูลในหน้าโปรไฟล์
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* ✅ Visa Requirement Check (แสดงถ้ามีข้อมูล transit countries) */}
                {flight?.segments && flight.segments.length > 1 && (
                  <div style={{
                    marginTop: '8px',
                    padding: '10px 12px',
                    background: 'rgba(255, 193, 7, 0.15)',
                    border: '1px solid rgba(255, 193, 7, 0.4)',
                    borderRadius: '6px',
                    fontSize: '14px',
                    lineHeight: '1.5'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ fontSize: '16px' }}>✈️</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '600', marginBottom: '4px', color: '#f57c00' }}>
                          เที่ยวบินนี้มีการแวะระหว่างทาง
                        </div>
                        <div style={{ fontSize: '13px', color: '#e65100' }}>
                          • เที่ยวบินนี้มี {flight.segments.length - 1} จุดแวะ (Transit)<br/>
                          • ตรวจสอบว่าคุณมีวีซ่าสำหรับประเทศที่ต้องผ่านทางหรือไม่<br/>
                          • บางประเทศอาจต้องใช้วีซ่า Transit แม้ไม่ต้องออกจากสนามบิน
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

                  {/* เวลาเดินทางทั้งหมด */}
                  {totalJourneyTime && (
                    <div className="plan-card-small" style={{ marginBottom: '6px', fontWeight: '600', fontSize: '16px', lineHeight: '1.6' }}>
                      เวลาเดินทางทั้งหมด: {totalJourneyTime}
                    </div>
                  )}

                  {/* ราคารวม */}
            {flightPrice && (
              <div className="plan-card-small" style={{ marginTop: '6px', fontWeight: '600', fontSize: '16px', lineHeight: '1.6' }}>
                      ราคารวม: {flightPrice}
              </div>
            )}
                </div>

                {/* ✅ ปุ่มแสดงรายละเอียดเพิ่มเติม (เฉพาะเมื่อไม่ใช้ display_text) */}
                {!display_text && (
                  <button
                    onClick={() => setShowFlightDetails(!showFlightDetails)}
                    style={{
                      marginTop: '8px',
                      padding: '6px 12px',
                      background: 'rgba(255, 255, 255, 0.15)',
                      border: '1px solid rgba(255, 255, 255, 0.3)',
                      borderRadius: '6px',
                      color: '#ffffff',
                      fontSize: '14px',
                      cursor: 'pointer',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                    }}
                    onMouseOver={(e) => {
                      e.target.style.background = 'rgba(255, 255, 255, 0.25)';
                    }}
                    onMouseOut={(e) => {
                      e.target.style.background = 'rgba(255, 255, 255, 0.15)';
                    }}
                  >
                    {showFlightDetails ? '▼ ซ่อนรายละเอียด' : '▶ ดูรายละเอียดเพิ่มเติม'}
                  </button>
                )}

                {/* ✅ รายละเอียดเพิ่มเติม (เฉพาะเมื่อไม่ใช้ display_text) */}
                {!display_text && showFlightDetails && flight_details && (
              <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '8px' }}>
                {/* 1) เส้นทาง & เวลา */}
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '16px' }}>1) เส้นทาง & เวลา</div>
                  {flight.segments && flight.segments.map((seg, idx) => (
                    <div key={idx} style={{ marginBottom: '8px', paddingLeft: '8px' }}>
                      <div className="plan-card-small">สายการบิน: {getAirlineName(seg.carrier)}</div>
                      <div className="plan-card-small">เลขเที่ยวบิน: {seg.carrier && seg.flight_number ? `${seg.carrier}${seg.flight_number}` : seg.flight_number || '-'}</div>
                      <div className="plan-card-small">ต้นทาง → ปลายทาง: {seg.from || '-'} → {seg.to || '-'}</div>
                      <div className="plan-card-small">วัน–เวลาออก: {seg.depart_at ? new Date(seg.depart_at).toLocaleString('th-TH') : seg.depart_time || '-'}</div>
                      <div className="plan-card-small">วัน–เวลาถึง: {seg.arrive_at ? new Date(seg.arrive_at).toLocaleString('th-TH') : seg.arrive_time || '-'}{seg.arrive_plus || ''}</div>
                      <div className="plan-card-small">ระยะเวลาบิน: {formatDuration(seg.duration)}</div>
                    </div>
                  ))}
                  <div className="plan-card-small" style={{ marginTop: '4px' }}>
                    {flightStops === 'Non-stop' ? 'บินตรง' : `${flightStops} (แวะ ${flight?.segments?.length - 1 || 0} ครั้ง)`}
                  </div>
                </div>

                {/* 2) ราคา & เงื่อนไข */}
                <div style={{ marginBottom: '12px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '16px' }}>2) ราคา & เงื่อนไข</div>
                  {flightPrice && (
                    <div className="plan-card-small">ราคารวม: {flightPrice}</div>
                  )}
                  {flight?.currency && (
                    <div className="plan-card-small">สกุลเงิน: {flight.currency}</div>
                  )}
                  {flight_details?.price_per_person && (
                    <div className="plan-card-small">ราคาต่อคน: {flight_details.price_per_person.toLocaleString('th-TH')} {flight?.currency || 'THB'}</div>
                  )}
                  {flight?.cabin && (
                    <div className="plan-card-small">ชั้นโดยสาร: {flight.cabin}</div>
                  )}
                  
                  {/* ✅ Badge เงื่อนไขตั๋ว (Refundable / Changeable) */}
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {/* Refundable Badge */}
                    <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '13px',
                        fontWeight: '500',
                        backgroundColor: flight_details?.refundable ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                        color: flight_details?.refundable ? '#4ade80' : '#f87171',
                        border: `1px solid ${flight_details?.refundable ? 'rgba(74, 222, 128, 0.4)' : 'rgba(248, 113, 113, 0.4)'}`
                    }}>
                        {flight_details?.refundable ? '✅ คืนเงินได้' : '❌ คืนเงินไม่ได้'}
                    </span>

                    {/* Changeable Badge */}
                    <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '13px',
                        fontWeight: '500',
                        backgroundColor: flight_details?.changeable ? 'rgba(96, 165, 250, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                        color: flight_details?.changeable ? '#60a5fa' : '#f87171',
                        border: `1px solid ${flight_details?.changeable ? 'rgba(96, 165, 250, 0.4)' : 'rgba(248, 113, 113, 0.4)'}`
                    }}>
                        {flight_details?.changeable ? '✅ เปลี่ยนวันได้' : '❌ เปลี่ยนวันไม่ได้'}
                    </span>
                  </div>
                  <div className="plan-card-small" style={{ marginTop: '4px', fontSize: '12px', opacity: 0.8 }}>
                      *เงื่อนไขเป็นไปตามที่สายการบินกำหนด อาจมีค่าธรรมเนียมเพิ่มเติม
                  </div>
                </div>

                {/* 3) กระเป๋า & สิ่งที่รวม */}
                <div style={{ marginBottom: '12px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '16px' }}>3) กระเป๋า & สิ่งที่รวม</div>
                  
                  {/* แสดงแบบ Icon + Text ให้ดูง่ายขึ้น */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div className="plan-card-small" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>👜</span> 
                        <span>{flight_details?.hand_baggage || '7 kg'} (ถือขึ้นเครื่อง)</span>
                    </div>
                    <div className="plan-card-small" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>🧳</span> 
                        <span style={{ fontWeight: '600', color: '#ffecb3' }}>
                            {flight?.baggage || flight_details?.checked_baggage || 'ไม่รวม'}
                        </span> 
                        <span>(โหลดใต้เครื่อง)</span>
                    </div>
                    <div className="plan-card-small" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>🍽️</span> 
                        <span>{flight_details?.meals || 'อาหารว่าง'}</span>
                    </div>
                    <div className="plan-card-small" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>📶</span> 
                        <span>{flight_details?.wifi || 'ไม่มี Wi-Fi'}</span>
                    </div>
                  </div>
                </div>

                {/* 4) โปรโมชั่น */}
                {flight_details?.promotions && flight_details.promotions.length > 0 && (
                  <div style={{ marginBottom: '12px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                    <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '16px' }}>🎁 โปรโมชั่น</div>
                    {flight_details.promotions.map((promo, idx) => (
                      <div key={idx} style={{ marginBottom: '8px', padding: '8px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '6px' }}>
                        <div className="plan-card-small" style={{ fontWeight: '600' }}>ชื่อโปรโมชั่น: {promo.name}</div>
                        {promo.type && <div className="plan-card-small">ประเภทโปรโมชั่น: {promo.type}</div>}
                        {promo.discount && <div className="plan-card-small">ลดราคา: {promo.discount}</div>}
                        {promo.code && <div className="plan-card-small">โค้ดส่วนลด: {promo.code}</div>}
                        {promo.extra_baggage && <div className="plan-card-small">แถมกระเป๋า: {promo.extra_baggage}</div>}
                        {promo.seat_upgrade && <div className="plan-card-small">อัปเกรดที่นั่ง: {promo.seat_upgrade}</div>}
                        {promo.benefit && <div className="plan-card-small">จำนวนเงินที่ลด / สิทธิ์ที่ได้: {promo.benefit}</div>}
                        {promo.conditions && <div className="plan-card-small">เงื่อนไขการใช้: {promo.conditions}</div>}
                        {promo.expiry && <div className="plan-card-small">วันหมดอายุ: {promo.expiry}</div>}
                        <div className="plan-card-small" style={{ fontWeight: '600', color: promo.applicable ? '#4ade80' : '#ef4444' }}>
                          ใช้ได้กับไฟท์นี้หรือไม่: {promo.applicable ? '✅ ใช้ได้' : '❌ ใช้ไม่ได้'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
              </div>
        </div>
      )}

      {/* Hotel Section (Production Grade UI) */}
      {hotel && (
        <div className="plan-card-section">
          {/* #region agent log */}
          {/* #endregion */}
          
          <div className="plan-card-section-title">🏨 ที่พัก: {hotel.hotelName || hotel.name || 'Unknown Hotel'}</div>
          
          {/* 1. Header Image Carousel */}
          {hotel.visuals?.image_urls && hotel.visuals.image_urls.length > 0 && (
             <div style={{ 
                 width: '100%', 
                 overflowX: 'auto', 
                 whiteSpace: 'nowrap', 
                 marginBottom: '12px',
                 borderRadius: '8px',
                 scrollbarWidth: 'none' 
             }}>
                 {hotel.visuals.image_urls.map((url, idx) => (
                     <img 
                         key={idx} 
                         src={url} 
                         alt={`hotel-${idx}`} 
                         style={{ 
                             width: '120px', 
                             height: '80px', 
                             objectFit: 'cover', 
                             borderRadius: '6px',
                             marginRight: '8px',
                             display: 'inline-block'
                         }} 
                     />
                 ))}
             </div>
          )}

          <div className="plan-card-section-body">
            
            {/* 2. Rating & Badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                {hotel.star_rating && (
                    <span style={{ color: '#FFD700', fontSize: '14px' }}>
                        {'⭐'.repeat(Math.round(hotel.star_rating))} ({hotel.star_rating})
                    </span>
                )}
                {hotel.visuals?.review_score && (
                    <span style={{ 
                        fontSize: '12px', 
                        background: '#4CAF50', 
                        color: 'white', 
                        padding: '2px 6px', 
                        borderRadius: '4px' 
                    }}>
                        {hotel.visuals.review_score} / 5 ({hotel.visuals.review_count || 0} รีวิว)
                    </span>
                )}
            </div>

            {/* 3. Address & Location */}
            {hotel.location?.address && (
                <div className="plan-card-small" style={{ marginBottom: '8px', opacity: 0.9 }}>
                    📍 {hotel.location.address}
                </div>
            )}

            {/* 4. Amenities Icons */}
            {hotel.amenities && (
                <div style={{ 
                    display: 'flex', 
                    gap: '12px', 
                    marginBottom: '12px', 
                    padding: '8px', 
                    background: 'rgba(255,255,255,0.1)', 
                    borderRadius: '6px',
                    fontSize: '18px'
                }}>
                    {hotel.amenities.has_wifi && <span title="Free Wi-Fi">📶</span>}
                    {hotel.amenities.has_pool && <span title="Swimming Pool">🏊</span>}
                    {hotel.amenities.has_fitness && <span title="Fitness Center">🏋️</span>}
                    {hotel.amenities.has_parking && <span title="Parking">🅿️</span>}
                    {hotel.amenities.has_spa && <span title="Spa">💆</span>}
                    {hotel.amenities.has_air_conditioning && <span title="Air Con">❄️</span>}
                </div>
            )}

            {/* 5. Room & Offer Details */}
            <div style={{ marginBottom: '12px', paddingLeft: '8px', borderLeft: '3px solid rgba(255,255,255,0.3)' }}>
                {hotel.booking?.room?.room_type && (
                    <div style={{ fontWeight: '600', fontSize: '15px' }}>🛏️ {hotel.booking.room.room_type}</div>
                )}
                {hotel.booking?.room?.bed_type && (
                    <div className="plan-card-small">{hotel.booking.room.bed_quantity} x {hotel.booking.room.bed_type}</div>
                )}
                {hotel.booking?.policies?.meal_plan && (
                    <div className="plan-card-small">🍽️ {hotel.booking.policies.meal_plan}</div>
                )}
                
                {/* Policy Badges */}
                <div style={{ marginTop: '6px', display: 'flex', gap: '6px' }}>
                    {hotel.booking?.policies && (
                        <span style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            backgroundColor: hotel.booking.policies.is_refundable ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                            color: hotel.booking.policies.is_refundable ? '#4ade80' : '#f87171',
                            border: `1px solid ${hotel.booking.policies.is_refundable ? 'rgba(74, 222, 128, 0.4)' : 'rgba(248, 113, 113, 0.4)'}`
                        }}>
                            {hotel.booking.policies.is_refundable ? '✅ ยกเลิกฟรี' : '❌ ห้ามยกเลิก'}
                        </span>
                    )}
                </div>
            </div>

            {/* 6. Price Breakdown */}
            {hotel.booking?.pricing && (
                 <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                         <span style={{ fontSize: '13px', opacity: 0.8 }}>ราคาต่อคืน</span>
                         <span style={{ fontWeight: '600' }}>{formatMoney(hotel.booking.pricing.price_per_night, hotel.booking.pricing.currency)}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                         <span style={{ fontSize: '13px', opacity: 0.8 }}>ภาษีและค่าธรรมเนียม</span>
                         <span style={{ fontSize: '13px' }}>{formatMoney(hotel.booking.pricing.taxes_and_fees, hotel.booking.pricing.currency)}</span>
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px', fontSize: '16px' }}>
                         <span style={{ fontWeight: '600' }}>ราคารวม ({hotel.booking.check_out_date ? 'ตามวันที่เลือก' : 'Total'})</span>
                         <span style={{ fontWeight: '700', color: '#81c784' }}>{formatMoney(hotel.booking.pricing.total_amount, hotel.booking.pricing.currency)}</span>
                     </div>
                 </div>
            )}
            
            {/* Legacy/Simple Fallback (ถ้าไม่มี booking object ใหม่) */}
            {!hotel.booking && (
               <>
                <div style={{ fontWeight: '500' }}>{hotelName || 'Unknown Hotel'}</div>
                <div className="plan-card-small">
                  {hotelNights != null ? `จำนวนคืน: ${hotelNights}` : ''}
                  {hotelBoard ? ` • แพ็กเกจ: ${hotelBoard}` : ''}
                </div>
                {hotel?.address && (
                  <div className="plan-card-small">
                    ที่อยู่: {hotel.address}
                  </div>
                )}
                {hotelPrice && (
                  <div className="plan-card-small" style={{ marginTop: '4px', fontWeight: '500' }}>
                    ราคา: {hotelPrice} (ตาม Amadeus)
                  </div>
                )}
               </>
            )}
            
          </div>
        </div>
      )}

      {/* Ground Transport Section - Enhanced with detailed information */}
      {ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 รายละเอียดการเดินทาง</div>
          <div className="plan-card-section-body plan-card-small">
            {typeof ground_transport === 'string' ? (
              ground_transport.split('\n').map((line, idx) => (
                <div key={idx}>{line}</div>
              ))
            ) : (
              <div>
                {ground_transport.description && (
                  <div style={{ marginBottom: '12px', fontSize: '15px', lineHeight: '1.6' }}>
                    {ground_transport.description}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Transport/Car Section - Detailed with price and all information */}
      {(transport || car) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">
            {transport?.type === 'car_rental' || car ? '🚗 รถเช่า' :
             transport?.type === 'bus' ? '🚌 รถโดยสาร' :
             transport?.type === 'train' ? '🚂 รถไฟ' :
             transport?.type === 'metro' ? '🚇 รถไฟฟ้า' :
             transport?.type === 'ferry' ? '⛴️ เรือ' :
             '🚗 การเดินทาง'}
          </div>
          <div className="plan-card-section-body plan-card-small">
            {/* Transport Type */}
            {transport?.type && (
              <div style={{ marginBottom: '8px', fontSize: '16px', fontWeight: '600' }}>
                ประเภท: {
                  transport.type === 'car_rental' ? 'รถเช่า' :
                  transport.type === 'bus' ? 'รถโดยสาร' :
                  transport.type === 'train' ? 'รถไฟ' :
                  transport.type === 'metro' ? 'รถไฟฟ้า' :
                  transport.type === 'ferry' ? 'เรือ' :
                  transport.type === 'transfer' ? 'รถรับส่ง' :
                  transport.type
                }
              </div>
            )}

            {/* Route/Origin → Destination */}
            {(transport?.route || transport?.data?.route || car?.route) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>เส้นทาง: </span>
                {transport?.route || transport?.data?.route || car?.route}
              </div>
            )}

            {/* Price - CRITICAL: Always show price prominently */}
            {(transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount) && (
              <div style={{ 
                marginBottom: '12px', 
                padding: '12px', 
                background: 'rgba(74, 222, 128, 0.15)', 
                borderRadius: '8px',
                border: '1px solid rgba(74, 222, 128, 0.3)'
              }}>
                <div style={{ fontSize: '18px', fontWeight: '700', color: '#4ade80', marginBottom: '4px' }}>
                  💰 ราคา: {formatMoney(
                    transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount,
                    transport?.currency || transport?.data?.currency || car?.currency || 'THB'
                  )}
                </div>
                {(transport?.price_per_day || car?.price_per_day) && (
                  <div style={{ fontSize: '14px', opacity: 0.9, marginTop: '4px' }}>
                    ราคาต่อวัน: {formatMoney(
                      transport?.price_per_day || car?.price_per_day,
                      transport?.currency || car?.currency || 'THB'
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Duration */}
            {(transport?.duration || transport?.data?.duration || car?.duration) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>⏱️ ระยะเวลา: </span>
                {formatDuration(transport?.duration || transport?.data?.duration || car?.duration) || 
                 (transport?.duration || transport?.data?.duration || car?.duration)}
              </div>
            )}

            {/* Distance */}
            {(transport?.distance || transport?.data?.distance || car?.distance) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>📏 ระยะทาง: </span>
                {typeof (transport?.distance || transport?.data?.distance || car?.distance) === 'number' 
                  ? `${(transport?.distance || transport?.data?.distance || car?.distance).toLocaleString('th-TH')} กม.`
                  : (transport?.distance || transport?.data?.distance || car?.distance)}
              </div>
            )}

            {/* Provider/Company */}
            {(transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>🏢 บริษัท: </span>
                {transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company}
              </div>
            )}

            {/* Vehicle Details (for car rental) */}
            {(transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>🚙 ประเภทรถ: </span>
                {transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type}
              </div>
            )}

            {/* Seats/Capacity */}
            {(transport?.seats || car?.seats || transport?.capacity || car?.capacity) && (
              <div style={{ marginBottom: '8px', fontSize: '15px' }}>
                <span style={{ fontWeight: '600' }}>💺 จำนวนที่นั่ง: </span>
                {transport?.seats || car?.seats || transport?.capacity || car?.capacity} ที่นั่ง
              </div>
            )}

            {/* Additional Details */}
            {(transport?.details || transport?.data?.details || car?.details) && (
              <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '6px' }}>
                <div style={{ fontWeight: '600', marginBottom: '6px' }}>รายละเอียดเพิ่มเติม:</div>
                {Array.isArray(transport?.details || transport?.data?.details || car?.details) ? (
                  (transport?.details || transport?.data?.details || car?.details).map((detail, idx) => (
                    <div key={idx} style={{ marginBottom: '4px' }}>• {detail}</div>
                  ))
                ) : (
                  <div>{transport?.details || transport?.data?.details || car?.details}</div>
                )}
              </div>
            )}

            {/* Features/Amenities (for car rental) */}
            {(transport?.features || car?.features || transport?.amenities || car?.amenities) && (
              <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '6px' }}>
                <div style={{ fontWeight: '600', marginBottom: '6px' }}>คุณสมบัติ:</div>
                {Array.isArray(transport?.features || car?.features || transport?.amenities || car?.amenities) ? (
                  (transport?.features || car?.features || transport?.amenities || car?.amenities).map((feature, idx) => (
                    <div key={idx} style={{ marginBottom: '4px' }}>✓ {feature}</div>
                  ))
                ) : (
                  <div>{transport?.features || car?.features || transport?.amenities || car?.amenities}</div>
                )}
              </div>
            )}

            {/* Note/Additional Info */}
            {(transport?.note || transport?.data?.note || car?.note) && (
              <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(255, 193, 7, 0.15)', borderRadius: '6px', fontSize: '14px' }}>
                <span style={{ fontWeight: '600' }}>📝 หมายเหตุ: </span>
                {transport?.note || transport?.data?.note || car?.note}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Itinerary Section - ซ่อนไว้และมีปุ่มแสดง/ซ่อน */}
      {itinerary && (
        <div className="plan-card-section">
          <div className="plan-card-section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>📅 Day-by-Day Itinerary</span>
            <button
              onClick={() => setShowItinerary(!showItinerary)}
              style={{
                background: 'transparent',
                border: '1px solid rgba(0,0,0,0.2)',
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                color: '#666',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(0,0,0,0.05)';
                e.target.style.borderColor = 'rgba(0,0,0,0.3)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'transparent';
                e.target.style.borderColor = 'rgba(0,0,0,0.2)';
              }}
            >
              {showItinerary ? '▼ ซ่อน' : '▶ ข้อมูลเพิ่มเติม'}
            </button>
          </div>
          {showItinerary && (
            <div className="plan-card-section-body plan-card-small" style={{ marginTop: '8px' }}>
              {typeof itinerary === 'string' ? (
                // If itinerary is a string (like day trip)
                <div style={{ whiteSpace: 'pre-line' }}>{itinerary}</div>
              ) : Array.isArray(itinerary) ? (
                // If itinerary is an array of days
                itinerary.map((day, idx) => (
                  <div key={idx} style={{ marginBottom: '8px' }}>
                    <div style={{ fontWeight: '500' }}>
                      🗓 Day {day.day || idx + 1} – {day.title || 'Day ' + (idx + 1)}
                    </div>
                    {day.items && Array.isArray(day.items) && (
                      <div style={{ marginLeft: '12px', marginTop: '4px' }}>
                        {day.items.map((item, itemIdx) => (
                          <div key={itemIdx}>- {item}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Transport Section (optional legacy) */}
      {transport && !ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 การเดินทาง</div>
          <div className="plan-card-section-body plan-card-small">
            {transportMode && <div>{transportMode}</div>}
            {transportNote && <div>{transportNote}</div>}
            {!transportMode && !transportNote && <div>มีข้อมูลการเดินทาง</div>}
          </div>
        </div>
      )}

      {/* Price Breakdown (ถ้ามี) */}
      {price_breakdown && (
        <div className="plan-card-section plan-card-price-breakdown">
          <div className="plan-card-section-title">💰 รายละเอียดราคา</div>
          <div className="plan-card-section-body plan-card-small">
            {breakdownFlight && <div>✈️ ตั๋วเครื่องบิน: {breakdownFlight}</div>}
            {breakdownHotel && <div>🏨 ที่พัก: {breakdownHotel}</div>}
            {breakdownTransport && (
              <div>
                {transportType === 'car_rental' ? '🚗 รถเช่า' : 
                 transportType === 'bus' ? '🚌 รถโดยสาร' :
                 transportType === 'train' ? '🚂 รถไฟ' :
                 transportType === 'metro' ? '🚇 รถไฟฟ้า' :
                 transportType === 'ferry' ? '⛴️ เรือ' :
                 '🚗 รถและเรือ'}: {breakdownTransport}
              </div>
            )}
            {!breakdownFlight && !breakdownHotel && !breakdownTransport && (
              <div>ไม่มีรายการแยกราคาเพิ่มเติม</div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="plan-card-footer">
        {displayTotalPrice && (
          <div className="plan-card-price">
            {displayTotalPrice}
          </div>
        )}
        <button
          className="plan-card-button"
          onClick={() => onSelect && onSelect(id)}
        >
          เลือกช้อยส์ {id}
        </button>
      </div>
    </div>
  );
}
