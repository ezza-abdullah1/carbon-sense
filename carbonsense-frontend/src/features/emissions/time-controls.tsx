import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import type { DataType } from "@shared/schema";
import type { TimeInterval } from "@/lib/api";

interface TimeControlsProps {
  interval: TimeInterval;
  onIntervalChange: (interval: TimeInterval) => void;
  dataType: DataType;
  onDataTypeChange: (type: DataType) => void;
}

export function TimeControls({
  interval,
  onIntervalChange,
  dataType,
  onDataTypeChange,
}: TimeControlsProps) {
  const intervals: { value: TimeInterval; label: string; description: string }[] = [
    { value: "monthly", label: "Monthly", description: "Last 12 months" },
    { value: "yearly", label: "Yearly", description: "Last 3 years" },
  ];

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label className="text-sm font-semibold tracking-tight">Time Range</Label>
        <div className="flex bg-black/5 dark:bg-white/5 p-1 rounded-lg">
          {intervals.map((item) => (
            <Button
              key={item.value}
              variant={interval === item.value ? "default" : "ghost"}
              size="sm"
              className={`flex-1 rounded-md text-xs font-medium transition-all ${
                interval === item.value 
                  ? "bg-white dark:bg-black/60 shadow-sm text-emerald-600 dark:text-emerald-400 hover:bg-white dark:hover:bg-black/60 hover:text-emerald-700 dark:hover:text-emerald-300" 
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"
              }`}
              onClick={() => onIntervalChange(item.value)}
              data-testid={`button-interval-${item.value}`}
              title={item.description}
            >
              {item.label}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {interval === "monthly" ? "Showing last 12 months" : "Showing last 3 years"}
        </p>
      </div>

      <div className="flex items-center space-x-3 pt-2">
        <Switch
          id="forecast-mode"
          checked={dataType === "forecast"}
          onCheckedChange={(checked) => onDataTypeChange(checked ? "forecast" : "historical")}
          data-testid="switch-forecast"
          className="data-[state=checked]:bg-emerald-500"
        />
        <Label htmlFor="forecast-mode" className="text-sm font-medium cursor-pointer">
          Show Forecast Data
        </Label>
      </div>
    </div>
  );
}
