import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, Map as MapIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getYlOrRdPalette } from "@/lib/map-utils";
import { formatTonnes } from "@/lib/map-utils";

interface MapLegendProps {
  minValue?: number;
  maxValue?: number;
}

export function MapLegend({ minValue = 0, maxValue = 0 }: MapLegendProps) {
  const [isOpen, setIsOpen] = useState(false);
  const palette = getYlOrRdPalette();

  if (!isOpen) {
    return (
      <Button
        variant="secondary"
        size="icon"
        onClick={() => setIsOpen(true)}
        className="w-10 h-10 rounded-full shadow-lg bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 group"
      >
        <MapIcon className="h-5 w-5 opacity-70 group-hover:opacity-100 transition-opacity" />
      </Button>
    );
  }

  const mid = (minValue + maxValue) / 2;

  return (
    <Card className="w-56 bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] transition-all duration-300">
      <CardHeader className="flex flex-row items-center justify-between pb-2 pt-3 px-4 shadow-sm border-b border-black/5 dark:border-white/5">
        <CardTitle className="text-xs font-semibold flex items-center gap-1.5">
          <MapIcon className="h-3.5 w-3.5" /> Annual CO&#x2082;e (tonnes)
        </CardTitle>
        <Button variant="ghost" size="icon" className="h-6 w-6 -mr-2" onClick={() => setIsOpen(false)}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="p-4 pt-3 space-y-2">
        {/* Gradient bar */}
        <div
          className="h-3 rounded-sm w-full"
          style={{
            background: `linear-gradient(to right, ${palette.join(", ")})`,
          }}
        />
        {/* Tick labels */}
        {maxValue > 0 && (
          <div className="flex justify-between text-[9px] font-mono text-muted-foreground">
            <span>{formatTonnes(minValue)}</span>
            <span>{formatTonnes(mid)}</span>
            <span>{formatTonnes(maxValue)}</span>
          </div>
        )}
        {/* Overlay legend */}
        <div className="pt-2 border-t border-black/5 dark:border-white/5 space-y-1.5">
          <div className="flex items-center gap-2 text-[10px]">
            <div className="w-5 h-0.5 bg-[#1a4fa0] rounded" style={{ borderTop: "2px dashed #1a4fa0" }} />
            <span className="text-muted-foreground">ML-1 Railway</span>
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span className="text-sm leading-none">&#9992;</span>
            <span className="text-muted-foreground">Airport</span>
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span className="text-sm leading-none">&#9899;</span>
            <span className="text-muted-foreground">City Centre</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
