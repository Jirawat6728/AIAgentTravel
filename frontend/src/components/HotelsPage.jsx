import React from 'react';
import AppHeader from './AppHeader';
import './HotelsPage.css';

export default function HotelsPage({ user, onLogout, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals }) {
  const handleTabChange = (tab) => {
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
    <div className="hotels-page">
      <AppHeader
        activeTab="hotels"
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

      <div className="hotels-content">
        <div className="hotels-hero">
          <h1>ค้นหาที่พัก</h1>
          {/* <p>ค้นหาที่พักที่เหมาะกับคุณมากที่สุด</p> */}
        </div>

        
      </div>
    </div>
  );
}

