import { createContext, useContext, useMemo, useState } from "react";
import { Link, useLocation } from "wouter";
import { motion } from "framer-motion";
import {
  Brain,
  Database,
  Home,
  Leaf,
  LogOut,
  MapPin,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  useAreas,
  useCombinedTimeSeriesData,
  useLatestEmissions,
  useLeaderboard,
  usePowerPlants,
  useStats,
  useUCBoundaries,
  useUCSummaries,
} from "@/hooks/use-emissions";
import type { LeaderboardEntry, Sector, DataType } from "@shared/schema";
import type { AreaInfo, PowerPlant, Stats, TimeInterval, UCSummary } from "@/lib/api";
import { getUCEmission } from "@/lib/map-utils";

type ViewMode = "monthly" | "yearly";

// Shape every dashboard page can read via `useDashboard()`. Filters and
// per-area selections live here so navigating between pages preserves
// what the user picked. The shared queries (areas, leaderboard, etc.)
// are also exposed so the page components don't each refetch them —
// React Query caches by key, but having a single call site is cleaner.
interface DashboardContextValue {
  // Filter state
  selectedSectors: Sector[];
  setSelectedSectors: (s: Sector[]) => void;
  dataType: DataType;
  setDataType: (t: DataType) => void;
  timeInterval: TimeInterval;
  setTimeInterval: (i: TimeInterval) => void;

  // Map page selections (shared so a returning navigator keeps state)
  selectedAreaId: string | null;
  setSelectedAreaId: (id: string | null) => void;
  selectedUCCode: string | null;
  setSelectedUCCode: (c: string | null) => void;
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  selectedMonth: string;
  setSelectedMonth: (m: string) => void;

  // Shared queries
  areas: AreaInfo[];
  areasLoading: boolean;
  stats: Stats | undefined;
  emissionData: Record<string, number>;
  emissionsLoading: boolean;
  leaderboard: LeaderboardEntry[];
  leaderboardLoading: boolean;
  ucBoundaries: GeoJSON.FeatureCollection | undefined;
  ucSummaries: UCSummary[];
  ucLoading: boolean;
  selectedUCSummary: UCSummary | null;
  ucLeaderboard: LeaderboardEntry[];
  legendMin: number;
  legendMax: number;
  availableMonths: string[];
  combinedData: { historical: any[]; forecast: any[] } | undefined;
  powerPlants: PowerPlant[];
  selectedPlantName: string | null;
  setSelectedPlantName: (name: string | null) => void;

  // Cross-page actions
  handleToggleSector: (s: Sector) => void;
  handleSelectAllSectors: () => void;
  handleClearAllSectors: () => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function useDashboard(): DashboardContextValue {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error("useDashboard must be used inside <DashboardLayout>");
  }
  return ctx;
}

