import { ModalsProvider } from '@mantine/modals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC, useEffect } from 'react';
import { describe, expect, it } from 'vitest';

import { InspectorPanel } from './InspectorPanel';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { GeneratorConfig } from '@/api/routes/generator-configs/schemas';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { StudioProvider } from '@/pages/ProjectPage/studio/StudioProvider';
import { Stage, useStudioShell } from '@/pages/ProjectPage/studio/context';
import { renderWithProviders } from '@/test/render';

const CONFIG: GeneratorConfig = {
  input: [
    { cron: { expression: '1 * * * *', count: 1 } },
    { cron: { expression: '2 * * * *', count: 2 } },
    { cron: { expression: '3 * * * *', count: 3 } },
  ],
  event: { template: PLUGIN_DEFAULT_CONFIGS.event.template },
  output: [
    { file: { path: './output/first.log' } },
    { file: { path: './output/second.log' } },
  ],
};

const OpenStage: FC<{ stage: Stage }> = ({ stage }) => {
  const { setActiveStage } = useStudioShell();
  useEffect(() => setActiveStage(stage), [setActiveStage, stage]);
  return null;
};

function renderInspector(stage: Stage): void {
  renderWithProviders(
    <ProjectNameProvider initialProjectName="demo">
      <FileTreeProvider>
        <StudioProvider serverConfig={CONFIG}>
          <ModalsProvider>
            <OpenStage stage={stage} />
            <InspectorPanel />
          </ModalsProvider>
        </StudioProvider>
      </FileTreeProvider>
    </ProjectNameProvider>
  );
}

// jsdom cannot resolve the CSS variables Mantine sizes its controls with, so
// `getComputedStyle` - and every role query built on it - throws. Controls
// are addressed by placeholder, title and text instead.
async function deletePlugin(index: number): Promise<void> {
  const user = userEvent.setup();
  await user.click(screen.getAllByTitle('Remove')[index]!);
  await user.click(await screen.findByText('Delete'));
  await waitFor(() => expect(screen.queryByText('Delete')).toBeNull());
}

function activePluginLabel(): string | null {
  return document.querySelector('a[data-active]')?.textContent ?? null;
}

describe('InspectorPanel plugin deletion', () => {
  it('reloads the parameters form with the plugin that takes the slot', async () => {
    renderInspector('input');

    expect(screen.getByPlaceholderText('cron expression')).toHaveValue(
      '1 * * * *'
    );

    await deletePlugin(0);

    expect(activePluginLabel()).toContain('cron #1');
    expect(screen.getByPlaceholderText('cron expression')).toHaveValue(
      '2 * * * *'
    );
  });

  it('keeps the selected plugin when an earlier one is deleted', async () => {
    const user = userEvent.setup();
    renderInspector('input');

    await user.click(screen.getByText('cron #2'));
    expect(screen.getByPlaceholderText('cron expression')).toHaveValue(
      '2 * * * *'
    );

    await deletePlugin(0);

    expect(activePluginLabel()).toContain('cron #1');
    expect(screen.getByPlaceholderText('cron expression')).toHaveValue(
      '2 * * * *'
    );
  });

  it('reloads the parameters form of output plugins as well', async () => {
    renderInspector('output');

    expect(screen.getByPlaceholderText('file path')).toHaveValue(
      './output/first.log'
    );

    await deletePlugin(0);

    expect(activePluginLabel()).toContain('file #1');
    expect(screen.getByPlaceholderText('file path')).toHaveValue(
      './output/second.log'
    );
  });

  it('drops the parameters form when the last plugin is deleted', async () => {
    renderInspector('output');

    await deletePlugin(0);
    await deletePlugin(0);

    expect(screen.queryByPlaceholderText('file path')).toBeNull();
    expect(screen.getByText('No plugin added yet')).toBeInTheDocument();
  });
});
