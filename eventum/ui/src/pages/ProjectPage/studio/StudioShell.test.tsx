import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { StudioProvider } from './StudioProvider';
import { StudioShell } from './StudioShell';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { GeneratorConfig } from '@/api/routes/generator-configs/schemas';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';
import { setViewportWidth } from '@/test/viewport';

const CONFIG: GeneratorConfig = {
  input: [{ cron: { expression: '* * * * *', count: 1 } }],
  event: { template: PLUGIN_DEFAULT_CONFIGS.event.template },
  output: [{ file: { path: './output/events.log' } }],
};

/**
 * Mount the shell in recovery mode.
 *
 * Recovery mode leaves out the console, whose dropdowns are positioned by a
 * library that measures its scroll ancestors - work jsdom cannot do. The
 * layout rule itself is the same one either mode runs, and it is covered
 * directly in `layout.test.ts`.
 */
function renderShell(width: number): void {
  setViewportWidth(width);

  // The command bar guards navigation away from unsaved files, and that guard
  // works only under a data router.
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <ProjectNameProvider initialProjectName="demo">
          <FileTreeProvider>
            <StudioProvider
              serverConfig={CONFIG}
              configError={new Error('generator.yml is not valid YAML')}
            >
              <ModalsProvider>
                <StudioShell />
              </ModalsProvider>
            </StudioProvider>
          </FileTreeProvider>
        </ProjectNameProvider>
      ),
    },
  ]);

  renderWithProviders(<RouterProvider router={router} />);
}

function panel(kind: 'explorer' | 'editor'): HTMLElement {
  const element = document.querySelector<HTMLElement>(`.studio-${kind}`);
  if (element === null) {
    throw new Error(`the ${kind} panel is not mounted`);
  }

  return element;
}

/** Panels stay mounted in either layout, so "on screen" is the question the
 *  inline display style answers. */
function isPanelVisible(kind: 'explorer' | 'editor'): boolean {
  return panel(kind).style.display !== 'none';
}

describe('StudioShell layout', () => {
  it('shares the row and offers no switcher on a wide viewport', () => {
    renderShell(1440);

    expect(isPanelVisible('explorer')).toBe(true);
    expect(isPanelVisible('editor')).toBe(true);
    expect(panel('editor').style.minWidth).toBe('360px');
    expect(screen.queryByRole('radio', { name: 'Explorer' })).toBeNull();
    expect(document.querySelector('.studio-resizer')).not.toBeNull();
  });

  it('shows one panel at a time below the wide breakpoint', () => {
    renderShell(1024);

    expect(isPanelVisible('editor')).toBe(true);
    expect(isPanelVisible('explorer')).toBe(false);
    expect(screen.getByRole('radio', { name: 'Explorer' })).toBeInTheDocument();
  });

  it('drops the drag handles along with the shared row', () => {
    renderShell(1024);

    expect(document.querySelector('.studio-resizer')).toBeNull();
  });

  it('leaves the inspector out of the switcher in recovery mode', () => {
    renderShell(1024);

    expect(screen.getByRole('radio', { name: 'Editor' })).toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Inspector' })).toBeNull();
  });

  it('switches the visible panel without unmounting the others', async () => {
    const user = userEvent.setup();
    renderShell(1024);

    await user.click(screen.getByRole('radio', { name: 'Explorer' }));

    expect(isPanelVisible('explorer')).toBe(true);
    // Still mounted, so the open tabs and their unsaved text survive.
    expect(isPanelVisible('editor')).toBe(false);
  });
});
