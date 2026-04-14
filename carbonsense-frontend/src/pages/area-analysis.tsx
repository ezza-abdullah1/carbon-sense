import { useMemo } from "react";
import { useLocation, useParams } from "wouter";
import { EmissionChart } from "@/components/emission-chart";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Leaf, ArrowLeft, TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { useAreas, useCombinedTimeSeriesData } from "@/hooks/use-emissions";
import { motion } from "framer-motion";

export default function AreaAnalysis() {
  const [, setLocation] = useLocation();
  const params = useParams<{ areaId: string }>();
  const areaId = params.areaId;

  // Fetch data
  const { data: areas = [], isLoading: areasLoading } = useAreas();
  const { data: combinedData, isLoading: dataLoading } = useCombinedTimeSeriesData(areaId);

  const area = areas.find(a => a.id === areaId);

  // Calculate stats from data
  const stats = useMemo(() => {
    if (!combinedData) return null;

    const { historical, forecast } = combinedData;

    // Total historical emissions
    const totalHistorical = historical.reduce((sum, d) => sum + d.total, 0);
    const totalForecast = forecast.reduce((sum, d) => sum + d.total, 0);

    // Average emissions
    const avgHistorical = historical.length > 0 ? totalHistorical / historical.length : 0;
    const avgForecast = forecast.length > 0 ? totalForecast / forecast.length : 0;

    // Trend calculation (compare forecast avg to historical avg)
    const trendPercentage = avgHistorical > 0
      ? ((avgForecast - avgHistorical) / avgHistorical) * 100
      : 0;

    // Sector breakdown (sum of all historical data)
    const sectorTotals = {
      transport: historical.reduce((sum, d) => sum + d.transport, 0),
      industry: historical.reduce((sum, d) => sum + d.industry, 0),
      energy: historical.reduce((sum, d) => sum + d.energy, 0),
      waste: historical.reduce((sum, d) => sum + d.waste, 0),
      buildings: historical.reduce((sum, d) => sum + d.buildings, 0),
    };

    return {
      totalHistorical,
      totalForecast,
      avgHistorical,
      avgForecast,
      trendPercentage,
      sectorTotals,
      historicalCount: historical.length,
      forecastCount: forecast.length,
    };
  }, [combinedData]);

  // Forecast trend chart data (historical vs forecast)
  const forecastTrendData = useMemo(() => {
    if (!combinedData) return { labels: [], datasets: [] };

    const { historical, forecast } = combinedData;

    const aggregateByMonth = (data: typeof historical) => {
      const monthMap = new Map<string, number>();
      data.forEach(item => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        monthMap.set(label, (monthMap.get(label) || 0) + item.total);
      });
      return monthMap;
    };

    const historicalMap = aggregateByMonth(historical);
    const forecastMap = aggregateByMonth(forecast);

    const allLabels = new Set([...historicalMap.keys(), ...forecastMap.keys()]);
    const sortedLabels = Array.from(allLabels).sort((a, b) => {
      const dateA = new Date(a);
      const dateB = new Date(b);
      return dateA.getTime() - dateB.getTime();
    });

    return {
      labels: sortedLabels,
      datasets: [
        {
          label: 'Historical Emissions',
          data: sortedLabels.map(label => {
            const val = historicalMap.get(label);
            return val ? Math.round(val / 1000) : null;
          }),
          backgroundColor: "rgba(96, 165, 250, 0.2)",
          borderColor: "hsl(217, 91%, 60%)",
          borderWidth: 2,
        },
        {
          label: 'Forecasted Emissions',
          data: sortedLabels.map(label => {
            const val = forecastMap.get(label);
            return val ? Math.round(val / 1000) : null;
          }),
          backgroundColor: "rgba(245, 158, 11, 0.2)",
          borderColor: "hsl(45, 93%, 47%)",
          borderWidth: 2,
          borderDash: [5, 5],
        },
      ],
    };
  }, [combinedData]);

  // Monthly comparison bar chart - shows AVERAGE per month for fair comparison
  const monthlyComparisonData = useMemo(() => {
    if (!combinedData) return { labels: [], datasets: [] };

    const { historical, forecast } = combinedData;

    // Calculate average per month (sum / count) for fair comparison
    const aggregateByMonth = (data: typeof historical) => {
      const monthMap = new Map<string, { sum: number; count: number }>();
      data.forEach(item => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short' });
        const existing = monthMap.get(label) || { sum: 0, count: 0 };
        monthMap.set(label, {
          sum: existing.sum + item.total,
          count: existing.count + 1
        });
      });
      // Convert to averages
      const avgMap = new Map<string, number>();
      monthMap.forEach((value, key) => {
        avgMap.set(key, value.sum / value.count);
      });
      return avgMap;
    };

    const historicalMap = aggregateByMonth(historical);
    const forecastMap = aggregateByMonth(forecast);

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const availableMonths = months.filter(m => historicalMap.has(m) || forecastMap.has(m));

    return {
      labels: availableMonths,
      datasets: [
        {
          label: 'Historical (Avg)',
          data: availableMonths.map(m => {
            const val = historicalMap.get(m);
            return val ? Math.round(val / 1000) : 0;
          }),
          backgroundColor: "hsl(217, 91%, 60%)",
        },
        {
          label: 'Forecast (Avg)',
          data: availableMonths.map(m => {
            const val = forecastMap.get(m);
            return val ? Math.round(val / 1000) : 0;
          }),
          backgroundColor: "hsl(45, 93%, 47%)",
        },
      ],
    };
  }, [combinedData]);

  // Sector pie chart data
  const sectorPieData = useMemo(() => {
    if (!stats) {
      return {
        labels: ["Energy"],
        datasets: [{ label: "Emissions by Sector", data: [100], backgroundColor: ["hsl(45, 93%, 47%)"] }]
      };
    }

    const { sectorTotals } = stats;
    const hasData = Object.values(sectorTotals).some(v => v > 0);

    if (!hasData) {
      return {
        labels: ["Energy"],
        datasets: [{ label: "Emissions by Sector", data: [100], backgroundColor: ["hsl(45, 93%, 47%)"] }]
      };
    }

    return {
      labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
      datasets: [
        {
          label: "Emissions by Sector",
          data: Object.values(sectorTotals).map(v => Math.round(v / 1000)),
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
  }, [stats]);

  // Loading state
  if (areasLoading || dataLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading area data...</p>
        </div>
      </div>
    );
  }

  // Area not found
  if (!area) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4 max-w-md">
          <Leaf className="h-16 w-16 mx-auto text-muted-foreground" />
          <h2 className="text-2xl font-semibold">Area Not Found</h2>
          <p className="text-muted-foreground">
            The emission source you're looking for doesn't exist or has been removed.
          </p>
          <Button onClick={() => setLocation("/dashboard")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const sectors = [
    { key: "transport", label: "Transport", color: "hsl(217, 91%, 60%)" },
    { key: "industry", label: "Industry", color: "hsl(280, 67%, 55%)" },
    { key: "energy", label: "Energy", color: "hsl(45, 93%, 47%)" },
    { key: "waste", label: "Waste", color: "hsl(25, 95%, 53%)" },
    { key: "buildings", label: "Buildings", color: "hsl(338, 78%, 56%)" },
  ];

  const maxSectorValue = stats ? Math.max(...Object.values(stats.sectorTotals)) : 0;

  return (
    <div className="min-h-screen flex flex-col bg-[#fafafa] dark:bg-[#030303] relative overflow-hidden text-slate-900 dark:text-white">
      {/* Dynamic Background */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <motion.div 
          animate={{ x: [0, 80, -40, 0], y: [0, -80, 40, 0], scale: [1, 1.15, 0.9, 1] }} 
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute top-[-5%] right-[-5%] w-[45vw] h-[45vw] bg-emerald-500/10 dark:bg-emerald-600/5 rounded-full filter blur-[120px] opacity-100" 
        />
      </div>

      {/* Header */}
      <header className="bg-white/80 dark:bg-[#030303]/90 backdrop-blur-2xl shadow-sm border-b border-black/5 dark:border-white/5 sticky top-0 z-50 px-6 py-5">
        <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-xl hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => setLocation("/dashboard")}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20">
              <Leaf className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">{area.name}</h1>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                Detailed Emission Profile
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-3 py-1 border-0">
              Live Source
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 overflow-auto relative z-10">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
              <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-black/5 dark:border-white/5 shadow-xl relative overflow-hidden h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />
                <CardHeader className="pb-2 relative z-10">
                  <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Total History</p>
                  <CardTitle className="text-3xl font-bold font-mono">
                    {stats ? Math.round(stats.totalHistorical / 1000).toLocaleString() : 0}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 relative z-10">
                  <p className="text-xs text-muted-foreground">thousand tons CO₂e</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300, delay: 0.1 }}>
              <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-black/5 dark:border-white/5 shadow-xl relative overflow-hidden h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent pointer-events-none" />
                <CardHeader className="pb-2 relative z-10">
                  <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Forecasted Sum</p>
                  <CardTitle className="text-3xl font-bold font-mono">
                    {stats ? Math.round(stats.totalForecast / 1000).toLocaleString() : 0}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 relative z-10">
                  <p className="text-xs text-muted-foreground">thousand tons CO₂e</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300, delay: 0.2 }}>
              <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-black/5 dark:border-white/5 shadow-xl relative overflow-hidden h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
                <CardHeader className="pb-2 relative z-10">
                  <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Avg per Month</p>
                  <CardTitle className="text-3xl font-bold font-mono">
                    {stats ? Math.round(stats.avgHistorical / 1000).toLocaleString() : 0}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 relative z-10">
                  <p className="text-xs text-muted-foreground">thousand tons CO₂e</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300, delay: 0.3 }}>
              <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-black/5 dark:border-white/5 shadow-xl relative overflow-hidden h-full">
                <div className={`absolute inset-0 bg-gradient-to-br ${stats && stats.trendPercentage > 0 ? "from-red-500/10" : "from-emerald-500/10"} to-transparent pointer-events-none`} />
                <CardHeader className="pb-2 relative z-10">
                  <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Projected Trend</p>
                  <div className="flex items-center gap-2">
                    {stats && stats.trendPercentage > 0 ? (
                      <Badge variant="destructive" className="gap-1 text-base px-3 py-1 font-mono">
                        <TrendingUp className="h-4 w-4" />
                        +{Math.abs(stats.trendPercentage).toFixed(1)}%
                      </Badge>
                    ) : (
                      <Badge className="gap-1 bg-emerald-500 text-white text-base px-3 py-1 font-mono">
                        <TrendingDown className="h-4 w-4" />
                        {stats ? Math.abs(stats.trendPercentage).toFixed(1) : 0}%
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0 relative z-10">
                  <p className="text-xs text-muted-foreground">vs historical average</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Main Trend Chart */}
          <div className="w-full">
            <EmissionChart
              title="Emission Trends: Historical vs Forecast"
              type="line"
              data={forecastTrendData}
            />
          </div>

          {/* Secondary Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EmissionChart
              title="Monthly Average Comparison"
              type="bar"
              data={monthlyComparisonData}
            />
            <EmissionChart
              title="Emissions by Sector"
              type="doughnut"
              data={sectorPieData}
            />
          </div>

          {/* Sector Breakdown Detail */}
          <motion.div whileHover={{ y: -5 }} transition={{ type: "spring", stiffness: 300 }}>
            <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 to-transparent pointer-events-none" />
              <CardHeader className="relative z-10">
                <CardTitle>Sectoral Breakdown (Historical Total)</CardTitle>
              </CardHeader>
              <CardContent className="relative z-10">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
                  {sectors.map((sector) => {
                    const value = stats?.sectorTotals[sector.key as keyof typeof stats.sectorTotals] || 0;
                    const percentage = maxSectorValue > 0 ? (value / maxSectorValue) * 100 : 0;

                    return (
                      <div key={sector.key} className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{sector.label}</span>
                        </div>
                        <div className="text-2xl font-mono font-bold tracking-tight">
                          {Math.round(value / 1000).toLocaleString()}
                        </div>
                        <div className="space-y-1.5">
                          <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Relative Impact</p>
                          <Progress
                            value={percentage}
                            className="h-2 rounded-full bg-black/5 dark:bg-white/5"
                            style={{
                              "--progress-background": sector.color,
                            } as React.CSSProperties}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Data Info */}
          <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-md border border-white/20 dark:border-white/10 shadow-xl">
            <CardHeader>
              <CardTitle className="text-base">Data Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Historical Data Points:</span>
                  <span className="ml-2 font-mono">{stats?.historicalCount || 0}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Forecast Data Points:</span>
                  <span className="ml-2 font-mono">{stats?.forecastCount || 0}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Location:</span>
                  <span className="ml-2 font-mono">
                    {area.coordinates[0].toFixed(4)}, {area.coordinates[1].toFixed(4)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Area ID:</span>
                  <span className="ml-2 font-mono">{area.id}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
