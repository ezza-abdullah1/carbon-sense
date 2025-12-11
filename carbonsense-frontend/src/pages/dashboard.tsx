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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Leaf, Home, LogOut, Loader2, Database } from "lucide-react";
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
  const [activeTab, setActiveTab] = useState<string>("map");
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

      // Historical line (solid blue-ish color)
      if (historicalMap.size > 0) {
        datasets.push({
          label: 'Historical',
          data: sortedLabels.map(label => {
            const val = historicalMap.get(label);
            return val ? Math.round(val / 1000) : null;
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
            return val ? Math.round(val / 1000) : null;
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
      return {
        label: sectorConfig[sector].label,
        data: months.map(m => {
          const val = sectorMap.get(m);
          return val ? Math.round(val / 1000) : 0;
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

  return (
    <div className="h-screen flex flex-col bg-background">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        {/* Combined Header with Tabs */}
        <header className="bg-card border-b border-border">
          <div className="px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-primary-foreground">
                  <Leaf className="h-4 w-4" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold leading-tight" data-testid="text-app-title">
                    CarbonSense
                  </h1>
                  <p className="text-xs text-muted-foreground">
                    Emissions monitoring & forecasting
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-xs text-muted-foreground mr-2 hidden sm:block">
                  {areas.length} Sources | {dataType === 'forecast' ? 'Forecast' : 'Historical'}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setLocation("/")}
                  data-testid="button-home"
                >
                  <Home className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={handleLogout}
                  data-testid="button-logout"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
                <ThemeToggle />
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="px-6">
            <TabsList className="h-10 w-full justify-start bg-transparent p-0 border-b-0">
              <TabsTrigger
                value="map"
                data-testid="tab-map"
                className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-primary data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                Map View
              </TabsTrigger>
              <TabsTrigger
                value="analytics"
                data-testid="tab-analytics"
                className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-primary data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                Analytics
              </TabsTrigger>
              <TabsTrigger
                value="data"
                data-testid="tab-data"
                className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-primary data-[state=active]:text-foreground data-[state=active]:shadow-none gap-1.5"
              >
                <Database className="h-4 w-4" />
                Data Explorer
              </TabsTrigger>
            </TabsList>
          </div>
        </header>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
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
                <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
                <p className="text-muted-foreground mt-1">
                  Comprehensive emission analysis across {areas.length} sources
                </p>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Total Sources</p>
                        <p className="text-3xl font-bold">{areas.length}</p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                        <Leaf className="h-6 w-6 text-blue-500" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Active Sectors</p>
                        <p className="text-3xl font-bold">{selectedSectors.length}<span className="text-lg text-muted-foreground">/5</span></p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
                        <div className="h-6 w-6 rounded-full bg-emerald-500" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Data Mode</p>
                        <p className="text-3xl font-bold capitalize">{dataType}</p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-amber-500/10 flex items-center justify-center">
                        <div className="h-3 w-3 rounded-full bg-amber-500 animate-pulse" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Total Emissions</p>
                        <p className="text-3xl font-bold">
                          {leaderboard.length > 0
                            ? `${(Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000000 * 10) / 10).toLocaleString()}M`
                            : '—'}
                        </p>
                      </div>
                      <p className="text-xs text-muted-foreground self-end">tons CO₂e</p>
                    </div>
                  </CardContent>
                </Card>
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

              {/* Sector Trends Section */}
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold">Sector Trends</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      Historical vs Forecasted emissions by sector
                    </p>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 rounded-full bg-blue-500" />
                      <span className="text-sm text-muted-foreground">Historical</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 rounded-full bg-amber-500" />
                      <span className="text-sm text-muted-foreground">Forecast</span>
                    </div>
                  </div>
                </div>

                {selectedSectors.length === 0 ? (
                  <Card className="p-12 text-center">
                    <Leaf className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-muted-foreground">Select at least one sector from the Map View to see trends</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {selectedSectors.map((sector) => {
                      const data = sectorChartData[sector];
                      if (!data || data.datasets.length === 0) return null;
                      return (
                        <EmissionChart
                          key={sector}
                          title={`${sectorConfig[sector].label} Emissions`}
                          type="line"
                          data={data}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
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
