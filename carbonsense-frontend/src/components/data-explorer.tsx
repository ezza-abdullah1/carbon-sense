import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart3,
  TableIcon,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Download,
  TrendingUp,
  TrendingDown,
  Calendar,
  Factory,
  Truck,
} from "lucide-react";
import { EmissionChart } from "@/components/emission-chart";
import { useAreas, useEmissions } from "@/hooks/use-emissions";
import type { EmissionDataPoint, AreaInfo } from "@/lib/api";

type ViewMode = "table" | "graph";
type DataType = "historical" | "forecast" | "both";
type SortField = "date" | "area_name" | "total" | "transport" | "industry" | "energy" | "waste" | "buildings";
type SortOrder = "asc" | "desc";

export function DataExplorer() {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [dataType, setDataType] = useState<DataType>("both");
  const [selectedArea, setSelectedArea] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Fetch data
  const { data: areas = [] } = useAreas();
  const { data: historicalData = [] } = useEmissions({ data_type: "historical" });
  const { data: forecastData = [] } = useEmissions({ data_type: "forecast" });

  // Combine and filter data
  const filteredData = useMemo(() => {
    let data: EmissionDataPoint[] = [];

    if (dataType === "historical" || dataType === "both") {
      data = [...data, ...historicalData];
    }
    if (dataType === "forecast" || dataType === "both") {
      data = [...data, ...forecastData];
    }

    // Filter by area
    if (selectedArea !== "all") {
      data = data.filter((d) => d.area_id === selectedArea);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      data = data.filter(
        (d) =>
          d.area_name.toLowerCase().includes(query) ||
          d.date.includes(query)
      );
    }

    // Sort data
    data.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      if (sortField === "date") {
        aVal = a.date;
        bVal = b.date;
      } else if (sortField === "area_name") {
        aVal = a.area_name;
        bVal = b.area_name;
      } else {
        aVal = a[sortField];
        bVal = b[sortField];
      }

      if (typeof aVal === "string") {
        return sortOrder === "asc"
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal);
      }
      return sortOrder === "asc" ? aVal - (bVal as number) : (bVal as number) - aVal;
    });

    return data;
  }, [historicalData, forecastData, dataType, selectedArea, searchQuery, sortField, sortOrder]);

  // Chart data for graph view
  const chartData = useMemo(() => {
    if (filteredData.length === 0) return { labels: [], datasets: [] };

    // Group by date
    const dateMap = new Map<string, { historical: number; forecast: number }>();

    filteredData.forEach((d) => {
      const existing = dateMap.get(d.date) || { historical: 0, forecast: 0 };
      if (d.type === "historical") {
        existing.historical += d.total;
      } else {
        existing.forecast += d.total;
      }
      dateMap.set(d.date, existing);
    });

    const sortedDates = Array.from(dateMap.keys()).sort();
    const labels = sortedDates.map((d) => {
      const date = new Date(d);
      return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    });

    const datasets = [];

    if (dataType === "historical" || dataType === "both") {
      datasets.push({
        label: "Historical",
        data: sortedDates.map((d) => Math.round((dateMap.get(d)?.historical || 0) / 1000)),
        backgroundColor: "rgba(59, 130, 246, 0.2)",
        borderColor: "hsl(217, 91%, 60%)",
        borderWidth: 2,
      });
    }

    if (dataType === "forecast" || dataType === "both") {
      datasets.push({
        label: "Forecast",
        data: sortedDates.map((d) => Math.round((dateMap.get(d)?.forecast || 0) / 1000)),
        backgroundColor: "rgba(245, 158, 11, 0.2)",
        borderColor: "hsl(45, 93%, 47%)",
        borderWidth: 2,
        borderDash: [5, 5],
      });
    }

    return { labels, datasets };
  }, [filteredData, dataType]);

  // Stats
  const stats = useMemo(() => {
    const historical = filteredData.filter((d) => d.type === "historical");
    const forecast = filteredData.filter((d) => d.type === "forecast");

    const historicalTotal = historical.reduce((sum, d) => sum + d.total, 0);
    const forecastTotal = forecast.reduce((sum, d) => sum + d.total, 0);

    const historicalAvg = historical.length > 0 ? historicalTotal / historical.length : 0;
    const forecastAvg = forecast.length > 0 ? forecastTotal / forecast.length : 0;

    const change = historicalAvg > 0 ? ((forecastAvg - historicalAvg) / historicalAvg) * 100 : 0;

    return {
      historicalCount: historical.length,
      forecastCount: forecast.length,
      historicalTotal,
      forecastTotal,
      historicalAvg,
      forecastAvg,
      change,
    };
  }, [filteredData]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4 ml-1 opacity-50" />;
    return sortOrder === "asc" ? (
      <ArrowUp className="h-4 w-4 ml-1" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1" />
    );
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toFixed(2);
  };

  const exportToCSV = () => {
    const headers = ["Date", "Area", "Type", "Transport", "Industry", "Energy", "Waste", "Buildings", "Total"];
    const rows = filteredData.map((d) => [
      d.date,
      d.area_name,
      d.type,
      d.transport,
      d.industry,
      d.energy,
      d.waste,
      d.buildings,
      d.total,
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `emissions-data-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
  };

  return (
    <div className="p-6 space-y-6 min-h-full w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Data Explorer</h1>
          <p className="text-muted-foreground mt-1">
            Browse and analyze emission data in detail
          </p>
        </div>
        <Button variant="outline" onClick={exportToCSV}>
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300 }}>
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden h-full">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />
            <CardContent className="pt-6 relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground font-medium">Historical Records</p>
                  <p className="text-2xl font-bold tracking-tight">{stats.historicalCount.toLocaleString()}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-blue-500/20 flex items-center justify-center shadow-inner">
                  <Calendar className="h-5 w-5 text-blue-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, delay: 0.05 }}>
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden h-full">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent pointer-events-none" />
            <CardContent className="pt-6 relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground font-medium">Forecast Records</p>
                  <p className="text-2xl font-bold tracking-tight">{stats.forecastCount.toLocaleString()}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-amber-500/20 flex items-center justify-center shadow-inner">
                  <TrendingUp className="h-5 w-5 text-amber-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, delay: 0.1 }}>
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden h-full">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
            <CardContent className="pt-6 relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground font-medium">Avg Historical</p>
                  <p className="text-2xl font-bold tracking-tight">{formatNumber(stats.historicalAvg)}</p>
                  <p className="text-xs text-muted-foreground">tons CO₂e</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-purple-500/20 flex items-center justify-center shadow-inner">
                  <Factory className="h-5 w-5 text-purple-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, delay: 0.15 }}>
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden h-full">
            <div className={`absolute inset-0 bg-gradient-to-br ${stats.change > 0 ? "from-red-500/10" : "from-emerald-500/10"} to-transparent pointer-events-none`} />
            <CardContent className="pt-6 relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground font-medium">Forecast Trend</p>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-2xl font-bold tracking-tight">
                      {stats.change > 0 ? "+" : ""}{stats.change.toFixed(1)}%
                    </p>
                    {stats.change > 0 ? (
                      <TrendingUp className="h-6 w-6 text-red-500/80 drop-shadow-sm" />
                    ) : (
                      <TrendingDown className="h-6 w-6 text-emerald-500/80 drop-shadow-sm" />
                    )}
                  </div>
                </div>
                <div className={`h-10 w-10 rounded-xl ${stats.change > 0 ? "bg-red-500/20" : "bg-emerald-500/20"} flex items-center justify-center shadow-inner`}>
                  {stats.change > 0 ? <TrendingUp className="h-5 w-5 text-red-500" /> : <TrendingDown className="h-5 w-5 text-emerald-500" />}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Filters and View Toggle */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl backdrop-saturate-150 border-black/5 dark:border-white/5 shadow-xl relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex flex-wrap items-end gap-5">
              {/* View Mode Toggle */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">View</Label>
                <div className="flex gap-1 bg-black/5 dark:bg-white/5 p-1 rounded-xl border border-black/5 dark:border-white/5 backdrop-blur-md">
                  <Button
                    variant={viewMode === "table" ? "secondary" : "ghost"}
                    size="sm"
                    className={`rounded-lg ${viewMode === "table" ? "shadow-sm bg-background dark:bg-background" : ""}`}
                    onClick={() => setViewMode("table")}
                  >
                    <TableIcon className="h-4 w-4 mr-1.5" />
                    Table
                  </Button>
                  <Button
                    variant={viewMode === "graph" ? "secondary" : "ghost"}
                    size="sm"
                    className={`rounded-lg ${viewMode === "graph" ? "shadow-sm bg-background dark:bg-background" : ""}`}
                    onClick={() => setViewMode("graph")}
                  >
                    <BarChart3 className="h-4 w-4 mr-1.5" />
                    Graph
                  </Button>
                </div>
              </div>

              {/* Data Type Filter */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Data Type</Label>
                <Select value={dataType} onValueChange={(v) => setDataType(v as DataType)}>
                  <SelectTrigger className="w-[150px] rounded-xl bg-black/5 dark:bg-white/5 border-black/5 dark:border-white/5 focus:ring-1 focus:ring-emerald-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-black/5 dark:border-white/5 shadow-xl backdrop-blur-2xl bg-white/90 dark:bg-[#0a0a0a]/90">
                    <SelectItem value="both">All Data</SelectItem>
                    <SelectItem value="historical">Historical</SelectItem>
                    <SelectItem value="forecast">Forecast</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Area Filter */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Area</Label>
                <Select value={selectedArea} onValueChange={setSelectedArea}>
                  <SelectTrigger className="w-[220px] rounded-xl bg-black/5 dark:bg-white/5 border-black/5 dark:border-white/5 focus:ring-1 focus:ring-emerald-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-black/5 dark:border-white/5 shadow-xl backdrop-blur-2xl bg-white/90 dark:bg-[#0a0a0a]/90">
                    <SelectItem value="all">All Areas</SelectItem>
                    {areas.map((area: AreaInfo) => (
                      <SelectItem key={area.id} value={area.id}>
                        {area.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Search */}
              <div className="space-y-2 flex-1 min-w-[240px]">
                <Label className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Search</Label>
                <div className="relative group">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-hover:text-emerald-500 transition-colors" />
                  <Input
                    placeholder="Search by area or date..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 bg-black/5 dark:bg-white/5 border-black/5 dark:border-white/5 focus-visible:ring-emerald-500 rounded-xl transition-all"
                  />
                </div>
              </div>

              {/* Results Count */}
              <div className="ml-auto flex items-center h-10">
                <Badge variant="secondary" className="text-xs font-mono bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10 px-3 py-1">
                  {filteredData.length.toLocaleString()} <span className="opacity-50 ml-1 font-sans">records</span>
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Data Display */}
      <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
        {viewMode === "table" ? (
          <Card className="bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-3xl backdrop-saturate-200 border-black/5 dark:border-white/5 shadow-2xl relative overflow-hidden">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="sticky top-0 z-10 bg-white/90 dark:bg-[#0a0a0a]/90 backdrop-blur-xl border-b border-black/5 dark:border-white/5">
                    <TableRow className="hover:bg-transparent border-none">
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6"
                        onClick={() => handleSort("date")}
                      >
                        <div className="flex items-center text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Date
                          <SortIcon field="date" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6"
                        onClick={() => handleSort("area_name")}
                      >
                        <div className="flex items-center text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Area
                          <SortIcon field="area_name" />
                        </div>
                      </TableHead>
                      <TableHead className="py-4 px-6 text-xs tracking-wider uppercase font-bold text-foreground opacity-80">Type</TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("transport")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Transport
                          <SortIcon field="transport" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("industry")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Industry
                          <SortIcon field="industry" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("energy")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Energy
                          <SortIcon field="energy" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("waste")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Waste
                          <SortIcon field="waste" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("buildings")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Buildings
                          <SortIcon field="buildings" />
                        </div>
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-emerald-600 transition-colors py-4 px-6 text-right"
                        onClick={() => handleSort("total")}
                      >
                        <div className="flex items-center justify-end text-xs tracking-wider uppercase font-bold text-foreground opacity-80">
                          Total
                          <SortIcon field="total" />
                        </div>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="divide-y divide-black/5 dark:divide-white/5">
                    {filteredData.slice(0, 500).map((row, idx) => (
                      <TableRow key={`${row.area_id}-${row.date}-${idx}`} className="hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors border-none group">
                        <TableCell className="font-mono text-[13px] px-6 py-3 text-muted-foreground group-hover:text-foreground transition-colors">
                          {new Date(row.date).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </TableCell>
                        <TableCell className="font-medium max-w-[200px] truncate px-6 py-3">
                          {row.area_name}
                        </TableCell>
                        <TableCell className="px-6 py-3">
                          <Badge
                            variant={row.type === "historical" ? "default" : "secondary"}
                            className={
                              row.type === "historical"
                                ? "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                                : "bg-amber-500/10 text-amber-600 border border-amber-500/20 border-dashed"
                            }
                          >
                            {row.type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono text-[13px] px-6 py-3 text-muted-foreground">{formatNumber(row.transport)}</TableCell>
                        <TableCell className="text-right font-mono text-[13px] px-6 py-3 text-muted-foreground">{formatNumber(row.industry)}</TableCell>
                        <TableCell className="text-right font-mono text-[13px] px-6 py-3 text-muted-foreground">{formatNumber(row.energy)}</TableCell>
                        <TableCell className="text-right font-mono text-[13px] px-6 py-3 text-muted-foreground">{formatNumber(row.waste)}</TableCell>
                        <TableCell className="text-right font-mono text-[13px] px-6 py-3 text-muted-foreground">{formatNumber(row.buildings)}</TableCell>
                        <TableCell className="text-right font-mono text-sm font-semibold px-6 py-3 text-foreground">
                          {formatNumber(row.total)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {filteredData.length > 500 && (
                <div className="p-4 text-center text-xs font-medium text-muted-foreground border-t border-black/5 dark:border-white/5 bg-black/[0.01] dark:bg-white/[0.01]">
                  Showing first 500 of {filteredData.length.toLocaleString()} records.
                  Use filters to narrow down results.
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
        <div className="grid grid-cols-1 gap-6">
          <EmissionChart
            title="Emission Trends Over Time"
            type="line"
            data={chartData}
          />

          {/* Sector Breakdown Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EmissionChart
              title="Sector Breakdown (Historical)"
              type="doughnut"
              data={{
                labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
                datasets: [
                  {
                    label: "Emissions",
                    data: [
                      Math.round(filteredData.filter(d => d.type === "historical").reduce((sum, d) => sum + d.transport, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "historical").reduce((sum, d) => sum + d.industry, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "historical").reduce((sum, d) => sum + d.energy, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "historical").reduce((sum, d) => sum + d.waste, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "historical").reduce((sum, d) => sum + d.buildings, 0) / 1000),
                    ],
                    backgroundColor: [
                      "hsl(217, 91%, 60%)",
                      "hsl(280, 67%, 55%)",
                      "hsl(45, 93%, 47%)",
                      "hsl(25, 95%, 53%)",
                      "hsl(338, 78%, 56%)",
                    ],
                  },
                ],
              }}
            />
            <EmissionChart
              title="Sector Breakdown (Forecast)"
              type="doughnut"
              data={{
                labels: ["Transport", "Industry", "Energy", "Waste", "Buildings"],
                datasets: [
                  {
                    label: "Emissions",
                    data: [
                      Math.round(filteredData.filter(d => d.type === "forecast").reduce((sum, d) => sum + d.transport, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "forecast").reduce((sum, d) => sum + d.industry, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "forecast").reduce((sum, d) => sum + d.energy, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "forecast").reduce((sum, d) => sum + d.waste, 0) / 1000),
                      Math.round(filteredData.filter(d => d.type === "forecast").reduce((sum, d) => sum + d.buildings, 0) / 1000),
                    ],
                    backgroundColor: [
                      "hsl(217, 91%, 60%)",
                      "hsl(280, 67%, 55%)",
                      "hsl(45, 93%, 47%)",
                      "hsl(25, 95%, 53%)",
                      "hsl(338, 78%, 56%)",
                    ],
                  },
                ],
              }}
            />
          </div>
        </div>
      )}
      </motion.div>
    </div>
  );
}
