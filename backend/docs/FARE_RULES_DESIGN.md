# ออกแบบโครงข้อมูล Fare Rules / Fare Details สำหรับ AI Travel Agent

## วัตถุประสงค์

- **เงื่อนไขตั๋ว (Fare Rules)** เป็นข้อมูลที่ผู้ใช้ถามซ้ำก่อนตัดสินใจจอง ต้องมีโครงข้อมูลชัดเจนทั้ง Backend (Amadeus → normalization) และ Frontend (การ์ดผลค้นหา / สรุปก่อนชำระเงิน)
- รองรับการแสดง: **การขอเงินคืน (Refund)**, **การเปลี่ยนเที่ยวบิน (Change)**, **การเช็คอิน (Check-in)**, **Baggage**, และ **ประเภทตั๋ว (Fare Type)** พร้อมข้อความสรุปสำหรับ UI

---

## 1. โครงข้อมูลหลัก (Canonical Schema)

### 1.1 Fare Type (ประเภทตั๋ว)

ใช้สำหรับแสดง label และ map กับเงื่อนไขโดยรวม (Economy Lite / Standard / Flex ฯลฯ)

| ค่า (code)        | แสดงใน UI (TH)     | แสดงใน UI (EN)   |
|-------------------|--------------------|-------------------|
| `ECONOMY_LITE`    | Economy Lite       | Economy Lite      |
| `ECONOMY_STANDARD`| Economy Standard   | Economy Standard  |
| `ECONOMY_FLEX`    | Economy Flex       | Economy Flex      |
| `BUSINESS`        | Business           | Business          |
| `FIRST`           | First Class        | First Class       |
| `UNKNOWN`         | (ไม่แสดงหรือแสดงเป็น "เที่ยวบิน") | — |

- **ที่มา:** จาก Amadeus `travelerPricings[].fareDetailsBySegment[].cabin` + ถ้ามี fare brand/code จาก Fare Rules API สามารถ map เป็น `ECONOMY_LITE` / `ECONOMY_STANDARD` / `ECONOMY_FLEX` ได้

---

### 1.2 Refund Policy (การขอเงินคืน)

```ts
// TypeScript-style (สำหรับอ้างอิง)
interface RefundPolicy {
  type: "non_refundable" | "refundable_fee" | "full_refund";
  refundable: boolean;           // สรุป: คืนได้หรือไม่ (สำหรับ badge)
  fee_amount?: number | null;    // ค่าธรรมเนียมยกเลิก (บาท หรือ currency ตาม fee_currency)
  fee_currency?: string | null;  // เช่น "THB"
  note?: string | null;          // ข้อความเพิ่ม e.g. "คืนได้เฉพาะภาษีสนามบิน"
  summary?: string | null;       // ข้อความสรุปสำหรับ UI e.g. "คืนเงินไม่ได้ (ยกเว้นภาษี)"
}
```

| type               | ความหมาย |
|--------------------|----------|
| `non_refundable`   | ตั๋วโปรโมชัน/ประหยัด — คืนเงินไม่ได้ (ยกเว้นภาษีในบางกรณี หรือสายการบินยกเลิกเอง) |
| `refundable_fee`   | คืนได้แต่มีค่าธรรมเนียมยกเลิก |
| `full_refund`      | คืนได้เต็มหรือค่าธรรมเนียมน้อยมาก (Flex/Business/First) |

---

### 1.3 Change Flight Policy (การเปลี่ยนเที่ยวบิน)

```ts
interface ChangePolicy {
  changeable: boolean;
  fee_amount?: number | null;    // ค่าธรรมเนียมการเปลี่ยน (บาท)
  fee_currency?: string | null;
  plus_fare_difference: boolean; // จริง = ต้องจ่ายส่วนต่างราคาตั๋วใหม่ด้วย
  time_limit_hours?: number | null; // แจ้งล่วงหน้าอย่างน้อยกี่ชม. (e.g. 24, 48)
  note?: string | null;
  summary?: string | null;        // e.g. "เปลี่ยนเที่ยวบินมีค่าธรรมเนียม 1,500 บาท + ส่วนต่างราคา"
}
```

---

### 1.4 Check-in Policy (การเช็คอิน)

```ts
interface CheckInPolicy {
  online_opens_hours_before?: number | null;  // เปิดเช็คอินออนไลน์ล่วงหน้า (ชม.) e.g. 48
  online_closes_hours_before?: number | null; // ปิดเช็คอินออนไลน์ก่อนบิน (ชม.) e.g. 1 หรือ 2
  counter_domestic_lead_hours?: number | null;   // ถึงสนามบินล่วงหน้า (ในประเทศ) ชม. e.g. 1.5 หรือ 2
  counter_international_lead_hours?: number | null; // ถึงสนามบินล่วงหน้า (ระหว่างประเทศ) ชม. e.g. 3
  counter_closes_minutes_before?: number | null;  // เคาน์เตอร์ปิดก่อนบิน (นาที) e.g. 45 หรือ 60
  no_show_forfeit?: boolean;     // true = ไม่มาเที่ยวบินถือว่าตั๋วถูกยกเลิก/ไม่คืนเงิน
  summary?: string | null;       // e.g. "เช็คอินออนไลน์ 24–48 ชม. / ถึงสนามบินล่วงหน้า 2 ชม. (ในประเทศ)"
}
```

