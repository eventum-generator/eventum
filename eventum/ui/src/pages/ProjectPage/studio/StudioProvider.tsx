import { ItemInstance } from '@headless-tree/core';
import { notifications } from '@mantine/notifications';
import isEqual from 'lodash/isEqual';
import {
  FC,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useFileTree } from '../hooks/useFileTree';
import { useProjectName } from '../hooks/useProjectName';
import {
  EventStage,
  InputStage,
  OutputStage,
  SaverFn,
  Stage,
  StudioConfigContext,
  StudioConfigValue,
  StudioShellContext,
  StudioShellValue,
} from './context';
import { useUpdateGeneratorConfigMutation } from '@/api/hooks/useGeneratorConfigs';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import {
  FileNode,
  GeneratorConfig,
  InputPluginsNamedConfig,
  OutputPluginsNamedConfig,
} from '@/api/routes/generator-configs/schemas';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface StudioProviderProps {
  // Null when the generator config could not be loaded/parsed; paired with
  // `configError` it drives recovery mode (file editor only).
  serverConfig: GeneratorConfig | null;
  configError?: Error | null;
  onReloadConfig?: () => void;
  children: ReactNode;
}

const pluginNames = (plugins: Record<string, unknown>[]): string[] =>
  plugins.map((plugin) => Object.keys(plugin)[0]!);

// A structurally-valid but empty config, used only to satisfy the config
// context type while in recovery mode. It is never persisted - saveConfig is
// gated whenever `configError` is set.
const EMPTY_CONFIG: GeneratorConfig = {
  input: [],
  event: { template: PLUGIN_DEFAULT_CONFIGS.event.template },
  output: [],
};

