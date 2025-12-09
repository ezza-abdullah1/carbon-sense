import { Badge } from "@/components/ui/badge";
import { Check } from "lucide-react";
import type { Sector } from "@shared/schema";

interface SectorFilterProps {
  selectedSectors: Sector[];
  onToggleSector: (sector: Sector) => void;
}

const sectorConfig: Record<Sector, { label: string; color: string }> = {
  transport: { label: "Transport", color: "hsl(217, 91%, 60%)" },
  industry: { label: "Industry", color: "hsl(280, 67%, 55%)" },
  energy: { label: "Energy", color: "hsl(45, 93%, 47%)" },
  waste: { label: "Waste", color: "hsl(25, 95%, 53%)" },
  buildings: { label: "Buildings", color: "hsl(338, 78%, 56%)" },
};

export function SectorFilter({ selectedSectors, onToggleSector }: SectorFilterProps) {
  const allSectors: Sector[] = ["transport", "industry", "energy", "waste", "buildings"];

  return (
    <div className="flex flex-wrap gap-2">
      {allSectors.map((sector) => {
        const isSelected = selectedSectors.includes(sector);
        const config = sectorConfig[sector];
        
        return (
          <Badge
            key={sector}
            variant={isSelected ? "default" : "outline"}
            className="cursor-pointer h-8 px-3 gap-1.5 hover-elevate active-elevate-2"
            style={isSelected ? { 
              backgroundColor: config.color,
              borderColor: config.color,
              color: "white"
            } : undefined}
            onClick={() => onToggleSector(sector)}
            data-testid={`filter-sector-${sector}`}
          >
            {isSelected && <Check className="h-3 w-3" />}
            {config.label}
          </Badge>
        );
      })}
    </div>
  );
}
