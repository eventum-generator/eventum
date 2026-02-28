import {
  IconType,
  SiApachekafka,
  SiClickhouse,
  SiOpensearch,
} from '@icons-pack/react-simple-icons';
import {
  Icon,
  IconAsteriskSimple,
  IconBraces,
  IconCalendarMonthFilled,
  IconChartBar,
  IconCode,
  IconFileDescription,
  IconList,
  IconNetwork,
  IconNumber100Small,
  IconRepeat,
  IconTerminal2,
  IconTimeDuration45,
} from '@tabler/icons-react';
import React, { createElement, forwardRef } from 'react';

import { EventPluginConfig } from '../../schemas/plugins/event';
import { EventPluginName } from '../../schemas/plugins/event/base-config';
import { InputPluginConfig } from '../../schemas/plugins/input';
import { InputPluginName } from '../../schemas/plugins/input/base-config';
import { OutputPluginConfig } from '../../schemas/plugins/output';
import { OutputPluginName } from '../../schemas/plugins/output/base-config';
import { ReplayEventPluginDefaultConfig } from './default-configs/event/replay';
import { ScriptEventPluginDefaultConfig } from './default-configs/event/script';
import { TemplateEventPluginDefaultConfig } from './default-configs/event/template';
import { CronInputPluginDefaultConfig } from './default-configs/input/cron';
import { HTTPInputPluginDefaultConfig } from './default-configs/input/http';
import { LinspaceInputPluginDefaultConfig } from './default-configs/input/linspace';
import { StaticInputPluginDefaultConfig } from './default-configs/input/static';
import { TimePatternsInputPluginDefaultConfig } from './default-configs/input/time_patterns';
import { TimerInputPluginDefaultConfig } from './default-configs/input/timer';
import { TimestampsInputPluginDefaultConfig } from './default-configs/input/timestamps';
import { ClickhouseOutputPluginDefaultConfig } from './default-configs/output/clickhouse';
import { FileOutputPluginDefaultConfig } from './default-configs/output/file';
import { HTTPOutputPluginDefaultConfig } from './default-configs/output/http';
import { KafkaOutputPluginDefaultConfig } from './default-configs/output/kafka';
import { OpensearchOutputPluginDefaultConfig } from './default-configs/output/opensearch';
import { StdoutOutputPluginDefaultConfig } from './default-configs/output/stdout';
import { TcpOutputPluginDefaultConfig } from './default-configs/output/tcp';

/** Scale down filled brand icons to visually match stroked Tabler icons. */
function brandIcon(BaseIcon: IconType): IconType {
  const Scaled = forwardRef<SVGSVGElement, React.ComponentPropsWithoutRef<IconType>>(
    ({ size, ...rest }, ref) =>
      createElement(BaseIcon, {
        ...rest,
        ref,
        size:
          typeof size === 'number' ? Math.round(size * 0.82) : size,
      }),
  );
  Scaled.displayName = `BrandIcon(${BaseIcon.displayName ?? 'Icon'})`;
  return Scaled;
}

export type PluginType = 'input' | 'event' | 'output';

export interface PluginInfo {
  label: string;
  icon: Icon | IconType;
  description: string;
}

export const INPUT_PLUGINS_INFO = {
  cron: {
    label: 'Cron',
    icon: IconAsteriskSimple,
    description: 'Generate timestamps at moments defined by cron expression',
  },
  http: {
    label: 'HTTP',
    icon: IconCode,
    description: 'Generate timestamps when HTTP request is received',
  },
  linspace: {
    label: 'Linspace',
    icon: IconCalendarMonthFilled,
    description: 'Generate timestamps linearly spaced in date range',
  },
  static: {
    label: 'Static',
    icon: IconNumber100Small,
    description: 'Generate specified number of current timestamps',
  },
  time_patterns: {
    label: 'Time patterns',
    icon: IconChartBar,
    description:
      'Generate timestamps with specific pattern of distribution in time',
  },
  timer: {
    label: 'Timer',
    icon: IconTimeDuration45,
    description: 'Generate timestamps after specified amount of time',
  },
  timestamps: {
    label: 'Timestamps',
    icon: IconList,
    description: 'Generate at specified timestamps',
  },
} as const satisfies Record<InputPluginName, PluginInfo>;

