import {
  Avatar,
  Group,
  Menu,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import {
  IconChevronDown,
  IconInfoCircle,
  IconLogout,
} from '@tabler/icons-react';
import { FC } from 'react';

interface UserMenuProps {
  username: string;
  onOpenAboutModal: () => void;
  onSignOut: () => void;
}

export const UserMenu: FC<UserMenuProps> = ({
  username,
  onOpenAboutModal,
  onSignOut,
}) => {
  return (
    <Menu>
      <Menu.Target>
        <UnstyledButton>
          <Group gap="xs" wrap="nowrap">
            {/* Narrow headers keep the avatar alone as the menu target - the
                name and role are the first things worth their width. */}
            <Stack gap="0" visibleFrom="xs">
              <Group gap="0" wrap="nowrap">
                <Text
                  size="sm"
                  fw={600}
                  mr="2px"
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {username}
                </Text>
                <IconChevronDown size="16px" />
              </Group>
              <Text size="xs" fw={500} style={{ whiteSpace: 'nowrap' }}>
                Internal user
              </Text>
            </Stack>

            <Avatar ml="0" color="primary">
              {username.charAt(0).toUpperCase()}
            </Avatar>
          </Group>
        </UnstyledButton>
      </Menu.Target>

      <Menu.Dropdown w="195px">
        <Menu.Label>Application</Menu.Label>
        <Menu.Item
          leftSection={<IconInfoCircle size="19px" />}
          onClick={onOpenAboutModal}
        >
          About
        </Menu.Item>
        <Menu.Divider />
        <Menu.Item leftSection={<IconLogout size="19px" />} onClick={onSignOut}>
          Sign out
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
