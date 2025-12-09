import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MapLegend() {
  const levels = [
    { label: "Low", color: "hsl(142, 65%, 45%)", range: "0-30%" },
    { label: "Moderate", color: "hsl(45, 93%, 47%)", range: "30-50%" },
    { label: "High", color: "hsl(25, 95%, 53%)", range: "50-70%" },
    { label: "Very High", color: "hsl(0, 72%, 51%)", range: "70-100%" },
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
