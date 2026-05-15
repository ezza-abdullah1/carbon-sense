import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { X } from "lucide-react";
import type { PointSource } from "@/lib/api";
import type { Sector } from "@shared/schema";
import { formatTonnes } from "@/lib/map-utils";

// Same visual treatment as risk flags on the UC panel.
const FUEL_COLORS: Record<string, string> = {
  gas: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  other_fossil:
    "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  coal: "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
  oil: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  nuclear: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  hydro: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
  solar: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  wind: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
};

// Header gradient + accent colours per sector — keeps the panel visually
// tied to whichever marker the user clicked on.
const SECTOR_THEME: Record<Sector, { title: string; accent: string; bar: string; label: string }> = {
  energy: {
    title: "from-amber-600 to-orange-500 dark:from-amber-400 dark:to-orange-300",
    accent: "via-amber-500/5",
    bar: "hsl(45, 93%, 47%)",
    label: "Energy facility",
  },
  industry: {
    title: "from-violet-600 to-purple-500 dark:from-violet-400 dark:to-purple-300",
    accent: "via-violet-500/5",
    bar: "hsl(280, 67%, 55%)",
    label: "Industrial facility",
  },
  waste: {
    // Teal — matches the new waste pin and sector-filter colour.
    title: "from-teal-600 to-cyan-500 dark:from-teal-400 dark:to-cyan-300",
    accent: "via-teal-500/5",
    bar: "hsl(180, 65%, 45%)",
    label: "Waste facility",
  },
  transport: {
    title: "from-blue-600 to-indigo-500 dark:from-blue-400 dark:to-indigo-300",
    accent: "via-blue-500/5",
    bar: "hsl(217, 91%, 60%)",
    label: "Transport facility",
  },
  buildings: {
    title: "from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300",
    accent: "via-emerald-500/5",
    bar: "hsl(160, 84%, 39%)",
    label: "Buildings facility",
  },
};

interface PointSourceDetailPanelProps {
  plant: PointSource;
  onClose: () => void;
}

export function PointSourceDetailPanel({ plant, onClose }: PointSourceDetailPanelProps) {
  const theme = SECTOR_THEME[plant.sector] ?? SECTOR_THEME.energy;
  const summary = plant.summary;
  const trend = summary?.trend ?? "stable";
  const trendColor =
    trend === "increasing"
      ? "text-rose-600 dark:text-rose-400"
      : trend === "declining"
        ? "text-emerald-600 dark:text-emerald-400"
        : "text-slate-500";

  // Facility/fuel type may come as a comma- or pipe-separated string. Some
  // industry "type" fields are very long; cap to keep the panel tidy.
  const tags = plant.type
    ? plant.type
        .split(/[,|]/)
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 4)
    : [];

  const generationBars = summary
    ? [
        {
          label: "Historical total",
          value: summary.total_historical_tonnes,
          color: theme.bar,
        },
        {
          label: "12-month forecast",
          value: summary.forecast_12m_total,
          color: "hsl(217, 91%, 60%)",
        },
      ].filter((s) => s.value > 0)
    : [];
  const maxGen = Math.max(...generationBars.map((s) => s.value), 1);

  return (
    <Card className="w-full h-full min-h-0 flex flex-col bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-tr from-transparent ${theme.accent} to-transparent pointer-events-none`} />

      <CardHeader className="flex-row items-start justify-between space-y-0 px-5 pt-5 pb-3 relative z-10 border-b border-white/10 shrink-0">
        <div className="space-y-0.5 min-w-0">
          <CardTitle
            className={`text-lg bg-clip-text text-transparent bg-gradient-to-r ${theme.title} truncate`}
            title={plant.source}
          >
            {plant.source}
          </CardTitle>
          <p className="text-xs text-muted-foreground font-mono">
            {plant.lat.toFixed(4)}, {plant.lng.toFixed(4)} · {theme.label}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-5 w-5 opacity-70 hover:opacity-100" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 min-h-0 space-y-5 pt-4 px-5 overflow-y-auto overscroll-contain pb-5">
        <div className="rounded-lg border border-border/50 overflow-hidden">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-border/30">
              <StatsRow
                label="Annual CO₂e"
                value={<b>{formatTonnes(plant.emissions)}</b>}
              />
              {summary && summary.last_historical_emissions > 0 && (
                <StatsRow
                  label="Last month"
                  value={<b>{formatTonnes(summary.last_historical_emissions)}</b>}
                />
              )}
              {summary && summary.last_historical_date && (
                <StatsRow label="As of" value={summary.last_historical_date} />
              )}
              {summary && summary.total_historical_tonnes > 0 && (
                <StatsRow
                  label="Historical total"
                  value={formatTonnes(summary.total_historical_tonnes)}
                />
              )}
              {summary && summary.forecast_12m_total > 0 && (
                <StatsRow
                  label="Forecast 12m"
                  value={formatTonnes(summary.forecast_12m_total)}
                />
              )}
              {summary && (
                <StatsRow
                  label="Year-over-year"
                  value={
                    <span className={`font-mono ${trendColor}`}>
                      {summary.change_pct >= 0 ? "+" : ""}
                      {summary.change_pct.toFixed(2)}%
                    </span>
                  }
                />
              )}
            </tbody>
          </table>
        </div>

        {(tags.length > 0 || summary) && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Flags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className={`text-[10px] font-medium px-2 py-0.5 ${FUEL_COLORS[tag.toLowerCase()] ?? ""}`}
                >
                  {tag.replace(/_/g, " ")}
                </Badge>
              ))}
              {summary && (
                <Badge
                  variant="secondary"
                  className={`text-[10px] font-medium px-2 py-0.5 ${
                    trend === "increasing"
                      ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
                      : trend === "declining"
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                        : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                  }`}
                >
                  {trend}
                </Badge>
              )}
            </div>
          </div>
        )}

        {generationBars.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Generation Profile
            </h3>
            <div className="space-y-2.5">
              {generationBars.map((bar) => (
                <div key={bar.label} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{bar.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTonnes(bar.value)}
                    </span>
                  </div>
                  <Progress
                    value={(bar.value / maxGen) * 100}
                    className="h-2"
                    style={{ "--progress-background": bar.color } as React.CSSProperties}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-[10px] text-muted-foreground italic px-1 pt-1">
          Point-source emissions from a specific facility. Not allocated to any Union Council.
        </p>
      </CardContent>
    </Card>
  );
}

function StatsRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td className="py-1.5 px-3 text-muted-foreground whitespace-nowrap">{label}</td>
      <td className="py-1.5 px-3 text-right font-mono">{value}</td>
    </tr>
  );
}
