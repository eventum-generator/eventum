import { ActionIcon, Anchor, Button, Group, Menu, Text } from '@mantine/core';
import { IconLayersSubtract, IconPlus, IconX } from '@tabler/icons-react';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import {
  useAddGeneratorToScenarioMutation,
  useRemoveGeneratorFromScenarioMutation,
} from '@/api/hooks/useScenarios';
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
 * Scenario membership for one instance: chips linking to each scenario, with
 * inline add / remove. Membership is shared startup state, so add and remove
 * apply immediately (the settings form never touches it).
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

  const addMenu = (
    <Menu shadow="md" width={200} position="bottom-end">
      <Menu.Target>
        <Button
          variant="subtle"
          size="compact-sm"
          leftSection={<IconPlus size={15} />}
          disabled={available.length === 0}
        >
          Add
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        {available.map((name) => (
          <Menu.Item
            key={name}
            leftSection={<IconLayersSubtract size={14} />}
            onClick={() => handleAdd(name)}
          >
            {name}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );

  return (
    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
      {memberScenarios.length === 0 ? (
        <Text size="sm" c="dimmed">
          Not part of any scenario.
        </Text>
      ) : (
        <Group gap={8}>
          {memberScenarios.map((name) => (
            <Group
              key={name}
              gap={4}
              wrap="nowrap"
              align="center"
              style={{
                border: '1px solid var(--ev-border)',
                borderRadius: 999,
                padding: '2px 4px 2px 10px',
                background: 'var(--ev-surface-2)',
              }}
            >
              <Anchor
                component={Link}
                to={`${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(name)}`}
                className="ev-record-link"
                underline="never"
              >
                <Group gap={6} wrap="nowrap" align="center">
                  <IconLayersSubtract
                    size={13}
                    color="var(--ev-muted)"
                    style={{ flexShrink: 0 }}
                  />
                  <Text size="xs" fw={500}>
                    {name}
                  </Text>
                </Group>
              </Anchor>
              <ActionIcon
                size="xs"
                variant="subtle"
                color="gray"
                title="Remove from scenario"
                onClick={() => handleRemove(name)}
              >
                <IconX size={12} />
              </ActionIcon>
            </Group>
          ))}
        </Group>
      )}
      {addMenu}
    </Group>
  );
};
