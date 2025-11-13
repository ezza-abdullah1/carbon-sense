import { EmissionChart } from '../emission-chart';

export default function EmissionChartExample() {
  const lineData = {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    datasets: [
      {
        label: "Transport",
        data: [250, 260, 245, 270, 265, 280],
        backgroundColor: "rgba(96, 165, 250, 0.2)",
        borderColor: "rgb(96, 165, 250)",
        borderWidth: 2,
      },
      {
        label: "Industry",
        data: [180, 190, 185, 200, 195, 210],
        backgroundColor: "rgba(192, 132, 252, 0.2)",
        borderColor: "rgb(192, 132, 252)",
        borderWidth: 2,
      },
    ],
  };

  const pieData = {
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

  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
      <EmissionChart title="Emission Trends" type="line" data={lineData} />
      <EmissionChart title="Sectoral Breakdown" type="doughnut" data={pieData} />
    </div>
  );
}
