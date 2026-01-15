import { FC } from 'react';

import { ReplayEventPluginParams } from './ReplayEventPluginParams';
import { ScriptEventPluginParams } from './ScriptEventPluginParams';
import { TemplateEventPluginParams } from './TemplateEventPluginParams';
import {
  EventPluginConfig,
  EventPluginNamedConfig,
} from '@/api/routes/generator-configs/schemas/plugins/event';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';

interface EventPluginParamsProps {
  eventPluginConfig: EventPluginNamedConfig;
  onChange: (eventPluginConfig: EventPluginNamedConfig) => void;
}

type PluginNameToConfigType = {
  [K in EventPluginName]: Extract<
    EventPluginNamedConfig,
    Record<K, unknown>
  >[K];
};

const pluginNamesToParamsComponent = {
  template: TemplateEventPluginParams,
  replay: ReplayEventPluginParams,
  script: ScriptEventPluginParams,
} as const satisfies {
  [K in EventPluginName]: FC<{
    initialConfig: PluginNameToConfigType[K];
    onChange: (config: PluginNameToConfigType[K]) => unknown;
  }>;
};

type UnionToIntersection<U> = (
  U extends unknown ? (x: U) => void : never
) extends (x: infer I) => void
  ? I
  : never;

export const EventPluginParams: FC<EventPluginParamsProps> = ({
  eventPluginConfig,
  onChange,
}) => {
  const [pluginName, pluginConfig] = Object.entries(eventPluginConfig)[0] as [
    EventPluginName,
    UnionToIntersection<EventPluginConfig>,
  ];

  const ParamsComponent = pluginNamesToParamsComponent[pluginName];

  return (
    <ParamsComponent
      initialConfig={pluginConfig}
      onChange={(newConfig) => {
        onChange({ [pluginName]: newConfig } as EventPluginNamedConfig);
      }}
    />
  );
};
