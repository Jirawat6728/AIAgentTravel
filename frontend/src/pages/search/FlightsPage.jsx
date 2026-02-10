import React from 'react';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import './FlightsPage.css';

export default function FlightsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile, onNavigateToSettings, onNavigateToHome = null }) {
  const theme = useTheme();
  const handleTabChange = (tab) => {
    if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
  };

  return (
    <div className="flights-page">
      <AppHeader
        activeTab="flights"
        user={user}
        onNavigateToHome={onNavigateToHome}
        onTabChange={handleTabChange}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        notificationCount={0}
        isConnected={true}
      />

      <div className="flights-content" data-theme={theme}>
        <div className="flights-hero">
          <h1>ค้นหาเที่ยวบิน</h1>
          {/* <p>ค้นหาเที่ยวบินราคาดีที่สุดสำหรับทริปของคุณ</p> */}
        </div>

        
        
      </div>
    </div>
  );
}

