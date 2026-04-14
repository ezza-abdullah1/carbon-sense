import { useState } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X, TrendingUp, TrendingDown, Sparkles, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { RecommendationsModal } from "@/components/recommendations-modal";
import type { Sector, SubSectorData } from "@/lib/api";

// Keys to render as emission bars (tonnes)
const EMISSION_BAR_KEYS: Record<string, { label: string; color: string }> = {
  road:         { label: "Road",          color: "hsl(217, 91%, 60%)" },
  intl_avi:     { label: "Intl. Aviation",color: "hsl(280, 67%, 55%)" },
  railways:     { label: "Railways",      color: "hsl(142, 65%, 45%)" },
  dom_avi:      { label: "Dom. Aviation", color: "hsl(45,  93%, 47%)" },
  solid_waste:  { label: "Solid Waste",   color: "hsl(25,  95%, 53%)" },
  wastewater:   { label: "Wastewater",    color: "hsl(200, 80%, 50%)" },
  point_source: { label: "Point Sources", color: "hsl(338, 78%, 56%)" },
};

// Keys to render as info badges
const BADGE_KEYS = new Set(["risk_level", "data_quality_flag", "dominant_source", "geo_type"]);
// Skip entirely (percentage/meta fields)
const SKIP_KEYS = new Set(["road_pct", "point_pct", "intensity_t_per_km2", "rank_in_division", "pop_weight"]);

