import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend } from "recharts";
import { motion } from "framer-motion";

interface EmissionChartProps {
  title: string;
  type: "line" | "bar" | "pie" | "doughnut";
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: (number | null)[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      borderDash?: number[];
    }[];
  };
}

export function EmissionChart({ title, type, data }: EmissionChartProps) {
  // Convert Chart.js data format to Recharts format
  const chartData = useMemo(() => {
    if (type === "pie" || type === "doughnut") {
      return data.labels.map((label, index) => {
        const dataset = data.datasets[0];
        const color = Array.isArray(dataset.backgroundColor)
          ? dataset.backgroundColor[index]
          : dataset.backgroundColor || "hsl(142, 65%, 45%)";
        
        return {
          name: label,
          value: dataset.data[index] || 0,
          color,
        };
      }).filter(item => item.value > 0);
    }

    return data.labels.map((label, index) => {
      const point: any = { name: label };
      data.datasets.forEach(dataset => {
        point[dataset.label] = dataset.data[index];
      });
      return point;
    });
  }, [data, type]);

  const renderChart = () => {
    const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#94a3b8' : '#64748b'; // slate-400 / slate-500
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
    const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)'; // slate-900 / white
    const tooltipColor = isDark ? '#f8fafc' : '#0f172a';
    const tooltipBorder = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        return (
          <div style={{ backgroundColor: tooltipBg, color: tooltipColor, borderColor: tooltipBorder }} className="px-4 py-3 rounded-xl border shadow-xl backdrop-blur-md">
            <p className="font-semibold text-sm mb-2">{label}</p>
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center gap-2 mb-1">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color || entry.payload?.color }} />
                <span className="text-xs text-muted-foreground">{entry.name}:</span>
                <span className="text-sm font-mono font-medium">{entry.value?.toLocaleString()}</span>
              </div>
            ))}
          </div>
        );
      }
      return null;
    };

    if (type === "line") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: textColor }} dy={10} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: textColor }} />
            <RechartsTooltip content={<CustomTooltip />} cursor={{ stroke: gridColor, strokeWidth: 2 }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
            {data.datasets.map((dataset, idx) => (
              <Line
                key={dataset.label}
                type="monotone"
                dataKey={dataset.label}
                stroke={dataset.borderColor as string}
                strokeWidth={3}
                strokeDasharray={dataset.borderDash ? "5 5" : undefined}
                dot={false}
                activeDot={{ r: 6, fill: dataset.borderColor as string, strokeWidth: 0 }}
                isAnimationActive={true}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      );
    }

    if (type === "bar") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: textColor }} dy={10} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: textColor }} />
            <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)' }} />
            {data.datasets.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />}
            {data.datasets.map((dataset, idx) => (
              <Bar
                key={dataset.label}
                dataKey={dataset.label}
                fill={dataset.backgroundColor as string || dataset.borderColor as string}
                radius={[4, 4, 0, 0]}
                isAnimationActive={true}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (type === "pie" || type === "doughnut") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={type === "doughnut" ? "65%" : 0}
              outerRadius="80%"
              paddingAngle={type === "doughnut" ? 3 : 0}
              dataKey="value"
              stroke="none"
              isAnimationActive={true}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <RechartsTooltip content={<CustomTooltip />} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} layout="vertical" verticalAlign="middle" align="right" />
          </PieChart>
        </ResponsiveContainer>
      );
    }

    return null;
  };

  return (
    <motion.div
      whileHover={{ y: -5 }}
      transition={{ duration: 0.3, type: "spring" }}
      className="h-full"
    >
      <Card className="relative h-full flex flex-col overflow-hidden border-white/20 dark:border-white/10 bg-white/50 dark:bg-black/40 backdrop-blur-xl shadow-2xl shadow-emerald-500/5 group">
        <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-transparent dark:from-white/5 dark:to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        
        {title && (
          <CardHeader className="pb-2 relative z-10 flex-none">
            <CardTitle className="text-base font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400">{title}</CardTitle>
          </CardHeader>
        )}
        
        <CardContent className={`${title ? 'pt-2' : 'pt-6'} flex-1 relative z-10 w-full min-h-0`}>
          <div
            className="w-full h-full"
            style={{ minHeight: type === "pie" || type === "doughnut" ? "280px" : "300px" }}
            data-testid={`chart-${title ? title.toLowerCase().replace(/\s+/g, "-") : type}`}
          >
            {renderChart()}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
