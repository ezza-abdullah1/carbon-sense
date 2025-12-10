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
        <Label className="text-sm font-medium">Time Range</Label>
        <div className="flex gap-2">
          {intervals.map((item) => (
            <Button
              key={item.value}
              variant={interval === item.value ? "default" : "outline"}
              size="sm"
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

      <div className="flex items-center space-x-2">
        <Switch
          id="forecast-mode"
          checked={dataType === "forecast"}
          onCheckedChange={(checked) => onDataTypeChange(checked ? "forecast" : "historical")}
          data-testid="switch-forecast"
        />
        <Label htmlFor="forecast-mode" className="text-sm cursor-pointer">
          Show Forecast Data
        </Label>
      </div>
    </div>
  );
}
