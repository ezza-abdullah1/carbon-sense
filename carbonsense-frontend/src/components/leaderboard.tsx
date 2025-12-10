import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendingUp, TrendingDown, Minus, Trophy, Medal, Award, Factory, Truck, Zap, Trash2, Building2 } from "lucide-react";
import type { LeaderboardEntry } from "@shared/schema";
import { ScrollArea } from "@/components/ui/scroll-area";

interface LeaderboardProps {
  entries: LeaderboardEntry[];
  selectedAreaId: string | null;
  onAreaSelect: (areaId: string) => void;
  sectorTotals?: {
    transport: number;
    industry: number;
    energy: number;
    waste: number;
    buildings: number;
  };
}

const sectorConfig = {
  energy: { label: "Energy", icon: Zap, color: "hsl(45, 93%, 47%)" },
  transport: { label: "Transport", icon: Truck, color: "hsl(217, 91%, 60%)" },
  industry: { label: "Industry", icon: Factory, color: "hsl(280, 67%, 55%)" },
  waste: { label: "Waste", icon: Trash2, color: "hsl(25, 95%, 53%)" },
  buildings: { label: "Buildings", icon: Building2, color: "hsl(338, 78%, 56%)" },
};

export function Leaderboard({ entries, selectedAreaId, onAreaSelect, sectorTotals }: LeaderboardProps) {
  const [viewMode, setViewMode] = useState<"areas" | "sectors">("areas");

  // Calculate sector rankings
  const sectorRankings = useMemo(() => {
    if (!sectorTotals) return [];

    const sectors = Object.entries(sectorTotals)
      .map(([key, value]) => ({
        key: key as keyof typeof sectorConfig,
        value,
        config: sectorConfig[key as keyof typeof sectorConfig],
      }))
      .sort((a, b) => b.value - a.value);

    const total = sectors.reduce((sum, s) => sum + s.value, 0);

    return sectors.map((s, index) => ({
      ...s,
      rank: index + 1,
      percentage: total > 0 ? (s.value / total) * 100 : 0,
    }));
  }, [sectorTotals]);

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <CardHeader className="pb-2 flex-shrink-0">
        <CardTitle className="text-lg">Emission Rankings</CardTitle>
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "areas" | "sectors")} className="mt-2">
          <TabsList className="grid w-full grid-cols-2 h-8">
            <TabsTrigger value="areas" className="text-xs">Areas ({entries.length})</TabsTrigger>
            <TabsTrigger value="sectors" className="text-xs">Sectors</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="flex-1 p-0 overflow-hidden">
        {viewMode === "areas" ? (
          <ScrollArea className="h-full max-h-[calc(100vh-280px)]">
            <div className="space-y-1 px-6 pb-6">
              {entries.map((entry) => (
                <div
                  key={entry.areaId}
                  onClick={() => onAreaSelect(entry.areaId)}
                  className={`
                    flex items-center gap-3 p-3 rounded-md cursor-pointer transition-colors
                    hover-elevate active-elevate-2
                    ${selectedAreaId === entry.areaId ? 'bg-accent' : ''}
                  `}
                  data-testid={`leaderboard-item-${entry.areaId}`}
                >
                  <div className="flex items-center justify-center w-8 h-8 flex-shrink-0">
                    {entry.rank === 1 && <Trophy className="h-5 w-5 text-chart-3" />}
                    {entry.rank === 2 && <Medal className="h-5 w-5 text-muted-foreground" />}
                    {entry.rank === 3 && <Award className="h-5 w-5 text-chart-4" />}
                    {entry.rank > 3 && (
                      <span className="font-mono text-sm font-medium text-muted-foreground">
                        #{entry.rank}
                      </span>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{entry.areaName}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {entry.emissions.toLocaleString(undefined, { maximumFractionDigits: 0 })} tons CO₂e
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {entry.trend === "up" && (
                      <>
                        <TrendingUp className="h-4 w-4 text-destructive" />
                        <span className="font-mono text-xs text-destructive">
                          +{entry.trendPercentage}%
                        </span>
                      </>
                    )}
                    {entry.trend === "down" && (
                      <>
                        <TrendingDown className="h-4 w-4 text-primary" />
                        <span className="font-mono text-xs text-primary">
                          -{entry.trendPercentage}%
                        </span>
                      </>
                    )}
                    {entry.trend === "stable" && (
                      <>
                        <Minus className="h-4 w-4 text-muted-foreground" />
                        <span className="font-mono text-xs text-muted-foreground">
                          {entry.trendPercentage}%
                        </span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <ScrollArea className="h-full max-h-[calc(100vh-280px)]">
            <div className="space-y-2 px-6 pb-6 pt-2">
              {sectorRankings.length > 0 ? (
                sectorRankings.map((sector) => {
                  const Icon = sector.config.icon;
                  return (
                    <div
                      key={sector.key}
                      className="flex items-center gap-3 p-3 rounded-md bg-muted/30"
                    >
                      <div className="flex items-center justify-center w-8 h-8 flex-shrink-0">
                        {sector.rank === 1 && <Trophy className="h-5 w-5 text-chart-3" />}
                        {sector.rank === 2 && <Medal className="h-5 w-5 text-muted-foreground" />}
                        {sector.rank === 3 && <Award className="h-5 w-5 text-chart-4" />}
                        {sector.rank > 3 && (
                          <span className="font-mono text-sm font-medium text-muted-foreground">
                            #{sector.rank}
                          </span>
                        )}
                      </div>

                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: sector.config.color }}
                      >
                        <Icon className="h-5 w-5 text-white" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">{sector.config.label}</div>
                        <div className="font-mono text-xs text-muted-foreground">
                          {Math.round(sector.value / 1000).toLocaleString()}k tons CO₂e
                        </div>
                      </div>

                      <Badge variant="secondary" className="font-mono">
                        {sector.percentage.toFixed(1)}%
                      </Badge>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  Select an area to view sector breakdown
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
