import React from 'react';
import AppHeader from './AppHeader';
import './FlightsPage.css';

export default function FlightsPage({ user, onLogout, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals }) {
  const handleTabChange = (tab) => {
    // Handle navigation to other tabs
    if (tab === 'ai' && onNavigateToAI) {
      onNavigateToAI();
    } else if (tab === 'bookings' && onNavigateToBookings) {
      onNavigateToBookings();
    } else if (tab === 'flights' && onNavigateToFlights) {
      onNavigateToFlights();
    } else if (tab === 'hotels' && onNavigateToHotels) {
      onNavigateToHotels();
    } else if (tab === 'car-rentals' && onNavigateToCarRentals) {
      onNavigateToCarRentals();
    }
  };

  return (
    <div className="flights-page">
      <AppHeader
        activeTab="flights"
        user={user}
        onTabChange={handleTabChange}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        onLogout={onLogout}
        notificationCount={0}
        isConnected={true}
      />

      <div className="flights-content">
        <div className="flights-hero">
          <h1>ค้นหาเที่ยวบิน</h1>
          {/* <p>ค้นหาเที่ยวบินราคาดีที่สุดสำหรับทริปของคุณ</p> */}
        </div>

        
        
      </div>
    </div>
  );
}

