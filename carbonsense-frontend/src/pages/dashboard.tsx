import { useState, useMemo } from "react";
import { useLocation } from "wouter";
import { EmissionMap } from "@/components/emission-map";
import { Leaderboard } from "@/components/leaderboard";
import { SectorFilter } from "@/components/sector-filter";
import { TimeControls } from "@/components/time-controls";
import { EmissionChart } from "@/components/emission-chart";
import { AreaDetailPanel } from "@/components/area-detail-panel";
import { MapLegend } from "@/components/map-legend";
import { ThemeToggle } from "@/components/theme-toggle";
import { DataExplorer } from "@/components/data-explorer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Leaf,
  Home,
  LogOut,
  Loader2,
  Database,
  TrendingUp,
  Brain,
  Download,
  Activity,
  BarChart3,
  MapPin,
  Zap,
  ArrowRight,
  Sparkles,
  Layers,
  Filter,
  X
} from "lucide-react";
import type { Sector, DataType, LeaderboardEntry } from "@shared/schema";
import type { TimeInterval, UCSummary } from "@/lib/api";
import { useAreas, useLatestEmissions, useLeaderboard, useTimeSeriesData, useCombinedTimeSeriesData, useUCBoundaries, useUCSummaries } from "@/hooks/use-emissions";
import type { EmissionDataPoint, AreaInfo } from "@/lib/api";
import { getUCEmission } from "@/lib/map-utils";
import { motion, AnimatePresence } from "framer-motion";

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>(["transport", "industry", "energy", "waste", "buildings"]); // Start with all sectors
  const [timeInterval, setTimeInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);
  const [selectedUCCode, setSelectedUCCode] = useState<string | null>(null);
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);

  // Fetch real data using hooks (pass selectedSectors and timeInterval for filtering)
  const { data: areas = [], isLoading: areasLoading } = useAreas();
  const { data: emissionData = {}, isLoading: emissionsLoading } = useLatestEmissions(dataType, selectedSectors, timeInterval);
  const { data: leaderboard = [], isLoading: leaderboardLoading } = useLeaderboard(dataType, selectedSectors, timeInterval);
  const { data: timeSeriesData = [] } = useTimeSeriesData(undefined, dataType);
  const { data: combinedData } = useCombinedTimeSeriesData(selectedAreaId || undefined);

  // UC-level data for choropleth map (supports historical + forecast toggle)
  const { data: ucBoundaries } = useUCBoundaries();
  const { data: ucSummaries = [], isLoading: ucLoading } = useUCSummaries(dataType);

  // Derive the selected UC summary
  const selectedUCSummary = useMemo(() => {
    if (!selectedUCCode || !ucSummaries) return null;
    return ucSummaries.find((uc: UCSummary) => uc.uc_code === selectedUCCode) ?? null;
  }, [selectedUCCode, ucSummaries]);

  // UC-based leaderboard (151 UCs, not duplicated per sector)
  const ucLeaderboard = useMemo((): LeaderboardEntry[] => {
    if (!ucSummaries || ucSummaries.length === 0) return [];
    return ucSummaries
      .map((uc: UCSummary) => ({
        rank: 0,
        areaId: uc.uc_code,
        areaName: uc.uc_name,
        emissions: getUCEmission(uc, selectedSectors),
        trend: 'stable' as const,
        trendPercentage: 0,
      }))
      .filter(e => e.emissions > 0)
      .sort((a, b) => b.emissions - a.emissions)
      .map((entry, index) => ({ ...entry, rank: index + 1 }));
  }, [ucSummaries, selectedSectors]);

  // Min/max emissions for map legend
  const [legendMin, legendMax] = useMemo(() => {
    if (!ucSummaries || ucSummaries.length === 0) return [0, 0];
    const values = ucSummaries
      .map((uc: UCSummary) => getUCEmission(uc, selectedSectors))
      .filter(v => v > 0);
    if (values.length === 0) return [0, 0];
    return [Math.min(...values), Math.max(...values)];
  }, [ucSummaries, selectedSectors]);

  const handleLogout = () => {
    localStorage.removeItem("user");
    setLocation("/");
  };

  const handleToggleSector = (sector: Sector) => {
    setSelectedSectors(prev =>
      prev.includes(sector)
        ? prev.filter(s => s !== sector)
        : [...prev, sector]
    );
  };

  const handleSelectAllSectors = () => {
    setSelectedSectors(["transport", "industry", "energy", "waste", "buildings"]);
  };

  const handleClearAllSectors = () => {
    setSelectedSectors([]);
  };

  // Calculate max emission for map scaling (use 75th percentile to avoid outlier skew)
  const maxEmission = useMemo(() => {
    const values = (Object.values(emissionData) as number[]).filter(v => v > 0).sort((a, b) => a - b);
    if (values.length === 0) return 1000000;
    // Use 75th percentile as reference to spread colors better
    const p75Index = Math.floor(values.length * 0.75);
    const p75Value = values[p75Index] || values[values.length - 1];
    // Return 1.5x the 75th percentile to allow some headroom
    return p75Value * 1.5;
  }, [emissionData]);

  // Calculate sector totals across all time series data
  const sectorTotals = useMemo(() => {
    const totals = {
      transport: 0,
      industry: 0,
      energy: 0,
      waste: 0,
      buildings: 0
    };

    timeSeriesData.forEach((item: EmissionDataPoint) => {
      totals.transport += item.transport;
      totals.industry += item.industry;
      totals.energy += item.energy;
      totals.waste += item.waste;
      totals.buildings += item.buildings;
    });

    return totals;
  }, [timeSeriesData]);

  // Sector breakdown pie chart
  const sectorPieData = useMemo(() => {
    const values = Object.values(sectorTotals);
    const hasData = values.some(v => v > 0);

    if (!hasData) {
      return {
        labels: ["Energy"],
        datasets: [{
          label: "Emissions by Sector",
          data: [100],
          backgroundColor: ["hsl(45, 93%, 47%)"],
        }]
      };
    }

    return {
      labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
      datasets: [
        {
          label: "Emissions by Sector",
          data: Object.values(sectorTotals).map(v => Math.round(v / 1000)), // Convert to thousands
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

  // Top areas bar chart
  const areaBarData = useMemo(() => {
    const topAreas = leaderboard.slice(0, 5) as LeaderboardEntry[];
    return {
      labels: topAreas.map((e: LeaderboardEntry) => e.areaName),
      datasets: [
        {
          label: "Total Emissions (thousands tons CO₂e)",
          data: topAreas.map((e: LeaderboardEntry) => Math.round(e.emissions / 1000)),
          backgroundColor: "hsl(142, 60%, 50%)",
        },
      ],
    };
  }, [leaderboard]);

  // Sector colors and labels for consistent styling
  // Historical = blue tones, Forecast = orange/amber tones for clear differentiation
  const sectorConfig = {
    transport: { label: "Transport", historical: "hsl(217, 91%, 60%)", forecast: "hsl(25, 95%, 53%)", transparent: "rgba(96, 165, 250, 0.2)" },
    industry: { label: "Industry", historical: "hsl(280, 67%, 55%)", forecast: "hsl(45, 93%, 47%)", transparent: "rgba(168, 85, 247, 0.2)" },
    energy: { label: "Energy", historical: "hsl(142, 65%, 45%)", forecast: "hsl(0, 72%, 51%)", transparent: "rgba(34, 197, 94, 0.2)" },
    waste: { label: "Waste", historical: "hsl(199, 89%, 48%)", forecast: "hsl(338, 78%, 56%)", transparent: "rgba(14, 165, 233, 0.2)" },
    buildings: { label: "Buildings", historical: "hsl(262, 83%, 58%)", forecast: "hsl(45, 93%, 47%)", transparent: "rgba(139, 92, 246, 0.2)" },
  };

  // Generate separate chart data for each sector
  const sectorChartData = useMemo(() => {
    if (!combinedData) {
      return {};
    }

    const { historical, forecast } = combinedData;

    // Helper to aggregate data by month for a specific sector
    const aggregateBySector = (data: EmissionDataPoint[], sectorKey: Sector) => {
      const monthMap = new Map<string, number>();
      data.forEach((item: EmissionDataPoint) => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        const value = item[sectorKey] as number;
        if (value > 0) {
          monthMap.set(label, (monthMap.get(label) || 0) + value);
        }
      });
      return monthMap;
    };

    const result: Record<Sector, { labels: string[]; datasets: Array<{ label: string; data: (number | null)[]; backgroundColor: string; borderColor: string; borderWidth: number; borderDash?: number[] }> }> = {} as any;

    const allSectors: Sector[] = ["transport", "industry", "energy", "waste", "buildings"];

    allSectors.forEach((sector) => {
      const historicalMap = aggregateBySector(historical, sector);
      const forecastMap = aggregateBySector(forecast, sector);
      const config = sectorConfig[sector];

      // Get all dates for this sector and sort
      const allDates = new Set([...historicalMap.keys(), ...forecastMap.keys()]);
      const sortedLabels = Array.from(allDates).sort((a, b) => {
        const dateA = new Date(a);
        const dateB = new Date(b);
        return dateA.getTime() - dateB.getTime();
      });

      const datasets: Array<{ label: string; data: (number | null)[]; backgroundColor: string; borderColor: string; borderWidth: number; borderDash?: number[] }> = [];

      // Determine if we need to scale values (only for large values > 1000)
      const allValues = [...historicalMap.values(), ...forecastMap.values()];
      const maxValue = allValues.length > 0 ? Math.max(...allValues) : 0;
      const shouldScale = maxValue > 1000;

      // Historical line (solid blue-ish color)
      if (historicalMap.size > 0) {
        datasets.push({
          label: 'Historical',
          data: sortedLabels.map(label => {
            const val = historicalMap.get(label);
            if (!val) return null;
            return shouldScale ? Math.round(val / 1000) : Math.round(val * 10) / 10;
          }),
          backgroundColor: "rgba(59, 130, 246, 0.2)",
          borderColor: "hsl(217, 91%, 60%)", // Blue for historical
          borderWidth: 2,
        });
      }

      // Forecast line (dashed orange color)
      if (forecastMap.size > 0) {
        datasets.push({
          label: 'Forecast',
          data: sortedLabels.map(label => {
            const val = forecastMap.get(label);
            if (!val) return null;
            return shouldScale ? Math.round(val / 1000) : Math.round(val * 10) / 10;
          }),
          backgroundColor: "rgba(245, 158, 11, 0.2)",
          borderColor: "hsl(45, 93%, 47%)", // Orange/Amber for forecast
          borderWidth: 2,
          borderDash: [5, 5],
        });
      }

      result[sector] = {
        labels: sortedLabels,
        datasets,
      };
    });

    return result;
  }, [combinedData]);

  // Monthly comparison bar chart - shows each sector's average per month
  const monthlyComparisonData = useMemo(() => {
    if (!combinedData) return { labels: [], datasets: [] };

    const { historical } = combinedData;

    // Calculate average per month for each sector
    const aggregateByMonthForSector = (data: EmissionDataPoint[], sectorKey: Sector) => {
      const monthMap = new Map<string, { sum: number; count: number }>();
      data.forEach((item: EmissionDataPoint) => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short' });
        const value = item[sectorKey] as number;

        if (value > 0) {
          const existing = monthMap.get(label) || { sum: 0, count: 0 };
          monthMap.set(label, {
            sum: existing.sum + value,
            count: existing.count + 1
          });
        }
      });
      // Convert to averages
      const avgMap = new Map<string, number>();
      monthMap.forEach((value, key) => {
        avgMap.set(key, value.sum / value.count);
      });
      return avgMap;
    };

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    // Create datasets for each selected sector
    const datasets = selectedSectors.map((sector) => {
      const sectorMap = aggregateByMonthForSector(historical, sector);
      // Determine if we need to scale (only for large values)
      const allValues = Array.from(sectorMap.values());
      const maxValue = allValues.length > 0 ? Math.max(...allValues) : 0;
      const shouldScale = maxValue > 1000;

      return {
        label: sectorConfig[sector].label,
        data: months.map(m => {
          const val = sectorMap.get(m);
          if (!val) return 0;
          return shouldScale ? Math.round(val / 1000) : Math.round(val * 10) / 10;
        }),
        backgroundColor: sectorConfig[sector].historical,
      };
    });

    return {
      labels: months,
      datasets,
    };
  }, [combinedData, selectedSectors]);

  const selectedArea = areas.find((a: AreaInfo) => a.id === selectedAreaId);

  // Loading state
  if (areasLoading || emissionsLoading || ucLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#fafafa] dark:bg-[#030303] relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none z-0">
          <motion.div 
            animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute top-[20%] left-[30%] w-[40vw] h-[40vw] bg-emerald-400/10 dark:bg-emerald-600/10 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] opacity-100" 
          />
        </div>
        <div className="text-center space-y-6 z-10">
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="relative h-24 w-24 mx-auto"
          >
            <div className="absolute inset-0 bg-emerald-500/20 rounded-full blur-xl animate-pulse" />
            <div className="relative h-full w-full rounded-2xl bg-white/10 dark:bg-black/10 backdrop-blur-xl border border-white/20 dark:border-white/10 flex items-center justify-center shadow-2xl">
              <Leaf className="h-10 w-10 text-emerald-500 animate-bounce" />
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="space-y-2"
          >
            <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300">
              Initializing Data Core
            </h2>
            <p className="text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading carbon emission datasets...
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  // No data state
  if (areas.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4 max-w-md">
          <Leaf className="h-16 w-16 mx-auto text-muted-foreground" />
          <h2 className="text-2xl font-semibold">No Data Available</h2>
          <p className="text-muted-foreground">
            Unable to load emissions data. Please ensure the backend server is running and the database is accessible.
          </p>
        </div>
      </div>
    );
  }

  // Get selected area details
  const selectedAreaEmissions = selectedAreaId && emissionData[selectedAreaId]
    ? emissionData[selectedAreaId]
    : 0;

  // findLast: timeSeriesData is sorted ascending, so the last match is the latest data point
  const selectedAreaData = [...timeSeriesData].reverse().find((d: EmissionDataPoint) => d.area_id === selectedAreaId);
  const sectorBreakdown = selectedAreaData ? {
    transport: selectedSectors.includes('transport') ? selectedAreaData.transport : 0,
    industry: selectedSectors.includes('industry') ? selectedAreaData.industry : 0,
    energy: selectedSectors.includes('energy') ? selectedAreaData.energy : 0,
    waste: selectedSectors.includes('waste') ? selectedAreaData.waste : 0,
    buildings: selectedSectors.includes('buildings') ? selectedAreaData.buildings : 0,
  } : {
    transport: 0,
    industry: 0,
    energy: 0,
    waste: 0,
    buildings: 0,
  };

  // Feature cards configuration
  const featureCards = [
    {
      id: "map",
      title: "Interactive Map",
      description: "Color-coded emission hotspots across Lahore",
      icon: MapPin,
      color: "emerald",
      bgClass: "bg-emerald-500/10",
      textClass: "text-emerald-600 dark:text-emerald-400",
      borderClass: "border-emerald-500/20 hover:border-emerald-500/40",
    },
    {
      id: "analytics",
      title: "Trend Analysis",
      description: "Historical patterns and time-series visualization",
      icon: TrendingUp,
      color: "blue",
      bgClass: "bg-blue-500/10",
      textClass: "text-blue-600 dark:text-blue-400",
      borderClass: "border-blue-500/20 hover:border-blue-500/40",
    },
    {
      id: "forecast",
      title: "ML Forecasting",
      description: "AI-powered predictions for proactive planning",
      icon: Brain,
      color: "purple",
      bgClass: "bg-purple-500/10",
      textClass: "text-purple-600 dark:text-purple-400",
      borderClass: "border-purple-500/20 hover:border-purple-500/40",
    },
    {
      id: "data",
      title: "Data Export",
      description: "Download and analyze raw emission data",
      icon: Download,
      color: "amber",
      bgClass: "bg-amber-500/10",
      textClass: "text-amber-600 dark:text-amber-400",
      borderClass: "border-amber-500/20 hover:border-amber-500/40",
    },
  ];

  const navItems = [
    { id: "overview", label: "Overview", icon: Sparkles },
    { id: "map", label: "Map View", icon: MapPin },
    { id: "analytics", label: "Trends", icon: TrendingUp },
    { id: "forecast", label: "ML Forecast", icon: Brain },
    { id: "data", label: "Data Export", icon: Database },
  ];

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full w-full flex overflow-hidden">
        {/* Hover-activated Sidebar */}
        <motion.aside
          initial={false}
          animate={{ width: isSidebarExpanded ? 260 : 80 }}
          onMouseEnter={() => setIsSidebarExpanded(true)}
          onMouseLeave={() => setIsSidebarExpanded(false)}
          className="h-full bg-white dark:bg-[#030303] border-r border-black/5 dark:border-white/5 shadow-2xl z-[100] relative flex flex-col transition-all duration-300 ease-in-out backdrop-blur-3xl"
        >
          {/* Sidebar Logo Area */}
          <div className="p-6 mb-4 flex items-center gap-4 overflow-hidden">
            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25">
              <Leaf className="h-5 w-5" />
            </div>
            <motion.div
              animate={{ opacity: isSidebarExpanded ? 1 : 0, x: isSidebarExpanded ? 0 : -10 }}
              className="whitespace-nowrap"
            >
              <h1 className="text-xl font-bold tracking-tight">CarbonSense</h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Intelligence</p>
            </motion.div>
          </div>

          {/* Navigation Items */}
          <nav className="flex-1 px-3 space-y-2">
            <TabsList className="bg-transparent flex flex-col items-stretch h-auto p-0 gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <TabsTrigger
                    key={item.id}
                    value={item.id}
                    className={`
                      w-full relative flex items-center gap-4 p-3 rounded-xl transition-all duration-300 border-none shadow-none text-left justify-start
                      ${isActive 
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' 
                        : 'text-muted-foreground hover:bg-black/5 dark:hover:bg-white/5 hover:text-foreground'}
                    `}
                  >
                    <div className="flex-shrink-0 w-6 flex items-center justify-center">
                      <Icon className={`h-5 w-5 transition-transform duration-300 ${isActive ? 'scale-110' : ''}`} />
                    </div>
                    <motion.span
                      animate={{ opacity: isSidebarExpanded ? 1 : 0, x: isSidebarExpanded ? 0 : -10 }}
                      className="whitespace-nowrap font-medium text-sm"
                    >
                      {item.label}
                    </motion.span>
                    {isActive && (
                      <motion.div
                        layoutId="active-nav-indicator"
                        className="absolute left-0 w-1 h-6 bg-emerald-500 rounded-r-full"
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </nav>

          {/* Bottom Actions */}
          <div className="p-4 border-t border-black/5 dark:border-white/5 space-y-2">
            <Button
              variant="ghost"
              className="w-full justify-start gap-4 p-3 rounded-xl hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => setLocation("/")}
            >
              <div className="w-6 flex items-center justify-center">
                <Home className="h-5 w-5" />
              </div>
              <motion.span
                animate={{ opacity: isSidebarExpanded ? 1 : 0 }}
                className="whitespace-nowrap"
              >
                Landing Page
              </motion.span>
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start gap-4 p-3 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 text-rose-500 hover:text-rose-600 hover:bg-rose-500/5"
              onClick={handleLogout}
            >
              <div className="w-6 flex items-center justify-center">
                <LogOut className="h-5 w-5" />
              </div>
              <motion.span
                animate={{ opacity: isSidebarExpanded ? 1 : 0 }}
                className="whitespace-nowrap"
              >
                Log Out
              </motion.span>
            </Button>
            <div className="flex items-center gap-4 p-3">
              <div className="w-6 flex items-center justify-center">
                <ThemeToggle />
              </div>
              <motion.span
                animate={{ opacity: isSidebarExpanded ? 1 : 0 }}
                className="whitespace-nowrap text-sm text-muted-foreground font-medium"
              >
                Theme Mode
              </motion.span>
            </div>
          </div>
        </motion.aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col relative overflow-hidden">
          {/* Dynamic Background */}
          <div className="absolute inset-0 pointer-events-none z-0">
             <motion.div 
               animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }} 
               transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
               className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-emerald-500/10 dark:bg-emerald-600/5 rounded-full filter blur-[120px] opacity-100" 
             />
          </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {/* Overview Tab - Welcome & Feature Navigation */}
          <TabsContent value="overview" className="h-full mt-0 overflow-auto">
            <div className="min-h-full bg-[#fafafa] dark:bg-[#030303] text-slate-900 dark:text-slate-50 relative overflow-hidden">
              <div className="absolute inset-0 pointer-events-none z-0">
                <motion.div 
                  animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
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
                      <Button onClick={() => setActiveTab("map")} className="rounded-full px-6 bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-500/20">
                        <MapPin className="h-4 w-4 mr-2" /> Explore Live Map
                      </Button>
                      <Button variant="outline" onClick={() => setActiveTab("analytics")} className="rounded-full px-6 bg-white/50 dark:bg-black/50 backdrop-blur-md">
                        <TrendingUp className="h-4 w-4 mr-2" /> View Trends
                      </Button>
                    </div>
                  </div>
                  
                  {/* Decorative abstract visualization for Hero right side */}
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
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, staggerChildren: 0.1 }}
                  className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
                >
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
                          <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-500 dark:from-blue-400 dark:to-indigo-300">5</p>
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
                          <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-pink-500 dark:from-purple-400 dark:to-pink-300">3+</p>
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
                            {leaderboard.length > 0
                              ? `${(Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000000 * 10) / 10).toLocaleString()}M`
                              : '—'}
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

              {/* Main Dashboard Grid inside Overview */}
              <div className="px-8 pb-12">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left Column: Charts */}
                  <div className="lg:col-span-2 space-y-6">
                    <motion.div 
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                    >
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
                          <Button variant="ghost" size="sm" onClick={() => setActiveTab("analytics")} className="text-xs">
                            View Full Analytics <ArrowRight className="h-3 w-3 ml-1" />
                          </Button>
                        </CardHeader>
                        <CardContent className="relative z-10 pt-4">
                          <EmissionChart title="" type="bar" data={areaBarData} />
                        </CardContent>
                      </Card>
                    </motion.div>
                    
                    <motion.div 
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.1 }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-6"
                    >
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
                      
                      {/* Interactive map feature shortcut */}
                      <Card 
                        className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-emerald-500/30 shadow-[0_8px_30px_rgb(16,185,129,0.1)] overflow-hidden relative group cursor-pointer hover:border-emerald-500/50 transition-all duration-300"
                        onClick={() => setActiveTab('map')}
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

                  {/* Right Column: Platform Features & Tags */}
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
                            {featureCards.map((feature, i) => {
                              const Icon = feature.icon;
                              return (
                                <motion.div key={feature.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1, duration: 0.5 }}>
                                  <button
                                    className={`w-full flex items-center gap-4 p-4 text-left transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02] group`}
                                    onClick={() => setActiveTab(feature.id)}
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

                    {/* Sector Tags Panel */}
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

                    {/* Live System Updates */}
                    <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.5 }}>
                      <Card className="bg-white/40 dark:bg-black/30 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        <CardHeader className="pb-3 flex flex-row items-center justify-between relative z-10">
                          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                            <Activity className="h-4 w-4 text-indigo-500" /> System Updates
                          </CardTitle>
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                          </span>
                        </CardHeader>
                        <CardContent className="relative z-10 p-5 md:p-6 pt-2">
                          <div className="space-y-6 md:space-y-7">
                            {[
                              { title: "Anomaly Detected", desc: "Spike in Gulberg energy usage", time: "Just now", icon: Zap, color: "text-amber-500", bg: "bg-amber-500/10" },
                              { title: "Model Deployed", desc: "ML Forecast updated to v2.1", time: "2h ago", icon: Brain, color: "text-purple-500", bg: "bg-purple-500/10" },
                              { title: "Data Sync Complete", desc: "Climate Trace API synchronized", time: "5h ago", icon: Database, color: "text-blue-500", bg: "bg-blue-500/10" },
                              { title: "New Route Parsed", desc: "Transport tracking optimized", time: "1d ago", icon: Activity, color: "text-emerald-500", bg: "bg-emerald-500/10" },
                            ].map((update, idx) => (
                              <div key={idx} className="flex gap-4 group/item items-start">
                                <div className={`flex-shrink-0 h-10 w-10 rounded-full ${update.bg} flex items-center justify-center mt-0.5 group-hover/item:scale-110 transition-transform`}>
                                  <update.icon className={`h-5 w-5 ${update.color}`} />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex justify-between items-center mb-1">
                                    <h4 className="text-[15px] font-semibold text-slate-800 dark:text-slate-200 truncate">{update.title}</h4>
                                    <span className="text-xs font-medium text-muted-foreground whitespace-nowrap ml-2 flex-shrink-0">{update.time}</span>
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
          </TabsContent>

          <TabsContent value="map" className="h-full mt-0 p-0 relative">
            <div className="absolute inset-0 z-0">
              <EmissionMap
                ucBoundaries={ucBoundaries}
                ucSummaries={ucSummaries}
                selectedUCCode={selectedUCCode}
                onUCSelect={setSelectedUCCode}
                selectedSectors={selectedSectors}
              />
            </div>

            <div className="absolute inset-0 pointer-events-none z-10 mix-blend-normal">
              {/* Left Side: Collapsible Filters */}
              <div className="absolute top-4 left-4 pointer-events-auto z-[1000]">
                <AnimatePresence mode="wait">
                  {!isFiltersOpen ? (
                    <motion.div
                      key="filter-button"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Button
                        variant="secondary"
                        onClick={() => setIsFiltersOpen(true)}
                        className="shadow-lg bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 flex items-center gap-2"
                      >
                        <Filter className="h-4 w-4" />
                        <span className="font-semibold text-sm">Filters</span>
                      </Button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="filter-panel"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="w-[320px]"
                    >
                      <div className="space-y-4">
                        <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-2xl rounded-2xl relative overflow-hidden">
                          <CardHeader className="pb-3 border-b border-black/5 dark:border-white/5 flex flex-row items-center justify-between">
                            <CardTitle className="text-sm font-bold tracking-tight">Filters</CardTitle>
                            <Button variant="ghost" size="icon" className="h-6 w-6 -mr-2" onClick={() => setIsFiltersOpen(false)}>
                              <X className="h-4 w-4" />
                            </Button>
                          </CardHeader>
                          <CardContent className="space-y-4 p-4 pt-4">
                            <div className="space-y-2">
                              <label className="text-xs font-medium text-muted-foreground">Sectors</label>
                              <SectorFilter
                                selectedSectors={selectedSectors}
                                onToggleSector={handleToggleSector}
                                onSelectAll={handleSelectAllSectors}
                                onClearAll={handleClearAllSectors}
                              />
                            </div>
                            <div className="flex items-center space-x-3 pt-1">
                              <div
                                className={`flex-1 text-center py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all ${
                                  dataType === 'historical'
                                    ? 'bg-white dark:bg-black/60 shadow-sm text-emerald-600 dark:text-emerald-400'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                }`}
                                onClick={() => setDataType('historical')}
                              >
                                Historical
                              </div>
                              <div
                                className={`flex-1 text-center py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all ${
                                  dataType === 'forecast'
                                    ? 'bg-white dark:bg-black/60 shadow-sm text-emerald-600 dark:text-emerald-400'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                }`}
                                onClick={() => setDataType('forecast')}
                              >
                                Forecast
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Legend */}
              <div className="absolute bottom-4 left-4 pointer-events-auto z-[1000]">
                <MapLegend minValue={legendMin} maxValue={legendMax} />
              </div>

              {/* Right Side: Area Details or Leaderboard */}
              <div className="absolute top-4 right-4 h-[calc(100%-2.5rem)] w-[380px] pointer-events-auto shadow-2xl rounded-2xl flex flex-col z-[1000]">
                  {selectedUCCode && selectedUCSummary ? (
                    <AreaDetailPanel
                      ucSummary={selectedUCSummary}
                      selectedSectors={selectedSectors}
                      onClose={() => setSelectedUCCode(null)}
                    />
                  ) : (
                    <>
                      {ucLoading ? (
                        <div className="flex items-center justify-center h-full">
                          <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                      ) : (
                        <Leaderboard
                          entries={ucLeaderboard}
                          selectedAreaId={selectedUCCode}
                          onAreaSelect={setSelectedUCCode}
                          sectorTotals={sectorTotals}
                        />
                      )}
                    </>
                  )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="h-full mt-0 overflow-auto bg-muted/30">
            <div className="p-8">
              {/* Page Header */}
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                  <div className="h-10 w-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight">Historical Trends</h1>
                    <p className="text-muted-foreground">
                      Analyze past emission patterns across {areas.length} sources
                    </p>
                  </div>
                </div>
              </div>

              {/* Main Charts Grid */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
                <div className="xl:col-span-2">
                  <EmissionChart
                    title="Top Emission Sources"
                    type="bar"
                    data={areaBarData}
                  />
                </div>
                <EmissionChart
                  title="Sector Distribution"
                  type="doughnut"
                  data={sectorPieData}
                />
              </div>

              {/* Monthly Comparison Section */}
              <div className="mb-8">
                <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl overflow-hidden relative">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-blue-500/5 pointer-events-none" />
                    <CardHeader className="relative z-10">
                      <CardTitle>Monthly Emission Patterns</CardTitle>
                      <CardDescription>
                        Average emissions by month across all years - identify seasonal trends
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      {selectedSectors.length === 0 ? (
                        <div className="py-12 text-center flex flex-col items-center justify-center">
                          <motion.div
                            animate={{ rotate: [0, 10, -10, 0] }}
                            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                          >
                            <BarChart3 className="h-12 w-12 text-muted-foreground/30 mb-4" />
                          </motion.div>
                          <p className="text-muted-foreground font-medium">Select sectors from the Map View to see monthly patterns</p>
                        </div>
                      ) : (
                        <EmissionChart
                          title=""
                          type="bar"
                          data={monthlyComparisonData}
                        />
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* Year over Year Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-blue-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 rounded-xl bg-blue-500/20 flex items-center justify-center shadow-inner">
                          <Database className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Data Source</p>
                          <p className="text-lg font-bold tracking-tight">Climate Trace</p>
                          <p className="text-xs text-muted-foreground">2021 - Present</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300, delay: 0.05 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-emerald-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 rounded-xl bg-emerald-500/20 flex items-center justify-center shadow-inner">
                          <MapPin className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Coverage</p>
                          <p className="text-lg font-bold tracking-tight">{areas.length} Sources</p>
                          <p className="text-xs text-muted-foreground">Lahore Division</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300, delay: 0.1 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-amber-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 rounded-xl bg-amber-500/20 flex items-center justify-center shadow-inner">
                          <Activity className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Total Tracked</p>
                          <p className="text-lg font-bold tracking-tight">
                            {leaderboard.length > 0
                              ? `${(Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000000 * 10) / 10).toLocaleString()}M`
                              : '—'} tons
                          </p>
                          <p className="text-xs text-muted-foreground">CO₂ equivalent</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </div>
          </TabsContent>

          {/* ML Forecast Tab */}
          <TabsContent value="forecast" className="h-full mt-0 overflow-auto bg-muted/30">
            <div className="p-8">
              {/* Page Header */}
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                  <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight">ML Forecasting</h1>
                    <p className="text-muted-foreground">
                      AI-powered predictions for proactive environmental planning
                    </p>
                  </div>
                </div>
              </div>

              {/* Forecast Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-purple-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-14 w-14 rounded-xl bg-purple-500/20 flex items-center justify-center shadow-inner">
                          <Brain className="h-7 w-7 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Models Used</p>
                          <p className="text-xl font-bold tracking-tight">Hybrid XGBoost + Prophet</p>
                          <p className="text-xs text-muted-foreground">Sector-specific model selection</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300, delay: 0.05 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-blue-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-14 w-14 rounded-xl bg-blue-500/20 flex items-center justify-center shadow-inner">
                          <TrendingUp className="h-7 w-7 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Forecast Horizon</p>
                          <p className="text-xl font-bold tracking-tight">12 Months</p>
                          <p className="text-xs text-muted-foreground">Future predictions</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div whileHover={{ y: -4, scale: 1.02 }} transition={{ type: "spring", stiffness: 300, delay: 0.1 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-emerald-500/10 shadow-lg relative overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
                    <CardContent className="pt-6 relative z-10">
                      <div className="flex items-center gap-4">
                        <div className="h-14 w-14 rounded-xl bg-emerald-500/20 flex items-center justify-center shadow-inner">
                          <Activity className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Accuracy</p>
                          <p className="text-xl font-bold tracking-tight">~94%</p>
                          <p className="text-xs text-muted-foreground">R² on validation data</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* Combined Historical + Forecast Chart */}
              <div className="mb-8">
                <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300 }}>
                  <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl overflow-hidden relative">
                    <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/5 to-transparent pointer-events-none" />
                    <CardHeader className="relative z-10">
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle>Historical vs Predicted Emissions</CardTitle>
                          <CardDescription>
                            Combined view showing actual data transitioning into 12-month forecasts
                          </CardDescription>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <div className="h-3 w-8 bg-blue-500 rounded" />
                            <span className="text-sm text-muted-foreground font-medium">Historical</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="h-3 w-8 bg-amber-500 rounded border-2 border-dashed border-amber-600" />
                            <span className="text-sm text-muted-foreground font-medium">Forecast</span>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      {selectedSectors.length === 0 ? (
                        <div className="py-20 text-center flex flex-col items-center justify-center">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 20, ease: "linear" }}
                          >
                            <Brain className="h-16 w-16 text-muted-foreground/30 mb-4" />
                          </motion.div>
                          <p className="text-muted-foreground font-medium">Select sectors from the Map View to see forecasts</p>
                        </div>
                      ) : (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {selectedSectors.map((sector) => {
                          const data = sectorChartData[sector];
                          if (!data || data.datasets.length === 0) return null;
                          return (
                            <div key={sector} className="h-[420px]">
                              <EmissionChart
                                titleNode={
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 relative mt-[-2px]">
                                      <div className={`h-2.5 w-2.5 rounded-full`} style={{ backgroundColor: sectorConfig[sector].historical }} />
                                      <span className="font-semibold text-sm tracking-tight text-foreground">{sectorConfig[sector].label}</span>
                                    </div>
                                    <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10 backdrop-blur-md">
                                      95% confidence
                                    </Badge>
                                  </div>
                                }
                                type="line"
                                data={data}
                              />
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* How It Works Section */}
              <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300 }}>
                <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 to-transparent pointer-events-none" />
                  <CardHeader className="relative z-10">
                    <CardTitle>How ML Forecasting Works</CardTitle>
                    <CardDescription>
                      Understanding our prediction methodology
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative z-10">
                    <div className="grid md:grid-cols-3 gap-6">
                      <motion.div whileHover={{ scale: 1.05 }} className="flex gap-4 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                          <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 shadow-sm">
                              STEP 1
                            </span>
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
                            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 shadow-sm">
                              STEP 2
                            </span>
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
                            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 shadow-sm">
                              STEP 3
                            </span>
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
          </TabsContent>

          <TabsContent value="data" className="h-full mt-0 p-0 overflow-auto">
            <DataExplorer />
          </TabsContent>
        </div>
      </div>
    </Tabs>
  </div>
);
}
