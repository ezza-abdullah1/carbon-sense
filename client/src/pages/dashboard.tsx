import { useState } from "react";
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
import { Leaf, Home, LogOut } from "lucide-react";
import type { Sector, TimeInterval, DataType, AreaInfo, LeaderboardEntry } from "@shared/schema";

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState<string>("map");
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>(["transport", "industry", "energy", "waste", "buildings"]);
  const [timeInterval, setTimeInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);
  
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

  const mockAreas: AreaInfo[] = [
    { id: "1", name: "Gulberg", coordinates: [31.5204, 74.3587], bounds: [[31.51, 74.34], [31.53, 74.37]] },
    { id: "2", name: "Model Town", coordinates: [31.4826, 74.3186], bounds: [[31.47, 74.30], [31.49, 74.33]] },
    { id: "3", name: "Johar Town", coordinates: [31.4697, 74.2728], bounds: [[31.46, 74.26], [31.48, 74.29]] },
    { id: "4", name: "DHA", coordinates: [31.4750, 74.4108], bounds: [[31.46, 74.40], [31.49, 74.42]] },
    { id: "5", name: "Iqbal Town", coordinates: [31.5140, 74.3127], bounds: [[31.50, 74.30], [31.53, 74.33]] },
    { id: "6", name: "Cantt", coordinates: [31.5656, 74.3597], bounds: [[31.55, 74.35], [31.58, 74.37]] },
    { id: "7", name: "Township", coordinates: [31.4556, 74.3478], bounds: [[31.44, 74.33], [31.47, 74.36]] },
  ];

  const historicalEmissionData: Record<string, number> = {
    "1": 1250.5,
    "2": 980.2,
    "3": 1450.8,
    "4": 1180.3,
    "5": 875.6,
    "6": 1050.4,
    "7": 790.3,
  };

  const forecastEmissionData: Record<string, number> = {
    "1": 1320.8,
    "2": 1015.5,
    "3": 1528.6,
    "4": 1240.2,
    "5": 920.3,
    "6": 1105.7,
    "7": 835.4,
  };

  const mockEmissionData = dataType === "forecast" ? forecastEmissionData : historicalEmissionData;

  const mockLeaderboard: LeaderboardEntry[] = [
    { rank: 1, areaId: "3", areaName: "Johar Town", emissions: 1450.8, trend: "up", trendPercentage: 5.2 },
    { rank: 2, areaId: "1", areaName: "Gulberg", emissions: 1250.5, trend: "down", trendPercentage: 2.1 },
    { rank: 3, areaId: "4", areaName: "DHA", emissions: 1180.3, trend: "stable", trendPercentage: 0.3 },
    { rank: 4, areaId: "6", areaName: "Cantt", emissions: 1050.4, trend: "down", trendPercentage: 1.5 },
    { rank: 5, areaId: "2", areaName: "Model Town", emissions: 980.2, trend: "down", trendPercentage: 3.4 },
    { rank: 6, areaId: "5", areaName: "Iqbal Town", emissions: 875.6, trend: "up", trendPercentage: 1.8 },
    { rank: 7, areaId: "7", areaName: "Township", emissions: 790.3, trend: "down", trendPercentage: 4.2 },
  ];

  const lineChartData = {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    datasets: [
      {
        label: "Transport",
        data: [250, 260, 245, 270, 265, 280, 275, 290, 285, 295, 300, 310],
        backgroundColor: "rgba(96, 165, 250, 0.2)",
        borderColor: "hsl(217, 91%, 60%)",
        borderWidth: 2,
      },
      {
        label: "Industry",
        data: [180, 190, 185, 200, 195, 210, 205, 220, 215, 225, 230, 240],
        backgroundColor: "rgba(192, 132, 252, 0.2)",
        borderColor: "hsl(280, 67%, 55%)",
        borderWidth: 2,
      },
    ],
  };

  const sectorPieData = {
    labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
    datasets: [
      {
        label: "Emissions by Sector",
        data: [35, 25, 20, 10, 10],
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

  const areaBarData = {
    labels: mockLeaderboard.slice(0, 5).map(e => e.areaName),
    datasets: [
      {
        label: "Total Emissions (tons CO₂e)",
        data: mockLeaderboard.slice(0, 5).map(e => e.emissions),
        backgroundColor: "hsl(142, 60%, 50%)",
      },
    ],
  };

  const selectedArea = mockAreas.find(a => a.id === selectedAreaId);

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
                Lahore Carbon Emissions Tracker
              </h1>
              <p className="text-sm text-muted-foreground">
                Real-time monitoring and forecasting platform
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
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
                  areas={mockAreas}
                  selectedAreaId={selectedAreaId}
                  onAreaSelect={setSelectedAreaId}
                  emissionData={mockEmissionData}
                  maxEmission={1500}
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
                      areaName={selectedArea.name}
                      totalEmissions={mockEmissionData[selectedAreaId]}
                      trend="down"
                      trendPercentage={2.1}
                      sectorBreakdown={{
                        transport: mockEmissionData[selectedAreaId] * 0.35,
                        industry: mockEmissionData[selectedAreaId] * 0.25,
                        energy: mockEmissionData[selectedAreaId] * 0.20,
                        waste: mockEmissionData[selectedAreaId] * 0.12,
                        buildings: mockEmissionData[selectedAreaId] * 0.08,
                      }}
                      onClose={() => setSelectedAreaId(null)}
                      onViewAnalysis={() => setActiveTab("analytics")}
                    />
                  ) : (
                    <Leaderboard
                      entries={mockLeaderboard}
                      selectedAreaId={selectedAreaId}
                      onAreaSelect={setSelectedAreaId}
                    />
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="flex-1 mt-0 p-6 overflow-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <EmissionChart
                title="Monthly Emission Trends"
                type="line"
                data={lineChartData}
              />
              <EmissionChart
                title="Sectoral Distribution"
                type="doughnut"
                data={sectorPieData}
              />
              <EmissionChart
                title="Top 5 Areas by Emissions"
                type="bar"
                data={areaBarData}
              />
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Key Insights</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Overall Trend</div>
                    <p className="text-sm text-muted-foreground">
                      Total emissions across Lahore show a 3.2% decrease compared to last year,
                      with significant reductions in the transport and energy sectors.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium">High Emission Areas</div>
                    <p className="text-sm text-muted-foreground">
                      Johar Town, Gulberg, and DHA continue to show the highest emission levels,
                      primarily due to high traffic density and industrial activity.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Forecast</div>
                    <p className="text-sm text-muted-foreground">
                      ML forecasts predict a potential 2.5% increase in transport emissions over
                      the next quarter if current trends continue.
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
