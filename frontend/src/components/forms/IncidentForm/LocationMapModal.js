import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { Button, Icon, Modal } from 'semantic-ui-react';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './leafletIcons';
import { reverseGeocode } from '../../../services/api';

const DEFAULT_CENTER = { lat: -34.42, lng: 150.89 };
const OSM_ATTRIBUTION = '© OpenStreetMap contributors';
const MAP_HEIGHT = 360;
const PREVIEW_DEBOUNCE_MS = 400;

// ---------------------------------------------------------------------------
// MapInvalidateSize — fixes Leaflet tile rendering inside a hidden modal
// ---------------------------------------------------------------------------
const MapInvalidateSize = ({ open }) => {
  const map = useMap();
  useEffect(() => {
    if (!open) return undefined;
    const id = window.setTimeout(() => map.invalidateSize(), 150);
    return () => window.clearTimeout(id);
  }, [open, map]);
  return null;
};

// ---------------------------------------------------------------------------
// LocationPin — draggable marker + map-click to reposition
// ---------------------------------------------------------------------------
const LocationPin = ({ position, onPositionChange }) => {
  const markerRef = useRef(null);
  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker) onPositionChange(marker.getLatLng());
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

// ---------------------------------------------------------------------------
// LocationMapModal
// ---------------------------------------------------------------------------
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
  const [previewAddress, setPreviewAddress] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const debounceRef = useRef(null);

  // Fetch a preview address for the given coords, debounced.
  const fetchPreview = useCallback((lat, lng) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setPreviewLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await reverseGeocode(lat, lng);
        setPreviewAddress(res.address || '');
      } catch {
        setPreviewAddress('');
      } finally {
        setPreviewLoading(false);
      }
    }, PREVIEW_DEBOUNCE_MS);
  }, []);

  const applyPosition = useCallback(
    (lat, lng) => {
      const next = { lat, lng };
      setPosition(next);
      setMapCenter(next);
      fetchPreview(lat, lng);
    },
    [fetchPreview]
  );

  // Reset state and resolve initial center when modal opens/closes.
  useEffect(() => {
    if (!open) {
      setPosition(null);
      setMapCenter(DEFAULT_CENTER);
      setPreviewAddress('');
      setPreviewLoading(false);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      return undefined;
    }

    if (typeof initialLat === 'number' && typeof initialLon === 'number') {
      applyPosition(initialLat, initialLon);
      return undefined;
    }

    if (!navigator.geolocation) {
      applyPosition(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
      return undefined;
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
        if (!cancelled) applyPosition(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 120000 }
    );

    return () => {
      cancelled = true;
    };
  }, [open, initialLat, initialLon, applyPosition]);

  const handlePositionChange = useCallback(
    (latlng) => {
      const next = { lat: latlng.lat, lng: latlng.lng };
      setPosition(next);
      fetchPreview(latlng.lat, latlng.lng);
    },
    [fetchPreview]
  );

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
              zoom={18}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom
            >
              <TileLayer
                attribution={OSM_ATTRIBUTION}
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapInvalidateSize open={open} />
              <LocationPin position={position} onPositionChange={handlePositionChange} />
            </MapContainer>
          )}
        </div>

        {/* Live address preview */}
        <div
          style={{
            minHeight: '2em',
            marginTop: '0.6rem',
            padding: '0.4rem 0.6rem',
            borderRadius: '4px',
            background: 'rgba(0,0,0,0.04)',
            fontSize: '0.9em',
            color: previewAddress ? 'rgba(0,0,0,0.75)' : 'rgba(0,0,0,0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}
        >
          {previewLoading ? (
            <>
              <Icon name="spinner" loading />
              <span>Resolving address…</span>
            </>
          ) : previewAddress ? (
            <>
              <Icon name="map marker alternate" />
              <span>{previewAddress}</span>
            </>
          ) : (
            <span>Tap the map to place a pin</span>
          )}
        </div>

        <p style={{ marginTop: '0.4rem', fontSize: '0.8em', color: 'rgba(0,0,0,0.4)' }}>
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
