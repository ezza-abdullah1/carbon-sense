import { useMemo } from "react";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Brain,
  Database,
  Download,
  Layers,
  Leaf,
  Loader2,
  MapPin,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmissionChart } from "@/features/emissions/emission-chart";
import type { LeaderboardEntry } from "@shared/schema";
import { DashboardLayout, useDashboard } from "./layout";

// Smart number formatter shared across pages.
function formatEmissions(v: number): string {
  if (v === 0) return "0";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 1) return "Just now";
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) return `${diffMonths}mo ago`;
  const diffYears = Math.floor(diffMonths / 12);
  return `${diffYears}y ago`;
}

const FEATURE_CARDS = [
  {
    href: "/dashboard/map",
    title: "Interactive Map",
    description: "Color-coded emission hotspots across Lahore",
    icon: MapPin,
    bgClass: "bg-emerald-500/10",
    textClass: "text-emerald-600 dark:text-emerald-400",
  },
  {
    href: "/dashboard/trends",
    title: "Trend Analysis",
    description: "Historical patterns and time-series visualization",
    icon: TrendingUp,
    bgClass: "bg-blue-500/10",
    textClass: "text-blue-600 dark:text-blue-400",
  },
  {
    href: "/dashboard/forecast",
    title: "ML Forecasting",
    description: "AI-powered predictions for proactive planning",
    icon: Brain,
    bgClass: "bg-purple-500/10",
    textClass: "text-purple-600 dark:text-purple-400",
  },
  {
    href: "/dashboard/data",
    title: "Data Export",
    description: "Download and analyze raw emission data",
    icon: Download,
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-600 dark:text-amber-400",
  },
];

