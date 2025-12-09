import { AreaDetailPanel } from '../area-detail-panel';

export default function AreaDetailPanelExample() {
  return (
    <div className="p-6 max-w-md">
      <AreaDetailPanel
        areaName="Gulberg"
        totalEmissions={1250.5}
        trend="down"
        trendPercentage={2.1}
        sectorBreakdown={{
          transport: 450.2,
          industry: 320.5,
          energy: 280.1,
          waste: 120.7,
          buildings: 79.0,
        }}
        onClose={() => console.log('Close panel')}
      />
    </div>
  );
}
