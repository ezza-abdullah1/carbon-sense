import { useEffect, useRef, useMemo } from "react";
import L from "leaflet";
import type { PowerPlant, UCSummary, Sector } from "@/lib/api";
import {
  computeQuantileBreaks,
  getYlOrRdColor,
  formatTonnes,
  getUCEmission,
  RAILWAY_COORDS,
  AIRPORT_COORDS,
  CITY_CENTRE_COORDS,
} from "@/lib/map-utils";
import "leaflet/dist/leaflet.css";

interface EmissionMapProps {
  ucBoundaries?: GeoJSON.FeatureCollection;
  ucSummaries?: UCSummary[];
  selectedUCCode: string | null;
  onUCSelect: (ucCode: string) => void;
  selectedSectors: Sector[];
  powerPlants?: PowerPlant[];
  selectedPlantName?: string | null;
  onPlantSelect?: (name: string | null) => void;
}

export function EmissionMap({
  ucBoundaries,
  ucSummaries,
  selectedUCCode,
  onUCSelect,
  selectedSectors,
  powerPlants,
  selectedPlantName,
  onPlantSelect,
}: EmissionMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const overlaysRef = useRef<L.LayerGroup | null>(null);
  const powerLayerRef = useRef<L.LayerGroup | null>(null);
  const onUCSelectRef = useRef(onUCSelect);
  const onPlantSelectRef = useRef(onPlantSelect);
  useEffect(() => {
    onPlantSelectRef.current = onPlantSelect;
  }, [onPlantSelect]);

  useEffect(() => {
    onUCSelectRef.current = onUCSelect;
  }, [onUCSelect]);

  // Build lookup: uc_code -> UCSummary
  const ucLookup = useMemo(() => {
    const map = new Map<string, UCSummary>();
    if (ucSummaries) {
      for (const uc of ucSummaries) {
        map.set(uc.uc_code, uc);
      }
    }
    return map;
  }, [ucSummaries]);

  // Compute quantile breaks from current sector selection
  const breaks = useMemo(() => {
    if (!ucSummaries) return [];
    const values = ucSummaries
      .map(uc => getUCEmission(uc, selectedSectors))
      .filter(v => v > 0)
      .sort((a, b) => a - b);
    return computeQuantileBreaks(values, 9);
  }, [ucSummaries, selectedSectors]);

  // Initialize map once
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [31.48, 74.33],
      zoom: 11,
      zoomControl: true,
      preferCanvas: false,
    });

    // CartoDB Positron — light basemap ideal for choropleths
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 20,
      }
    ).addTo(map);

    // Add static overlays (railway, airport, city centre)
    const overlayGroup = L.layerGroup();

    // ML-1 Railway line
    L.polyline(RAILWAY_COORDS, {
      color: "#1a4fa0",
      weight: 3,
      opacity: 0.8,
      dashArray: "10,6",
    })
      .bindTooltip("ML-1 Pakistan Railways", { sticky: true })
      .addTo(overlayGroup);

    // Airport marker
    L.marker(AIRPORT_COORDS, {
      icon: L.divIcon({
        html: '<div style="font-size:20px;text-shadow:1px 1px 2px rgba(0,0,0,0.5)">&#9992;</div>',
        className: "",
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      }),
    })
      .bindTooltip("Allama Iqbal International Airport", { sticky: true })
      .addTo(overlayGroup);

    // City centre marker
    L.marker(CITY_CENTRE_COORDS, {
      icon: L.divIcon({
        html: '<div style="font-size:16px;text-shadow:1px 1px 2px rgba(0,0,0,0.5)">&#9899;</div>',
        className: "",
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      }),
    })
      .bindTooltip("Lahore City Centre", { sticky: true })
      .addTo(overlayGroup);

    overlayGroup.addTo(map);
    overlaysRef.current = overlayGroup;
    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Render/update choropleth layer
  useEffect(() => {
    if (!mapRef.current || !ucBoundaries || !ucSummaries) return;

    // Remove previous GeoJSON layer
    if (geoJsonLayerRef.current) {
      geoJsonLayerRef.current.remove();
      geoJsonLayerRef.current = null;
    }

    const map = mapRef.current;

    const geoJsonLayer = L.geoJSON(ucBoundaries, {
      style: (feature) => {
        const ucCode = feature?.properties?.uc_code;
        const uc = ucLookup.get(ucCode);
        const emission = uc ? getUCEmission(uc, selectedSectors) : 0;
        const fillColor = getYlOrRdColor(emission, breaks);
        const isSelected = ucCode === selectedUCCode;

        return {
          fillColor,
          fillOpacity: isSelected ? 0.85 : 0.75,
          color: isSelected ? "#222" : "#444",
          weight: isSelected ? 3 : 0.6,
          opacity: isSelected ? 1 : 0.7,
        };
      },
      onEachFeature: (feature, layer) => {
        const ucCode: string = feature.properties?.uc_code ?? "";
        const ucName: string = feature.properties?.uc_name ?? "";
        const uc = ucLookup.get(ucCode);
        const emission = uc ? getUCEmission(uc, selectedSectors) : 0;

        // Sticky tooltip on hover
        layer.bindTooltip(
          `<div style="font-family:Arial,sans-serif;font-size:13px">
            <b>${ucName}</b><br/>${formatTonnes(emission)} CO\u2082e/yr
          </div>`,
          { sticky: true }
        );

        // Click to select
        layer.on("click", () => {
          onUCSelectRef.current(ucCode);
        });

        // Hover highlight
        layer.on("mouseover", () => {
          (layer as L.Path).setStyle({ weight: 2.5, fillOpacity: 0.85 });
          (layer as L.Path).bringToFront();
        });
        layer.on("mouseout", () => {
          geoJsonLayer.resetStyle(layer);
        });
      },
    }).addTo(map);

    geoJsonLayerRef.current = geoJsonLayer;

    // Bring overlays (railway, markers) to front
    if (overlaysRef.current) {
      overlaysRef.current.eachLayer((l) => {
        if ((l as L.Path).bringToFront) {
          (l as L.Path).bringToFront();
        }
      });
    }
  }, [ucBoundaries, ucSummaries, ucLookup, breaks, selectedSectors, selectedUCCode]);

  // Fly to selected UC
  useEffect(() => {
    if (!mapRef.current || !selectedUCCode || !ucSummaries) return;

    const uc = ucLookup.get(selectedUCCode);
    if (uc) {
      mapRef.current.flyTo(uc.centroid, 13, { duration: 0.5 });
    }
  }, [selectedUCCode, ucLookup, ucSummaries]);

  // Render/remove power-plant point markers.
  // Energy is a point-source sector — pins (sized by emissions) appear
  // whenever the user has "energy" toggled on, regardless of which other
  // sectors are active. The pin's anchor is its bottom tip so it points
  // exactly at the plant's coordinates.
  useEffect(() => {
    if (!mapRef.current) return;

    if (powerLayerRef.current) {
      powerLayerRef.current.remove();
      powerLayerRef.current = null;
    }

    if (!selectedSectors.includes("energy") || !powerPlants || powerPlants.length === 0) {
      return;
    }

    const group = L.layerGroup();
    const maxEmissions = Math.max(...powerPlants.map((p) => p.emissions), 1);

    const buildPinHtml = (width: number, fill: string, stroke: string, strokeWidth: number) => {
      const height = Math.round(width * 1.35);
      // Classic location pin: teardrop body + inner circle, viewBox 24×32 so
      // the tip lands at (12, 32) — matches the iconAnchor below.
      return `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="${width}" height="${height}" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,0.35))">
  <path d="M12 0C5.4 0 0 5.4 0 12c0 8.4 12 20 12 20s12-11.6 12-20C24 5.4 18.6 0 12 0z"
        fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>
  <circle cx="12" cy="12" r="4.5" fill="#fff" stroke="${stroke}" stroke-width="${Math.max(strokeWidth - 0.5, 0.5)}"/>
</svg>`;
    };

    for (const plant of powerPlants) {
      const ratio = Math.sqrt(plant.emissions / maxEmissions);
      const width = Math.round(18 + ratio * 16); // 18 → 34 px
      const height = Math.round(width * 1.35);
      const isSelected = plant.source === selectedPlantName;
      const fill = isSelected ? "#f59e0b" : "#facc15";
      const stroke = isSelected ? "#000" : "#7c2d12";
      const strokeWidth = isSelected ? 2 : 1.25;

      const marker = L.marker([plant.lat, plant.lng], {
        icon: L.divIcon({
          html: buildPinHtml(width, fill, stroke, strokeWidth),
          className: "power-plant-pin",
          iconSize: [width, height],
          iconAnchor: [Math.round(width / 2), height], // bottom tip
          tooltipAnchor: [0, -height],
        }),
        // Selected pin on top so it isn't visually buried by neighbours.
        zIndexOffset: isSelected ? 1000 : 0,
      });
      marker.bindTooltip(
        `<div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.4">
          <b>${plant.source}</b><br/>
          ${plant.type ? `<span style="color:#666">${plant.type}</span><br/>` : ""}
          ${formatTonnes(plant.emissions)} CO₂e
        </div>`,
        { sticky: true },
      );
      marker.on("click", () => {
        onPlantSelectRef.current?.(plant.source);
      });
      marker.addTo(group);
    }

    group.addTo(mapRef.current);
    powerLayerRef.current = group;

    return () => {
      if (powerLayerRef.current) {
        powerLayerRef.current.remove();
        powerLayerRef.current = null;
      }
    };
  }, [powerPlants, selectedSectors, selectedPlantName]);

  return (
    <div
      ref={mapContainerRef}
      className="w-full h-full rounded-lg border border-border"
      data-testid="map-container"
    />
  );
}
