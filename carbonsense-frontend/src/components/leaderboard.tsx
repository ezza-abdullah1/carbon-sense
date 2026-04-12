import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendingUp, TrendingDown, Minus, Trophy, Medal, Award, Factory, Truck, Zap, Trash2, Building2, ChevronDown } from "lucide-react";
import type { LeaderboardEntry } from "@shared/schema";
import { ScrollArea } from "@/components/ui/scroll-area";
import { motion } from "framer-motion";

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
    <Card className="h-full flex flex-col overflow-hidden bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-0 sm:border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]">
      <CardHeader className="pb-2 flex-shrink-0 relative z-10">
        <CardTitle className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-emerald-800 to-teal-800 dark:from-white dark:via-emerald-200 dark:to-teal-200">Emission Rankings</CardTitle>
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "areas" | "sectors")} className="mt-4">
          <TabsList className="grid w-full grid-cols-2 h-10 p-1 bg-black/5 dark:bg-white/5 rounded-xl backdrop-blur-md">
            <TabsTrigger value="areas" className="text-sm rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-black/40 data-[state=active]:shadow-sm data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 font-medium transition-all duration-300">Areas ({entries.length})</TabsTrigger>
            <TabsTrigger value="sectors" className="text-sm rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-black/40 data-[state=active]:shadow-sm data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 font-medium transition-all duration-300">Sectors</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0 overflow-hidden relative">
        <ScrollArea className="h-full w-full">
          {viewMode === "areas" ? (
            <div className="space-y-1 px-6 pb-12 mt-1">
              {entries.map((entry) => (
                <div
                  key={entry.areaId}
                  onClick={() => onAreaSelect(entry.areaId)}
                  className={`
                    flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-300
                    hover:scale-[1.02] hover:shadow-lg hover:bg-white/60 dark:hover:bg-white/10 border border-transparent
                    ${selectedAreaId === entry.areaId ? 'bg-emerald-500/10 dark:bg-emerald-500/20 shadow-inner !border-emerald-500/30 z-10' : 'bg-transparent'}
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

                  <div className="flex-1 min-w-0 pr-2">
                    <div className="font-medium text-[15px] leading-tight mb-1 text-slate-800 dark:text-slate-200 line-clamp-2" title={entry.areaName}>{entry.areaName}</div>
                    <div className="font-mono text-xs font-semibold text-emerald-600 dark:text-emerald-400 px-2 py-0.5 bg-emerald-500/10 rounded-md inline-block">
                      {entry.emissions.toLocaleString(undefined, { maximumFractionDigits: 0 })} <span className="font-sans font-normal opacity-80 text-[10px]">tons CO₂e</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 shrink-0">
                    {entry.trend === "up" && (
                      <div className="flex items-center bg-destructive/10 px-2 py-1 rounded-full">
                        <TrendingUp className="h-3 w-3 text-destructive mr-1" />
                        <span className="font-mono text-[11px] font-medium text-destructive whitespace-nowrap">
                          +{Number(entry.trendPercentage).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {entry.trend === "down" && (
                      <div className="flex items-center bg-emerald-500/10 px-2 py-1 rounded-full">
                        <TrendingDown className="h-3 w-3 text-emerald-600 dark:text-emerald-400 mr-1" />
                        <span className="font-mono text-[11px] font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                          -{Number(entry.trendPercentage).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {entry.trend === "stable" && (
                      <div className="flex items-center bg-slate-500/10 px-2 py-1 rounded-full">
                        <Minus className="h-3 w-3 text-slate-500 mr-1" />
                        <span className="font-mono text-[11px] font-medium text-slate-500 whitespace-nowrap">
                          {Number(entry.trendPercentage).toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
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

                      <div className="flex-1 min-w-0 pr-2">
                        <div className="font-medium text-[15px] text-slate-800 dark:text-slate-200">{sector.config.label}</div>
                        <div className="font-mono text-xs font-semibold text-emerald-600 dark:text-emerald-400 px-2 py-0.5 bg-emerald-500/10 rounded-md inline-block mt-1">
                          {Math.round(sector.value / 1000).toLocaleString()} <span className="font-sans font-normal opacity-80 text-[10px]">k tons CO₂e</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-center bg-black/5 dark:bg-white/5 rounded-full px-3 py-1 shrink-0 border border-black/10 dark:border-white/10">
                        <span className="font-mono text-xs font-semibold">{sector.percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-muted-foreground text-sm">
                  No data available for the selected period
                </div>
              )}
            </div>
          )}
        </ScrollArea>
        {/* Scroll Indicator Overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white dark:from-[#0a0a0a] to-transparent pointer-events-none z-20 flex items-end justify-center pb-2">
          <motion.div
            animate={{ y: [0, 5, 0] }}
            transition={{ repeat: Infinity, duration: 2 }}
            className="flex flex-col items-center gap-1"
          >
            <span className="text-[10px] uppercase font-bold tracking-widest text-emerald-500/50">Scroll for more</span>
            <ChevronDown className="h-4 w-4 text-emerald-500/50" />
          </motion.div>
        </div>
      </CardContent>
    </Card>
  );
}
