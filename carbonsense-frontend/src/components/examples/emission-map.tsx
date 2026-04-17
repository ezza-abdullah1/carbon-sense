import { useState } from 'react';
import { EmissionMap } from '../emission-map';

export default function EmissionMapExample() {
  const [selectedUCCode, setSelectedUCCode] = useState<string | null>(null);

  return (
    <div className="h-screen w-full">
      <EmissionMap
        selectedUCCode={selectedUCCode}
        onUCSelect={setSelectedUCCode}
        selectedSectors={["transport", "buildings", "energy", "industry", "waste"]}
      />
    </div>
  );
}
