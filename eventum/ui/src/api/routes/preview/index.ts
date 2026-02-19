import { InputPluginsNamedConfig } from '../generator-configs/schemas';
import { EventPluginNamedConfig } from '../generator-configs/schemas/plugins/event';
import {
  AggregatedTimestamps,
  AggregatedTimestampsSchema,
  FormatEventsBody,
  FormattingResult,
  FormattingResultSchema,
  ProduceParamsBody,
  ProducedEventsInfo,
  ProducedEventsInfoSchema,
  TemplateEventPluginState,
  TemplateEventPluginStateSchema,
  VersatileDatetimeParametersBody,
  VersatileDatetimeResponse,
  VersatileDatetimeResponseSchema,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function generateTimestamps(
  name: string,
  size: number,
  skipPast: boolean,
  timezone: string,
  span: string | null,
  inputPluginsConfig: InputPluginsNamedConfig
): Promise<AggregatedTimestamps> {
  return await validateResponse(
    AggregatedTimestampsSchema,
    apiClient.post(
      `/preview/${name}/input-plugins/generate`,
      inputPluginsConfig,
      {
        params: {
          size,
          skip_past: skipPast,
          timezone,
          span,
        },
      }
    )
  );
}

export async function initializeEventPlugin(
  name: string,
  eventPluginConfig: EventPluginNamedConfig
) {
  await apiClient.post(`/preview/${name}/event-plugin`, eventPluginConfig);
}

export async function releaseEventPlugin(name: string) {
  await apiClient.delete(`/preview/${name}/event-plugin`);
}

export async function produceEvents(
  name: string,
  produceParams: ProduceParamsBody
): Promise<ProducedEventsInfo> {
  return await validateResponse(
    ProducedEventsInfoSchema,
    apiClient.post(`/preview/${name}/event-plugin/produce`, produceParams)
  );
}

export async function getTemplateEventPluginLocalState(
  name: string,
  templateAlias: string
): Promise<TemplateEventPluginState> {
  return await validateResponse(
    TemplateEventPluginStateSchema,
    apiClient.get(
      `/preview/${name}/event-plugin/template/state/local/${templateAlias}`
    )
  );
}

export async function updateTemplateEventPluginLocalState(
  name: string,
  templateAlias: string,
  state: TemplateEventPluginState
) {
  await apiClient.patch(
    `/preview/${name}/event-plugin/template/state/local/${templateAlias}`,
    state
  );
}

export async function clearTemplateEventPluginLocalState(
  name: string,
  templateAlias: string
) {
  await apiClient.delete(
    `/preview/${name}/event-plugin/template/state/local/${templateAlias}`
  );
}

export async function getTemplateEventPluginSharedState(
  name: string
): Promise<TemplateEventPluginState> {
  return await validateResponse(
    TemplateEventPluginStateSchema,
    apiClient.get(`/preview/${name}/event-plugin/template/state/shared`)
  );
}

export async function updateTemplateEventPluginSharedState(
  name: string,
  state: TemplateEventPluginState
) {
  await apiClient.patch(
    `/preview/${name}/event-plugin/template/state/shared`,
    state
  );
}

export async function clearTemplateEventPluginSharedState(name: string) {
  await apiClient.delete(`/preview/${name}/event-plugin/template/state/shared`);
}

export async function getTemplateEventPluginGlobalState(
  name: string
): Promise<TemplateEventPluginState> {
  return await validateResponse(
    TemplateEventPluginStateSchema,
    apiClient.get(`/preview/${name}/event-plugin/template/state/global`)
  );
}

export async function updateTemplateEventPluginGlobalState(
  name: string,
  state: TemplateEventPluginState
) {
  await apiClient.patch(
    `/preview/${name}/event-plugin/template/state/global`,
    state
  );
}

export async function clearTemplateEventPluginGlobalState(name: string) {
  await apiClient.delete(`/preview/${name}/event-plugin/template/state/global`);
}

export async function normalizeVersatileDatetime(
  name: string,
  parameters: VersatileDatetimeParametersBody
): Promise<VersatileDatetimeResponse> {
  return await validateResponse(
    VersatileDatetimeResponseSchema,
    apiClient.post(`/preview/${name}/versatile-datetime/normalize`, parameters)
  );
}

export async function formatEvents(
  name: string,
  body: FormatEventsBody
): Promise<FormattingResult> {
  return await validateResponse(
    FormattingResultSchema,
    apiClient.post(`/preview/${name}/formatter/format`, body)
  );
}
