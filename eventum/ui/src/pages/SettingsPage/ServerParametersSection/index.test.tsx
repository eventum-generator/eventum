import { useForm } from '@mantine/form';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { describe, expect, it } from 'vitest';

import { ServerParametersSection } from './index';
import { ServerParameters } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

const SERVED: ServerParameters = {
  api: { enabled: true },
  ui: { enabled: true },
  host: '0.0.0.0',
  port: 9474,
};

const Host: FC<{
  initial?: ServerParameters;
  onValues?: (values: ServerParameters) => void;
}> = ({ initial, onValues }) => {
  const form = useForm<ServerParameters>({
    mode: 'uncontrolled',
    initialValues: initial ?? SERVED,
  });

  return (
    <>
      <ServerParametersSection form={form} />
      <button type="button" onClick={() => onValues?.(form.getValues())}>
        read values
      </button>
    </>
  );
};

function switchOf(label: string): HTMLElement {
  return screen.getByRole('switch', { name: new RegExp(label) });
}

function field(label: string): HTMLElement {
  return screen.getByRole('textbox', { name: new RegExp(`^${label}`) });
}

/**
 * These settings decide what the instance answers on and who may reach
 * it, so the section holds the dependencies between them: there is
 * nothing to secure or to authenticate against while neither the API nor
 * the UI is served, and the MCP settings mean nothing while the MCP
 * server is not mounted. A control left live in those states offers a
 * setting that is never read.
 */
describe('ServerParametersSection', () => {
  it('opens on what the instance is served as', () => {
    renderWithProviders(<Host />);

    expect(switchOf('Enable API')).toBeChecked();
    expect(switchOf('Enable web UI')).toBeChecked();
    expect(field('Bind host')).toHaveValue('0.0.0.0');
  });

  it.each([
    ['Enable SSL', 'switch'],
    ['Username', 'textbox'],
  ])('holds %s back while nothing is served', (label, role) => {
    renderWithProviders(
      <Host initial={{ api: { enabled: false }, ui: { enabled: false } }} />
    );

    expect(screen.getByRole(role, { name: new RegExp(label) })).toBeDisabled();
  });

  it('offers the authentication once the API alone is served', () => {
    renderWithProviders(
      <Host initial={{ api: { enabled: true }, ui: { enabled: false } }} />
    );

    // Either transport being served is enough: both go through the same
    // basic auth.
    expect(field('Username')).toBeEnabled();
    expect(switchOf('Enable SSL')).toBeEnabled();
  });

  it('holds the MCP settings back while it is not mounted', () => {
    renderWithProviders(
      <Host initial={{ ...SERVED, mcp: { enabled: false } }} />
    );

    expect(switchOf('Allow write tools')).toBeDisabled();
    expect(field('Mount path')).toBeDisabled();
  });

  it('offers the MCP settings once it is mounted', () => {
    renderWithProviders(
      <Host initial={{ ...SERVED, mcp: { enabled: true } }} />
    );

    expect(switchOf('Allow write tools')).toBeEnabled();
    expect(field('Mount path')).toBeEnabled();
  });

  it('says what the write tools of a mounted MCP server allow', () => {
    renderWithProviders(
      <Host initial={{ ...SERVED, mcp: { enabled: true } }} />
    );

    // A connected agent can run code on the host through some plugins,
    // so the section has to say so where the switch is.
    expect(screen.getByText(/execute code on the host/)).toBeInTheDocument();
  });

  it('holds a port to what a port can be', async () => {
    const user = userEvent.setup();
    let values: ServerParameters | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    // 94740 is no port, and the field holds the value at the top of the
    // range rather than letting the backend refuse it.
    await user.click(field('Bind port'));
    await user.keyboard('{End}0');
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect(values?.port).toBe(65_535);
  });

  it('holds the verification modes back while SSL is off', () => {
    renderWithProviders(<Host />);

    // There is no handshake to verify anything in, so none of the three
    // is a setting yet.
    for (const mode of ['None', 'Optional', 'Required']) {
      expect(screen.getByRole('radio', { name: mode })).toBeDisabled();
    }
  });

  it('reports the verification mode picked once SSL is on', async () => {
    const user = userEvent.setup();
    let values: ServerParameters | undefined;

    renderWithProviders(
      <Host
        initial={{ ...SERVED, ssl: { enabled: true } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(screen.getByRole('radio', { name: 'Required' }));
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect(values?.ssl?.verify_mode).toBe('required');
  });

  it('takes the hosts an MCP request may name', async () => {
    const user = userEvent.setup();
    let values: ServerParameters | undefined;

    renderWithProviders(
      <Host
        initial={{ ...SERVED, mcp: { enabled: true } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    const hosts = screen.getByRole('textbox', { name: /Allowed hosts/ });
    await user.click(hosts);
    await user.paste('agent.internal');
    await user.keyboard('{Enter}');
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect(values?.mcp?.allowed_hosts).toEqual(['agent.internal']);
  });
});
