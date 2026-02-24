import React from 'react';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import './HotelsPage.css';

export default function HotelsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, notificationCount = 0, notifications = [], onMarkNotificationAsRead = null, onClearAllNotifications = null }) {
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
    <div className="hotels-page">
      <AppHeader
        activeTab="hotels"
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
        notificationCount={notificationCount}
        notifications={notifications}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
        onClearAllNotifications={onClearAllNotifications}
        isConnected={true}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
      />

      <div className="hotels-content" data-theme={theme} data-font-size={fontSize}>
        <div className="hotels-hero">
          <h1>{t('hotels.title')}</h1>
          {/* <p>ค้นหาที่พักที่เหมาะกับคุณมากที่สุด</p> */}
        </div>

        
      </div>
    </div>
  );
}

