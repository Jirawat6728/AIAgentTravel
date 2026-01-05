import React from 'react';
import AppHeader from './AppHeader';
import './CarRentalsPage.css';

export default function CarRentalsPage({ user, onLogout, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals }) {
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
    <div className="car-rentals-page">
      <AppHeader
        activeTab="car-rentals"
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

      <div className="car-rentals-content">
        <div className="car-rentals-hero">
          <h1>เช่ารถ</h1>
          {/* <p>ค้นหารถเช่าที่เหมาะกับคุณ</p> */}
        </div>

        

        
      </div>
    </div>
  );
}

