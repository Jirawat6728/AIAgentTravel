import React from 'react';

const STEPS = [
  {
    key: 'confirming_search',
    label: 'ค้นหา',
    icon: '🔍',
    description: 'ยืนยันรายละเอียดทริป',
  },
  {
    key: 'selecting',
    label: 'เลือก',
    icon: '✈️',
    description: 'เลือกเที่ยวบิน & ที่พัก',
  },
  {
    key: 'confirming_booking',
    label: 'ยืนยัน',
    icon: '📋',
    description: 'ยืนยันรายละเอียดการจอง',
  },
  {
    key: 'completed',
    label: 'จอง',
    icon: '🎉',
    description: 'การจองสำเร็จ',
  },
];

const STATE_TO_STEP_INDEX = {
  idle: -1,
  confirming_search: 0,
  searching: 0,
  selecting: 1,
  confirming_booking: 2,
  completed: 3,
};

export default function BookingProgressBar({ funnelState }) {
  const activeIndex = STATE_TO_STEP_INDEX[funnelState] ?? -1;

  if (activeIndex < 0) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '8px 16px',
        background: 'rgba(0, 0, 0, 0.2)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        gap: '0',
        userSelect: 'none',
      }}
    >
      {STEPS.map((step, idx) => {
        const isDone = idx < activeIndex;
        const isActive = idx === activeIndex;
        const isFuture = idx > activeIndex;

        return (
          <React.Fragment key={step.key}>
            {/* Step node */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '3px',
                minWidth: '64px',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: isDone ? '14px' : '16px',
                  background: isDone
                    ? 'rgba(34, 197, 94, 0.25)'
                    : isActive
                    ? 'rgba(59, 130, 246, 0.35)'
                    : 'rgba(255,255,255,0.06)',
                  border: isDone
                    ? '1.5px solid rgba(34, 197, 94, 0.6)'
                    : isActive
                    ? '2px solid rgba(99, 179, 246, 0.8)'
                    : '1.5px solid rgba(255,255,255,0.12)',
                  boxShadow: isActive ? '0 0 8px rgba(99,179,246,0.4)' : 'none',
                  transition: 'all 0.3s ease',
                }}
              >
                {isDone ? '✓' : step.icon}
              </div>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: isActive ? '600' : '400',
                  color: isDone
                    ? 'rgba(134, 239, 172, 0.9)'
                    : isActive
                    ? 'rgba(147, 197, 253, 1)'
                    : 'rgba(255,255,255,0.3)',
                  whiteSpace: 'nowrap',
                  transition: 'color 0.3s ease',
                }}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div
                style={{
                  flex: 1,
                  height: '2px',
                  marginBottom: '14px',
                  background: idx < activeIndex
                    ? 'rgba(34, 197, 94, 0.5)'
                    : 'rgba(255,255,255,0.08)',
                  transition: 'background 0.4s ease',
                  minWidth: '16px',
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
