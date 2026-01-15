import { ActionIcon, Group, Select, Stack, Text } from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { modals } from '@mantine/modals';
import { IconPlus } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { AddSampleModal } from './AddSampleModal';
import { SamplesParams } from './SamplesParams';
import { TemplateEventPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface SamplesSectionProps {
  form: UseFormReturnType<TemplateEventPluginConfig>;
}

export const SamplesSection: FC<SamplesSectionProps> = ({ form }) => {
  const [selectedSample, setSelectedSample] = useState<string | null>(null);
  const { projectName } = useProjectName();

  const existingSamples = Object.keys(form.getValues().samples ?? {});

  return (
    <Stack gap="xs">
      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Samples
        </Text>
        <Group align="end" wrap="nowrap" gap="xs">
          <Select
            label="Select sample to edit"
            data={existingSamples}
            value={selectedSample}
            onChange={setSelectedSample}
            searchable
            nothingFoundMessage="No samples found"
            placeholder="sample name"
            w="100%"
            clearable
          />
          <ActionIcon
            title="Adding sample"
            size="lg"
            variant="default"
            onClick={() => {
              modals.open({
                title: 'Add new sample',
                children: (
                  <ProjectNameProvider initialProjectName={projectName}>
                    <AddSampleModal
                      existingSamples={existingSamples}
                      onAdd={(sampleName, sampleConfig) => {
                        form.setFieldValue('samples', (value) => ({
                          ...value,
                          [sampleName]: sampleConfig,
                        }));

                        modals.closeAll();

                        setSelectedSample(sampleName);
                      }}
                    />
                  </ProjectNameProvider>
                ),
                size: 'md',
              });
            }}
          >
            <IconPlus size={20} />
          </ActionIcon>
        </Group>
      </Stack>

      {selectedSample !== null && existingSamples.includes(selectedSample) && (
        <SamplesParams
          key={selectedSample}
          value={form.values.samples![selectedSample]!}
          onChange={(value) =>
            form.setFieldValue('samples', (prevValue) => {
              return { ...prevValue, [selectedSample]: value };
            })
          }
          onDelete={() => {
            modals.openConfirmModal({
              title: 'Deleting sample',
              children: (
                <Text size="sm">
                  Sample <b>{selectedSample}</b> will be deleted. Do you want to
                  continue?
                </Text>
              ),
              labels: { confirm: 'Confirm', cancel: 'Cancel' },
              onConfirm: () => {
                form.setFieldValue('samples', (prevValue) => {
                  const newValue = { ...prevValue };
                  delete newValue[selectedSample];

                  if (Object.keys(newValue).length === 0) {
                    return;
                  }
                  return newValue;
                });
                setSelectedSample(null);
              },
            });
          }}
        />
      )}
    </Stack>
  );
};
