import { useState } from 'react';
import { EmissionMap } from '../emission-map';
import type { AreaInfo } from '@shared/schema';

export default function EmissionMapExample() {
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);

  const mockAreas: AreaInfo[] = [
    { id: "1", name: "Gulberg", coordinates: [31.5204, 74.3587], bounds: [[31.51, 74.34], [31.53, 74.37]] },
    { id: "2", name: "Model Town", coordinates: [31.4826, 74.3186], bounds: [[31.47, 74.30], [31.49, 74.33]] },
    { id: "3", name: "Johar Town", coordinates: [31.4697, 74.2728], bounds: [[31.46, 74.26], [31.48, 74.29]] },
  ];

  const mockEmissionData = {
    "1": 1250.5,
    "2": 980.2,
    "3": 1450.8,
  };

  return (
    <div className="h-screen w-full">
      <EmissionMap
        areas={mockAreas}
        selectedAreaId={selectedAreaId}
        onAreaSelect={setSelectedAreaId}
        emissionData={mockEmissionData}
        maxEmission={1500}
      />
    </div>
  );
}
