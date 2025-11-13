import { useEffect, useRef } from "react";
import { Chart, ChartConfiguration, registerables } from "chart.js";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

Chart.register(...registerables);

interface EmissionChartProps {
  title: string;
  type: "line" | "bar" | "pie" | "doughnut";
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
    }[];
  };
}

export function EmissionChart({ title, type, data }: EmissionChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const config: ChartConfiguration = {
      type,
      data,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              font: {
                family: "Inter, sans-serif",
                size: 12,
              },
              padding: 12,
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            titleFont: {
              family: "Inter, sans-serif",
              size: 13,
            },
            bodyFont: {
              family: "IBM Plex Mono, monospace",
              size: 12,
            },
            padding: 12,
            cornerRadius: 6,
          },
        },
        scales: type === "line" || type === "bar" ? {
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
            ticks: {
              font: {
                family: "IBM Plex Mono, monospace",
                size: 11,
              },
            },
          },
          x: {
            grid: {
              display: false,
            },
            ticks: {
              font: {
                family: "Inter, sans-serif",
                size: 11,
              },
            },
          },
        } : undefined,
      },
    };

    chartRef.current = new Chart(canvasRef.current, config);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [type, data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative w-full" style={{ height: type === "pie" || type === "doughnut" ? "300px" : "250px" }}>
          <canvas ref={canvasRef} data-testid={`chart-${title.toLowerCase().replace(/\s+/g, "-")}`} />
        </div>
      </CardContent>
    </Card>
  );
}
