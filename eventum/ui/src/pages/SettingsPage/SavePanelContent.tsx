import { Button, Group, Title } from '@mantine/core';
import { FC } from 'react';

interface SavePanelProps {
  onSave: () => void;
}

export const SavePanel: FC<SavePanelProps> = ({ onSave }) => {
  return (
    <Group align="center" justify="space-between" w="100%" mx="md">
      <Group mah="50px">
        <Title size="sm">There are unsaved changes</Title>
      </Group>
      <Button onClick={onSave}>Save</Button>
    </Group>
  );
};
