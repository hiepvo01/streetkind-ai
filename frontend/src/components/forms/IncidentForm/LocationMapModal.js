import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { Button, Modal } from 'semantic-ui-react';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './leafletIcons';

const DEFAULT_CENTER = { lat: -34.42, lng: 150.89 };
const OSM_ATTRIBUTION = '© OpenStreetMap contributors';
const MAP_HEIGHT = 360;

const MapInvalidateSize = ({ open }) => {
  const map = useMap();
  useEffect(() => {
    if (!open) return undefined;
    const id = window.setTimeout(() => {
      map.invalidateSize();
    }, 150);
    return () => window.clearTimeout(id);
  }, [open, map]);
  return null;
};

const LocationPin = ({ position, onPositionChange }) => {
  const markerRef = useRef(null);
  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker) {
          onPositionChange(marker.getLatLng());
        }
      },
    }),
    [onPositionChange]
  );

  useMapEvents({
    click(e) {
      onPositionChange(e.latlng);
    },
  });

  if (!position) return null;

  return (
    <Marker
      draggable
      eventHandlers={eventHandlers}
      position={position}
      ref={markerRef}
    />
  );
};

LocationPin.propTypes = {
  position: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lng: PropTypes.number.isRequired,
  }),
  onPositionChange: PropTypes.func.isRequired,
};

const LocationMapModal = ({
  open,
  onClose,
  initialLat,
  initialLon,
  onConfirm,
  loading,
}) => {
  const [position, setPosition] = useState(null);
  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);

  const applyPosition = useCallback((lat, lng) => {
    const next = { lat, lng };
    setPosition(next);
    setMapCenter(next);
  }, []);

  useEffect(() => {
    if (!open) {
      setPosition(null);
      setMapCenter(DEFAULT_CENTER);
      return;
    }

    if (typeof initialLat === 'number' && typeof initialLon === 'number') {
      applyPosition(initialLat, initialLon);
      return;
    }

    if (!navigator.geolocation) {
      applyPosition(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
      return;
    }

    let cancelled = false;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (cancelled) return;
        const lat = pos?.coords?.latitude;
        const lon = pos?.coords?.longitude;
        if (typeof lat === 'number' && typeof lon === 'number') {
          applyPosition(lat, lon);
        } else {
          applyPosition(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
        }
      },
      () => {
        if (!cancelled) {
          applyPosition(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
        }
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 120000 }
    );

    return () => {
      cancelled = true;
    };
  }, [open, initialLat, initialLon, applyPosition]);

  const handleConfirm = () => {
    if (!position || loading) return;
    onConfirm({ lat: position.lat, lon: position.lng });
  };

  return (
    <Modal open={open} onClose={onClose} size="small" closeIcon>
      <Modal.Header>Pick incident location</Modal.Header>
      <Modal.Content>
        <p style={{ marginBottom: '0.75rem', color: 'rgba(0,0,0,0.6)' }}>
          Tap the map or drag the pin to set where the incident happened.
        </p>
        <div style={{ height: MAP_HEIGHT, width: '100%' }}>
          {open && position && (
            <MapContainer
              center={[mapCenter.lat, mapCenter.lng]}
              zoom={16}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom
            >
              <TileLayer
                attribution={OSM_ATTRIBUTION}
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapInvalidateSize open={open} />
              <LocationPin position={position} onPositionChange={setPosition} />
            </MapContainer>
          )}
        </div>
        <p style={{ marginTop: '0.5rem', fontSize: '0.85em', color: 'rgba(0,0,0,0.5)' }}>
          {OSM_ATTRIBUTION}
        </p>
      </Modal.Content>
      <Modal.Actions>
        <Button type="button" onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          type="button"
          primary
          icon="checkmark"
          labelPosition="left"
          content="Use this location"
          onClick={handleConfirm}
          loading={loading}
          disabled={!position || loading}
        />
      </Modal.Actions>
    </Modal>
  );
};

LocationMapModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  initialLat: PropTypes.number,
  initialLon: PropTypes.number,
  onConfirm: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};

LocationMapModal.defaultProps = {
  initialLat: null,
  initialLon: null,
  loading: false,
};

export default LocationMapModal;