---

### 1.5 Baggage (กระเป๋า)

```ts
interface BaggageInfo {
  checked?: string | null;   // e.g. "20 KG", "1 Piece(s)", "ไม่รวม"
  carry_on?: string | null;  // e.g. "1 กระเป๋าถือ (7 kg)"
}
```

- **ที่มา:** ปัจจุบันใช้จาก Amadeus `fareDetailsBySegment[].includedCheckedBags` (weight/quantity) และ carry-on ใช้ default "1 กระเป๋าถือ (7 kg)" ถ้า API ไม่ส่ง

---

### 1.6 Seat / Extras (เลือกที่นั่ง ฯลฯ)

```ts
interface SeatAndExtras {
  seat_selection?: string | null;  // "ฟรี" | "อาจมีค่าธรรมเนียม" | "มีค่าใช้จ่ายเพิ่มเติม"
  meals?: string | null;           // "รวมอาหาร" | "อาหารว่าง/ซื้อเพิ่ม" | "ไม่รวม"
}
```

---

## 2. โครงใน Backend (enhanced_info + fare_rules)

ข้อมูลที่ **data_aggregator** สร้างและใส่ใน `raw_data.enhanced_info` ของ flight option (และถ้ามี Fare Rules API จะเติม `raw_data.fare_rules`):

### 2.1 enhanced_info (มีอยู่แล้ว + ขยายได้)

```json
{
  "cabin": "ECONOMY",
  "fare_type": "ECONOMY_LITE",
  "baggage": "20 KG",
  "hand_baggage": "1 กระเป๋าถือ (7 kg)",
  "refundable": false,
  "changeable": true,
  "change_fee": null,
  "transit_warning": null,
  "co2_emissions_kg": 120,
  "refund_policy": {
    "type": "non_refundable",
    "refundable": false,
    "fee_amount": null,
    "fee_currency": null,
    "note": "คืนได้เฉพาะภาษีสนามบินในบางกรณี",
    "summary": "คืนเงินไม่ได้ (ยกเว้นภาษี)"
  },
  "change_policy": {
    "changeable": true,
    "fee_amount": 1500,
    "fee_currency": "THB",
    "plus_fare_difference": true,
    "time_limit_hours": 24,
    "note": null,
    "summary": "เปลี่ยนเที่ยวบินมีค่าธรรมเนียม 1,500 บาท + ส่วนต่างราคา"
  },
  "check_in_policy": {
    "online_opens_hours_before": 48,
    "online_closes_hours_before": 1,
    "counter_domestic_lead_hours": 2,
    "counter_international_lead_hours": 3,
    "counter_closes_minutes_before": 45,
    "no_show_forfeit": true,
    "summary": "เช็คอินออนไลน์ 24–48 ชม. / ถึงสนามบินล่วงหน้า 2 ชม. (ในประเทศ)"
  }
}
```

- **ฟิลด์เดิมที่ใช้อยู่:** `cabin`, `baggage`, `refundable`, `changeable`, `change_fee`, `hand_baggage`, `transit_warning`, `co2_emissions_kg`
- **ฟิลด์ที่แนะนำเพิ่ม:** `fare_type`, `refund_policy`, `change_policy`, `check_in_policy` (หรือใช้แค่ `summary` ในแต่ละส่วนถ้าไม่มี API ละเอียด)

### 2.2 fare_rules (จาก Amadeus Fare Rules API — อนาคต)

เมื่อเรียก Fare Rules API ได้ สามารถเก็บ object เดิมจาก Amadeus ไว้ใน `raw_data.fare_rules` แล้วค่อย parse เป็น `refund_policy` / `change_policy` / `check_in_policy` ด้านบนได้

---

## 3. โครงใน Frontend (flight_details + fare_details_summary)

### 3.1 flight_details (ที่ chat.py ส่งไปให้ UI)

โครงปัจจุบันใน `chat.py` มีอยู่แล้ว; แนะนำให้ขยายตาม schema นี้ (เก็บ backward compatible):

```json
{
  "price_per_person": 3500,
  "changeable": true,
  "refundable": false,
  "change_fee": "ค่าธรรมเนียมตามเงื่อนไขสายการบิน",
  "change_fee_amount": 1500,
  "change_fee_currency": "THB",
  "hand_baggage": "1 กระเป๋าถือ (7 kg)",
  "checked_baggage": "20 KG",
  "meals": "อาหารว่าง/ซื้อเพิ่ม",
  "seat_selection": "อาจมีค่าธรรมเนียม",
  "fare_type": "ECONOMY_LITE",
  "refund_summary": "คืนเงินไม่ได้ (ยกเว้นภาษี)",
  "change_summary": "เปลี่ยนเที่ยวบินมีค่าธรรมเนียม 1,500 บาท + ส่วนต่างราคา",
  "check_in_summary": "เช็คอินออนไลน์ 24–48 ชม. / ถึงสนามบินล่วงหน้า 2 ชม. (ในประเทศ)",
  "co2_emissions_kg": 120
}
```

