import { AreaDetailPanel } from '../area-detail-panel';
import type { UCSummary } from '@/lib/api';

const mockUCSummary: UCSummary = {
  uc_code: 'PB-LAH-UC039',
  uc_name: 'Cantonment',
  area_km2: 99.254,
  centroid: [31.503418, 74.406132],
  data_type: 'forecast',
  sectors: {
    transport: {
      annual_t: 554311,
      road_annual_t: 487791,
      dom_avi_annual_t: 4745,
      intl_avi_annual_t: 60715,
      rail_annual_t: 1059,
      road_pct: 88.0,
      road_weight: 0.0874,
      rail_weight: 0.0132,
      intensity_t_per_km2: 5585,
      rank_in_division: 1,
      ci_lower_annual_t: 526220,
      ci_upper_annual_t: 582402,
      dominant_source: 'road',
      risk_flags: ['high_absolute', 'aviation_plume_proximity'],
      monthly_t: [43951, 39821, 43982, 45650, 49770, 48974, 49626, 49361, 47920, 47073, 43005, 45178],
    },
    buildings: {
      residential_t: 1279346,
      non_residential_t: 24508,
      total_t: 1303854,
      intensity_t_km2: 13137,
      ci_lower_90_t: 941457,
      ci_upper_90_t: 1666251,
      rank_in_district: 1,
      risk: { RF1_intensity_hotspot: true, RF1_volume_hotspot: true },
    },
    energy: 12345.6,
    industry: 0,
    waste: {
      annual_t: 8901.2,
      monthly_t: [],
      point_source_t: 6000,
      solid_waste_t: 2000,
      wastewater_t: 901.2,
      point_pct: 67.4,
      risk_level: 'Moderate',
    },
  },
  total_annual_t: 1879412,
};

export default function AreaDetailPanelExample() {
  return (
    <div className="p-6 max-w-md h-[600px]">
      <AreaDetailPanel
        ucSummary={mockUCSummary}
        selectedSectors={['transport', 'buildings', 'energy', 'industry', 'waste']}
        onClose={() => console.log('Close panel')}
      />
    </div>
  );
}
