import React, { useMemo } from 'react';
import { GoogleMap, Marker, InfoWindow, useLoadScript } from '@react-google-maps/api';

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

const libraries = ['places'];

const defaultCenter = {
  lat: 13.7563, // กรุงเทพ
  lng: 100.5018
};

const defaultMapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  streetViewControl: false,
  mapTypeControl: false,
  fullscreenControl: true,
};

export default function GoogleMapView({
  center,
  zoom = 15,
  markers = [],
  height = '300px',
  width = '100%',
  onMarkerClick,
  showInfoWindow = false,
  selectedMarkerIndex = null,
}) {
  const { isLoaded, loadError } = useLoadScript({
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
    libraries,
  });

  const mapCenter = useMemo(() => {
    if (center) return center;
    if (markers.length > 0) {
      return {
        lat: markers[0].lat,
        lng: markers[0].lng,
      };
    }
    return defaultCenter;
  }, [center, markers]);

  if (loadError) {
    return (
      <div style={{ 
        height, 
        width, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd',
        borderRadius: '4px'
      }}>
        <div style={{ color: '#666', textAlign: 'center' }}>
          <div>⚠️ ไม่สามารถโหลด Google Maps ได้</div>
          <div style={{ fontSize: '12px', marginTop: '4px' }}>
            {GOOGLE_MAPS_API_KEY ? 'ตรวจสอบ API Key' : 'กรุณาตั้งค่า VITE_GOOGLE_MAPS_API_KEY'}
          </div>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div style={{ 
        height, 
        width, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd',
        borderRadius: '4px'
      }}>
        <div style={{ color: '#666' }}>กำลังโหลดแผนที่...</div>
      </div>
    );
  }

  return (
    <div style={{ height, width, borderRadius: '4px', overflow: 'hidden' }}>
      <GoogleMap
        mapContainerStyle={{ height: '100%', width: '100%' }}
        center={mapCenter}
        zoom={zoom}
        options={defaultMapOptions}
      >
        {markers.map((marker, index) => (
          <React.Fragment key={index}>
            <Marker
              position={{ lat: marker.lat, lng: marker.lng }}
              title={marker.title}
              onClick={() => onMarkerClick && onMarkerClick(index, marker)}
            />
            {showInfoWindow && selectedMarkerIndex === index && marker.info && (
              <InfoWindow
                position={{ lat: marker.lat, lng: marker.lng }}
                onCloseClick={() => {}}
              >
                <div style={{ padding: '4px' }}>
                  <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                    {marker.title}
                  </div>
                  {marker.info && (
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {marker.info}
                    </div>
                  )}
                </div>
              </InfoWindow>
            )}
          </React.Fragment>
        ))}
      </GoogleMap>
    </div>
  );
}

