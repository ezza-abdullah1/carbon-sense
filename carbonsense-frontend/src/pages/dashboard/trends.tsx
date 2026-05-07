import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Calendar,
  Download,
  Layers,
  LineChart,
  Loader2,
  MapPin,
  RotateCcw,
  TrendingDown,
  TrendingUp,
  Trophy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmissionChart } from "@/features/emissions/emission-chart";
import { useEmissions } from "@/hooks/use-emissions";
import type { EmissionDataPoint } from "@/lib/api";
import type { Sector } from "@shared/schema";
import { DashboardLayout } from "./layout";

// Sector colours for charts. Historical = blue tones, forecast = orange/amber.
const SECTOR_CONFIG: Record<Sector, { label: string; historical: string }> = {
  transport: { label: "Transport", historical: "hsl(217, 91%, 60%)" },
  industry: { label: "Industry", historical: "hsl(280, 67%, 55%)" },
  energy: { label: "Energy", historical: "hsl(142, 65%, 45%)" },
  waste: { label: "Waste", historical: "hsl(199, 89%, 48%)" },
  buildings: { label: "Buildings", historical: "hsl(262, 83%, 58%)" },
};

function TrendsContent() {
  // Local UI state — these filters only matter on this page.
  const [trendsSector, setTrendsSector] = useState<string>("all");
  const [trendsArea, setTrendsArea] = useState<string>("all");
  const [trendsTopN, setTrendsTopN] = useState<number>(5);
  const [trendsSeasonalYear, setTrendsSeasonalYear] = useState<string>("all");

  // Heavy fetch — fires only when this page is mounted.
  const { data: allHistorical = [], isLoading: historicalLoading } = useEmissions(
    { data_type: "historical" },
  );

  // The dropdown identifier scheme (area_id vs area_name) flips when the
  // sector filter changes, so reset the area selection to keep state valid.
  useEffect(() => {
    setTrendsArea("all");
  }, [trendsSector]);

  // Filter historical data by selected sector & area.
  const trendsFiltered = useMemo(() => {
    let data = allHistorical;
    if (trendsSector !== "all") {
      data = data.filter((d: EmissionDataPoint) => (d as any)[trendsSector] > 0);
      if (trendsArea !== "all") {
        data = data.filter((d: EmissionDataPoint) => d.area_id === trendsArea);
      }
    } else if (trendsArea !== "all") {
      data = data.filter((d: EmissionDataPoint) => d.area_name === trendsArea);
    }
    return data;
  }, [allHistorical, trendsSector, trendsArea]);

  const trendsAreaOptions = useMemo(() => {
    let data = allHistorical;
    if (trendsSector !== "all") {
      data = data.filter((d: EmissionDataPoint) => (d as any)[trendsSector] > 0);
      const unique = new Map<string, string>();
      data.forEach((d: EmissionDataPoint) => unique.set(d.area_id, d.area_name));
      return Array.from(unique.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    }
    const names = new Set<string>();
    data.forEach((d: EmissionDataPoint) => names.add(d.area_name));
    return Array.from(names)
      .map((n) => [n, n] as [string, string])
      .sort((a, b) => a[1].localeCompare(b[1]));
  }, [allHistorical, trendsSector]);

  const trendsTopSourcesData = useMemo(() => {
    const areaMap = new Map<string, { name: string; total: number }>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      const existing = areaMap.get(d.area_id) || { name: d.area_name, total: 0 };
      existing.total += val;
      areaMap.set(d.area_id, existing);
    });
    const sorted = Array.from(areaMap.values()).sort((a, b) => b.total - a.total).slice(0, trendsTopN);
    return {
      labels: sorted.map((s) => s.name),
      datasets: [
        {
          label: "Total Emissions (thousands tons CO₂e)",
          data: sorted.map((s) => Math.round(s.total / 100) / 10),
          backgroundColor: "hsl(142, 60%, 50%)",
        },
      ],
    };
  }, [trendsFiltered, trendsTopN, trendsSector]);

  const trendsYearOptions = useMemo(() => {
    const years = new Set<string>();
    trendsFiltered.forEach((d: EmissionDataPoint) => years.add(d.date.slice(0, 4)));
    return Array.from(years).sort();
  }, [trendsFiltered]);

  const trendsMonthlyData = useMemo(() => {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const sectorsToShow: Sector[] = trendsSector === "all"
      ? ["transport", "industry", "energy", "waste", "buildings"]
      : [trendsSector as Sector];

    const yearFiltered = trendsSeasonalYear === "all"
      ? trendsFiltered
      : trendsFiltered.filter((d) => d.date.startsWith(trendsSeasonalYear));

    const datasets = sectorsToShow.map((sector) => {
      const monthMap = new Map<string, { sum: number; count: number }>();
      yearFiltered.forEach((item: EmissionDataPoint) => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString("en-US", { month: "short" });
        const value = (item as any)[sector] as number;
        if (value > 0) {
          const existing = monthMap.get(label) || { sum: 0, count: 0 };
          monthMap.set(label, { sum: existing.sum + value, count: existing.count + 1 });
        }
      });
      const allValues = Array.from(monthMap.values()).map((v) => v.sum / v.count);
      const maxValue = allValues.length > 0 ? Math.max(...allValues) : 0;
      const shouldScale = maxValue > 10000;
      return {
        label: SECTOR_CONFIG[sector]?.label || sector,
        data: months.map((m) => {
          const entry = monthMap.get(m);
          if (!entry) return 0;
          const avg = entry.sum / entry.count;
          return shouldScale ? Math.round(avg / 100) / 10 : Math.round(avg * 10) / 10;
        }),
        backgroundColor: SECTOR_CONFIG[sector]?.historical || "hsl(142, 60%, 50%)",
      };
    });

    return { labels: months, datasets };
  }, [trendsFiltered, trendsSector, trendsSeasonalYear]);

  const trendsTimelineData = useMemo(() => {
    const monthMap = new Map<string, number>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      if (val > 0) monthMap.set(d.date, (monthMap.get(d.date) || 0) + val);
    });
    const sorted = Array.from(monthMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    const maxVal = sorted.length > 0 ? Math.max(...sorted.map(([_, v]) => v)) : 0;
    const useKt = maxVal >= 10000;
    return {
      labels: sorted.map(([d]) => {
        const dt = new Date(d);
        return dt.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
      }),
      datasets: [
        {
          label: useKt ? "Emissions (kt CO₂e)" : "Emissions (t CO₂e)",
          data: sorted.map(([_, v]) =>
            useKt ? Math.round(v / 100) / 10 : Math.round(v * 10) / 10,
          ),
          backgroundColor: "rgba(16, 185, 129, 0.2)",
          borderColor: "hsl(160, 84%, 39%)",
          borderWidth: 2,
        },
      ],
    };
  }, [trendsFiltered, trendsSector]);

  const trendsYearlyData = useMemo(() => {
    const yearMap = new Map<string, number>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const year = d.date.slice(0, 4);
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      if (val > 0) yearMap.set(year, (yearMap.get(year) || 0) + val);
    });
    const sorted = Array.from(yearMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    const shouldScale = sorted.length > 0 && Math.max(...sorted.map(([_, v]) => v)) > 10000;
    return {
      labels: sorted.map(([y]) => y),
      datasets: [
        {
          label: shouldScale ? "Annual emissions (kt CO₂e)" : "Annual emissions (t CO₂e)",
          data: sorted.map(([_, v]) =>
            shouldScale ? Math.round(v / 100) / 10 : Math.round(v * 10) / 10,
          ),
          backgroundColor: "hsl(217, 91%, 60%)",
        },
      ],
    };
  }, [trendsFiltered, trendsSector]);

  const trendsStats = useMemo(() => {
    if (trendsFiltered.length === 0) {
      return { peakMonth: "—", yoyPct: 0, topEmitter: "—", topEmitterPct: 0, dataSpan: "—", months: 0 };
    }

    const monthAvg = new Map<string, { sum: number; count: number }>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const label = new Date(d.date).toLocaleDateString("en-US", { month: "long" });
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      const entry = monthAvg.get(label) || { sum: 0, count: 0 };
      monthAvg.set(label, { sum: entry.sum + val, count: entry.count + 1 });
    });
    const peakMonthEntry = Array.from(monthAvg.entries())
      .map(([m, v]) => [m, v.sum / v.count] as [string, number])
      .sort((a, b) => b[1] - a[1])[0];
    const peakMonth = peakMonthEntry ? peakMonthEntry[0] : "—";

    const yearTotals = new Map<string, number>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const y = d.date.slice(0, 4);
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      yearTotals.set(y, (yearTotals.get(y) || 0) + val);
    });
    const years = Array.from(yearTotals.keys()).sort();
    let yoyPct = 0;
    if (years.length >= 2) {
      const latest = yearTotals.get(years[years.length - 1]) || 0;
      const prev = yearTotals.get(years[years.length - 2]) || 0;
      yoyPct = prev > 0 ? ((latest - prev) / prev) * 100 : 0;
    }

    const areaMap = new Map<string, { name: string; total: number }>();
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      const val = trendsSector === "all" ? d.total : ((d as any)[trendsSector] as number || 0);
      const existing = areaMap.get(d.area_id) || { name: d.area_name, total: 0 };
      existing.total += val;
      areaMap.set(d.area_id, existing);
    });
    const sortedAreas = Array.from(areaMap.values()).sort((a, b) => b.total - a.total);
    const grandTotal = sortedAreas.reduce((s, a) => s + a.total, 0);
    const topEmitter = sortedAreas[0]?.name || "—";
    const topEmitterPct = grandTotal > 0 && sortedAreas[0] ? (sortedAreas[0].total / grandTotal) * 100 : 0;

    const dates = trendsFiltered.map((d) => d.date).sort();
    const first = dates[0];
    const last = dates[dates.length - 1];
    const fmt = (s: string) => new Date(s).toLocaleDateString("en-US", { month: "short", year: "numeric" });
    const uniqueMonths = new Set(dates).size;
    const dataSpan = first && last ? `${fmt(first)} – ${fmt(last)}` : "—";

    return { peakMonth, yoyPct, topEmitter, topEmitterPct, dataSpan, months: uniqueMonths };
  }, [trendsFiltered, trendsSector]);

  const handleExportCsv = () => {
    if (trendsFiltered.length === 0) return;
    const headers = ["date", "area_name", "area_id", "transport", "industry", "energy", "waste", "buildings", "total"];
    const rows = [headers.join(",")];
    trendsFiltered.forEach((d: EmissionDataPoint) => {
      rows.push([
        d.date, `"${d.area_name}"`, d.area_id,
        d.transport, d.industry, d.energy, d.waste, d.buildings, d.total,
      ].join(","));
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `emissions_${trendsSector}_${trendsArea}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full mt-0 overflow-auto bg-muted/30">
      {/* Sticky filter bar */}
      <div className="sticky top-0 z-20 bg-background/80 dark:bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-border/50">
        <div className="px-8 py-4 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-3 mr-4">
            <div className="h-9 w-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight leading-tight">Historical Trends</h1>
              <p className="text-xs text-muted-foreground">{trendsStats.dataSpan}</p>
            </div>
          </div>

          <div className="h-8 w-px bg-border mx-1 hidden md:block" />

          <div className="flex flex-wrap items-center gap-2 flex-1">
            <Select value={trendsSector} onValueChange={(v) => { setTrendsSector(v); setTrendsArea("all"); }}>
              <SelectTrigger className="w-[170px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                <div className="flex items-center gap-2">
                  <Layers className="h-3.5 w-3.5 text-muted-foreground" />
                  <SelectValue placeholder="Sector" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sectors</SelectItem>
                <SelectItem value="transport">Transport</SelectItem>
                <SelectItem value="industry">Industry</SelectItem>
                <SelectItem value="energy">Energy</SelectItem>
                <SelectItem value="waste">Waste</SelectItem>
                <SelectItem value="buildings">Buildings</SelectItem>
              </SelectContent>
            </Select>

            <Select value={trendsArea} onValueChange={setTrendsArea}>
              <SelectTrigger className="w-[220px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                <div className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  <SelectValue placeholder="Area" />
                </div>
              </SelectTrigger>
              <SelectContent className="max-h-[320px]">
                <SelectItem value="all">All Areas ({trendsAreaOptions.length})</SelectItem>
                {trendsAreaOptions.map(([id, name]) => (
                  <SelectItem key={id} value={id}>{name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            {(trendsSector !== "all" || trendsArea !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setTrendsSector("all"); setTrendsArea("all"); }}
                className="h-9 gap-1.5 text-muted-foreground hover:text-foreground"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCsv}
              disabled={trendsFiltered.length === 0}
              className="h-9 gap-1.5"
            >
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      <div className="p-8 space-y-6">
        {/* Key Stats — 4 meaningful cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-emerald-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3 mb-2">
                  <div className="h-10 w-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Total Emissions</p>
                    <p className="text-xl font-bold tracking-tight truncate">
                      {(() => {
                        if (trendsFiltered.length === 0) return "—";
                        const total = trendsFiltered.reduce((sum: number, d: EmissionDataPoint) => sum + (trendsSector === "all" ? d.total : (d as any)[trendsSector] || 0), 0);
                        if (total >= 1_000_000) return `${(total / 1_000_000).toFixed(2)}M`;
                        if (total >= 1_000) return `${(total / 1_000).toFixed(1)}K`;
                        return total.toLocaleString("en-US", { maximumFractionDigits: 0 });
                      })()}
                    </p>
                    <p className="text-[11px] text-muted-foreground">tons CO₂e</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-purple-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3 mb-2">
                  <div className="h-10 w-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Calendar className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Peak Month</p>
                    <p className="text-xl font-bold tracking-tight truncate">{trendsStats.peakMonth}</p>
                    <p className="text-[11px] text-muted-foreground">highest avg emissions</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}>
            <Card className={`bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-lg h-full relative overflow-hidden ${trendsStats.yoyPct >= 0 ? "border-rose-500/10" : "border-emerald-500/10"}`}>
              <div className={`absolute inset-0 bg-gradient-to-br ${trendsStats.yoyPct >= 0 ? "from-rose-500/10" : "from-emerald-500/10"} to-transparent pointer-events-none`} />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3 mb-2">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${trendsStats.yoyPct >= 0 ? "bg-rose-500/20" : "bg-emerald-500/20"}`}>
                    {trendsStats.yoyPct >= 0 ? (
                      <TrendingUp className="h-5 w-5 text-rose-600 dark:text-rose-400" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Year-over-Year</p>
                    <p className={`text-xl font-bold tracking-tight ${trendsStats.yoyPct >= 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                      {trendsStats.yoyPct >= 0 ? "+" : ""}{trendsStats.yoyPct.toFixed(1)}%
                    </p>
                    <p className="text-[11px] text-muted-foreground">latest vs previous year</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.15 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-amber-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3 mb-2">
                  <div className="h-10 w-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Trophy className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Top Emitter</p>
                    <p className="text-base font-bold tracking-tight truncate" title={trendsStats.topEmitter}>{trendsStats.topEmitter}</p>
                    <p className="text-[11px] text-muted-foreground">{trendsStats.topEmitterPct.toFixed(1)}% of total</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Loading / empty state */}
        {historicalLoading ? (
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-lg">
            <CardContent className="py-16 text-center flex flex-col items-center">
              <Loader2 className="h-12 w-12 text-emerald-600 dark:text-emerald-400 mb-4 animate-spin" />
              <h3 className="text-lg font-semibold mb-1">Loading historical data…</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                First load can take a few seconds while we pull every emission point. Subsequent loads are cached and instant.
              </p>
            </CardContent>
          </Card>
        ) : trendsFiltered.length === 0 ? (
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-lg">
            <CardContent className="py-16 text-center flex flex-col items-center">
              <motion.div animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}>
                <BarChart3 className="h-16 w-16 text-muted-foreground/30 mb-4" />
              </motion.div>
              <h3 className="text-lg font-semibold mb-1">No historical data</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                No records match the current filters. Try clearing filters or selecting a different sector / area.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setTrendsSector("all"); setTrendsArea("all"); }}
                className="mt-4 gap-1.5"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset filters
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Emission Timeline — full-width hero chart */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.2 }}>
              <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-2xl overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-teal-500/5 pointer-events-none" />
                <CardHeader className="relative z-10">
                  <div className="flex items-center gap-2">
                    <LineChart className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <CardTitle className="text-base">Emission Timeline</CardTitle>
                  </div>
                  <CardDescription>
                    {trendsStats.months} months of data
                    {trendsSector !== "all" && ` · ${SECTOR_CONFIG[trendsSector as Sector]?.label}`}
                    {trendsArea !== "all" && ` · ${trendsAreaOptions.find(([id]) => id === trendsArea)?.[1]}`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="relative z-10">
                  <EmissionChart title="" type="line" data={trendsTimelineData} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Two-column grid: Yearly comparison + Seasonal pattern */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.25 }}>
                <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-xl overflow-hidden relative h-full">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-indigo-500/5 pointer-events-none" />
                  <CardHeader className="relative z-10">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      <CardTitle className="text-base">Yearly Comparison</CardTitle>
                    </div>
                    <CardDescription>Total emissions per year</CardDescription>
                  </CardHeader>
                  <CardContent className="relative z-10">
                    <EmissionChart title="" type="bar" data={trendsYearlyData} />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.3 }}>
                <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-xl overflow-hidden relative h-full">
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 pointer-events-none" />
                  <CardHeader className="relative z-10 flex flex-row items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                        <CardTitle className="text-base">Seasonal Patterns</CardTitle>
                      </div>
                      <CardDescription>
                        {trendsSeasonalYear === "all"
                          ? `Average by month (${trendsYearOptions[0] || ""}–${trendsYearOptions[trendsYearOptions.length - 1] || ""})`
                          : `Monthly emissions for ${trendsSeasonalYear}`}
                      </CardDescription>
                    </div>
                    <Select value={trendsSeasonalYear} onValueChange={setTrendsSeasonalYear}>
                      <SelectTrigger className="w-[130px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                        <SelectValue placeholder="Year" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All years avg</SelectItem>
                        {trendsYearOptions.map((y) => (
                          <SelectItem key={y} value={y}>{y}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </CardHeader>
                  <CardContent className="relative z-10">
                    <EmissionChart title="" type="bar" data={trendsMonthlyData} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Top Emission Sources — hidden when specific area selected */}
            {trendsArea === "all" && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.35 }}>
                <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-xl overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-orange-500/5 pointer-events-none" />
                  <CardHeader className="relative z-10 flex flex-row items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Trophy className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        <CardTitle className="text-base">Top Emission Sources</CardTitle>
                      </div>
                      <CardDescription>
                        Highest emitters by total historical emissions
                        {trendsSector !== "all" && ` in ${SECTOR_CONFIG[trendsSector as Sector]?.label}`}
                      </CardDescription>
                    </div>
                    <Select value={String(trendsTopN)} onValueChange={(v) => setTrendsTopN(Number(v))}>
                      <SelectTrigger className="w-[110px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                        <SelectValue placeholder="Top N" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="5">Top 5</SelectItem>
                        <SelectItem value="7">Top 7</SelectItem>
                        <SelectItem value="10">Top 10</SelectItem>
                        <SelectItem value="15">Top 15</SelectItem>
                      </SelectContent>
                    </Select>
                  </CardHeader>
                  <CardContent className="relative z-10">
                    <EmissionChart title="" type="bar" data={trendsTopSourcesData} />
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function DashboardTrendsPage() {
  return (
    <DashboardLayout>
      <TrendsContent />
    </DashboardLayout>
  );
}
