import { DashboardLayout } from "./layout";
import { DataExplorer } from "@/components/data-explorer";

export default function DashboardDataPage() {
  return (
    <DashboardLayout>
      <div className="h-full mt-0 p-0 overflow-auto">
        <DataExplorer />
      </div>
    </DashboardLayout>
  );
}
