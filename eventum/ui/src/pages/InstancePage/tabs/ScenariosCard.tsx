import { ActionIcon, Button, Group, Menu, Stack, Text } from '@mantine/core';
import { IconPlus, IconTransform, IconX } from '@tabler/icons-react';
import { FC } from 'react';

import {
  useAddGeneratorToScenarioMutation,
  useRemoveGeneratorFromScenarioMutation,
} from '@/api/hooks/useScenarios';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface ScenariosCardProps {
  instanceId: string;
  memberScenarios: string[];
  allScenarios: string[];
}

/**
 * Scenario membership for one instance, shown as an evenly-spaced list.
 * Membership is shared startup state, so add and remove apply immediately
 * (the settings form never touches it).
 */
export const ScenariosCard: FC<ScenariosCardProps> = ({
  instanceId,
  memberScenarios,
  allScenarios,
}) => {
  const addToScenario = useAddGeneratorToScenarioMutation();
  const removeFromScenario = useRemoveGeneratorFromScenarioMutation();

  const available = allScenarios.filter((s) => !memberScenarios.includes(s));

  function handleAdd(name: string) {
    addToScenario.mutate(
      { name, generatorId: instanceId },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Added to scenario'),
        onError: (error) =>
          showErrorNotification('Failed to add to scenario', error),
      }
    );
  }

  function handleRemove(name: string) {
    removeFromScenario.mutate(
      { name, generatorId: instanceId },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Removed from scenario'),
        onError: (error) =>
          showErrorNotification('Failed to remove from scenario', error),
      }
    );
  }

  return (
    <Stack gap="sm">
      {memberScenarios.length === 0 ? (
        <Text size="sm" c="dimmed">
          Not part of any scenario.
        </Text>
      ) : (
        memberScenarios.map((name) => (
          <Group key={name} justify="space-between" wrap="nowrap" gap="sm">
            <RecordNameLink
              to={`${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(name)}`}
            >
              <Group gap={8} wrap="nowrap" align="center">
                <IconTransform size={16} style={{ flexShrink: 0 }} />
                <Text size="sm" fw={500} truncate>
                  {name}
                </Text>
              </Group>
            </RecordNameLink>
            <ActionIcon
              size="sm"
              variant="subtle"
              color="var(--ev-muted)"
              title="Remove from scenario"
              onClick={() => handleRemove(name)}
            >
              <IconX size={14} color="var(--ev-muted)" />
            </ActionIcon>
          </Group>
        ))
      )}

      <Menu shadow="md" width={220} position="bottom-start">
        <Menu.Target>
          <Button
            variant="subtle"
            leftSection={<IconPlus size={16} />}
            disabled={available.length === 0}
            style={{ alignSelf: 'flex-start' }}
            mt={memberScenarios.length > 0 ? 4 : 0}
          >
            Add to scenario
          </Button>
        </Menu.Target>
        <Menu.Dropdown>
          {available.map((name) => (
            <Menu.Item
              key={name}
              leftSection={<IconTransform size={14} />}
              onClick={() => handleAdd(name)}
            >
              {name}
            </Menu.Item>
          ))}
        </Menu.Dropdown>
      </Menu>
    </Stack>
  );
};
