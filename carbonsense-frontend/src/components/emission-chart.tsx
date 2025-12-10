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
      data: (number | null)[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      borderDash?: number[];
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
        maintainAspectRatio: false,
        spanGaps: true,
        interaction: {
          intersect: false,
          mode: 'index',
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              font: {
                family: "Inter, system-ui, sans-serif",
                size: 12,
                weight: 500,
              },
              padding: 20,
              usePointStyle: true,
              pointStyle: 'circle',
            },
          },
          tooltip: {
            backgroundColor: "rgba(17, 24, 39, 0.95)",
            titleFont: {
              family: "Inter, system-ui, sans-serif",
              size: 14,
              weight: 600,
            },
            bodyFont: {
              family: "Inter, system-ui, sans-serif",
              size: 13,
            },
            padding: 14,
            cornerRadius: 10,
            boxPadding: 6,
          },
        },
        scales: type === "line" || type === "bar" ? {
          y: {
            beginAtZero: true,
            border: {
              display: false,
            },
            grid: {
              color: "rgba(156, 163, 175, 0.15)",
            },
            ticks: {
              font: {
                family: "Inter, system-ui, sans-serif",
                size: 11,
              },
              padding: 8,
              color: "#6b7280",
            },
          },
          x: {
            border: {
              display: false,
            },
            grid: {
              display: false,
            },
            ticks: {
              font: {
                family: "Inter, system-ui, sans-serif",
                size: 11,
              },
              padding: 8,
              color: "#6b7280",
              maxRotation: 45,
              minRotation: 0,
            },
          },
        } : undefined,
        elements: {
          line: {
            tension: 0.35,
            borderWidth: 3,
          },
          point: {
            radius: 4,
            hoverRadius: 7,
            borderWidth: 2,
            backgroundColor: '#fff',
          },
          bar: {
            borderRadius: 6,
          },
          arc: {
            borderWidth: 2,
            borderColor: '#fff',
          },
        },
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
    <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold tracking-tight">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        <div
          className="relative w-full"
          style={{ height: type === "pie" || type === "doughnut" ? "320px" : "300px" }}
        >
          <canvas ref={canvasRef} data-testid={`chart-${title.toLowerCase().replace(/\s+/g, "-")}`} />
        </div>
      </CardContent>
    </Card>
  );
}
