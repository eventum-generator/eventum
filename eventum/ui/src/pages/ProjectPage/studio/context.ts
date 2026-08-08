import { ItemInstance } from '@headless-tree/core';
import { createContext, useContext } from 'react';

import {
  FileNode,
  GeneratorConfig,
  InputPluginsNamedConfig,
} from '@/api/routes/generator-configs/schemas';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';
import { InputPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/input';
import { InputPluginName } from '@/api/routes/generator-configs/schemas/plugins/input/base-config';
import { OutputPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/output';
import { OutputPluginName } from '@/api/routes/generator-configs/schemas/plugins/output/base-config';

export type Stage = 'input' | 'event' | 'output';

export type SaverFn = () => void;

export interface InputStage {
  names: string[];
  selected: number;
  // Identity of the plugin at the selected position - unlike the position
  // itself, it changes whenever another plugin takes that slot.
  selectedId: string | undefined;
  setSelected: (index: number) => void;
  add: (name: InputPluginName) => void;
  remove: (index: number) => void;
  change: (config: InputPluginNamedConfig) => void;
  getConfig: () => InputPluginsNamedConfig;
  getSelected: () => number;
}

export interface EventStage {
  name: EventPluginName | null;
  config: EventPluginNamedConfig | null;
  add: (name: EventPluginName) => void;
  remove: () => void;
  change: (config: EventPluginNamedConfig) => void;
  getConfig: () => EventPluginNamedConfig | null;
}

export interface OutputStage {
  names: string[];
  selected: number;
  selectedId: string | undefined;
  setSelected: (index: number) => void;
  add: (name: OutputPluginName) => void;
  remove: (index: number) => void;
  change: (config: OutputPluginNamedConfig) => void;
}

export interface StudioConfigValue {
  config: GeneratorConfig;
  isConfigDirty: boolean;
  saveConfig: () => void;
  isSavingConfig: boolean;
  input: InputStage;
  event: EventStage;
  output: OutputStage;
}

export interface StudioShellValue {
  projectName: string;
  activeStage: Stage;
  setActiveStage: (stage: Stage) => void;
  openedItems: ItemInstance<FileNode>[];
  activeId: string | undefined;
  activateItem: (item: ItemInstance<FileNode>) => void;
  closeItem: (item: ItemInstance<FileNode>) => void;
  savedStatuses: Record<string, boolean>;
  setSaved: (id: string, saved: boolean) => void;
  registerSaver: (id: string, fn: SaverFn) => void;
  unregisterSaver: (id: string) => void;
  saveFile: (id: string) => void;
  dirtyFileIds: string[];
  // Set when the generator config could not be parsed/loaded; the shell
  // enters recovery mode (file editor only). `reloadConfig` re-fetches it.
  configError: Error | null;
  reloadConfig: () => void;
}

export const StudioConfigContext = createContext<StudioConfigValue | undefined>(
  undefined
);
export const StudioShellContext = createContext<StudioShellValue | undefined>(
  undefined
);

export const useStudioConfig = (): StudioConfigValue => {
  const ctx = useContext(StudioConfigContext);
  if (ctx === undefined) {
    throw new Error('useStudioConfig must be used within StudioProvider');
  }
  return ctx;
};

export const useStudioShell = (): StudioShellValue => {
  const ctx = useContext(StudioShellContext);
  if (ctx === undefined) {
    throw new Error('useStudioShell must be used within StudioProvider');
  }
  return ctx;
};
