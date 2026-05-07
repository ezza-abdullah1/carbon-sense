import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import type { Sector } from "@shared/schema";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SectorFilterProps {
  selectedSectors: Sector[];
  onToggleSector: (sector: Sector) => void;
  onSelectAll?: () => void;
  onClearAll?: () => void;
}

const sectorConfig: Record<Sector, { label: string; color: string; description: string }> = {
  transport: {
    label: "Transport",
    color: "hsl(217, 91%, 60%)",
    description: "Road vehicles, aviation, railways, and shipping emissions"
  },
  industry: {
    label: "Industry",
    color: "hsl(280, 67%, 55%)",
    description: "Manufacturing, cement, steel, and chemical production"
  },
  energy: {
    label: "Energy",
    color: "hsl(45, 93%, 47%)",
    description: "Power plants, electricity generation, and fuel combustion"
  },
  waste: {
    label: "Waste",
    color: "hsl(25, 95%, 53%)",
    description: "Landfills, waste treatment, and incineration"
  },
  buildings: {
    label: "Buildings",
    color: "hsl(338, 78%, 56%)",
    description: "Residential and commercial heating, cooling, and appliances"
  },
};

export function SectorFilter({ selectedSectors, onToggleSector, onSelectAll, onClearAll }: SectorFilterProps) {
  const allSectors: Sector[] = ["transport", "industry", "energy", "waste", "buildings"];
  const allSelected = selectedSectors.length === allSectors.length;
  const noneSelected = selectedSectors.length === 0;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {allSectors.map((sector) => {
          const isSelected = selectedSectors.includes(sector);
          const config = sectorConfig[sector];

          return (
            <Tooltip key={sector}>
              <TooltipTrigger asChild>
                <Badge
                  variant={isSelected ? "default" : "outline"}
                  className={`cursor-pointer h-8 px-3 gap-1.5 transition-all duration-300 font-medium ${
                    isSelected 
                      ? "shadow-md hover:scale-105" 
                      : "bg-black/5 dark:bg-white/5 border-transparent text-slate-600 dark:text-slate-400 hover:bg-black/10 dark:hover:bg-white/10 hover:text-slate-900 dark:hover:text-white"
                  }`}
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
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[200px]">
                <p className="text-xs">{config.description}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>

      {/* Quick actions */}
      <div className="flex gap-3 pt-1">
        {onSelectAll && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2.5 font-medium text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 hover:bg-emerald-500/10"
            onClick={onSelectAll}
            disabled={allSelected}
          >
            Select All
          </Button>
        )}
        {onClearAll && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2.5 font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-500/10"
            onClick={onClearAll}
            disabled={noneSelected}
          >
            Clear All
          </Button>
        )}
      </div>

      {/* Validation message */}
      {noneSelected && (
        <p className="text-xs text-destructive">Please select at least one sector to analyze.</p>
      )}
    </div>
  );
}
