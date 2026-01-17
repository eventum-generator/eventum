import { Stack, TextInput } from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { FC } from 'react';

import { PathParameters } from '@/api/routes/instance/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface PathParametersSectionProps {
  form: UseFormReturnType<PathParameters>;
}

export const PathParametersSection: FC<PathParametersSectionProps> = ({
  form,
}) => {
  return (
    <Stack gap="xs">
      <TextInput
        label={
          <LabelWithTooltip
            label="Generator configuration file name"
            tooltip={`Filename for generator configurations.
                            This parameter is used by the API for detection directories with generator configurations.
                            Directory with generator configuration named other than this parameter value will not be operable using API endpoints.`}
            maw="500px"
          />
        }
        placeholder="file name (e.g. generator.yml)"
        {...form.getInputProps('generator_config_filename')}
        key={form.key('generator_config_filename')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to generators directory"
            tooltip="Absolute path to directory with generators configuration files"
          />
        }
        placeholder="/path/to/generators/"
        {...form.getInputProps('generators_dir')}
        key={form.key('generators_dir')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to startup file"
            tooltip="Absolute path to file with list of generators to run at startup"
          />
        }
        placeholder="/path/to/startup.yml"
        {...form.getInputProps('startup')}
        key={form.key('startup')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to keyring file"
            tooltip="Absolute path to keyring encrypted file with stored secrets"
          />
        }
        placeholder="/path/to/cryptfile_pass.cfg"
        {...form.getInputProps('keyring_cryptfile')}
        key={form.key('keyring_cryptfile')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to logs directory"
            tooltip="Absolute path to logs directory"
          />
        }
        placeholder="/path/to/logs/"
        {...form.getInputProps('logs')}
        key={form.key('logs')}
      />
    </Stack>
  );
};
