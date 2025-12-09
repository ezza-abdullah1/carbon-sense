import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, Trophy, Medal, Award } from "lucide-react";
import type { LeaderboardEntry } from "@shared/schema";
import { ScrollArea } from "@/components/ui/scroll-area";

interface LeaderboardProps {
  entries: LeaderboardEntry[];
  selectedAreaId: string | null;
  onAreaSelect: (areaId: string) => void;
  sortBy?: "total" | "sector";
}

export function Leaderboard({ entries, selectedAreaId, onAreaSelect }: LeaderboardProps) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg">Emission Rankings</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full">
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
                    {entry.emissions.toFixed(2)} tons CO₂e
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
      </CardContent>
    </Card>
  );
}
