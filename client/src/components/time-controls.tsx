import { Button } from "@/components/ui/button";
import { Calendar } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import type { TimeInterval, DataType } from "@shared/schema";

interface TimeControlsProps {
  interval: TimeInterval;
  onIntervalChange: (interval: TimeInterval) => void;
  dataType: DataType;
  onDataTypeChange: (type: DataType) => void;
  startDate?: string;
  endDate?: string;
}

export function TimeControls({
  interval,
  onIntervalChange,
  dataType,
  onDataTypeChange,
}: TimeControlsProps) {
  const intervals: { value: TimeInterval; label: string }[] = [
    { value: "monthly", label: "Monthly" },
    { value: "yearly", label: "Yearly" },
    { value: "custom", label: "Custom" },
  ];

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label className="text-sm font-medium">Time Interval</Label>
        <div className="flex gap-2">
          {intervals.map((item) => (
            <Button
              key={item.value}
              variant={interval === item.value ? "default" : "outline"}
              size="sm"
              onClick={() => onIntervalChange(item.value)}
              data-testid={`button-interval-${item.value}`}
            >
              {item.label}
            </Button>
          ))}
        </div>
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

      {interval === "custom" && (
        <Button variant="outline" size="sm" className="w-full" data-testid="button-date-picker">
          <Calendar className="h-4 w-4 mr-2" />
          Select Date Range
        </Button>
      )}
    </div>
  );
}
