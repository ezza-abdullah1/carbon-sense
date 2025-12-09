import { useState } from 'react';
import { Leaderboard } from '../leaderboard';
import type { LeaderboardEntry } from '@shared/schema';

export default function LeaderboardExample() {
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);

  const mockEntries: LeaderboardEntry[] = [
    { rank: 1, areaId: "3", areaName: "Johar Town", emissions: 1450.8, trend: "up", trendPercentage: 5.2 },
    { rank: 2, areaId: "1", areaName: "Gulberg", emissions: 1250.5, trend: "down", trendPercentage: 2.1 },
    { rank: 3, areaId: "4", areaName: "DHA", emissions: 1180.3, trend: "stable", trendPercentage: 0.3 },
    { rank: 4, areaId: "2", areaName: "Model Town", emissions: 980.2, trend: "down", trendPercentage: 3.4 },
    { rank: 5, areaId: "5", areaName: "Iqbal Town", emissions: 875.6, trend: "up", trendPercentage: 1.8 },
  ];

  return (
    <div className="h-screen p-6">
      <Leaderboard
        entries={mockEntries}
        selectedAreaId={selectedAreaId}
        onAreaSelect={setSelectedAreaId}
      />
    </div>
  );
}
