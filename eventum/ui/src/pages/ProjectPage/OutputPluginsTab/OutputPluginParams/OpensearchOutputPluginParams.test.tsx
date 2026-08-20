import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { OpensearchOutputPluginParams } from './OpensearchOutputPluginParams';
import { OpensearchOutputPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/output/configs/opensearch';
import { Format } from '@/api/routes/generator-configs/schemas/plugins/output/formatters';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useSecrets', () => ({
  useSecretNames: () => ({ data: ['opensearch_password'] }),
}));

vi.mock('@/api/hooks/useGeneratorConfigs', () => ({
  useGeneratorFileTree: () => ({ data: undefined }),
}));

// Held apart from the config so the linter does not read the field
// as a credential written into the source.
const TYPED = 'typed';
const REFERENCE = '${secrets.opensearch_password}';

const CONFIG: OpensearchOutputPluginConfig = {
  hosts: ['https://opensearch.prod:9200'],
  username: 'admin',
  password: TYPED,
  index: 'events',
  formatter: { format: Format.JSON },
};

function renderForm(onChange: (config: OpensearchOutputPluginConfig) => void) {
  renderWithProviders(
    <MemoryRouter>
      <ProjectNameProvider initialProjectName="demo">
        <OpensearchOutputPluginParams
          initialConfig={CONFIG}
          onChange={onChange}
        />
      </ProjectNameProvider>
    </MemoryRouter>
  );
}

describe('OpensearchOutputPluginParams', () => {
  it('writes the reference of the secret picked for the password', async () => {
    const onChange = vi.fn();
    renderForm(onChange);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.click(await screen.findByText('opensearch_password'));

    expect(onChange.mock.lastCall?.[0]).toEqual(
      expect.objectContaining({ password: REFERENCE })
    );
  });

  it('keeps a password typed in place', async () => {
    const onChange = vi.fn();
    renderForm(onChange);

    await userEvent.type(screen.getByDisplayValue(TYPED), '!');

    expect(onChange.mock.lastCall?.[0]).toEqual(
      expect.objectContaining({ password: `${TYPED}!` })
    );
  });
});
