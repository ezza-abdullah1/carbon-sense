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
  Sparkles
} from "lucide-react";
import type { Sector, DataType } from "@shared/schema";
import type { TimeInterval } from "@/lib/api";
import { useAreas, useLatestEmissions, useLeaderboard, useTimeSeriesData, useCombinedTimeSeriesData } from "@/hooks/use-emissions";
import type { EmissionDataPoint, AreaInfo } from "@/lib/api";

interface LeaderboardEntry {
  rank: number;
  areaId: string;
  areaName: string;
  emissions: number;
  trend: 'up' | 'down' | 'stable';
  trendPercentage: number;
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>(["transport", "industry", "energy", "waste", "buildings"]); // Start with all sectors
  const [timeInterval, setTimeInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);

  // Fetch real data using hooks (pass selectedSectors and timeInterval for filtering)
  const { data: areas = [], isLoading: areasLoading } = useAreas();
  const { data: emissionData = {}, isLoading: emissionsLoading } = useLatestEmissions(dataType, selectedSectors, timeInterval);
  const { data: leaderboard = [], isLoading: leaderboardLoading } = useLeaderboard(dataType, selectedSectors, timeInterval);
  const { data: timeSeriesData = [] } = useTimeSeriesData(selectedAreaId || undefined, dataType);
  const { data: combinedData } = useCombinedTimeSeriesData(selectedAreaId || undefined);

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
  if (areasLoading || emissionsLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading emissions data...</p>
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
            Please load emissions data first by running:
            <code className="block mt-2 p-2 bg-muted rounded text-sm">
              python manage.py load_emissions_data
            </code>
          </p>
        </div>
      </div>
    );
  }

  // Get selected area details
  const selectedAreaEmissions = selectedAreaId && emissionData[selectedAreaId]
    ? emissionData[selectedAreaId]
    : 0;

  const selectedAreaData = timeSeriesData.find((d: EmissionDataPoint) => d.area_id === selectedAreaId);
  const sectorBreakdown = selectedAreaData ? {
    transport: selectedAreaData.transport,
    industry: selectedAreaData.industry,
    energy: selectedAreaData.energy,
    waste: selectedAreaData.waste,
    buildings: selectedAreaData.buildings,
  } : {
    transport: 0,
    industry: 0,
    energy: selectedAreaEmissions, // Assume it's all energy for power plants
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

  return (
    <div className="h-screen flex flex-col bg-background">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        {/* Modern Header */}
        <header className="bg-card/95 backdrop-blur-md border-b border-border sticky top-0 z-50">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25">
                  <Leaf className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold tracking-tight" data-testid="text-app-title">
                      CarbonSense
                    </h1>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-0">
                      BETA
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Environmental Intelligence Platform
                  </p>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="hidden lg:flex items-center gap-6 px-6 py-2 bg-muted/50 rounded-full">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-sm font-medium">{areas.length}</span>
                  <span className="text-xs text-muted-foreground">Sources</span>
                </div>
                <div className="w-px h-4 bg-border" />
                <div className="flex items-center gap-2">
                  <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm font-medium">5</span>
                  <span className="text-xs text-muted-foreground">Sectors</span>
                </div>
                <div className="w-px h-4 bg-border" />
                <div className="flex items-center gap-2">
                  <Badge variant={dataType === 'forecast' ? 'default' : 'secondary'} className="text-[10px] px-2 py-0 h-5">
                    {dataType === 'forecast' ? 'Forecast Mode' : 'Historical'}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-lg"
                  onClick={() => setLocation("/")}
                  data-testid="button-home"
                >
                  <Home className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-lg"
                  onClick={handleLogout}
                  data-testid="button-logout"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
                <div className="w-px h-6 bg-border mx-1" />
                <ThemeToggle />
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="px-6 pb-0">
            <TabsList className="h-11 w-full justify-start bg-transparent p-0 gap-1">
              <TabsTrigger
                value="overview"
                data-testid="tab-overview"
                className="relative h-11 rounded-t-lg rounded-b-none border-b-2 border-transparent bg-transparent px-4 font-medium text-muted-foreground shadow-none transition-all data-[state=active]:border-emerald-500 data-[state=active]:text-foreground data-[state=active]:bg-muted/50 gap-2"
              >
                <Sparkles className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="map"
                data-testid="tab-map"
                className="relative h-11 rounded-t-lg rounded-b-none border-b-2 border-transparent bg-transparent px-4 font-medium text-muted-foreground shadow-none transition-all data-[state=active]:border-emerald-500 data-[state=active]:text-foreground data-[state=active]:bg-muted/50 gap-2"
              >
                <MapPin className="h-4 w-4" />
                Map View
              </TabsTrigger>
              <TabsTrigger
                value="analytics"
                data-testid="tab-analytics"
                className="relative h-11 rounded-t-lg rounded-b-none border-b-2 border-transparent bg-transparent px-4 font-medium text-muted-foreground shadow-none transition-all data-[state=active]:border-emerald-500 data-[state=active]:text-foreground data-[state=active]:bg-muted/50 gap-2"
              >
                <TrendingUp className="h-4 w-4" />
                Trends
              </TabsTrigger>
              <TabsTrigger
                value="forecast"
                data-testid="tab-forecast"
                className="relative h-11 rounded-t-lg rounded-b-none border-b-2 border-transparent bg-transparent px-4 font-medium text-muted-foreground shadow-none transition-all data-[state=active]:border-emerald-500 data-[state=active]:text-foreground data-[state=active]:bg-muted/50 gap-2"
              >
                <Brain className="h-4 w-4" />
                ML Forecast
              </TabsTrigger>
              <TabsTrigger
                value="data"
                data-testid="tab-data"
                className="relative h-11 rounded-t-lg rounded-b-none border-b-2 border-transparent bg-transparent px-4 font-medium text-muted-foreground shadow-none transition-all data-[state=active]:border-emerald-500 data-[state=active]:text-foreground data-[state=active]:bg-muted/50 gap-2"
              >
                <Database className="h-4 w-4" />
                Data Export
              </TabsTrigger>
            </TabsList>
          </div>
        </header>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {/* Overview Tab - Welcome & Feature Navigation */}
          <TabsContent value="overview" className="h-full mt-0 overflow-auto">
            <div className="min-h-full bg-gradient-to-br from-background via-background to-muted/30">
              {/* Hero Section */}
              <div className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-transparent to-teal-500/5" />
                <div className="relative px-8 py-12">
                  <div className="max-w-4xl">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-sm font-medium mb-4">
                      <Zap className="h-3.5 w-3.5" />
                      Environmental Intelligence Platform
                    </div>
                    <h1 className="text-4xl font-bold tracking-tight mb-4">
                      Welcome to CarbonSense
                    </h1>
                    <p className="text-lg text-muted-foreground max-w-2xl">
                      Monitor, analyze, and forecast carbon emissions across Lahore's neighborhoods.
                      Make data-driven decisions for a sustainable future.
                    </p>
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="px-8 -mt-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  <Card className="bg-gradient-to-br from-emerald-500/5 to-emerald-500/10 border-emerald-500/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Total Sources</p>
                          <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{areas.length}</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                          <MapPin className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-500/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Sectors Tracked</p>
                          <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">5</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                          <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-purple-500/5 to-purple-500/10 border-purple-500/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Years of Data</p>
                          <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">3+</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                          <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-amber-500/5 to-amber-500/10 border-amber-500/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Total Emissions</p>
                          <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">
                            {leaderboard.length > 0
                              ? `${(Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000000 * 10) / 10).toLocaleString()}M`
                              : '—'}
                          </p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                          <Activity className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">tons CO₂e</p>
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* Feature Cards Section */}
              <div className="px-8 pb-8">
                <div className="mb-6">
                  <h2 className="text-2xl font-bold mb-2">Platform Features</h2>
                  <p className="text-muted-foreground">
                    Tools for monitoring, analyzing, and forecasting carbon emissions
                  </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  {featureCards.map((feature) => {
                    const Icon = feature.icon;
                    return (
                      <Card
                        key={feature.id}
                        className={`group cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 border-2 ${feature.borderClass}`}
                        onClick={() => setActiveTab(feature.id)}
                      >
                        <CardContent className="pt-6">
                          <div className={`h-12 w-12 rounded-xl ${feature.bgClass} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                            <Icon className={`h-6 w-6 ${feature.textClass}`} />
                          </div>
                          <h3 className="font-semibold text-lg mb-1">{feature.title}</h3>
                          <p className="text-sm text-muted-foreground mb-4">{feature.description}</p>
                          <div className={`flex items-center gap-1 text-sm font-medium ${feature.textClass}`}>
                            <span>Explore</span>
                            <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {/* Sector Tags */}
                <Card className="bg-muted/30">
                  <CardContent className="pt-6">
                    <h3 className="font-semibold mb-4">Monitored Sectors</h3>
                    <div className="flex flex-wrap gap-3">
                      {[
                        { label: "Transport", color: "bg-blue-500", description: "Vehicle emissions, traffic" },
                        { label: "Industry", color: "bg-purple-500", description: "Manufacturing, factories" },
                        { label: "Energy", color: "bg-amber-500", description: "Power plants, electricity" },
                        { label: "Waste", color: "bg-orange-500", description: "Landfills, treatment" },
                        { label: "Buildings", color: "bg-pink-500", description: "Residential, commercial" },
                      ].map((sector) => (
                        <div
                          key={sector.label}
                          className="flex items-center gap-3 px-4 py-2 rounded-lg bg-card border hover:shadow-md transition-shadow"
                        >
                          <span className={`h-3 w-3 rounded-full ${sector.color}`} />
                          <div>
                            <span className="font-medium">{sector.label}</span>
                            <span className="text-xs text-muted-foreground ml-2">{sector.description}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="map" className="h-full mt-0 p-0">
            <div className="h-full grid grid-cols-1 lg:grid-cols-[1fr_380px]">
              <div className="relative h-full">
                <EmissionMap
                  areas={areas}
                  selectedAreaId={selectedAreaId}
                  onAreaSelect={setSelectedAreaId}
                  emissionData={emissionData}
                  maxEmission={maxEmission}
                />

                <div className="absolute top-4 right-4 max-w-xs space-y-4 z-[1000]">
                  <Card className="backdrop-blur-md bg-card/95">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Filters</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-muted-foreground">Sectors</label>
                        <SectorFilter
                          selectedSectors={selectedSectors}
                          onToggleSector={handleToggleSector}
                          onSelectAll={handleSelectAllSectors}
                          onClearAll={handleClearAllSectors}
                        />
                      </div>
                      <TimeControls
                        interval={timeInterval}
                        onIntervalChange={setTimeInterval}
                        dataType={dataType}
                        onDataTypeChange={setDataType}
                      />
                    </CardContent>
                  </Card>
                </div>

                <div className="absolute bottom-4 left-4 z-[1000]">
                  <MapLegend />
                </div>
              </div>

              <div className="border-l border-border bg-card flex flex-col">
                <div className="flex-1 overflow-hidden p-6">
                  {selectedAreaId && selectedArea ? (
                    <AreaDetailPanel
                      areaId={selectedAreaId}
                      areaName={selectedArea.name}
                      totalEmissions={selectedAreaEmissions}
                      trend="down"
                      trendPercentage={2.1}
                      sectorBreakdown={sectorBreakdown}
                      onClose={() => setSelectedAreaId(null)}
                      coordinates={selectedArea.coordinates}
                      selectedSectors={selectedSectors}
                    />
                  ) : (
                    <>
                      {leaderboardLoading ? (
                        <div className="flex items-center justify-center h-full">
                          <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                      ) : (
                        <Leaderboard
                          entries={leaderboard}
                          selectedAreaId={selectedAreaId}
                          onAreaSelect={setSelectedAreaId}
                          sectorTotals={sectorTotals}
                        />
                      )}
                    </>
                  )}
                </div>
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
                <Card>
                  <CardHeader>
                    <CardTitle>Monthly Emission Patterns</CardTitle>
                    <CardDescription>
                      Average emissions by month across all years - identify seasonal trends
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {selectedSectors.length === 0 ? (
                      <div className="py-12 text-center">
                        <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">Select sectors from the Map View to see monthly patterns</p>
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
              </div>

              {/* Year over Year Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                        <Database className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Data Source</p>
                        <p className="text-lg font-bold">Climate Trace</p>
                        <p className="text-xs text-muted-foreground">2021 - Present</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-emerald-500/5 to-emerald-500/10 border-emerald-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                        <MapPin className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Coverage</p>
                        <p className="text-lg font-bold">{areas.length} Sources</p>
                        <p className="text-xs text-muted-foreground">Lahore Division</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-amber-500/5 to-amber-500/10 border-amber-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                        <Activity className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Total Tracked</p>
                        <p className="text-lg font-bold">
                          {leaderboard.length > 0
                            ? `${(Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000000 * 10) / 10).toLocaleString()}M`
                            : '—'} tons
                        </p>
                        <p className="text-xs text-muted-foreground">CO₂ equivalent</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
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
                <Card className="bg-gradient-to-br from-purple-500/5 to-purple-500/10 border-purple-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-14 w-14 rounded-xl bg-purple-500/20 flex items-center justify-center">
                        <Brain className="h-7 w-7 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Model Type</p>
                        <p className="text-xl font-bold">SARIMA + Holt-Winters</p>
                        <p className="text-xs text-muted-foreground">Auto-selected best performer</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-14 w-14 rounded-xl bg-blue-500/20 flex items-center justify-center">
                        <TrendingUp className="h-7 w-7 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Forecast Horizon</p>
                        <p className="text-xl font-bold">12 Months</p>
                        <p className="text-xs text-muted-foreground">Future predictions</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-emerald-500/5 to-emerald-500/10 border-emerald-500/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      <div className="h-14 w-14 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                        <Activity className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Accuracy</p>
                        <p className="text-xl font-bold">~94%</p>
                        <p className="text-xs text-muted-foreground">R² on validation data</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Combined Historical + Forecast Chart */}
              <div className="mb-8">
                <Card>
                  <CardHeader>
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
                          <span className="text-sm text-muted-foreground">Historical</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-8 bg-amber-500 rounded border-2 border-dashed border-amber-600" />
                          <span className="text-sm text-muted-foreground">Forecast</span>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {selectedSectors.length === 0 ? (
                      <div className="py-12 text-center">
                        <Brain className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">Select sectors from the Map View to see forecasts</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {selectedSectors.map((sector) => {
                          const data = sectorChartData[sector];
                          if (!data || data.datasets.length === 0) return null;
                          return (
                            <div key={sector} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className={`h-2.5 w-2.5 rounded-full`} style={{ backgroundColor: sectorConfig[sector].historical }} />
                                  <span className="font-medium text-sm">{sectorConfig[sector].label}</span>
                                </div>
                                <Badge variant="outline" className="text-xs">
                                  95% confidence
                                </Badge>
                              </div>
                              <EmissionChart
                                title=""
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
              </div>

              {/* How It Works Section */}
              <Card>
                <CardHeader>
                  <CardTitle>How ML Forecasting Works</CardTitle>
                  <CardDescription>
                    Understanding our prediction methodology
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                        <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400">
                            STEP 1
                          </span>
                        </div>
                        <h3 className="font-semibold mb-1">Data Collection</h3>
                        <p className="text-sm text-muted-foreground">Climate Trace power emissions data (2021-2025) aggregated monthly with interpolation for gaps</p>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-purple-500/10 flex items-center justify-center">
                        <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400">
                            STEP 2
                          </span>
                        </div>
                        <h3 className="font-semibold mb-1">Model Training</h3>
                        <p className="text-sm text-muted-foreground">SARIMA and Holt-Winters models trained on 6-month validation split, best model auto-selected by R²</p>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                        <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                            STEP 3
                          </span>
                        </div>
                        <h3 className="font-semibold mb-1">Prediction</h3>
                        <p className="text-sm text-muted-foreground">Generate 12-month forecasts with 95% confidence intervals for proactive planning</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="data" className="h-full mt-0 p-0 overflow-auto">
            <DataExplorer />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
