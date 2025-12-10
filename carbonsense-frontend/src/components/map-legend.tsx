import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MapLegend() {
  // Evidence-based thresholds aligned with climate science and Paris Agreement targets
  const levels = [
    { label: "Low", color: "hsl(142, 65%, 45%)", range: "<20k tonnes" },
    { label: "Moderate", color: "hsl(45, 93%, 47%)", range: "20k-100k tonnes" },
    { label: "High", color: "hsl(25, 95%, 53%)", range: "100k-500k tonnes" },
    { label: "Very High", color: "hsl(0, 72%, 51%)", range: ">500k tonnes" },
  ];

  return (
    <Card className="backdrop-blur-md bg-card/95">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Emission Levels</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {levels.map((level) => (
          <div key={level.label} className="flex items-center gap-2">
            <div
              className="w-6 h-4 rounded border border-border"
              style={{ backgroundColor: level.color }}
            />
            <div className="flex-1">
              <div className="text-xs font-medium">{level.label}</div>
              <div className="text-xs text-muted-foreground font-mono">{level.range}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
