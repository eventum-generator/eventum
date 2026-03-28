import { FC } from 'react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

import classes from './SummaryBar.module.css';

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

interface SummaryBarProps {
  stats: GeneratorStats;
}

export const SummaryBar: FC<SummaryBarProps> = ({ stats }) => {
  const items = [
    { label: 'Instance', value: stats.id },
    { label: 'Start time', value: new Date(stats.start_time).toLocaleString() },
    { label: 'Uptime', value: formatUptime(stats.uptime) },
    { label: 'Generated', value: stats.total_generated },
    { label: 'Written', value: stats.total_written },
    { label: 'Input EPS', value: stats.input_eps.toFixed(2) },
    { label: 'Output EPS', value: stats.output_eps.toFixed(2) },
  ];

  return (
    <div className={classes.bar}>
      {items.map((item) => (
        <div key={item.label} className={classes.item}>
          <div className={classes.label}>{item.label}</div>
          <div className={classes.value}>{item.value}</div>
        </div>
      ))}
    </div>
  );
};
