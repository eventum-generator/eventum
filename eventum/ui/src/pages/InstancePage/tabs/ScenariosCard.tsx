import {
  ActionIcon,
  Button,
  Divider,
  Group,
  Menu,
  Stack,
  Text,
} from '@mantine/core';
import { IconLayersSubtract, IconPlus, IconX } from '@tabler/icons-react';
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
 * Scenario membership for one instance, shown as a list. Membership is shared
 * startup state, so add and remove apply immediately (the settings form never
 * touches it).
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
    <Stack gap="xs">
      {memberScenarios.length === 0 ? (
        <Text size="sm" c="dimmed">
          Not part of any scenario.
        </Text>
      ) : (
        <Stack gap={0}>
          {memberScenarios.map((name, i) => (
            <div key={name}>
              {i > 0 && <Divider />}
              <Group justify="space-between" wrap="nowrap" gap="sm" py={8}>
                <RecordNameLink
                  to={`${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(name)}`}
                >
                  <Group gap={8} wrap="nowrap" align="center">
                    <IconLayersSubtract size={15} style={{ flexShrink: 0 }} />
                    <Text size="sm" fw={500} truncate>
                      {name}
                    </Text>
                  </Group>
                </RecordNameLink>
                <ActionIcon
                  size="sm"
                  variant="subtle"
                  color="gray"
                  title="Remove from scenario"
                  onClick={() => handleRemove(name)}
                >
                  <IconX size={14} />
                </ActionIcon>
              </Group>
            </div>
          ))}
        </Stack>
      )}

      {memberScenarios.length > 0 && <Divider />}

      <Menu shadow="md" width={200} position="bottom-start">
        <Menu.Target>
          <Button
            variant="subtle"
            size="compact-sm"
            leftSection={<IconPlus size={15} />}
            disabled={available.length === 0}
            style={{ alignSelf: 'flex-start' }}
          >
            Add to scenario
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
    </Stack>
  );
};
