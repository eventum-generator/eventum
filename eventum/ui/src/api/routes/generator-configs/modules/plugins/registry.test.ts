import { render } from '@testing-library/react';
import { ComponentType, createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  EVENT_PLUGINS_INFO,
  EVENT_PLUGIN_DEFAULT_ASSETS,
  EVENT_PLUGIN_DEFAULT_CONFIGS,
  INPUT_PLUGINS_INFO,
  INPUT_PLUGIN_DEFAULT_CONFIGS,
  OUTPUT_PLUGINS_INFO,
  OUTPUT_PLUGIN_DEFAULT_CONFIGS,
  PLUGINS_INFO,
  PluginInfo,
} from './registry';
import { EventPluginConfigSchema } from '@/api/routes/generator-configs/schemas/plugins/event';
import { InputPluginConfigSchema } from '@/api/routes/generator-configs/schemas/plugins/input';
import { OutputPluginConfigSchema } from '@/api/routes/generator-configs/schemas/plugins/output';

/** Every plugin of every stage, as a name and the entry describing it. */
function everyPlugin(): [string, PluginInfo][] {
  return Object.values(PLUGINS_INFO).flatMap((info) =>
    Object.entries(info as Record<string, PluginInfo>)
  );
}

/**
 * The registry is what the studio offers when a plugin is added: the
 * label in the list, and the configuration the form starts from. A
 * default the schema rejects reaches the backend as an invalid config
 * the moment the project is saved, and nothing between the two catches
 * it - the form only validates what the user then edits.
 */
describe('plugin default configs', () => {
  it.each(Object.entries(INPUT_PLUGIN_DEFAULT_CONFIGS))(
    'accepts the default config of the %s input plugin',
    (_name, config) => {
      expect(InputPluginConfigSchema.safeParse(config).success).toBe(true);
    }
  );

  it.each(Object.entries(EVENT_PLUGIN_DEFAULT_CONFIGS))(
    'accepts the default config of the %s event plugin',
    (_name, config) => {
      expect(EventPluginConfigSchema.safeParse(config).success).toBe(true);
    }
  );

  it.each(Object.entries(OUTPUT_PLUGIN_DEFAULT_CONFIGS))(
    'accepts the default config of the %s output plugin',
    (_name, config) => {
      expect(OutputPluginConfigSchema.safeParse(config).success).toBe(true);
    }
  );
});

describe('plugin info', () => {
  it.each([
    ['input', INPUT_PLUGINS_INFO, INPUT_PLUGIN_DEFAULT_CONFIGS],
    ['event', EVENT_PLUGINS_INFO, EVENT_PLUGIN_DEFAULT_CONFIGS],
    ['output', OUTPUT_PLUGINS_INFO, OUTPUT_PLUGIN_DEFAULT_CONFIGS],
  ] as const)(
    'describes exactly the %s plugins that have a default config',
    (_type, info, configs) => {
      expect(Object.keys(info).sort()).toEqual(Object.keys(configs).sort());
    }
  );

  it('gives every plugin a label and a description', () => {
    expect(everyPlugin().length).toBeGreaterThan(0);

    for (const [name, plugin] of everyPlugin()) {
      expect(plugin.label, name).toBeTruthy();
      expect(plugin.description, name).toBeTruthy();
    }
  });

  it('gives every plugin an icon that draws', () => {
    // A brand icon is wrapped before it lands here, so what the entry
    // holds is not necessarily a plain component - rendering it is the
    // only check that it is usable at all.
    for (const [name, plugin] of everyPlugin()) {
      // A standard icon and a brand icon take different props, so the
      // union they form is not one `createElement` can resolve; both
      // are components, which is all that is drawn here.
      const Glyph = plugin.icon as ComponentType;
      const { container, unmount } = render(createElement(Glyph));

      expect(container.querySelector('svg'), name).not.toBeNull();

      unmount();
    }
  });

  it('keys the plugin types the pipeline has stages for', () => {
    expect(Object.keys(PLUGINS_INFO)).toEqual(['input', 'event', 'output']);
  });
});

describe('event plugin default assets', () => {
  it('ships an asset for every event plugin', () => {
    expect(Object.keys(EVENT_PLUGIN_DEFAULT_ASSETS).sort()).toEqual(
      Object.keys(EVENT_PLUGIN_DEFAULT_CONFIGS).sort()
    );
  });

  it('places every asset on a relative path with content', () => {
    for (const [name, asset] of Object.entries(EVENT_PLUGIN_DEFAULT_ASSETS)) {
      expect(asset.path, name).toMatch(/^\.\//);
      expect(asset.content, name).not.toBe('');
    }
  });

  it('points the template default config at the asset it ships', () => {
    const templates = EVENT_PLUGIN_DEFAULT_CONFIGS.template.templates.map(
      (entry) => Object.values(entry)[0]?.template
    );

    expect(templates).toContain(EVENT_PLUGIN_DEFAULT_ASSETS.template.path);
  });
});
