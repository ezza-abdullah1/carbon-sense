import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Filter, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmissionMap } from "@/features/emissions/emission-map";
import { MapLegend } from "@/features/emissions/map-legend";
import { Leaderboard } from "@/features/emissions/leaderboard";
import { SectorFilter } from "@/features/emissions/sector-filter";
import { AreaDetailPanel } from "@/features/area/area-detail-panel";
import { PointSourceDetailPanel } from "@/features/emissions/point-source-detail-panel";
import { DashboardLayout, useDashboard } from "./layout";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function MapContent() {
  const {
    selectedSectors,
    handleToggleSector,
    handleSelectAllSectors,
    handleClearAllSectors,
    dataType,
    setDataType,
    viewMode,
    setViewMode,
    selectedMonth,
    setSelectedMonth,
    availableMonths,
    selectedUCCode,
    setSelectedUCCode,
    selectedUCSummary,
    ucBoundaries,
    ucSummaries,
    ucLoading,
    ucLeaderboard,
    legendMin,
    legendMax,
    stats,
    pointSourcesBySector,
    allPointSources,
    selectedPlantName,
    setSelectedPlantName,
  } = useDashboard();

  const selectedPlant = useMemo(
    () => allPointSources.find((p) => p.source === selectedPlantName) ?? null,
    [allPointSources, selectedPlantName],
  );

  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

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

  return (
    <div className="h-full mt-0 p-0 relative">
      <div className="absolute inset-0 z-0">
        <EmissionMap
          ucBoundaries={ucBoundaries}
          ucSummaries={ucSummaries}
          selectedUCCode={selectedUCCode}
          onUCSelect={(code) => {
            // Selecting a UC clears any selected plant (panels are mutually exclusive)
            setSelectedPlantName(null);
            setSelectedUCCode(code);
          }}
          selectedSectors={selectedSectors}
          pointSourcesBySector={pointSourcesBySector}
          selectedPlantName={selectedPlantName}
          onPlantSelect={(name) => {
            // Selecting a plant clears any selected UC
            setSelectedUCCode(null);
            setSelectedPlantName(name);
          }}
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

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Data</label>
                      <div className="flex bg-black/5 dark:bg-white/5 p-1 rounded-lg">
                        {(["historical", "forecast"] as const).map((dt) => (
                          <div
                            key={dt}
                            className={`flex-1 text-center py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all ${
                              dataType === dt
                                ? "bg-white dark:bg-black/60 shadow-sm text-emerald-600 dark:text-emerald-400"
                                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                            }`}
                            onClick={() => {
                              setDataType(dt);
                              setSelectedMonth(dt === "forecast" ? "2026-12" : "2025-12");
                            }}
                          >
                            {dt === "historical" ? "Historical" : "Forecast"}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">View</label>
                      <div className="flex bg-black/5 dark:bg-white/5 p-1 rounded-lg">
                        {(["monthly", "yearly"] as const).map((vm) => (
                          <div
                            key={vm}
                            className={`flex-1 text-center py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all ${
                              viewMode === vm
                                ? "bg-white dark:bg-black/60 shadow-sm text-emerald-600 dark:text-emerald-400"
                                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                            }`}
                            onClick={() => setViewMode(vm)}
                          >
                            {vm === "monthly" ? "Monthly" : "Yearly"}
                          </div>
                        ))}
                      </div>
                    </div>

                    {viewMode === "monthly" && availableMonths.length > 0 && (() => {
                      const years = Array.from(new Set(availableMonths.map((m) => m.slice(0, 4)))).sort();
                      const selectedYear = selectedMonth.slice(0, 4);
                      const monthsInYear = availableMonths
                        .filter((m) => m.startsWith(selectedYear))
                        .sort();
                      return (
                        <div className="flex gap-2">
                          <select
                            className="flex-1 text-xs bg-white dark:bg-[#1a1a1a] border border-slate-300 dark:border-slate-600 rounded-md px-2 py-1.5 text-slate-800 dark:text-slate-200"
                            value={selectedYear}
                            onChange={(e) => {
                              const newYear = e.target.value;
                              const monthsForYear = availableMonths.filter((m) => m.startsWith(newYear));
                              setSelectedMonth(monthsForYear[monthsForYear.length - 1] || `${newYear}-12`);
                            }}
                          >
                            {years.map((y) => <option key={y} value={y}>{y}</option>)}
                          </select>
                          <select
                            className="flex-1 text-xs bg-white dark:bg-[#1a1a1a] border border-slate-300 dark:border-slate-600 rounded-md px-2 py-1.5 text-slate-800 dark:text-slate-200"
                            value={selectedMonth}
                            onChange={(e) => setSelectedMonth(e.target.value)}
                          >
                            {monthsInYear.map((m) => {
                              const mi = parseInt(m.slice(5, 7), 10) - 1;
                              return <option key={m} value={m}>{MONTH_NAMES[mi]}</option>;
                            })}
                          </select>
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>
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
          {selectedPlant ? (
            <PointSourceDetailPanel
              plant={selectedPlant}
              onClose={() => setSelectedPlantName(null)}
            />
          ) : selectedUCCode && selectedUCSummary ? (
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
    </div>
  );
}

export default function DashboardMapPage() {
  return (
    <DashboardLayout>
      <MapContent />
    </DashboardLayout>
  );
}
