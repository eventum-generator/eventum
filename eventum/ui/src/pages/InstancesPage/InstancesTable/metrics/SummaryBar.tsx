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

interface SummaryItemProps {
  label: string;
  value: string | number;
}

function SummaryItem({ label, value }: SummaryItemProps) {
  return (
    <div className={classes.item}>
      <div className={classes.label}>{label}</div>
      <div className={classes.value}>{value}</div>
    </div>
  );
}

interface SummaryBarProps {
  stats: GeneratorStats;
}

export const SummaryBar: FC<SummaryBarProps> = ({ stats }) => {
  return (
    <div className={classes.bar}>
      <div className={classes.row}>
        <SummaryItem label="Instance" value={stats.id} />
        <SummaryItem label="Start time" value={new Date(stats.start_time).toLocaleString()} />
        <SummaryItem label="Uptime" value={formatUptime(stats.uptime)} />
      </div>
      <div className={classes.row}>
        <SummaryItem label="Generated" value={stats.total_generated} />
        <SummaryItem label="Written" value={stats.total_written} />
        <SummaryItem label="Input EPS" value={stats.input_eps.toFixed(2)} />
        <SummaryItem label="Output EPS" value={stats.output_eps.toFixed(2)} />
      </div>
    </div>
  );
};
