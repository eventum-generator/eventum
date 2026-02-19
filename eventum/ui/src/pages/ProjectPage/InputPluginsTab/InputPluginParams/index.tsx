import { FC } from 'react';

import { CronInputPluginParams } from './CronInputPluginParams';
import { HTTPInputPluginParams } from './HTTPInputPluginParams';
import { LinspaceInputPluginParams } from './LinspaceInputPluginParams';
import { StaticInputPluginParams } from './StaticInputPluginParams';
import { TimePatternsInputPluginParams } from './TimePatternsInputPluginParams';
import { TimerInputPluginParams } from './TimerInputPluginParams';
import { TimestampsInputPluginParams } from './TimestampsInputPluginParams';
import {
  InputPluginConfig,
  InputPluginNamedConfig,
} from '@/api/routes/generator-configs/schemas/plugins/input';
import { InputPluginName } from '@/api/routes/generator-configs/schemas/plugins/input/base-config';

interface InputPluginParamsProps {
  inputPluginConfig: InputPluginNamedConfig;
  onChange: (inputPluginConfig: InputPluginNamedConfig) => void;
}

type PluginNameToConfigType = {
  [K in InputPluginName]: Extract<
    InputPluginNamedConfig,
    Record<K, unknown>
  >[K];
};

const pluginNamesToParamsComponent = {
  cron: CronInputPluginParams,
  http: HTTPInputPluginParams,
  linspace: LinspaceInputPluginParams,
  static: StaticInputPluginParams,
  time_patterns: TimePatternsInputPluginParams,
  timer: TimerInputPluginParams,
  timestamps: TimestampsInputPluginParams,
} as const satisfies {
  [K in InputPluginName]: FC<{
    initialConfig: PluginNameToConfigType[K];
    onChange: (config: PluginNameToConfigType[K]) => unknown;
  }>;
};

type UnionToIntersection<U> = (
  U extends unknown ? (x: U) => void : never
) extends (x: infer I) => void
  ? I
  : never;

export const InputPluginParams: FC<InputPluginParamsProps> = ({
  inputPluginConfig,
  onChange,
}) => {
  const [pluginName, pluginConfig] = Object.entries(inputPluginConfig)[0] as [
    InputPluginName,
    UnionToIntersection<InputPluginConfig>,
  ];

  const ParamsComponent = pluginNamesToParamsComponent[pluginName];

  return (
    <ParamsComponent
      initialConfig={pluginConfig}
      onChange={(newConfig) => {
        onChange({ [pluginName]: newConfig } as InputPluginNamedConfig);
      }}
    />
  );
};
