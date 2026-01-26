/**
 * User Data Manager - Utility functions for managing user data and clearing cache
 * ✅ SECURITY: Prevents data leakage between users
 */

/**
 * Clear all user-specific data from localStorage and sessionStorage
 * Call this when user logs out or logs in as a different user
 */
export function clearAllUserData() {
  console.log('🗑️ Clearing all user data...');
  
  // Clear localStorage
  const localStorageKeys = [
    'is_logged_in',
    'user_data',
    'session_timestamp',
    'app_view',
    'ai_travel_trips_v1',
    'ai_travel_active_trip_id_v1',
    'remembered_email',
    'remember_me'
  ];
  
  localStorageKeys.forEach(key => {
    try {
      localStorage.removeItem(key);
    } catch (e) {
      console.error(`Failed to remove ${key} from localStorage:`, e);
    }
  });
  
  // Clear sessionStorage
  const sessionStorageKeys = [
    'ai_travel_loaded_trips'
  ];
  
  sessionStorageKeys.forEach(key => {
    try {
      sessionStorage.removeItem(key);
    } catch (e) {
      console.error(`Failed to remove ${key} from sessionStorage:`, e);
    }
  });
  
  console.log('✅ User data cleared');
}

/**
 * Validate that current user_id matches the user_id in trips
 * Returns true if validation passes, false if data belongs to different user
 */
export function validateUserOwnsTrips(currentUserId, trips) {
  if (!currentUserId || !trips || trips.length === 0) {
    return true; // No validation needed
  }
  
  const firstTripUserId = trips[0]?.userId || trips[0]?.user_id;
  
  // If trip doesn't have userId, assume it's from current user (backward compatibility)
  if (!firstTripUserId) {
    return true;
  }
  
  // Check if userId matches
  if (firstTripUserId !== currentUserId) {
    console.error(`🚨 SECURITY ALERT: Trips belong to different user! current=${currentUserId}, trips=${firstTripUserId}`);
    return false;
  }
  
  return true;
}

/**
 * Get user_id from localStorage (for checking before API calls)
 * Returns null if not logged in
 */
export function getUserIdFromStorage() {
  try {
    const userData = localStorage.getItem('user_data');
    if (!userData) return null;
    
    const user = JSON.parse(userData);
    return user?.id || user?.user_id || null;
  } catch (e) {
    console.error('Failed to get user_id from localStorage:', e);
    return null;
  }
}

/**
 * Check if user has changed and clear data if needed
 * Call this on app init or when user logs in
 */
export function checkAndClearIfUserChanged(newUserId) {
  if (!newUserId) return;
  
  const storedUserId = getUserIdFromStorage();
  
  if (storedUserId && storedUserId !== newUserId) {
    console.warn(`🚨 SECURITY: User changed from ${storedUserId} to ${newUserId}, clearing all data`);
    clearAllUserData();
    return true;
  }
  
  return false;
}
