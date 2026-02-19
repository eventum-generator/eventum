import { Button, Checkbox, Group, Stack, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { FC } from 'react';

interface RemoveTemplateModalProps {
  templateName: string;
  filePath?: string;
  onDelete: ({ isRemoveFile }: { isRemoveFile: boolean }) => void;
  isDeleting: boolean;
}

export const RemoveTemplateModal: FC<RemoveTemplateModalProps> = ({
  templateName,
  filePath,
  onDelete,
  isDeleting,
}) => {
  const form = useForm<{ isRemoveFile: boolean }>({
    initialValues: {
      isRemoveFile: false,
    },
    onSubmitPreventDefault: 'always',
  });

  return (
    <form onSubmit={form.onSubmit(onDelete)}>
      <Stack>
        <Text size="sm">
          Template <b>{templateName}</b> will be deleted. Do you want to
          continue?
        </Text>
        <Stack gap="4px">
          <Checkbox
            label="Delete template file"
            disabled={filePath === undefined}
            {...form.getInputProps('isRemoveFile', {
              type: 'checkbox',
            })}
          />
          {form.getValues().isRemoveFile && (
            <Text size="sm" c="gray.6">
              File <b>{filePath}</b> will be removed
            </Text>
          )}
        </Stack>
        <Group justify="end">
          <Button type="submit" loading={isDeleting}>
            Confirm
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
