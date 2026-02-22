import React from 'react';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import './CarRentalsPage.css';

export default function CarRentalsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();
  const handleTabChange = (tab) => {
    if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
  };

  return (
    <div className="car-rentals-page">
      <AppHeader
        activeTab="car-rentals"
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
        notificationCount={0}
        isConnected={true}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
      />

      <div className="car-rentals-content" data-theme={theme} data-font-size={fontSize}>
        <div className="car-rentals-hero">
          <h1>{t('carRentals.title')}</h1>
          {/* <p>ค้นหารถเช่าที่เหมาะกับคุณ</p> */}
        </div>

        

        
      </div>
    </div>
  );
}

