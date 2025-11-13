import { useState } from 'react';
import { SectorFilter } from '../sector-filter';
import type { Sector } from '@shared/schema';

export default function SectorFilterExample() {
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>(["transport", "energy"]);

  const handleToggle = (sector: Sector) => {
    setSelectedSectors(prev =>
      prev.includes(sector)
        ? prev.filter(s => s !== sector)
        : [...prev, sector]
    );
  };

  return (
    <div className="p-6">
      <SectorFilter selectedSectors={selectedSectors} onToggleSector={handleToggle} />
    </div>
  );
}