function OverviewContent() {
  const [, setLocation] = useLocation();
  const { areas, areasLoading, stats, leaderboard, leaderboardLoading } = useDashboard();

  // Aggregate stats served by /api/stats/ (one tiny call on layout mount).
  const overviewStats = useMemo(() => {
    if (!stats) {
      return {
        sectorsCount: 0,
        yearsOfData: 0,
        totalHistorical: 0,
        totalForecast: 0,
        historicalRecords: 0,
        forecastRecords: 0,
        latestDate: null as string | null,
        earliestDate: null as string | null,
      };
    }
    return {
      sectorsCount: stats.sectors_tracked,
      yearsOfData: stats.years_of_data,
      totalHistorical: stats.historical.total_emissions,
      totalForecast: stats.forecast.total_emissions,
      historicalRecords: 0,
      forecastRecords: 0,
      latestDate: null,
      earliestDate: null,
    };
  }, [stats]);

  // Sector totals come straight from /api/stats/.
  const sectorTotals = useMemo(
    () =>
      stats?.sector_totals ?? {
        transport: 0,
        industry: 0,
        energy: 0,
        waste: 0,
        buildings: 0,
      },
    [stats],
  );

  const sectorPieData = useMemo(() => {
    const values = Object.values(sectorTotals);
    const hasData = values.some((v) => v > 0);
    if (!hasData) {
      return {
        labels: ["Energy"],
        datasets: [
          {
            label: "Emissions by Sector",
            data: [100],
            backgroundColor: ["hsl(45, 93%, 47%)"],
          },
        ],
      };
    }
    return {
      labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
      datasets: [
        {
          label: "Emissions by Sector",
          data: Object.values(sectorTotals).map((v) => Math.round(v / 100) / 10),
          backgroundColor: [
            "hsl(217, 91%, 60%)",
            "hsl(280, 67%, 55%)",
            "hsl(45, 93%, 47%)",
            "hsl(25, 95%, 53%)",
            "hsl(338, 78%, 56%)",
          ],
        },
      ],
    };
  }, [sectorTotals]);

  const areaBarData = useMemo(() => {
    const topAreas = (leaderboard.slice(0, 5) ?? []) as LeaderboardEntry[];
    return {
      labels: topAreas.map((e) => e.areaName),
      datasets: [
        {
          label: "Total Emissions (thousands tons CO₂e)",
          data: topAreas.map((e) => Math.round(e.emissions / 100) / 10),
          backgroundColor: "hsl(142, 60%, 50%)",
        },
      ],
    };
  }, [leaderboard]);

  // Hold the page on a full-screen loader until the critical APIs resolve.
  // Placed after all hooks to keep call order stable across renders.
  const initialLoading = areasLoading || !stats || leaderboardLoading;
  if (initialLoading) {
    return (
      <div className="h-full mt-0 overflow-auto">
        <div className="min-h-full bg-[#fafafa] dark:bg-[#030303] text-slate-900 dark:text-slate-50 relative overflow-hidden flex items-center justify-center">
          <div className="absolute inset-0 pointer-events-none z-0">
            <motion.div
              animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="absolute top-[20%] left-[20%] w-[40vw] h-[40vw] bg-emerald-400/10 dark:bg-emerald-600/10 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] opacity-100"
            />
          </div>
          <div className="relative z-10 flex flex-col items-center gap-4 px-6 text-center">
            <Loader2 className="h-12 w-12 text-emerald-600 dark:text-emerald-400 animate-spin" />
            <h2 className="text-lg font-semibold">Loading dashboard…</h2>
            <p className="text-sm text-muted-foreground max-w-sm">
              Pulling the latest emission records and stats. First load can take a few seconds; subsequent loads are cached and instant.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full mt-0 overflow-auto">
      <div className="min-h-full bg-[#fafafa] dark:bg-[#030303] text-slate-900 dark:text-slate-50 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none z-0">
          <motion.div
            animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute top-[0%] left-[20%] w-[40vw] h-[40vw] bg-emerald-400/10 dark:bg-emerald-600/10 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] opacity-100"
          />
        </div>

        {/* Hero Section */}
        <div className="relative overflow-hidden z-10 mt-6 mx-8 mb-8 rounded-3xl bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 shadow-xl backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-transparent to-teal-500/5 pointer-events-none" />
          <div className="relative px-10 py-12 flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="max-w-xl">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/60 dark:bg-black/40 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-bold uppercase tracking-widest mb-6 shadow-sm">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Live Environmental Core
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-emerald-800 to-teal-800 dark:from-white dark:via-emerald-200 dark:to-teal-200">
                Welcome to CarbonSense.
              </h1>
              <p className="text-base text-slate-600 dark:text-slate-400 max-w-lg mb-8 leading-relaxed">
                Monitor, analyze, and accurately forecast carbon emissions across Lahore. Instantly empower your sustainability initiatives with data-driven precision.
              </p>
              <div className="flex items-center gap-4">
                <Button onClick={() => setLocation("/dashboard/map")} className="rounded-full px-6 bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-500/20">
                  <MapPin className="h-4 w-4 mr-2" /> Explore Live Map
                </Button>
                <Button variant="outline" onClick={() => setLocation("/dashboard/trends")} className="rounded-full px-6 bg-white/50 dark:bg-black/50 backdrop-blur-md">
                  <TrendingUp className="h-4 w-4 mr-2" /> View Trends
                </Button>
              </div>
            </div>
            <div className="hidden md:flex relative h-48 w-48 items-center justify-center">
              <div className="absolute inset-0 bg-emerald-500/20 rounded-full blur-[60px] animate-pulse" />
              <svg viewBox="0 0 200 200" className="w-full h-full relative z-10 animate-[spin_40s_linear_infinite] opacity-80 mix-blend-overlay">
                <path fill="currentColor" className="text-emerald-500" d="M42.7,-68.8C55.9,-61.7,67.6,-51.2,76.5,-38.5C85.4,-25.9,91.6,-11.1,89.6,2.8C87.6,16.7,77.5,29.7,66.8,40.8C56.1,51.8,44.9,60.8,31.7,68.6C18.5,76.3,3.3,82.8,-11.8,81.1C-26.9,79.4,-41.8,69.5,-55.1,58.8C-68.4,48.1,-80,36.6,-86.3,22.2C-92.6,7.8,-93.6,-9.4,-87.3,-23.7C-81,-38,-67.4,-49.4,-53.4,-57.2C-39.4,-65,-25,-69.1,-10.8,-71.4C3.4,-73.7,17.7,-74.3,29.8,-70.6C41.9,-66.9,51.8,-58.9,42.7,-68.8Z" transform="translate(100 100) scale(0.9)" />
              </svg>
              <Leaf className="absolute h-14 w-14 text-white drop-shadow-[0_0_15px_rgba(16,185,129,0.8)] z-20" />
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="px-8 -mt-4">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, staggerChildren: 0.1 }} className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
              <Card className="relative overflow-hidden bg-white/50 dark:bg-black/40 backdrop-blur-xl border border-emerald-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(16,185,129,0.05)] group">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="pt-6 relative z-10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Sources</p>
                      <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300">{areas.length}</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 flex items-center justify-center border border-emerald-500/20 shadow-inner">
                      <MapPin className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
              <Card className="relative overflow-hidden bg-white/50 dark:bg-black/40 backdrop-blur-xl border border-blue-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(59,130,246,0.05)] group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="pt-6 relative z-10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Sectors Tracked</p>
                      <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-500 dark:from-blue-400 dark:to-indigo-300">{overviewStats.sectorsCount}</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 flex items-center justify-center border border-blue-500/20 shadow-inner">
                      <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
              <Card className="relative overflow-hidden bg-white/50 dark:bg-black/40 backdrop-blur-xl border border-purple-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(168,85,247,0.05)] group">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="pt-6 relative z-10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Years of Data</p>
                      <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-pink-500 dark:from-purple-400 dark:to-pink-300">{overviewStats.yearsOfData || "—"}</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/10 flex items-center justify-center border border-purple-500/20 shadow-inner">
                      <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
              <Card className="relative overflow-hidden bg-white/50 dark:bg-black/40 backdrop-blur-xl border border-amber-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(245,158,11,0.05)] group">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="pt-6 relative z-10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Emissions</p>
                      <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-600 to-orange-500 dark:from-amber-400 dark:to-orange-300 flex items-baseline gap-1">
                        {overviewStats.totalHistorical > 0 ? formatEmissions(overviewStats.totalHistorical) : "—"}
                        <span className="text-xs font-normal text-slate-400 dark:text-slate-500">CO₂e tons</span>
                      </p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/10 flex items-center justify-center border border-amber-500/20 shadow-inner">
                      <Activity className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        </div>

        {/* Main Dashboard Grid */}
        <div className="px-8 pb-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
                <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden relative group">
                  <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative z-10 pb-0 flex flex-row items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-emerald-500" />
                        Top Emission Sources
                      </CardTitle>
                      <CardDescription className="mt-1">Highest producing areas</CardDescription>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setLocation("/dashboard/trends")} className="text-xs">
                      View Full Analytics <ArrowRight className="h-3 w-3 ml-1" />
                    </Button>
                  </CardHeader>
                  <CardContent className="relative z-10 pt-4">
                    <EmissionChart title="" type="bar" data={areaBarData} />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1 }} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden relative group">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative z-10 pb-0">
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-blue-500" />
                      Overview by Sector
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="relative z-10 pt-4 max-w-full">
                    <EmissionChart title="" type="doughnut" data={sectorPieData} />
                  </CardContent>
                </Card>

                <Card
                  className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-emerald-500/30 shadow-[0_8px_30px_rgb(16,185,129,0.1)] overflow-hidden relative group cursor-pointer hover:border-emerald-500/50 transition-all duration-300"
                  onClick={() => setLocation("/dashboard/map")}
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent z-0" />
                  <CardContent className="relative z-10 h-full flex flex-col items-center justify-center text-center p-8">
                    <div className="h-20 w-20 rounded-full bg-emerald-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500 shadow-[0_0_20px_rgba(16,185,129,0.3)]">
                      <MapPin className="h-10 w-10 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Live Map View</h3>
                    <p className="text-sm text-muted-foreground mb-6">
                      Interact with spatial data to explore emission hotspots in Lahore.
                    </p>
                    <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-medium bg-emerald-500/10 px-4 py-2 rounded-full group-hover:bg-emerald-500/20 transition-colors">
                      Explore Map <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
                  <CardHeader className="pb-3 border-b border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02]">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                      <Sparkles className="h-4 w-4 text-emerald-500" /> Platform Quick Links
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="flex flex-col divide-y divide-black/5 dark:divide-white/5">
                      {FEATURE_CARDS.map((feature, i) => {
                        const Icon = feature.icon;
                        return (
                          <motion.div key={feature.href} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1, duration: 0.5 }}>
                            <button
                              className="w-full flex items-center gap-4 p-4 text-left transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02] group"
                              onClick={() => setLocation(feature.href)}
                            >
                              <div className={`h-10 w-10 rounded-xl flex-shrink-0 ${feature.bgClass} flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-300`}>
                                <Icon className={`h-5 w-5 ${feature.textClass}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-sm mb-0.5 text-slate-800 dark:text-slate-200">{feature.title}</h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{feature.description}</p>
                              </div>
                              <ArrowRight className={`h-4 w-4 ${feature.textClass} opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all duration-300`} />
                            </button>
                          </motion.div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.4 }}>
                <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
                  <CardHeader className="pb-3 border-b border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02]">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                      <Layers className="h-4 w-4 text-blue-500" /> Monitored Sectors
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-5 md:p-6">
                    <div className="flex flex-wrap gap-3 md:gap-4">
                      {[
                        { label: "Transport", color: "bg-indigo-500", shadow: "shadow-indigo-500/50" },
                        { label: "Industry", color: "bg-rose-500", shadow: "shadow-rose-500/50" },
                        { label: "Energy", color: "bg-amber-500", shadow: "shadow-amber-500/50" },
                        { label: "Waste", color: "bg-orange-500", shadow: "shadow-orange-500/50" },
                        { label: "Buildings", color: "bg-emerald-500", shadow: "shadow-emerald-500/50" },
                      ].map((sector) => (
                        <div
                          key={sector.label}
                          className="flex items-center gap-2.5 px-4 py-2 rounded-lg bg-black/[0.03] dark:bg-white/[0.03] border border-black/5 dark:border-white/5 text-sm font-medium hover:bg-black/[0.05] dark:hover:bg-white/[0.05] transition-colors cursor-default"
                        >
                          <span className={`h-2.5 w-2.5 rounded-full ${sector.color} ${sector.shadow} shadow-sm`} />
                          <span className="text-slate-700 dark:text-slate-300">{sector.label}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.5 }}>
                <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="pb-3 flex flex-row items-center justify-between relative z-10">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                      <Activity className="h-4 w-4 text-indigo-500" /> Data Summary
                    </CardTitle>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                  </CardHeader>
                  <CardContent className="relative z-10 p-5 md:p-6 pt-2">
                    <div className="space-y-6 md:space-y-7">
                      {[
                        {
                          title: "Historical Records",
                          desc: overviewStats.earliestDate && overviewStats.latestDate
                            ? `${new Date(overviewStats.earliestDate).toLocaleDateString("en-US", { month: "short", year: "numeric" })} – ${new Date(overviewStats.latestDate).toLocaleDateString("en-US", { month: "short", year: "numeric" })}`
                            : "Building dataset…",
                          value: overviewStats.historicalRecords.toLocaleString(),
                          icon: Database,
                          color: "text-blue-500",
                          bg: "bg-blue-500/10",
                        },
                        {
                          title: "Forecast Records",
                          desc: `${overviewStats.sectorsCount} sector${overviewStats.sectorsCount !== 1 ? "s" : ""} modeled`,
                          value: overviewStats.forecastRecords.toLocaleString(),
                          icon: Brain,
                          color: "text-purple-500",
                          bg: "bg-purple-500/10",
                        },
                        {
                          title: "Total Forecast",
                          desc: "Projected CO₂e emissions",
                          value: overviewStats.totalForecast > 0 ? `${formatEmissions(overviewStats.totalForecast)} t` : "—",
                          icon: TrendingUp,
                          color: "text-emerald-500",
                          bg: "bg-emerald-500/10",
                        },
                        {
                          title: "Latest Data",
                          desc: overviewStats.latestDate
                            ? new Date(overviewStats.latestDate).toLocaleDateString("en-US", { month: "long", year: "numeric" })
                            : "Syncing…",
                          value: timeAgo(overviewStats.latestDate),
                          icon: Zap,
                          color: "text-amber-500",
                          bg: "bg-amber-500/10",
                        },
                      ].map((update, idx) => (
                        <div key={idx} className="flex gap-4 group/item items-start">
                          <div className={`flex-shrink-0 h-10 w-10 rounded-full ${update.bg} flex items-center justify-center mt-0.5 group-hover/item:scale-110 transition-transform`}>
                            <update.icon className={`h-5 w-5 ${update.color}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-center mb-1">
                              <h4 className="text-[15px] font-semibold text-slate-800 dark:text-slate-200 truncate">{update.title}</h4>
                              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 whitespace-nowrap ml-2 flex-shrink-0 tabular-nums">{update.value}</span>
                            </div>
                            <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{update.desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardOverviewPage() {
  return (
    <DashboardLayout>
      <OverviewContent />
    </DashboardLayout>
  );
}