// Items appear in the sidebar in this order. `href` doubles as the active-
// detection key — we match against the current URL prefix.
const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: Sparkles },
  { href: "/dashboard/map", label: "Map View", icon: MapPin },
  { href: "/dashboard/trends", label: "Trends", icon: TrendingUp },
  { href: "/dashboard/forecast", label: "ML Forecast", icon: Brain },
  { href: "/dashboard/data", label: "Data Export", icon: Database },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [location, setLocation] = useLocation();
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);

  // ─── Shared filter state ───
  const [selectedSectors, setSelectedSectors] = useState<Sector[]>([
    "transport",
    "industry",
    "energy",
    "waste",
    "buildings",
  ]);
  const [timeInterval, setTimeInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);
  const [selectedUCCode, setSelectedUCCode] = useState<string | null>(null);
  const [selectedPlantName, setSelectedPlantName] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("yearly");
  const [selectedMonth, setSelectedMonth] = useState<string>("2025-12");

  // ─── Shared queries (single fetch site, pages just read context) ───
  const { data: areas = [], isLoading: areasLoading } = useAreas();
  const { data: stats } = useStats();
  const { data: emissionData = {}, isLoading: emissionsLoading } =
    useLatestEmissions(dataType, selectedSectors, timeInterval);
  const { data: leaderboard = [], isLoading: leaderboardLoading } =
    useLeaderboard(dataType, selectedSectors, timeInterval);
  const { data: combinedData } = useCombinedTimeSeriesData(
    selectedAreaId || undefined,
  );
  const { data: ucBoundaries } = useUCBoundaries();
  const { data: ucSummaries = [], isLoading: ucLoading } = useUCSummaries(
    dataType,
    viewMode,
    viewMode === "monthly" ? selectedMonth : undefined,
  );
  const { data: powerPlants = [] } = usePowerPlants(dataType);

  const availableMonths = useMemo(() => {
    if (!ucSummaries || ucSummaries.length === 0) return [];
    return ucSummaries[0]?.available_months ?? [];
  }, [ucSummaries]);

  const selectedUCSummary = useMemo(() => {
    if (!selectedUCCode || !ucSummaries) return null;
    return (
      ucSummaries.find((uc: UCSummary) => uc.uc_code === selectedUCCode) ?? null
    );
  }, [selectedUCCode, ucSummaries]);

  // UC-based leaderboard (151 UCs, not duplicated per sector)
  const ucLeaderboard = useMemo<LeaderboardEntry[]>(() => {
    if (!ucSummaries || ucSummaries.length === 0) return [];
    return ucSummaries
      .map((uc: UCSummary) => ({
        rank: 0,
        areaId: uc.uc_code,
        areaName: uc.uc_name,
        emissions: getUCEmission(uc, selectedSectors),
        trend: "stable" as const,
        trendPercentage: 0,
      }))
      .filter((e) => e.emissions > 0)
      .sort((a, b) => b.emissions - a.emissions)
      .map((entry, index) => ({ ...entry, rank: index + 1 }));
  }, [ucSummaries, selectedSectors]);

  const [legendMin, legendMax] = useMemo(() => {
    if (!ucSummaries || ucSummaries.length === 0) return [0, 0];
    const values = ucSummaries
      .map((uc: UCSummary) => getUCEmission(uc, selectedSectors))
      .filter((v) => v > 0);
    if (values.length === 0) return [0, 0];
    return [Math.min(...values), Math.max(...values)];
  }, [ucSummaries, selectedSectors]);

  // ─── Sector toggle helpers ───
  const handleToggleSector = (sector: Sector) => {
    setSelectedSectors((prev) =>
      prev.includes(sector)
        ? prev.filter((s) => s !== sector)
        : [...prev, sector],
    );
  };
  const handleSelectAllSectors = () =>
    setSelectedSectors(["transport", "industry", "energy", "waste", "buildings"]);
  const handleClearAllSectors = () => setSelectedSectors([]);

  const handleLogout = () => {
    localStorage.removeItem("user");
    setLocation("/");
  };

  const ctxValue: DashboardContextValue = {
    selectedSectors,
    setSelectedSectors,
    dataType,
    setDataType,
    timeInterval,
    setTimeInterval,
    selectedAreaId,
    setSelectedAreaId,
    selectedUCCode,
    setSelectedUCCode,
    viewMode,
    setViewMode,
    selectedMonth,
    setSelectedMonth,
    areas,
    areasLoading,
    stats,
    emissionData,
    emissionsLoading,
    leaderboard,
    leaderboardLoading,
    ucBoundaries,
    ucSummaries,
    ucLoading,
    selectedUCSummary,
    ucLeaderboard,
    legendMin,
    legendMax,
    availableMonths,
    combinedData,
    powerPlants,
    selectedPlantName,
    setSelectedPlantName,
    handleToggleSector,
    handleSelectAllSectors,
    handleClearAllSectors,
  };

  // The "active" sidebar item is whichever nav href the URL starts with.
  // Sort longer hrefs first so /dashboard/map matches before /dashboard.
  const sortedNav = [...NAV_ITEMS].sort((a, b) => b.href.length - a.href.length);
  const activeHref = sortedNav.find((item) => location.startsWith(item.href))
    ?.href ?? "/dashboard";

  return (
    <DashboardContext.Provider value={ctxValue}>
      <div className="h-screen flex bg-background overflow-hidden">
        {/* Hover-activated Sidebar */}
        <motion.aside
          initial={false}
          animate={{ width: isSidebarExpanded ? 260 : 80 }}
          onMouseEnter={() => setIsSidebarExpanded(true)}
          onMouseLeave={() => setIsSidebarExpanded(false)}
          className="h-full bg-white dark:bg-[#030303] border-r border-black/5 dark:border-white/5 shadow-2xl z-[100] relative flex flex-col transition-all duration-300 ease-in-out backdrop-blur-3xl"
        >
          {/* Logo */}
          <div className="p-6 mb-4 flex items-center gap-4 overflow-hidden">
            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25">
              <Leaf className="h-5 w-5" />
            </div>
            <motion.div
              animate={{
                opacity: isSidebarExpanded ? 1 : 0,
                x: isSidebarExpanded ? 0 : -10,
              }}
              className="whitespace-nowrap"
            >
              <h1 className="text-xl font-bold tracking-tight">CarbonSense</h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
                Intelligence
              </p>
            </motion.div>
          </div>

          {/* Nav */}
          <nav className="flex-1 px-3 space-y-2">
            <div className="flex flex-col items-stretch h-auto p-0 gap-2">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = item.href === activeHref;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`
                      w-full relative flex items-center gap-4 p-3 rounded-xl transition-all duration-300 border-none shadow-none text-left justify-start
                      ${
                        isActive
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : "text-muted-foreground hover:bg-black/5 dark:hover:bg-white/5 hover:text-foreground"
                      }
                    `}
                  >
                    <div className="flex-shrink-0 w-6 flex items-center justify-center">
                      <Icon
                        className={`h-5 w-5 transition-transform duration-300 ${
                          isActive ? "scale-110" : ""
                        }`}
                      />
                    </div>
                    <motion.span
                      animate={{
                        opacity: isSidebarExpanded ? 1 : 0,
                        x: isSidebarExpanded ? 0 : -10,
                      }}
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
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* Bottom actions */}
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
              animate={{
                x: [0, 100, -50, 0],
                y: [0, -100, 50, 0],
                scale: [1, 1.2, 0.9, 1],
              }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-emerald-500/10 dark:bg-emerald-600/5 rounded-full filter blur-[120px] opacity-100"
            />
          </div>

          <div className="flex-1 overflow-hidden relative z-10">
            {children}
          </div>
        </div>
      </div>
    </DashboardContext.Provider>
  );
}
