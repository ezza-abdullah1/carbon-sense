import { useState } from 'react';
import { TimeControls } from '../time-controls';
import type { TimeInterval, DataType } from '@shared/schema';

export default function TimeControlsExample() {
  const [interval, setInterval] = useState<TimeInterval>("monthly");
  const [dataType, setDataType] = useState<DataType>("historical");

  return (
    <div className="p-6 max-w-md">
      <TimeControls
        interval={interval}
        onIntervalChange={setInterval}
        dataType={dataType}
        onDataTypeChange={setDataType}
      />
    </div>
  );
}
