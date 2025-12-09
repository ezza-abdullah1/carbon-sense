import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X, TrendingUp, TrendingDown } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface AreaDetailPanelProps {
  areaName: string;
  totalEmissions: number;
  trend: "up" | "down";
  trendPercentage: number;
  sectorBreakdown: {
    transport: number;
    industry: number;
    energy: number;
    waste: number;
    buildings: number;
  };
  onClose: () => void;
  onViewAnalysis?: () => void;
}

export function AreaDetailPanel({
  areaName,
  totalEmissions,
  trend,
  trendPercentage,
  sectorBreakdown,
  onClose,
  onViewAnalysis,
}: AreaDetailPanelProps) {
  const maxSector = Math.max(...Object.values(sectorBreakdown));

  const sectors = [
    { key: "transport", label: "Transport", color: "hsl(217, 91%, 60%)" },
    { key: "industry", label: "Industry", color: "hsl(280, 67%, 55%)" },
    { key: "energy", label: "Energy", color: "hsl(45, 93%, 47%)" },
    { key: "waste", label: "Waste", color: "hsl(25, 95%, 53%)" },
    { key: "buildings", label: "Buildings", color: "hsl(338, 78%, 56%)" },
  ];

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex-row items-start justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-xl">{areaName}</CardTitle>
          <p className="text-sm text-muted-foreground">Emission Details</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          data-testid="button-close-detail"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 space-y-6">
        <div className="space-y-2">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-mono font-bold">
              {totalEmissions.toFixed(2)}
            </span>
            <span className="text-sm text-muted-foreground">tons CO₂e</span>
          </div>
          
          <div className="flex items-center gap-2">
            {trend === "up" ? (
              <Badge variant="destructive" className="gap-1">
                <TrendingUp className="h-3 w-3" />
                +{trendPercentage}%
              </Badge>
            ) : (
              <Badge className="gap-1 bg-primary">
                <TrendingDown className="h-3 w-3" />
                -{trendPercentage}%
              </Badge>
            )}
            <span className="text-xs text-muted-foreground">vs last period</span>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Sectoral Breakdown</h3>
          <div className="space-y-3">
            {sectors.map((sector) => {
              const value = sectorBreakdown[sector.key as keyof typeof sectorBreakdown];
              const percentage = maxSector > 0 ? (value / maxSector) * 100 : 0;

              return (
                <div key={sector.key} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{sector.label}</span>
                    <span className="font-mono text-muted-foreground">
                      {value.toFixed(2)} tons
                    </span>
                  </div>
                  <Progress
                    value={percentage}
                    className="h-2"
                    style={{
                      "--progress-background": sector.color,
                    } as React.CSSProperties}
                  />
                </div>
              );
            })}
          </div>
        </div>

        <Button 
          className="w-full" 
          onClick={onViewAnalysis}
          data-testid="button-view-analysis"
        >
          View Full Analysis
        </Button>
      </CardContent>
    </Card>
  );
}
