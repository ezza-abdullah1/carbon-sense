import { useState, useMemo } from "react";
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
    <div className="p-6 space-y-6 bg-muted/30 min-h-full">
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
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Historical Records</p>
                <p className="text-2xl font-bold">{stats.historicalCount.toLocaleString()}</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                <Calendar className="h-5 w-5 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Forecast Records</p>
                <p className="text-2xl font-bold">{stats.forecastCount.toLocaleString()}</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Historical</p>
                <p className="text-2xl font-bold">{formatNumber(stats.historicalAvg)}</p>
                <p className="text-xs text-muted-foreground">tons CO₂e</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Forecast Trend</p>
                <div className="flex items-center gap-2">
                  <p className="text-2xl font-bold">
                    {stats.change > 0 ? "+" : ""}{stats.change.toFixed(1)}%
                  </p>
                  {stats.change > 0 ? (
                    <TrendingUp className="h-5 w-5 text-red-500" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-green-500" />
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Toggle */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            {/* View Mode Toggle */}
            <div className="space-y-2">
              <Label>View</Label>
              <div className="flex gap-1 bg-muted p-1 rounded-lg">
                <Button
                  variant={viewMode === "table" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("table")}
                >
                  <TableIcon className="h-4 w-4 mr-1" />
                  Table
                </Button>
                <Button
                  variant={viewMode === "graph" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("graph")}
                >
                  <BarChart3 className="h-4 w-4 mr-1" />
                  Graph
                </Button>
              </div>
            </div>

            {/* Data Type Filter */}
            <div className="space-y-2">
              <Label>Data Type</Label>
              <Select value={dataType} onValueChange={(v) => setDataType(v as DataType)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="both">All Data</SelectItem>
                  <SelectItem value="historical">Historical</SelectItem>
                  <SelectItem value="forecast">Forecast</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Area Filter */}
            <div className="space-y-2">
              <Label>Area</Label>
              <Select value={selectedArea} onValueChange={setSelectedArea}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
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
            <div className="space-y-2 flex-1 min-w-[200px]">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by area or date..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            {/* Results Count */}
            <div className="ml-auto">
              <Badge variant="secondary" className="text-sm">
                {filteredData.length.toLocaleString()} records
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Display */}
      {viewMode === "table" ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-card z-10">
                  <TableRow>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("date")}
                    >
                      <div className="flex items-center">
                        Date
                        <SortIcon field="date" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("area_name")}
                    >
                      <div className="flex items-center">
                        Area
                        <SortIcon field="area_name" />
                      </div>
                    </TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("transport")}
                    >
                      <div className="flex items-center justify-end">
                        Transport
                        <SortIcon field="transport" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("industry")}
                    >
                      <div className="flex items-center justify-end">
                        Industry
                        <SortIcon field="industry" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("energy")}
                    >
                      <div className="flex items-center justify-end">
                        Energy
                        <SortIcon field="energy" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("waste")}
                    >
                      <div className="flex items-center justify-end">
                        Waste
                        <SortIcon field="waste" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("buildings")}
                    >
                      <div className="flex items-center justify-end">
                        Buildings
                        <SortIcon field="buildings" />
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50 text-right"
                      onClick={() => handleSort("total")}
                    >
                      <div className="flex items-center justify-end">
                        Total
                        <SortIcon field="total" />
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredData.slice(0, 500).map((row, idx) => (
                    <TableRow key={`${row.area_id}-${row.date}-${idx}`}>
                      <TableCell className="font-mono text-sm">
                        {new Date(row.date).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </TableCell>
                      <TableCell className="font-medium max-w-[200px] truncate">
                        {row.area_name}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={row.type === "historical" ? "default" : "secondary"}
                          className={
                            row.type === "historical"
                              ? "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20"
                              : "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"
                          }
                        >
                          {row.type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(row.transport)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(row.industry)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(row.energy)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(row.waste)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(row.buildings)}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {formatNumber(row.total)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {filteredData.length > 500 && (
              <div className="p-4 text-center text-sm text-muted-foreground border-t">
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
    </div>
  );
}