export const EVENT_PLUGINS_INFO = {
  template: {
    label: 'Template',
    icon: IconBraces,
    description: 'Produce events using templates',
  },
  replay: {
    label: 'Replay',
    icon: IconRepeat,
    description: 'Produce events by replaying existing log files',
  },
  script: {
    label: 'Script',
    icon: IconCode,
    description: 'Produce events using Python scripts',
  },
} as const satisfies Record<EventPluginName, PluginInfo>;

export const OUTPUT_PLUGINS_INFO = {
  clickhouse: {
    label: 'ClickHouse',
    icon: brandIcon(SiClickhouse),
    description: 'Index events to ClickHouse',
  },
  file: {
    label: 'File',
    icon: IconFileDescription,
    description: 'Write events to a file',
  },
  http: {
    label: 'HTTP',
    icon: IconCode,
    description: 'Send events using HTTP requests',
  },
  opensearch: {
    label: 'OpenSearch',
    icon: brandIcon(SiOpensearch),
    description: 'Index events to OpenSearch',
  },
  kafka: {
    label: 'Kafka',
    icon: brandIcon(SiApachekafka),
    description: 'Produce events to Apache Kafka topics',
  },
  stdout: {
    label: 'Stdout',
    icon: IconTerminal2,
    description: 'Write events to stdout',
  },
  tcp: {
    label: 'TCP',
    icon: IconNetwork,
    description: 'Send events over a TCP connection',
  },
} as const satisfies Record<OutputPluginName, PluginInfo>;

export const PLUGINS_INFO = {
  input: INPUT_PLUGINS_INFO,
  event: EVENT_PLUGINS_INFO,
  output: OUTPUT_PLUGINS_INFO,
} as const satisfies Record<
  PluginType,
  | typeof INPUT_PLUGINS_INFO
  | typeof EVENT_PLUGINS_INFO
  | typeof OUTPUT_PLUGINS_INFO
>;

export const INPUT_PLUGIN_DEFAULT_CONFIGS = {
  cron: CronInputPluginDefaultConfig,
  http: HTTPInputPluginDefaultConfig,
  linspace: LinspaceInputPluginDefaultConfig,
  static: StaticInputPluginDefaultConfig,
  time_patterns: TimePatternsInputPluginDefaultConfig,
  timer: TimerInputPluginDefaultConfig,
  timestamps: TimestampsInputPluginDefaultConfig,
} as const satisfies Record<InputPluginName, InputPluginConfig>;

export const EVENT_PLUGIN_DEFAULT_CONFIGS = {
  replay: ReplayEventPluginDefaultConfig,
  script: ScriptEventPluginDefaultConfig,
  template: TemplateEventPluginDefaultConfig,
} as const satisfies Record<EventPluginName, EventPluginConfig>;

export const OUTPUT_PLUGIN_DEFAULT_CONFIGS = {
  clickhouse: ClickhouseOutputPluginDefaultConfig,
  file: FileOutputPluginDefaultConfig,
  http: HTTPOutputPluginDefaultConfig,
  kafka: KafkaOutputPluginDefaultConfig,
  opensearch: OpensearchOutputPluginDefaultConfig,
  stdout: StdoutOutputPluginDefaultConfig,
  tcp: TcpOutputPluginDefaultConfig,
} as const satisfies Record<OutputPluginName, OutputPluginConfig>;

export const EVENT_PLUGIN_DEFAULT_ASSETS = {
  replay: {
    path: './static/data.log',
    content: 'Event 1\nEvent 2\nEvent 3\n',
  },
  script: {
    path: './scripts/event.py',
    content: 'def produce(params: dict) -> str | list[str]:\n    ...\n',
  },
  template: {
    path: './templates/template.jinja',
    content: 'Template content',
  },
} as const satisfies Record<
  EventPluginName,
  {
    path: string;
    content: string;
  }
>;

export const PLUGIN_DEFAULT_CONFIGS = {
  input: INPUT_PLUGIN_DEFAULT_CONFIGS,
  event: EVENT_PLUGIN_DEFAULT_CONFIGS,
  output: OUTPUT_PLUGIN_DEFAULT_CONFIGS,
} as const satisfies Record<
  PluginType,
  | typeof INPUT_PLUGIN_DEFAULT_CONFIGS
  | typeof EVENT_PLUGIN_DEFAULT_CONFIGS
  | typeof OUTPUT_PLUGIN_DEFAULT_CONFIGS
>;

export type PluginNamesMap = {
  [K in keyof typeof PLUGINS_INFO]: keyof (typeof PLUGINS_INFO)[K];
};
