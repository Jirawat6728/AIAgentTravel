import React, { useState, useMemo } from 'react';
import './AITravelChat.css'; // ใช้คลาสจากไฟล์หลักร่วมกันได้

function formatMoney(value, currency = 'THB') {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return `${currency} ${value.toLocaleString('th-TH')}`;
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
    return null;
  }
}

// ✅ คำนวณราคาต่อ segment (แบ่งตามสัดส่วน duration)
function calculateSegmentPrice(totalPrice, segmentDuration, totalDuration) {
  if (!totalPrice || !segmentDuration || !totalDuration || totalDuration === 0) {
    return null;
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
    return null;
  }
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
        parts.push(`${hours} ชั่วโมง`);
      }
      if (minutes > 0) {
        parts.push(`${minutes} นาที`);
      }
      
      return parts.length > 0 ? parts.join(' ') : 'ไม่ระบุ';
    } catch (e) {
      return durationStr; // Return original if parsing fails
    }
  }
  
  return durationStr; // Return original if not ISO 8601 format
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
  
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:177',message:'PlanChoiceCard render - received choice',data:{choiceId:choice?.id,hasFlight:!!choice?.flight,hasSegments:!!choice?.flight?.segments,segmentsCount:choice?.flight?.segments?.length||0,hasDisplayText:!!choice?.display_text,slot:choice?.slot},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion
  
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
  
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:203',message:'PlanChoiceCard - destructured values',data:{id,hasFlight:!!flight,flightPriceTotal:flight?.price_total,flightCurrency:flight?.currency,segmentsCount:flight?.segments?.length||0,hasDisplayText:!!display_text,displayTextLength:display_text?.length||0,slot},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion

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
  
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:216',message:'Flight segments analysis',data:{segmentsCount:flight?.segments?.length||0,segments:flight?.segments?.map((s,i)=>({idx:i,from:s?.from,to:s?.to,depart_time:s?.depart_time,arrive_time:s?.arrive_time,depart_at:s?.depart_at,arrive_at:s?.arrive_at,duration:s?.duration,carrier:s?.carrier})),hasFirstSeg:!!firstSeg,hasLastSeg:!!lastSeg},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion

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
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:307',message:'Total journey time calculation',data:{hasFirstSeg:!!firstSeg,hasLastSeg:!!lastSeg,firstDepart,lastArrive,arrivePlus:lastSeg?.arrive_plus,segmentsCount:flight.segments.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
      
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
          
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:318',message:'Total journey time calculation - diff',data:{firstTime:firstTime.toISOString(),lastTime:lastTime.toISOString(),diffMs,diffHours:Math.floor(diffMs/(1000*60*60)),diffMinutes:Math.floor((diffMs%(1000*60*60))/(1000*60))},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
          // #endregion
          
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
      
      // #region agent log
      if (totalJourneyTime) {
        fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:332',message:'Total journey time result',data:{totalJourneyTime},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      }
      // #endregion
    } catch (e) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:339',message:'Total journey time calculation error',data:{error:String(e)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
      // ถ้าคำนวณไม่ได้ก็ไม่แสดง
    }
  }
  
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:262',message:'Flight computed fields',data:{flightRoute,flightTime,flightStops,flightCarriers,flightPrice,flightPriceTotal:flight?.price_total,totalJourneyTime},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion

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
              background: '#e3f2fd', 
              color: '#1976d2',
              marginLeft: '6px',
              fontSize: '13px',
              padding: '3px 10px'
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
          {(() => {
            fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:443',message:'Flight section render check',data:{hasFlight:!!flight,hasDisplayText:!!display_text,slot,willShowDisplayText:!!(display_text&&slot==='flight'),hasSegments:!!flight?.segments,segmentsCount:flight?.segments?.length||0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
            return null;
          })()}
          {/* #endregion */}
          
          <div className="plan-card-section-title">✈️ รายละเอียดเที่ยวบิน</div>
            <div className="plan-card-section-body">
                {/* #region agent log */}
                {(() => {
                  fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:408',message:'Rendering segments list',data:{segmentsCount:flight.segments.length,segments:flight.segments.map((s,i)=>({idx:i,from:s?.from,to:s?.to,carrier:s?.carrier,flightNumber:s?.flight_number,hasDuration:!!s?.duration,hasDepartTime:!!s?.depart_time,hasArriveTime:!!s?.arrive_time}))},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
                  return null;
                })()}
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
                      
                      // #region agent log
                      const segDurationStr = seg.duration;
                      const segSeconds = parseDuration(segDurationStr);
                      fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:432',message:'Segment price calculation',data:{segmentIdx:idx,segmentDuration:segDurationStr,segSeconds,totalDuration,totalFlightPrice,calculatedPrice:totalDuration>0?Math.round((totalFlightPrice*segSeconds)/totalDuration):null},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
                      // #endregion
                      
                      if (totalDuration > 0) {
                        segmentPrice = Math.round((totalFlightPrice * segSeconds) / totalDuration);
                      }
                    }
                    
                    // คำนวณ layover time (ถ้ามี segment ถัดไป)
                    const nextSegment = idx < flight.segments.length - 1 ? flight.segments[idx + 1] : null;
                    const layoverTime = calculateLayoverTime(seg, nextSegment);
                    
                    // #region agent log
                    fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:445',message:'Layover time calculation',data:{segmentIdx:idx,hasNextSegment:!!nextSegment,prevArriveAt:seg?.arrive_at,prevArriveTime:seg?.arrive_time,nextDepartAt:nextSegment?.depart_at,nextDepartTime:nextSegment?.depart_time,layoverTime},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
                    // #endregion
                    
                    return (
                    <div key={idx} style={{ marginBottom: idx < flight.segments.length - 1 ? '12px' : '0' }}>
                      <div style={{ fontWeight: '600', marginBottom: '6px', fontSize: '16px', lineHeight: '1.4' }}>
                        ไฟลท์ {idx + 1}
                      </div>
                  <div style={{ fontSize: '16px', marginBottom: '4px', lineHeight: '1.5' }}>
                    สายการบิน: {getAirlineName(seg.carrier)}
                    {seg.carrier && seg.flight_number ? ` • ${seg.carrier}${seg.flight_number}` : seg.flight_number ? ` • ${seg.flight_number}` : ''}
                  </div>
                  <div className="plan-card-small">
                    เส้นทาง: {seg.from || '-'} → {seg.to || '-'}
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
                        {/* ✅ แสดงราคาต่อ segment */}
                        {segmentPrice && (
                          <div className="plan-card-small" style={{ 
                            fontSize: '16px', 
                            color: 'rgba(255, 255, 255, 0.8)',
                            marginTop: '4px',
                            fontWeight: '500'
                          }}>
                            💰 ราคา: {formatMoney(segmentPrice, flight?.currency || displayCurrency)}
                </div>
                        )}
                        {/* #region agent log */}
                        {(() => {
                          fetch('http://127.0.0.1:7242/ingest/d477114a-a3a9-4d28-9739-4efb8ed13297',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanChoiceCard.jsx:473',message:'Segment render - price and layover',data:{segmentIdx:idx,hasSegmentPrice:!!segmentPrice,segmentPrice,hasLayoverTime:!!layoverTime,layoverTime,willShowPrice:!!segmentPrice,willShowLayover:!!layoverTime},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
                          return null;
                        })()}
                        {/* #endregion */}
                        {/* ✅ แสดงเวลารอคอยต่อเครื่อง */}
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
                            ⏱️ รอคอยต่อเครื่อง: {layoverTime}
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
            
                  {/* Cabin และ Baggage */}
            {(flight?.cabin || flight?.baggage) && (
                    <div className="plan-card-small" style={{ marginBottom: '6px', fontSize: '16px', lineHeight: '1.6' }}>
                {flight?.cabin && <div style={{ marginBottom: '4px' }}>ชั้นโดยสาร: {flight.cabin}</div>}
                {flight?.baggage && <div>กระเป๋าโหลด: {flight.baggage}</div>}
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
                  <div className="plan-card-small">เปลี่ยนวันได้ไหม: {flight_details?.changeable !== null ? (flight_details.changeable ? 'ได้ (อาจมีค่าธรรมเนียม)' : 'ไม่ได้') : 'กรุณาติดต่อสายการบิน'}</div>
                  <div className="plan-card-small">คืนเงินได้ไหม: {flight_details?.refundable !== null ? (flight_details.refundable ? 'ได้ (อาจมีค่าธรรมเนียม)' : 'ไม่ได้') : 'กรุณาติดต่อสายการบิน'}</div>
                </div>

                {/* 3) กระเป๋า & สิ่งที่รวม */}
                <div style={{ marginBottom: '12px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '16px' }}>3) กระเป๋า & สิ่งที่รวม</div>
                  <div className="plan-card-small">กระเป๋าถือ: {flight_details?.hand_baggage || '1 กระเป๋าถือ (7-10 kg)'}</div>
                  <div className="plan-card-small">กระเป๋าโหลด: {flight?.baggage || flight_details?.checked_baggage || 'กรุณาติดต่อสายการบิน'}</div>
                  <div className="plan-card-small">อาหารบนเครื่อง: {flight_details?.meals || 'ขึ้นอยู่กับสายการบินและชั้นโดยสาร'}</div>
                  <div className="plan-card-small">เลือกที่นั่ง: {flight_details?.seat_selection || 'สามารถเลือกได้ (อาจมีค่าใช้จ่ายเพิ่มเติม)'}</div>
                  <div className="plan-card-small">Wi-Fi: {flight_details?.wifi || 'ขึ้นอยู่กับสายการบิน'}</div>
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

      {/* Hotel Section (Amadeus) - รองรับทั้ง single และ multiple segments */}
      {hotel && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🏨 ที่พัก</div>
          <div className="plan-card-section-body">
            {/* ✅ รองรับทั้ง single hotel และ multiple hotel segments */}
            {hotel.segments ? (
              // Multiple hotel segments (หลายโรงแรม)
              hotel.segments.map((seg, idx) => (
                <div key={idx} style={{ marginBottom: idx < hotel.segments.length - 1 ? '12px' : '0' }}>
                  <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                    Segment {idx + 1}
                  </div>
                  <div style={{ fontWeight: '500' }}>{seg.hotelName || 'Unknown Hotel'}</div>
                  <div className="plan-card-small">
                    เมือง: {seg.cityCode || 'N/A'}
                  </div>
                  {seg.nights != null && (
                    <div className="plan-card-small">
                      จำนวนคืน: {seg.nights}
                    </div>
                  )}
                  {seg.boardType && (
                    <div className="plan-card-small">
                      แพ็กเกจ: {seg.boardType}
                    </div>
                  )}
                  {seg.address && (
                    <div className="plan-card-small">
                      ที่อยู่: {seg.address}
                    </div>
                  )}
                  {seg.price_total && seg.currency && (
                    <div className="plan-card-small" style={{ marginTop: '4px', fontWeight: '500' }}>
                      ราคา: {seg.price_total.toLocaleString('th-TH')} {seg.currency} (ตาม Amadeus)
                    </div>
                  )}
                </div>
              ))
            ) : (
              // Single hotel (backward compatibility)
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
                {hotel?.cityCode && (
                  <div className="plan-card-small">
                    เมือง: {hotel.cityCode}
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

      {/* Ground Transport Section */}
      {ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚆/🚗 เดินทาง/ขนส่ง</div>
          <div className="plan-card-section-body plan-card-small">
            {ground_transport.split('\n').map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
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
