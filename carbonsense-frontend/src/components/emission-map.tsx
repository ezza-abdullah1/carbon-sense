import { useEffect, useRef, useCallback } from "react";
import L from "leaflet";
import type { AreaInfo } from "@shared/schema";
import "leaflet/dist/leaflet.css";

interface EmissionMapProps {
  areas: AreaInfo[];
  selectedAreaId: string | null;
  onAreaSelect: (areaId: string) => void;
  emissionData: Record<string, number>;
  maxEmission: number;
}

export function EmissionMap({ areas, selectedAreaId, onAreaSelect, emissionData, maxEmission }: EmissionMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Map<string, L.Circle>>(new Map());
  const onAreaSelectRef = useRef(onAreaSelect);

  useEffect(() => {
    onAreaSelectRef.current = onAreaSelect;
  }, [onAreaSelect]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [31.5497, 74.3436],
      zoom: 12,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    markersRef.current.forEach(marker => marker.remove());
    markersRef.current.clear();

    const map = mapRef.current;

    areas.forEach(area => {
      const emission = emissionData[area.id] || 0;

      // Use absolute emission value for color (evidence-based thresholds)
      const color = getEmissionColor(emission);

      // Scale radius based on relative intensity for visual distinction
      const intensity = maxEmission > 0 ? emission / maxEmission : 0;
      const radius = 800 + (Math.min(intensity, 1) * 1200);

      const circle = L.circle(area.coordinates, {
        color: color,
        fillColor: color,
        fillOpacity: 0.4,
        radius: radius,
        weight: selectedAreaId === area.id ? 3 : 1,
      }).addTo(map);

      // Tooltip on hover (brief info)
      circle.bindTooltip(`
        <div class="font-sans text-sm">
          <strong>${area.name}</strong><br/>
          ${emission.toLocaleString(undefined, { maximumFractionDigits: 0 })} tons CO₂e
        </div>
      `, {
        permanent: false,
        direction: 'top',
        offset: [0, -10],
        className: 'emission-tooltip'
      });

      // Popup on click (detailed info)
      circle.bindPopup(`
        <div class="font-sans">
          <h3 class="font-semibold text-base mb-1">${area.name}</h3>
          <p class="text-sm text-muted-foreground">
            Emissions: <span class="font-mono font-medium">${emission.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span> tons CO₂e
          </p>
          <p class="text-xs text-muted-foreground mt-1">Click "View Full Analysis" for details</p>
        </div>
      `);

      circle.on("click", () => {
        onAreaSelectRef.current(area.id);
      });

      markersRef.current.set(area.id, circle);
    });
  }, [areas, emissionData, maxEmission, selectedAreaId]);

  useEffect(() => {
    if (!mapRef.current || !selectedAreaId) return;

    const selectedArea = areas.find(a => a.id === selectedAreaId);
    if (selectedArea) {
      mapRef.current.flyTo(selectedArea.coordinates, 13, {
        duration: 0.5,
      });
    }
  }, [selectedAreaId, areas]);

  return (
    <div 
      ref={mapContainerRef} 
      className="w-full h-full rounded-lg border border-border"
      data-testid="map-container"
    />
  );
}

/**
 * Get emission color based on absolute thresholds (tonnes CO₂e)
 * Based on climate science and Paris Agreement targets:
 * - Low: <20,000 tonnes (below EIB materiality threshold)
 * - Moderate: 20,000-100,000 tonnes (significant but manageable)
 * - High: 100,000-500,000 tonnes (major emitters requiring reduction plans)
 * - Very High: >500,000 tonnes (critical - immediate action required)
 */
function getEmissionColor(emissionTonnes: number): string {
  if (emissionTonnes < 20000) return "hsl(142, 65%, 45%)";   // Green - Low
  if (emissionTonnes < 100000) return "hsl(45, 93%, 47%)";   // Yellow - Moderate
  if (emissionTonnes < 500000) return "hsl(25, 95%, 53%)";   // Orange - High
  return "hsl(0, 72%, 51%)";                                  // Red - Very High
}
