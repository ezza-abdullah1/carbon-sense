import { useState } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X, Sparkles, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { RecommendationsModal } from "@/components/recommendations-modal";
import type { UCSummary, Sector } from "@/lib/api";
import { formatTonnes, getUCEmission } from "@/lib/map-utils";

// ---- Risk flag color mapping ----
const FLAG_COLORS: Record<string, string> = {
  high_absolute: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  high_intensity: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  aviation_plume_proximity: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  winter_smog_zone: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  rail_corridor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  road_dominant: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400",
};

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
  ucSummary: UCSummary;
  selectedSectors: Sector[];
  onClose: () => void;
}

export function AreaDetailPanel({
  ucSummary,
  selectedSectors,
  onClose,
}: AreaDetailPanelProps) {
  const [, setLocation] = useLocation();
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [recommendationsData, setRecommendationsData] = useState<RecommendationsResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const uc = ucSummary;
  const transport = uc.sectors.transport;
  const buildings = uc.sectors.buildings;
  const waste = uc.sectors.waste && typeof uc.sectors.waste === 'object' ? uc.sectors.waste : null;
  const industry = uc.sectors.industry && typeof uc.sectors.industry === 'object' ? uc.sectors.industry : null;
  const totalEmission = getUCEmission(uc, selectedSectors);

  const handleViewAnalysis = () => {
    setLocation(`/area/${uc.uc_code}`);
  };

  const handleGenerateRecommendations = async () => {
    setIsLoadingRecommendations(true);
    try {
      const response = await fetch("/api/recommendations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          coordinates: { lat: uc.centroid[0], lng: uc.centroid[1] },
          sector: selectedSectors[0] || "transport",
          area_name: uc.uc_name,
          area_id: uc.uc_code,
        }),
      });
      if (!response.ok) throw new Error("Failed to fetch recommendations");
      const data = await response.json();
      setRecommendationsData(Array.isArray(data) ? data[0] : data);
      setIsModalOpen(true);
    } catch (error) {
      console.error("Error fetching recommendations:", error);
    } finally {
      setIsLoadingRecommendations(false);
    }
  };

  // ---- Sector breakdown for progress bars ----
  const sectorValues = [
    { key: "transport", label: "Transport", color: "hsl(25, 95%, 53%)", value: transport?.display_t ?? 0 },
    { key: "buildings", label: "Buildings", color: "hsl(338, 78%, 56%)", value: buildings?.display_t ?? 0 },
    { key: "energy", label: "Energy", color: "hsl(45, 93%, 47%)", value: typeof uc.sectors.energy === 'number' ? uc.sectors.energy : 0 },
    { key: "industry", label: "Industry", color: "hsl(280, 67%, 55%)", value: industry?.display_t ?? 0 },
    { key: "waste", label: "Waste", color: "hsl(200, 80%, 50%)", value: waste?.display_t ?? 0 },
  ].filter(s => selectedSectors.includes(s.key as Sector));

  const maxSectorVal = Math.max(...sectorValues.map(s => s.value), 1);

  // ---- Transport sub-sector bars ----
  const transportSubs = transport ? [
    { label: "Road", value: transport.road_annual_t, color: "hsl(217, 91%, 60%)" },
    { label: "Intl. Aviation", value: transport.intl_avi_annual_t, color: "hsl(280, 67%, 55%)" },
    { label: "Dom. Aviation", value: transport.dom_avi_annual_t, color: "hsl(45, 93%, 47%)" },
    { label: "Railways", value: transport.rail_annual_t, color: "hsl(142, 65%, 45%)" },
  ].filter(s => s.value > 0) : [];

  const maxTransportSub = Math.max(...transportSubs.map(s => s.value), 1);

  // ---- Buildings sub-sector bars ----
  const buildingSubs = buildings ? [
    { label: "Residential", value: buildings.residential_t, color: "hsl(338, 78%, 56%)" },
    { label: "Non-residential", value: buildings.non_residential_t, color: "hsl(200, 80%, 50%)" },
  ].filter(s => s.value > 0) : [];

  const maxBuildingSub = Math.max(...buildingSubs.map(s => s.value), 1);

  // ---- Risk flags (transport + buildings) ----
  const riskFlags: string[] = [
    ...(transport?.risk_flags ?? []),
    ...Object.entries(buildings?.risk ?? {})
      .filter(([, v]) => v === true)
      .map(([k]) => k),
  ];

  return (
    <Card className="w-full h-full min-h-0 flex flex-col bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border border-black/10 dark:border-white/10 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-emerald-500/5 to-transparent pointer-events-none" />
      <CardHeader className="flex-row items-start justify-between space-y-0 px-5 pt-5 pb-3 relative z-10 border-b border-white/10 shrink-0">
        <div className="space-y-0.5">
          <CardTitle className="text-lg bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300">
            {uc.uc_name}
          </CardTitle>
          <p className="text-xs text-muted-foreground font-mono">{uc.uc_code}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} data-testid="button-close-detail">
          <X className="h-5 w-5 opacity-70 hover:opacity-100" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 min-h-0 space-y-5 pt-4 px-5 overflow-y-auto overscroll-contain pb-5">
        {/* ---- Stats Table (Folium-style) ---- */}
        <div className="rounded-lg border border-border/50 overflow-hidden">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-border/30">
              <StatsRow
                label={uc.view_mode === 'monthly' && uc.month_label
                  ? `CO\u2082e (${uc.month_label})`
                  : 'Annual CO\u2082e'}
                value={<b>{formatTonnes(totalEmission)}</b>}
              />
              {transport && (
                <>
                  <StatsRow label="Road share" value={<b>{transport.road_pct.toFixed(1)}%</b>} />
                  <StatsRow label="Intensity" value={<b>{Math.round(transport.intensity_t_per_km2).toLocaleString()} t/km\u00B2</b>} />
                </>
              )}
              <StatsRow label="Area" value={`${uc.area_km2.toFixed(1)} km\u00B2`} />
              {transport && (
                <>
                  <StatsRow label="District rank" value={`#${transport.rank_in_division}/151`} />
                  <StatsRow
                    label="CI (annual)"
                    value={`${Math.round(transport.ci_lower_annual_t).toLocaleString()}\u2013${Math.round(transport.ci_upper_annual_t).toLocaleString()} t`}
                  />
                  <StatsRow label="Road weight" value={`${(transport.road_weight * 100).toFixed(2)}%`} />
                  <StatsRow label="Rail weight" value={`${(transport.rail_weight * 100).toFixed(2)}%`} />
                </>
              )}
              {buildings && (
                <StatsRow
                  label="Bldg intensity"
                  value={`${Math.round(buildings.intensity_t_km2).toLocaleString()} t/km\u00B2`}
                />
              )}
            </tbody>
          </table>
        </div>

        {/* ---- Risk Flags ---- */}
        {riskFlags.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Flags</h3>
            <div className="flex flex-wrap gap-1.5">
              {riskFlags.map((flag) => (
                <Badge
                  key={flag}
                  variant="secondary"
                  className={`text-[10px] font-medium px-2 py-0.5 ${FLAG_COLORS[flag] ?? ""}`}
                >
                  {flag.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* ---- Sector Breakdown ---- */}
        {sectorValues.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sector Breakdown</h3>
            <div className="space-y-2.5">
              {sectorValues.map((sector) => (
                <div key={sector.key} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{sector.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTonnes(sector.value)}
                    </span>
                  </div>
                  <Progress
                    value={(sector.value / maxSectorVal) * 100}
                    className="h-2"
                    style={{ "--progress-background": sector.color } as React.CSSProperties}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---- Transport Sub-sectors ---- */}
        {selectedSectors.includes("transport") && transportSubs.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Transport Sub-sectors</h3>
            <div className="space-y-2.5">
              {transportSubs.map((sub) => (
                <div key={sub.label} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{sub.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTonnes(sub.value)}
                    </span>
                  </div>
                  <Progress
                    value={(sub.value / maxTransportSub) * 100}
                    className="h-1.5"
                    style={{ "--progress-background": sub.color } as React.CSSProperties}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---- Buildings Sub-sectors ---- */}
        {selectedSectors.includes("buildings") && buildingSubs.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Buildings Sub-sectors</h3>
            <div className="space-y-2.5">
              {buildingSubs.map((sub) => (
                <div key={sub.label} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{sub.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTonnes(sub.value)}
                    </span>
                  </div>
                  <Progress
                    value={(sub.value / maxBuildingSub) * 100}
                    className="h-1.5"
                    style={{ "--progress-background": sub.color } as React.CSSProperties}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---- Waste Sub-sectors ---- */}
        {selectedSectors.includes("waste") && waste && waste.annual_t > 0 && (() => {
          const wasteSubs = [
            { label: "Point Sources", value: waste.point_source_t, color: "hsl(338, 78%, 56%)" },
            { label: "Solid Waste", value: waste.solid_waste_t, color: "hsl(25, 95%, 53%)" },
            { label: "Wastewater", value: waste.wastewater_t, color: "hsl(200, 80%, 50%)" },
          ].filter(s => s.value > 0);
          const maxWasteSub = Math.max(...wasteSubs.map(s => s.value), 1);
          if (wasteSubs.length === 0) return null;
          return (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Waste Sub-sectors</h3>
              <div className="space-y-2.5">
                {wasteSubs.map((sub) => (
                  <div key={sub.label} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{sub.label}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {formatTonnes(sub.value)}
                      </span>
                    </div>
                    <Progress
                      value={(sub.value / maxWasteSub) * 100}
                      className="h-1.5"
                      style={{ "--progress-background": sub.color } as React.CSSProperties}
                    />
                  </div>
                ))}
                {waste.risk_level && (
                  <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
                    Risk: {waste.risk_level}
                  </Badge>
                )}
              </div>
            </div>
          );
        })()}

        {/* Monthly sparkline removed — monthly data now shown via map toggle */}

        {/* ---- Action Buttons ---- */}
        <div className="space-y-3 pt-1">
          <Button
            className="w-full"
            variant="outline"
            onClick={handleGenerateRecommendations}
            disabled={isLoadingRecommendations}
            data-testid="button-generate-recommendations"
          >
            {isLoadingRecommendations ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
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
        areaName={uc.uc_name}
      />
    </Card>
  );
}

// ---- Helper: Stats table row ----
function StatsRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td className="py-1.5 px-3 text-muted-foreground whitespace-nowrap">{label}</td>
      <td className="py-1.5 px-3 text-right font-mono">{value}</td>
    </tr>
  );
}

// ---- Helper: Monthly bar chart ----
function MonthlyBars({ values }: { values: number[] }) {
  const months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
  const max = Math.max(...values, 1);
  const min = Math.min(...values);

  return (
    <div className="flex items-end gap-0.5 h-12">
      {values.map((v, i) => {
        const pct = max > min ? ((v - min) / (max - min)) * 100 : 50;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
            <div
              className="w-full rounded-t-sm bg-orange-400/70 dark:bg-orange-500/60 transition-all"
              style={{ height: `${Math.max(pct, 8)}%` }}
              title={`${months[i]}: ${Math.round(v).toLocaleString()} t`}
            />
            <span className="text-[8px] text-muted-foreground leading-none">{months[i]}</span>
          </div>
        );
      })}
    </div>
  );
}
