import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Brain,
  Calendar,
  Database,
  Download,
  Layers,
  Loader2,
  MapPin,
  RotateCcw,
  TrendingUp,
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

const SECTOR_LABELS: Record<Sector, string> = {
  transport: "Transport",
  industry: "Industry",
  energy: "Energy",
  waste: "Waste",
  buildings: "Buildings",
};

function ForecastContent() {
  const [forecastView, setForecastView] = useState<"table" | "graph">("table");
  const [forecastSector, setForecastSector] = useState<string>("all");
  const [forecastArea, setForecastArea] = useState<string>("all");
  const [forecastGroupBy, setForecastGroupBy] = useState<"month" | "year">("month");

  const { data: allForecast = [], isLoading: forecastLoading } = useEmissions(
    { data_type: "forecast" },
  );

  useEffect(() => {
    setForecastArea("all");
  }, [forecastSector]);

  const forecastFiltered = useMemo(() => {
    let data = allForecast.filter((d: EmissionDataPoint) => d.date >= "2026-02-01");
    if (forecastSector !== "all") {
      data = data.filter((d: EmissionDataPoint) => (d as any)[forecastSector] > 0);
      if (forecastArea !== "all") {
        data = data.filter((d: EmissionDataPoint) => d.area_id === forecastArea);
      }
    } else if (forecastArea !== "all") {
      data = data.filter((d: EmissionDataPoint) => d.area_name === forecastArea);
    }
    return data;
  }, [allForecast, forecastSector, forecastArea]);

  const forecastAreaOptions = useMemo(() => {
    let data = allForecast.filter((d: EmissionDataPoint) => d.date >= "2026-02-01");
    if (forecastSector !== "all") {
      data = data.filter((d: EmissionDataPoint) => (d as any)[forecastSector] > 0);
      const unique = new Map<string, string>();
      data.forEach((d: EmissionDataPoint) => unique.set(d.area_id, d.area_name));
      return Array.from(unique.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    }
    const names = new Set<string>();
    data.forEach((d: EmissionDataPoint) => names.add(d.area_name));
    return Array.from(names)
      .map((n) => [n, n] as [string, string])
      .sort((a, b) => a[1].localeCompare(b[1]));
  }, [allForecast, forecastSector]);

  const forecastTable = useMemo(() => {
    const periodKey = (d: EmissionDataPoint) =>
      forecastGroupBy === "month"
        ? new Date(d.date).toLocaleDateString("en-US", { month: "short", year: "numeric" })
        : d.date.slice(0, 4);

    const allPeriodsSet = new Set<string>();
    const areaMap = new Map<string, { id: string; name: string; periods: Map<string, number> }>();

    forecastFiltered.forEach((d: EmissionDataPoint) => {
      const period = periodKey(d);
      allPeriodsSet.add(period);
      const val = forecastSector === "all" ? d.total : ((d as any)[forecastSector] as number || 0);
      const entry = areaMap.get(d.area_id) || { id: d.area_id, name: d.area_name, periods: new Map() };
      entry.periods.set(period, (entry.periods.get(period) || 0) + val);
      areaMap.set(d.area_id, entry);
    });

    const periods = Array.from(allPeriodsSet).sort((a, b) => {
      if (forecastGroupBy === "year") return a.localeCompare(b);
      return new Date(a).getTime() - new Date(b).getTime();
    });

    const areas = Array.from(areaMap.values())
      .map((a) => ({
        ...a,
        total: Array.from(a.periods.values()).reduce((s, v) => s + v, 0),
      }))
      .sort((a, b) => b.total - a.total);

    return { periods, areas };
  }, [forecastFiltered, forecastGroupBy, forecastSector]);

  const forecastChartData = useMemo(() => {
    const periodTotals = new Map<string, number>();
    forecastTable.periods.forEach((p) => periodTotals.set(p, 0));
    forecastTable.areas.forEach((a) => {
      a.periods.forEach((v, p) => periodTotals.set(p, (periodTotals.get(p) || 0) + v));
    });
    const shouldScale = Math.max(...Array.from(periodTotals.values()), 0) > 10000;
    return {
      labels: forecastTable.periods,
      datasets: [
        {
          label: shouldScale ? "Forecast (kt CO₂e)" : "Forecast (t CO₂e)",
          data: forecastTable.periods.map((p) => {
            const v = periodTotals.get(p) || 0;
            return shouldScale ? Math.round(v / 100) / 10 : Math.round(v * 10) / 10;
          }),
          backgroundColor: "hsl(280, 67%, 55%)",
          borderColor: "hsl(280, 67%, 55%)",
          borderWidth: 2,
        },
      ],
    };
  }, [forecastTable]);

  const handleExportForecastCsv = () => {
    if (forecastTable.areas.length === 0) return;
    const header = ["Area", ...forecastTable.periods, "Total"].join(",");
    const rows = [header];
    forecastTable.areas.forEach((a) => {
      const vals = forecastTable.periods.map((p) => (a.periods.get(p) || 0).toFixed(2));
      rows.push([`"${a.name}"`, ...vals, a.total.toFixed(2)].join(","));
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `forecast_${forecastSector}_${forecastArea}_${forecastGroupBy}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full mt-0 overflow-auto bg-muted/30">
      {/* Sticky filter bar */}
      <div className="sticky top-0 z-20 bg-background/80 dark:bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-border/50">
        <div className="px-8 py-4 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-3 mr-4">
            <div className="h-9 w-9 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight leading-tight">ML Forecasting</h1>
              <p className="text-xs text-muted-foreground">Per-area predicted emissions · 2026</p>
            </div>
          </div>

          <div className="h-8 w-px bg-border mx-1 hidden md:block" />

          <div className="flex flex-wrap items-center gap-2 flex-1">
            <Select value={forecastSector} onValueChange={(v) => { setForecastSector(v); setForecastArea("all"); }}>
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

            <Select value={forecastArea} onValueChange={setForecastArea}>
              <SelectTrigger className="w-[220px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                <div className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  <SelectValue placeholder="Area" />
                </div>
              </SelectTrigger>
              <SelectContent className="max-h-[320px]">
                <SelectItem value="all">All Areas ({forecastAreaOptions.length})</SelectItem>
                {forecastAreaOptions.map(([id, name]) => (
                  <SelectItem key={id} value={id}>{name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={forecastGroupBy} onValueChange={(v: any) => setForecastGroupBy(v)}>
              <SelectTrigger className="w-[130px] h-9 bg-white/80 dark:bg-[#0a0a0a]/80">
                <div className="flex items-center gap-2">
                  <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                  <SelectValue />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="month">Monthly</SelectItem>
                <SelectItem value="year">Yearly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <div className="inline-flex items-center rounded-lg border border-border bg-white/80 dark:bg-[#0a0a0a]/80 p-0.5">
              <Button
                variant={forecastView === "table" ? "default" : "ghost"}
                size="sm"
                onClick={() => setForecastView("table")}
                className="h-8 px-3 gap-1.5"
              >
                <Database className="h-3.5 w-3.5" />
                Table
              </Button>
              <Button
                variant={forecastView === "graph" ? "default" : "ghost"}
                size="sm"
                onClick={() => setForecastView("graph")}
                className="h-8 px-3 gap-1.5"
              >
                <BarChart3 className="h-3.5 w-3.5" />
                Graph
              </Button>
            </div>

            {(forecastSector !== "all" || forecastArea !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setForecastSector("all"); setForecastArea("all"); }}
                className="h-9 gap-1.5 text-muted-foreground hover:text-foreground"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportForecastCsv}
              disabled={forecastTable.areas.length === 0}
              className="h-9 gap-1.5"
            >
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      <div className="p-8 space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-purple-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Model</p>
                    <p className="text-base font-bold tracking-tight truncate">XGBoost + Prophet</p>
                    <p className="text-[11px] text-muted-foreground">Per-sector hybrid</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-blue-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Areas Covered</p>
                    <p className="text-xl font-bold tracking-tight">{forecastTable.areas.length}</p>
                    <p className="text-[11px] text-muted-foreground">{forecastSector === "all" ? "All sectors" : SECTOR_LABELS[forecastSector as Sector]}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-emerald-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Total Forecast</p>
                    <p className="text-xl font-bold tracking-tight">
                      {(() => {
                        if (forecastTable.areas.length === 0) return "—";
                        const total = forecastTable.areas.reduce((s, a) => s + a.total, 0);
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

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.15 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-amber-500/10 shadow-lg h-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent pointer-events-none" />
              <CardContent className="pt-6 relative z-10">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Calendar className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground font-medium">Horizon</p>
                    <p className="text-xl font-bold tracking-tight">{forecastTable.periods.length}</p>
                    <p className="text-[11px] text-muted-foreground">{forecastGroupBy === "month" ? "months forecasted" : "years forecasted"}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Loading / empty / data */}
        {forecastLoading ? (
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-lg">
            <CardContent className="py-16 text-center flex flex-col items-center">
              <Loader2 className="h-12 w-12 text-purple-600 dark:text-purple-400 mb-4 animate-spin" />
              <h3 className="text-lg font-semibold mb-1">Loading forecast data…</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                First load can take a few seconds while we pull the full forecast set. Subsequent loads are cached and instant.
              </p>
            </CardContent>
          </Card>
        ) : forecastTable.areas.length === 0 ? (
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-lg">
            <CardContent className="py-16 text-center flex flex-col items-center">
              <motion.div animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}>
                <Brain className="h-16 w-16 text-muted-foreground/30 mb-4" />
              </motion.div>
              <h3 className="text-lg font-semibold mb-1">No forecast data</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                No records match the current filters. Try clearing filters or selecting a different sector / area.
              </p>
            </CardContent>
          </Card>
        ) : forecastView === "graph" ? (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.2 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-2xl overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 pointer-events-none" />
              <CardHeader className="relative z-10">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                  <CardTitle className="text-base">Forecast Emissions by {forecastGroupBy === "month" ? "Month" : "Year"}</CardTitle>
                </div>
                <CardDescription>
                  {forecastArea === "all"
                    ? `Aggregate of ${forecastTable.areas.length} area${forecastTable.areas.length !== 1 ? "s" : ""}`
                    : forecastAreaOptions.find(([id]) => id === forecastArea)?.[1]}
                  {forecastSector !== "all" && ` · ${SECTOR_LABELS[forecastSector as Sector]}`}
                </CardDescription>
              </CardHeader>
              <CardContent className="relative z-10">
                <EmissionChart title="" type="bar" data={forecastChartData} />
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.2 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-2xl overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 pointer-events-none" />
              <CardHeader className="relative z-10">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                  <CardTitle className="text-base">Forecast Emissions Table</CardTitle>
                </div>
                <CardDescription>
                  Per-area predicted emissions by {forecastGroupBy === "month" ? "month" : "year"} (tons CO₂e)
                </CardDescription>
              </CardHeader>
              <CardContent className="relative z-10 p-0">
                <div className="overflow-x-auto max-h-[70vh]">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 sticky top-0 backdrop-blur-md z-10">
                      <tr>
                        <th className="text-left font-semibold px-4 py-3 min-w-[180px]">Area</th>
                        {forecastTable.periods.map((p) => (
                          <th key={p} className="text-right font-semibold px-3 py-3 whitespace-nowrap min-w-[100px]">
                            {p}
                          </th>
                        ))}
                        <th className="text-right font-bold px-4 py-3 whitespace-nowrap border-l min-w-[120px] bg-purple-500/5">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastTable.areas.map((area, i) => (
                        <tr key={area.id} className={`border-t hover:bg-muted/30 ${i % 2 === 0 ? "bg-muted/10" : ""}`}>
                          <td className="px-4 py-2.5 font-medium truncate max-w-[280px]" title={area.name}>{area.name}</td>
                          {forecastTable.periods.map((p) => {
                            const v = area.periods.get(p) || 0;
                            return (
                              <td key={p} className="text-right px-3 py-2.5 tabular-nums text-muted-foreground">
                                {v > 0 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "—"}
                              </td>
                            );
                          })}
                          <td className="text-right px-4 py-2.5 font-bold tabular-nums border-l bg-purple-500/5">
                            {area.total.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-muted/50 sticky bottom-0 backdrop-blur-md">
                      <tr className="border-t-2 font-bold">
                        <td className="px-4 py-3">Total ({forecastTable.areas.length} area{forecastTable.areas.length !== 1 ? "s" : ""})</td>
                        {forecastTable.periods.map((p) => {
                          const total = forecastTable.areas.reduce((s, a) => s + (a.periods.get(p) || 0), 0);
                          return (
                            <td key={p} className="text-right px-3 py-3 tabular-nums">
                              {total.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                            </td>
                          );
                        })}
                        <td className="text-right px-4 py-3 tabular-nums border-l bg-purple-500/10">
                          {forecastTable.areas.reduce((s, a) => s + a.total, 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* How It Works */}
        <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300 }}>
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 to-transparent pointer-events-none" />
            <CardHeader className="relative z-10">
              <CardTitle>How ML Forecasting Works</CardTitle>
              <CardDescription>Understanding our prediction methodology</CardDescription>
            </CardHeader>
            <CardContent className="relative z-10">
              <div className="grid md:grid-cols-3 gap-6">
                <motion.div whileHover={{ scale: 1.05 }} className="flex gap-4 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors">
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 shadow-sm">STEP 1</span>
                    </div>
                    <h3 className="font-semibold mb-1">Data Collection</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">Climate Trace power emissions data (2021-2025) aggregated monthly with interpolation for gaps</p>
                  </div>
                </motion.div>
                <motion.div whileHover={{ scale: 1.05 }} className="flex gap-4 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors">
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 shadow-sm">STEP 2</span>
                    </div>
                    <h3 className="font-semibold mb-1">Model Training</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">Hybrid XGBoost + Prophet for power, Prophet for transport and waste — each sector uses the best-fit model</p>
                  </div>
                </motion.div>
                <motion.div whileHover={{ scale: 1.05 }} className="flex gap-4 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors">
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 shadow-sm">STEP 3</span>
                    </div>
                    <h3 className="font-semibold mb-1">Prediction</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">Generate 12-month forecasts with 95% confidence intervals for proactive planning</p>
                  </div>
                </motion.div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

export default function DashboardForecastPage() {
  return (
    <DashboardLayout>
      <ForecastContent />
    </DashboardLayout>
  );
}