export const StudioProvider: FC<StudioProviderProps> = ({
  serverConfig,
  configError = null,
  onReloadConfig,
  children,
}) => {
  const { projectName } = useProjectName();
  const { selectedItem, setSelectedItem } = useFileTree();

  // --- Pipeline stage config (mirrors the former per-tab state) ---
  const [inputConfig, setInputConfig] = useState<InputPluginsNamedConfig>(
    serverConfig?.input ?? []
  );
  const [eventConfig, setEventConfig] = useState<EventPluginNamedConfig[]>(
    serverConfig?.event ? [serverConfig.event] : []
  );
  const [outputConfig, setOutputConfig] = useState<OutputPluginsNamedConfig>(
    serverConfig?.output ?? []
  );
  const [inputSelected, setInputSelected] = useState(0);
  const [outputSelected, setOutputSelected] = useState(0);

  const config = useMemo<GeneratorConfig>(
    () => ({
      ...(serverConfig ?? EMPTY_CONFIG),
      input: inputConfig,
      event: eventConfig[0] ?? EMPTY_CONFIG.event,
      output: outputConfig,
    }),
    [serverConfig, inputConfig, eventConfig, outputConfig]
  );

  const isConfigDirty = useMemo(
    () => !configError && !isEqual(serverConfig, config),
    [configError, serverConfig, config]
  );

  // Stable getters for memoized consoles (preserve the ref pattern).
  const inputConfigRef = useRef(inputConfig);
  inputConfigRef.current = inputConfig;
  const inputSelectedRef = useRef(inputSelected);
  inputSelectedRef.current = inputSelected;
  const eventConfigRef = useRef(eventConfig);
  eventConfigRef.current = eventConfig;

  const input = useMemo<InputStage>(
    () => ({
      names: pluginNames(inputConfig),
      selected: inputSelected,
      setSelected: setInputSelected,
      add: (name) =>
        setInputConfig(
          (prev) =>
            [
              ...prev,
              { [name]: PLUGIN_DEFAULT_CONFIGS.input[name] },
            ] as InputPluginsNamedConfig
        ),
      remove: (index) => {
        setInputConfig((prev) => {
          const next = [...prev.slice(0, index), ...prev.slice(index + 1)];
          setInputSelected((sel) =>
            sel >= next.length ? Math.max(next.length - 1, 0) : sel
          );
          return next;
        });
      },
      change: (cfg) =>
        setInputConfig((prev) => {
          const next = [...prev];
          next[inputSelectedRef.current] = cfg;
          return next;
        }),
      getConfig: () => inputConfigRef.current,
      getSelected: () => inputSelectedRef.current,
    }),
    [inputConfig, inputSelected]
  );

  const event = useMemo<EventStage>(() => {
    const current = eventConfig[0] ?? null;
    return {
      name: current ? (Object.keys(current)[0] as EventPluginName) : null,
      config: current,
      add: (name) =>
        setEventConfig([
          {
            [name]: PLUGIN_DEFAULT_CONFIGS.event[name],
          } as EventPluginNamedConfig,
        ]),
      remove: () => setEventConfig([]),
      change: (cfg) => setEventConfig([cfg]),
      getConfig: () => eventConfigRef.current[0] ?? null,
    };
  }, [eventConfig]);

  const output = useMemo<OutputStage>(
    () => ({
      names: pluginNames(outputConfig),
      selected: outputSelected,
      setSelected: setOutputSelected,
      add: (name) =>
        setOutputConfig(
          (prev) =>
            [
              ...prev,
              { [name]: PLUGIN_DEFAULT_CONFIGS.output[name] },
            ] as OutputPluginsNamedConfig
        ),
      remove: (index) => {
        setOutputConfig((prev) => {
          const next = [...prev.slice(0, index), ...prev.slice(index + 1)];
          setOutputSelected((sel) =>
            sel >= next.length ? Math.max(next.length - 1, 0) : sel
          );
          return next;
        });
      },
      change: (cfg) =>
        setOutputConfig((prev) => {
          const next = [...prev];
          next[outputSelected] = cfg;
          return next;
        }),
    }),
    [outputConfig, outputSelected]
  );

  const updateConfig = useUpdateGeneratorConfigMutation();
  const saveConfig = useCallback(() => {
    // Never write the config in recovery mode: the in-memory config is a
    // placeholder and would overwrite the user's broken (but real) file.
    if (configError) {
      return;
    }

    updateConfig.mutate(
      { name: projectName, config },
      {
        onSuccess: () =>
          notifications.show({
            title: 'Success',
            message: 'Project configuration saved',
            color: 'green',
          }),
        onError: (error) =>
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to save configuration
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          }),
      }
    );
  }, [updateConfig, projectName, config, configError]);

  const configValue = useMemo<StudioConfigValue>(
    () => ({
      config,
      isConfigDirty,
      saveConfig,
      isSavingConfig: updateConfig.isPending,
      input,
      event,
      output,
    }),
    [
      config,
      isConfigDirty,
      saveConfig,
      updateConfig.isPending,
      input,
      event,
      output,
    ]
  );

  // --- Shell: stage + open files + savers (rarely-changing) ---
  const [activeStage, setActiveStage] = useState<Stage>('input');
  const [openedItems, setOpenedItems] = useState<ItemInstance<FileNode>[]>([]);
  const [activeId, setActiveId] = useState<string>();
  const [savedStatuses, setSavedStatuses] = useState<Record<string, boolean>>(
    {}
  );
  const saversRef = useRef<Record<string, SaverFn>>({});

  // Open + activate a file the instant it is picked in the tree (the fix).
  // Folder clicks only expand the tree; they never blank the editor.
  useEffect(() => {
    if (selectedItem === undefined || selectedItem.isFolder()) {
      return;
    }
    const id = selectedItem.getId();
    setOpenedItems((prev) =>
      prev.some((item) => item.getId() === id) ? prev : [...prev, selectedItem]
    );
    setActiveId(id);
  }, [selectedItem]);

  const activateItem = useCallback(
    (item: ItemInstance<FileNode>) => {
      setActiveId(item.getId());
      setSelectedItem(item);
    },
    [setSelectedItem]
  );

  const closeItem = useCallback(
    (item: ItemInstance<FileNode>) => {
      const id = item.getId();
      setOpenedItems((prev) => {
        const index = prev.findIndex((it) => it.getId() === id);
        if (index === -1) {
          return prev;
        }
        const next = [...prev.slice(0, index), ...prev.slice(index + 1)];
        if (id === activeId) {
          const neighbor = index === 0 ? next[0] : next[index - 1];
          setActiveId(neighbor?.getId());
          if (neighbor !== undefined) {
            setSelectedItem(neighbor);
          }
        }
        return next;
      });
      setSavedStatuses((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    },
    [activeId, setSelectedItem]
  );

  const setSaved = useCallback(
    (id: string, saved: boolean) =>
      setSavedStatuses((prev) => ({ ...prev, [id]: saved })),
    []
  );

  const registerSaver = useCallback((id: string, fn: SaverFn) => {
    saversRef.current[id] = fn;
  }, []);
  const unregisterSaver = useCallback((id: string) => {
    delete saversRef.current[id];
  }, []);
  const saveFile = useCallback((id: string) => {
    saversRef.current[id]?.();
  }, []);

  const dirtyFileIds = useMemo(
    () =>
      Object.keys(savedStatuses).filter((id) => savedStatuses[id] === false),
    [savedStatuses]
  );

  const reloadConfig = useCallback(() => {
    onReloadConfig?.();
  }, [onReloadConfig]);

  const shellValue = useMemo<StudioShellValue>(
    () => ({
      projectName,
      activeStage,
      setActiveStage,
      openedItems,
      activeId,
      activateItem,
      closeItem,
      savedStatuses,
      setSaved,
      registerSaver,
      unregisterSaver,
      saveFile,
      dirtyFileIds,
      configError,
      reloadConfig,
    }),
    [
      projectName,
      activeStage,
      openedItems,
      activeId,
      activateItem,
      closeItem,
      savedStatuses,
      setSaved,
      registerSaver,
      unregisterSaver,
      saveFile,
      dirtyFileIds,
      configError,
      reloadConfig,
    ]
  );

  return (
    <StudioShellContext.Provider value={shellValue}>
      <StudioConfigContext.Provider value={configValue}>
        {children}
      </StudioConfigContext.Provider>
    </StudioShellContext.Provider>
  );
};