function SubSectorBreakdown({ data }: { data: SubSectorData }) {
  const bars = Object.entries(EMISSION_BAR_KEYS)
    .map(([key, cfg]) => ({ key, ...cfg, value: (data[key] as number) ?? 0 }))
    .filter(({ value }) => value > 0);

  const maxVal = Math.max(...bars.map(b => b.value), 1);

  const badges: string[] = [];
  BADGE_KEYS.forEach(k => { if (data[k]) badges.push(`${k.replace(/_/g, " ")}: ${data[k]}`); });
  const riskFlags = (data.risk_flags as string[] | undefined) ?? [];

  if (bars.length === 0 && badges.length === 0 && riskFlags.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Sub-sector Breakdown</h3>
      {bars.length > 0 && (
        <div className="space-y-3">
          {bars.map(({ key, label, color, value }) => (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{label}</span>
                <span className="font-mono text-muted-foreground">
                  {(value / 1000).toFixed(1)}kt
                </span>
              </div>
              <Progress
                value={(value / maxVal) * 100}
                className="h-2"
                style={{ "--progress-background": color } as React.CSSProperties}
              />
            </div>
          ))}
        </div>
      )}
      {(badges.length > 0 || riskFlags.length > 0) && (
        <div className="flex flex-wrap gap-1">
          {badges.map(b => (
            <Badge key={b} variant="secondary" className="text-xs capitalize">{b}</Badge>
          ))}
          {riskFlags.map(flag => (
            <Badge key={flag} variant="outline" className="text-xs">
              {flag.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

interface RecommendationsResponse {
  success: boolean;
  query: {
    area_name: string;
    area_id: string;
    sector: string;
    coordinates: { lat: number; lng: number };
  };
  recommendations: {
    summary: string;
    immediate_actions: string[];
    long_term_strategies: string[];
    policy_recommendations: string[];
    monitoring_metrics: string[];
    risk_factors: string[];
  };
  confidence?: {
    overall: number;
    evidence_strength: number;
    data_completeness: number;
    geographic_relevance: number;
  };
  raw_response: string;
  generated_at: string;
}

interface AreaDetailPanelProps {
  areaId: string;
  areaName: string;
  totalEmissions: number;
  trend: "up" | "down";
  trendPercentage: number;
  sectorBreakdown: {
    transport: number;
    industry: number;
    energy: number;
    waste: number;
    buildings: number;
  };
  onClose: () => void;
  coordinates?: [number, number];
  selectedSectors?: Sector[];
  subSectorData?: SubSectorData | null;
}

export function AreaDetailPanel({
  areaId,
  areaName,
  totalEmissions,
  trend,
  trendPercentage,
  sectorBreakdown,
  onClose,
  coordinates,
  selectedSectors = ["transport", "industry", "energy", "waste", "buildings"],
  subSectorData,
}: AreaDetailPanelProps) {
  const [, setLocation] = useLocation();
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [recommendationsData, setRecommendationsData] = useState<RecommendationsResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const maxSector = Math.max(...Object.values(sectorBreakdown));

  const handleViewAnalysis = () => {
    setLocation(`/area/${areaId}`);
  };

  const handleGenerateRecommendations = async () => {
    if (!coordinates) return;

    setIsLoadingRecommendations(true);

    try {
      // Determine the primary sector based on filter or highest emission
      const sectorValues = Object.entries(sectorBreakdown) as [Sector, number][];
      const primarySector = selectedSectors.length === 1
        ? selectedSectors[0]
        : sectorValues.sort((a, b) => b[1] - a[1])[0][0];

      const response = await fetch("/api/recommendations/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          coordinates: {
            lat: coordinates[0],
            lng: coordinates[1],
          },
          sector: primarySector,
          area_name: areaName,
          area_id: areaId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch recommendations");
      }

      const data = await response.json();

      // Handle the response - it might be an array
      const recommendationData = Array.isArray(data) ? data[0] : data;
      setRecommendationsData(recommendationData);
      setIsModalOpen(true);
    } catch (error) {
      console.error("Error fetching recommendations:", error);
    } finally {
      setIsLoadingRecommendations(false);
    }
  };

  const sectors = [
    { key: "transport", label: "Transport", color: "hsl(217, 91%, 60%)" },
    { key: "industry", label: "Industry", color: "hsl(280, 67%, 55%)" },
    { key: "energy", label: "Energy", color: "hsl(45, 93%, 47%)" },
    { key: "waste", label: "Waste", color: "hsl(25, 95%, 53%)" },
    { key: "buildings", label: "Buildings", color: "hsl(338, 78%, 56%)" },
  ];

  return (
    <Card className="w-full h-full min-h-0 flex flex-col bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-emerald-500/5 to-transparent pointer-events-none" />
      <CardHeader className="flex-row items-start justify-between space-y-0 px-6 pt-6 pb-4 relative z-10 border-b border-white/10 shrink-0">
        <div className="space-y-1">
          <CardTitle className="text-xl bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300">{areaName}</CardTitle>
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Emission Details</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          data-testid="button-close-detail"
        >
          <X className="h-5 w-5 opacity-70 hover:opacity-100" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 min-h-0 space-y-6 pt-6 px-6 overflow-y-auto overscroll-contain pb-6">
        <div className="space-y-3">
          <div className="flex items-baseline flex-wrap gap-x-2 gap-y-1">
            <span className="text-3xl font-mono font-bold">
              {totalEmissions.toFixed(2)}
            </span>
            <span className="text-sm text-muted-foreground">tons CO₂e</span>
          </div>
          
          <div className="flex items-center gap-2">
            {trend === "up" ? (
              <Badge variant="destructive" className="gap-1">
                <TrendingUp className="h-3 w-3" />
                +{trendPercentage}%
              </Badge>
            ) : (
              <Badge className="gap-1 bg-primary">
                <TrendingDown className="h-3 w-3" />
                -{trendPercentage}%
              </Badge>
            )}
            <span className="text-xs text-muted-foreground">vs last period</span>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Sectoral Breakdown</h3>
          <div className="space-y-3">
            {sectors.map((sector) => {
              const value = sectorBreakdown[sector.key as keyof typeof sectorBreakdown];
              const percentage = maxSector > 0 ? (value / maxSector) * 100 : 0;

              return (
                <div key={sector.key} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{sector.label}</span>
                    <span className="font-mono text-muted-foreground">
                      {value.toFixed(2)} tons
                    </span>
                  </div>
                  <Progress
                    value={percentage}
                    className="h-2"
                    style={{
                      "--progress-background": sector.color,
                    } as React.CSSProperties}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {subSectorData && <SubSectorBreakdown data={subSectorData} />}

        <div className="space-y-3">
          <Button
            className="w-full"
            onClick={handleViewAnalysis}
            data-testid="button-view-analysis"
          >
            View Full Analysis
          </Button>

          <Button
            className="w-full"
            variant="outline"
            onClick={handleGenerateRecommendations}
            disabled={isLoadingRecommendations || !coordinates}
            data-testid="button-generate-recommendations"
          >
            {isLoadingRecommendations ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating Recommendations...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Recommendations
              </>
            )}
          </Button>
        </div>
      </CardContent>

      <RecommendationsModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        data={recommendationsData}
        areaName={areaName}
      />
    </Card>
  );
}
