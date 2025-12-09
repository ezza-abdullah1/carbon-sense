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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Leaf, Home, LogOut, Loader2 } from "lucide-react";
import type { Sector, TimeInterval, DataType } from "@shared/schema";
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
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>(["energy"]); // Start with energy since we have power data
  const [timeInterval, setTimeInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);

  // Fetch real data using hooks
  const { data: areas = [], isLoading: areasLoading } = useAreas();
  const { data: emissionData = {}, isLoading: emissionsLoading } = useLatestEmissions(dataType);
  const { data: leaderboard = [], isLoading: leaderboardLoading } = useLeaderboard(dataType);
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

  // Calculate max emission for map scaling
  const maxEmission = useMemo(() => {
    const values = Object.values(emissionData) as number[];
    return values.length > 0 ? Math.max(...values) : 1000000;
  }, [emissionData]);

  // Format time series data for charts
  const lineChartData = useMemo(() => {
    if (timeSeriesData.length === 0) {
      return {
        labels: [],
        datasets: []
      };
    }

    // Group data by date and sum across selected sectors
    const dateMap = new Map<string, number>();
    timeSeriesData.forEach((item: EmissionDataPoint) => {
      const date = new Date(item.date);
      const label = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

      let value = 0;
      if (selectedSectors.includes('transport')) value += item.transport;
      if (selectedSectors.includes('industry')) value += item.industry;
      if (selectedSectors.includes('energy')) value += item.energy;
      if (selectedSectors.includes('waste')) value += item.waste;
      if (selectedSectors.includes('buildings')) value += item.buildings;

      dateMap.set(label, (dateMap.get(label) || 0) + value);
    });

    const sortedEntries = Array.from(dateMap.entries()).sort((a, b) => {
      const dateA = new Date(a[0]);
      const dateB = new Date(b[0]);
      return dateA.getTime() - dateB.getTime();
    });

    return {
      labels: sortedEntries.map(([label]) => label),
      datasets: [
        {
          label: `${dataType === 'forecast' ? 'Forecasted' : 'Historical'} Emissions`,
          data: sortedEntries.map(([, value]) => Math.round(value / 1000)), // Convert to thousands
          backgroundColor: dataType === 'forecast'
            ? "rgba(245, 158, 11, 0.2)"
            : "rgba(96, 165, 250, 0.2)",
          borderColor: dataType === 'forecast'
            ? "hsl(45, 93%, 47%)"
            : "hsl(217, 91%, 60%)",
          borderWidth: 2,
        },
      ],
    };
  }, [timeSeriesData, selectedSectors, dataType]);

  // Sector breakdown pie chart
  const sectorPieData = useMemo(() => {
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

    const values = Object.values(totals);
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
          data: Object.values(totals).map(v => Math.round(v / 1000)), // Convert to thousands
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
  }, [timeSeriesData]);

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

  // Combined forecast trend chart (historical + forecast)
  const forecastTrendData = useMemo(() => {
    if (!combinedData) {
      return { labels: [], datasets: [] };
    }

    const { historical, forecast } = combinedData;

    // Helper to aggregate data by month
    const aggregateByMonth = (data: EmissionDataPoint[]) => {
      const monthMap = new Map<string, number>();
      data.forEach((item: EmissionDataPoint) => {
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

        let value = 0;
        if (selectedSectors.includes('transport')) value += item.transport;
        if (selectedSectors.includes('industry')) value += item.industry;
        if (selectedSectors.includes('energy')) value += item.energy;
        if (selectedSectors.includes('waste')) value += item.waste;
        if (selectedSectors.includes('buildings')) value += item.buildings;

        monthMap.set(label, (monthMap.get(label) || 0) + value);
      });
      return monthMap;
    };

    const historicalMap = aggregateByMonth(historical);
    const forecastMap = aggregateByMonth(forecast);

    // Get all unique labels and sort by date
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
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground">
              <Leaf className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold" data-testid="text-app-title">
                CarbonSense
              </h1>
              <p className="text-sm text-muted-foreground">
                Carbon emissions monitoring and forecasting platform
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-sm text-muted-foreground mr-4">
              {areas.length} Sources | {dataType === 'forecast' ? 'Forecast' : 'Historical'} Data
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLocation("/")}
              data-testid="button-home"
            >
              <Home className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              data-testid="button-logout"
            >
              <LogOut className="h-5 w-5" />
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <div className="border-b border-border px-6">
            <TabsList className="h-12">
              <TabsTrigger value="map" data-testid="tab-map">Map View</TabsTrigger>
              <TabsTrigger value="analytics" data-testid="tab-analytics">Analytics</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="map" className="flex-1 mt-0 p-0">
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
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="flex-1 mt-0 p-6 overflow-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="lg:col-span-2">
                <EmissionChart
                  title="Emission Forecast Trends (Historical vs Forecast)"
                  type="line"
                  data={forecastTrendData}
                />
              </div>
              <EmissionChart
                title={`${dataType === 'forecast' ? 'Forecasted' : 'Historical'} Emission Trends`}
                type="line"
                data={lineChartData}
              />
              <EmissionChart
                title="Sectoral Distribution"
                type="doughnut"
                data={sectorPieData}
              />
              <EmissionChart
                title="Top 5 Emission Sources"
                type="bar"
                data={areaBarData}
              />
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Key Insights</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Data Source</div>
                    <p className="text-sm text-muted-foreground">
                      Showing emissions data from {areas.length} sources across Pakistan.
                      Data includes both historical measurements and SARIMA-based forecasts.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Forecast Trend</div>
                    <p className="text-sm text-muted-foreground">
                      The top chart shows historical emissions (solid blue line) alongside
                      forecasted emissions (dashed orange line) for comparison.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Total Emissions</div>
                    <p className="text-sm text-muted-foreground">
                      {leaderboard.length > 0
                        ? `Total: ${Math.round((leaderboard as LeaderboardEntry[]).reduce((sum: number, e: LeaderboardEntry) => sum + e.emissions, 0) / 1000).toLocaleString()} thousand tons CO₂e`
                        : 'Loading...'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
