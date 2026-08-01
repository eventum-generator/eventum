import { Button, Group, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { FC, ReactNode } from 'react';

export interface RenameModalProps {
  /** Label of the name input, e.g. "New scenario name". */
  label: string;
  /** Current name of the object being renamed. */
  currentName: string;
  /** Names already in use - the new name must not be one of them. */
  takenNames: string[];
  /** Rendered above the input: warnings, affected-object lists. */
  children?: ReactNode;
  /** Names must match this pattern when it is provided. */
  pattern?: RegExp;
  /** Message shown when the name does not match `pattern`. */
  patternError?: string;
  isPending: boolean;
  onRename: (newName: string) => void;
}

/**
 * Form shell shared by every rename dialog: one name input validated
 * against the current name, the names already in use, and an optional
 * pattern. Callers own the mutation and its notifications.
 */
export const RenameModal: FC<RenameModalProps> = ({
  label,
  currentName,
  takenNames,
  children,
  pattern,
  patternError,
  isPending,
  onRename,
}) => {
  const form = useForm<{ newName: string }>({
    initialValues: { newName: currentName },
    validate: {
      newName: (value) => {
        const name = value.trim();

        if (!name) {
          return 'Name is required';
        }

        if (name === currentName) {
          return 'Name is unchanged';
        }

        if (pattern !== undefined && !pattern.test(name)) {
          return patternError ?? 'Name has invalid format';
        }

        if (takenNames.includes(name)) {
          return 'This name is already taken';
        }

        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  return (
    <form onSubmit={form.onSubmit((values) => onRename(values.newName.trim()))}>
      <Stack>
        {children}

        <TextInput
          label={label}
          placeholder={currentName}
          required
          data-autofocus
          {...form.getInputProps('newName')}
        />

        <Group justify="end">
          <Button disabled={!form.isValid()} loading={isPending} type="submit">
            Rename
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
