import { FC } from 'react';

import { ClickhouseOutputPluginParams } from './ClickhouseOutputPluginParams';
import { FileOutputPluginParams } from './FileOutputPluginParams';
import { HTTPOutputPluginParams } from './HTTPOutputPluginParams';
import { OpensearchOutputPluginParams } from './OpensearchOutputPluginParams';
import { StdoutOutputPluginParams } from './StdoutOutputPluginParams';
import {
  OutputPluginConfig,
  OutputPluginNamedConfig,
} from '@/api/routes/generator-configs/schemas/plugins/output';
import { OutputPluginName } from '@/api/routes/generator-configs/schemas/plugins/output/base-config';

interface OutputPluginParamsProps {
  outputPluginConfig: OutputPluginNamedConfig;
  onChange: (inputPluginConfig: OutputPluginNamedConfig) => void;
}

type PluginNameToConfigType = {
  [K in OutputPluginName]: Extract<
    OutputPluginNamedConfig,
    Record<K, unknown>
  >[K];
};

const pluginNamesToParamsComponent = {
  clickhouse: ClickhouseOutputPluginParams,
  file: FileOutputPluginParams,
  http: HTTPOutputPluginParams,
  opensearch: OpensearchOutputPluginParams,
  stdout: StdoutOutputPluginParams,
} as const satisfies {
  [K in OutputPluginName]: FC<{
    initialConfig: PluginNameToConfigType[K];
    onChange: (config: PluginNameToConfigType[K]) => unknown;
  }>;
};

type UnionToIntersection<U> = (
  U extends unknown ? (x: U) => void : never
) extends (x: infer I) => void
  ? I
  : never;

export const OutputPluginParams: FC<OutputPluginParamsProps> = ({
  outputPluginConfig,
  onChange,
}) => {
  const [pluginName, pluginConfig] = Object.entries(outputPluginConfig)[0] as [
    OutputPluginName,
    UnionToIntersection<OutputPluginConfig>,
  ];

  const ParamsComponent = pluginNamesToParamsComponent[pluginName];

  return (
    <ParamsComponent
      initialConfig={pluginConfig}
      onChange={(newConfig) => {
        onChange({ [pluginName]: newConfig } as OutputPluginNamedConfig);
      }}
    />
  );
};
