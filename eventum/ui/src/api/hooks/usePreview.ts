import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { InputPluginsNamedConfig } from '../routes/generator-configs/schemas';
import { EventPluginNamedConfig } from '../routes/generator-configs/schemas/plugins/event';
import {
  clearTemplateEventPluginGlobalState,
  clearTemplateEventPluginLocalState,
  clearTemplateEventPluginSharedState,
  formatEvents,
  generateTimestamps,
  getTemplateEventPluginGlobalState,
  getTemplateEventPluginLocalState,
  getTemplateEventPluginSharedState,
  initializeEventPlugin,
  normalizeVersatileDatetime,
  produceEvents,
  releaseEventPlugin,
  updateTemplateEventPluginGlobalState,
  updateTemplateEventPluginLocalState,
  updateTemplateEventPluginSharedState,
} from '../routes/preview';
import {
  FormatEventsBody,
  ProduceParamsBody,
  TemplateEventPluginState,
  VersatileDatetimeParametersBody,
} from '../routes/preview/schemas';

export function useGenerateTimestampsMutation() {
  return useMutation({
    mutationFn: ({
      name,
      size,
      skipPast,
      timezone,
      span,
      inputPluginsConfig,
    }: {
      name: string;
      size: number;
      skipPast: boolean;
      timezone: string;
      span: string | null;
      inputPluginsConfig: InputPluginsNamedConfig;
    }) =>
      generateTimestamps(
        name,
        size,
        skipPast,
        timezone,
        span,
        inputPluginsConfig
      ),
  });
}

export function useInitializeEventPluginMutation() {
  return useMutation({
    mutationFn: ({
      name,
      eventPluginConfig,
    }: {
      name: string;
      eventPluginConfig: EventPluginNamedConfig;
    }) => initializeEventPlugin(name, eventPluginConfig),
  });
}

export function useReleaseEventPluginMutation() {
  return useMutation({
    mutationFn: ({ name }: { name: string }) => releaseEventPlugin(name),
  });
}

export function useProduceEventsMutation() {
  return useMutation({
    mutationFn: ({
      name,
      produceParams,
    }: {
      name: string;
      produceParams: ProduceParamsBody;
    }) => produceEvents(name, produceParams),
  });
}

const TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY = [
  'preview-event-plugin-template-state',
];

export function useTemplateEventPluginLocalState(
  name: string,
  templateAlias: string
) {
  return useQuery({
    queryKey: [
      ...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY,
      name,
      'local',
      templateAlias,
    ],
    queryFn: () => getTemplateEventPluginLocalState(name, templateAlias),
  });
}

export function useUpdateTemplateEventPluginLocalStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      templateAlias,
      state,
    }: {
      name: string;
      templateAlias: string;
      state: TemplateEventPluginState;
    }) => updateTemplateEventPluginLocalState(name, templateAlias, state),
    onSuccess: async (_, { name, templateAlias }) => {
      await queryClient.invalidateQueries({
        queryKey: [
          ...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY,
          name,
          'local',
          templateAlias,
        ],
        exact: true,
      });
    },
  });
}

export function useClearTemplateEventPluginLocalStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      templateAlias,
    }: {
      name: string;
      templateAlias: string;
    }) => clearTemplateEventPluginLocalState(name, templateAlias),
    onSuccess: async (_, { name, templateAlias }) => {
      await queryClient.invalidateQueries({
        queryKey: [
          ...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY,
          name,
          'local',
          templateAlias,
        ],
        exact: true,
      });
    },
  });
}

export function useTemplateEventPluginSharedState(name: string) {
  return useQuery({
    queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'shared'],
    queryFn: () => getTemplateEventPluginSharedState(name),
  });
}

export function useUpdateTemplateEventPluginSharedStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      state,
    }: {
      name: string;
      state: TemplateEventPluginState;
    }) => updateTemplateEventPluginSharedState(name, state),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'shared'],
        exact: true,
      });
    },
  });
}

export function useClearTemplateEventPluginSharedStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name }: { name: string }) =>
      clearTemplateEventPluginSharedState(name),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'shared'],
        exact: true,
      });
    },
  });
}

export function useTemplateEventPluginGlobalState(name: string) {
  return useQuery({
    queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'global'],
    queryFn: () => getTemplateEventPluginGlobalState(name),
  });
}

export function useUpdateTemplateEventPluginGlobalStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      state,
    }: {
      name: string;
      state: TemplateEventPluginState;
    }) => updateTemplateEventPluginGlobalState(name, state),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'global'],
        exact: true,
      });
    },
  });
}

export function useClearTemplateEventPluginGlobalStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name }: { name: string }) =>
      clearTemplateEventPluginGlobalState(name),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...TEMPLATE_EVENT_PLUGIN_STATE_QUERY_KEY, name, 'global'],
        exact: true,
      });
    },
  });
}

export function useFormatEventsMutation() {
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: FormatEventsBody }) =>
      formatEvents(name, body),
  });
}

export function useNormalizedVersatileDatetimeMutation() {
  return useMutation({
    mutationFn: ({
      name,
      parameters,
    }: {
      name: string;
      parameters: VersatileDatetimeParametersBody;
    }) => normalizeVersatileDatetime(name, parameters),
  });
}
