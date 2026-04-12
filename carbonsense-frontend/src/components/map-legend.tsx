import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle, X, Map as MapIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function MapLegend() {
  const [isOpen, setIsOpen] = useState(false); // start closed by default so it's clean!

  // Evidence-based thresholds aligned with climate science and Paris Agreement targets
  const levels = [
    { label: "Low", color: "hsl(142, 65%, 45%)", range: "<20k tonnes" },
    { label: "Moderate", color: "hsl(45, 93%, 47%)", range: "20k-100k tonnes" },
    { label: "High", color: "hsl(25, 95%, 53%)", range: "100k-500k tonnes" },
    { label: "Very High", color: "hsl(0, 72%, 51%)", range: ">500k tonnes" },
  ];

  if (!isOpen) {
    return (
      <Button 
        variant="secondary" 
        size="icon" 
        onClick={() => setIsOpen(true)}
        className="w-10 h-10 rounded-full shadow-lg bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 group"
      >
        <HelpCircle className="h-5 w-5 opacity-70 group-hover:opacity-100 transition-opacity" />
      </Button>
    );
  }

  return (
    <Card className="w-48 bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] transition-all duration-300">
      <CardHeader className="flex flex-row items-center justify-between pb-2 pt-3 px-4 shadow-sm border-b border-black/5 dark:border-white/5">
        <CardTitle className="text-xs font-semibold flex items-center gap-1.5"><MapIcon className="h-3.5 w-3.5"/> Emission Levels</CardTitle>
        <Button variant="ghost" size="icon" className="h-6 w-6 -mr-2" onClick={() => setIsOpen(false)}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 p-4 pt-3">
        {levels.map((level) => (
          <div key={level.label} className="flex items-center gap-2">
            <div
              className="w-3.5 h-3.5 rounded-[3px]"
              style={{ backgroundColor: level.color }}
            />
            <div className="flex-1 leading-none">
              <div className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{level.label}</div>
              <div className="text-[9px] text-muted-foreground font-mono mt-0.5">{level.range}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