- **refund_summary / change_summary / check_in_summary:** ใช้แสดงใน "Fare Details Summary" ก่อนชำระเงิน และในปุ่ม "แสดงรายละเอียดเพิ่มเติม"
- **change_fee_amount / change_fee_currency:** ใช้เมื่อมีค่าจริงจาก Fare Rules; ถ้าไม่มี ให้ใช้เฉพาะ `change_fee` (ข้อความ) อย่างเดิม

### 3.2 Fare Details Summary (ก่อนชำระเงิน)

Object สรุปสำหรับแสดงในหน้ายืนยัน/ชำระเงิน:

```ts
interface FareDetailsSummary {
  fare_type_label: string;      // "Economy Lite"
  refund_badge: "refundable" | "non_refundable" | "refundable_fee";
  refund_summary: string;
  change_summary: string;
  check_in_summary: string;
  baggage_checked: string;
  baggage_carry_on: string;
}
```

- Frontend สามารถ build จาก `flight_details` ได้เลย ไม่จำเป็นต้องมี API แยก

---

## 4. ตารางสรุปเงื่อนไขตามประเภทตั๋ว (สำหรับ UI / คู่มือ)

| ประเภทตั๋ว (Fare Type) | การขอเงินคืน (Refund) | การเปลี่ยนเที่ยวบิน (Change) | การเลือกที่นั่ง |
|------------------------|------------------------|-------------------------------|------------------|
| Economy Lite           | ไม่ได้ (ยกเว้นภาษี)   | มีค่าธรรมเนียม + ส่วนต่าง     | มีค่าใช้จ่ายเพิ่มเติม |
| Economy Standard       | ได้ (มีค่าธรรมเนียม)  | มีค่าธรรมเนียม + ส่วนต่าง     | เลือกได้บางโซน |
| Economy Flex           | ได้ (ฟรีหรือค่าต่ำ)   | ฟรี (จ่ายแค่ส่วนต่างราคา)     | เลือกได้ฟรี |
| Business / First       | ได้เต็มจำนวน          | ฟรีหรือค่าต่ำมาก              | เลือกได้ฟรี |

- ค่าจริงควรมาจาก Amadeus (pricingOptions / fareRules); ตารางนี้ใช้เป็น default หรือ fallback เมื่อ API ไม่ส่ง

---

## 5. การ map จาก Amadeus

| แหล่ง (Amadeus) | ฟิลด์ที่ใช้ในโครงเรา |
|------------------|------------------------|
| `price.pricingOptions.refundableFare` | `refundable`, `refund_policy.type` |
| `travelerPricings[0].fareDetailsBySegment[0].includedCheckedBags` | `baggage` (checked) |
| `travelerPricings[0].fareDetailsBySegment[0].cabin` | `cabin`, `fare_type` (ถ้า map ได้) |
| Fare Rules API (อนาคต) | `refund_policy`, `change_policy`, `check_in_policy`, `change_fee_amount` |

- คอมเมนต์ใน `data_aggregator._normalize_flight`: *"Ideally, we need 'fareRules' from a separate pricing API"* — เมื่อมี Fare Rules API ให้ parse แล้วเติม `enhanced_info.refund_policy`, `change_policy`, `check_in_policy` และ `change_fee` (จำนวนเงิน) ตาม schema นี้

---

## 6. ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | บทบาท |
|------|--------|
| `backend/app/services/data_aggregator.py` | สร้าง `enhanced_info` จาก Amadeus flight offer; ขยายเป็น refund_policy / change_policy / check_in_policy / fare_type ได้ |
| `backend/app/api/chat.py` | map `enhanced_info` → `ui_option["flight_details"]`; เพิ่ม refund_summary, change_summary, check_in_summary, change_fee_amount, fare_type |
| Frontend: `PlanChoiceCard.jsx`, `PlanChoiceCardFlights.jsx` | แสดง baggage, refundable badge, และรายละเอียดเที่ยวบิน; ใช้ flight_details สำหรับ Fare Details Summary |
| หน้าการชำระเงิน / ยืนยันจอง | แสดง Fare Details Summary จาก flight_details |

---

## 7. สรุป

- **Backend:** ขยาย `enhanced_info` ด้วย `fare_type`, `refund_policy`, `change_policy`, `check_in_policy` (หรืออย่างน้อย `*_summary`) และส่งต่อใน `flight_details`
- **Frontend:** ใช้ `flight_details.refund_summary`, `change_summary`, `check_in_summary`, `change_fee_amount` สำหรับ Badge ในผลค้นหา และบล็อก "Fare Details Summary" ก่อนชำระเงิน
- **Amadeus Fare Rules API:** เมื่อพร้อม ให้เรียกและ map ลงโครงนี้ เพื่อได้ค่าธรรมเนียมจริงและข้อความเงื่อนไขที่ตรงสายการบิน
