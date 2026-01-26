import React, { useState } from 'react';
import './AuthHeader.css';

export default function AuthHeader({ onNavigateToHome }) {
  return (
    <header className="auth-header">
      <div className="header-content">
        <div className="logo-section" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <div className="logo-icon">
            <svg className="plane-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
            </svg>
          </div>
          <span className="logo-text">AI Travel Agent</span>
        </div>
      </div>
    </header>
  );
}
