import {
  ActionIcon,
  Group,
  Menu,
  PasswordInput,
  PasswordInputProps,
  ScrollArea,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { IconEye, IconEyeOff, IconKey, IconSearch } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { useSecretNames } from '@/api/hooks/useSecrets';
import {
  isReferenceable,
  isSecretReference,
  secretReference,
} from '@/utils/secretReference';

// Number of secrets from which the dropdown is worth searching.
const SEARCHABLE_FROM = 8;

export interface SecretPasswordInputProps extends Omit<
  PasswordInputProps,
  'value' | 'onChange' | 'rightSection' | 'visible'
> {
  value?: string;
  /** Called with the value itself rather than with the event, so a
   *  secret picked from the dropdown arrives the same way typing
   *  does. */
  onChange: (value: string) => void;
  /** Opens the page secrets are managed on. Passed in rather than
   *  navigated to here: modal content is rendered outside the
   *  router. */
  onOpenSecrets?: () => void;
}

/**
 * Password field that either holds the value or names the keyring
 * secret holding it. The dropdown writes the reference, so the syntax
 * does not have to be known to use a secret here.
 */
export const SecretPasswordInput: FC<SecretPasswordInputProps> = ({
  value,
  onChange,
  onOpenSecrets,
  ...props
}) => {
  const { data: secretNames } = useSecretNames();
  const [revealed, setRevealed] = useState(false);
  const [query, setQuery] = useState('');

  const names = secretNames ?? [];
  const searchable = names.length > SEARCHABLE_FROM;
  const matching = searchable
    ? names.filter((name) =>
        name.toLowerCase().includes(query.trim().toLowerCase())
      )
    : names;

  // A reference names a secret instead of carrying one, so there is
  // nothing behind the mask to keep.
  const reference = isSecretReference(value);

  return (
    <PasswordInput
      {...props}
      value={value ?? ''}
      onChange={(event) => onChange(event.currentTarget.value)}
      visible={reference || revealed}
      rightSectionWidth={reference ? 34 : 62}
      rightSectionPointerEvents="all"
      rightSection={
        <Group gap={0} wrap="nowrap" justify="flex-end">
          {!reference && (
            <ActionIcon
              variant="subtle"
              color="gray"
              size="sm"
              aria-label={revealed ? 'Hide the password' : 'Show the password'}
              onClick={() => setRevealed((shown) => !shown)}
            >
              {revealed ? <IconEyeOff size={16} /> : <IconEye size={16} />}
            </ActionIcon>
          )}
          <Menu
            position="bottom-end"
            shadow="md"
            width={240}
            onClose={() => setQuery('')}
          >
            <Menu.Target>
              <Tooltip label="Use a keyring secret" openDelay={400}>
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="sm"
                  aria-label="Use a keyring secret"
                >
                  <IconKey size={16} />
                </ActionIcon>
              </Tooltip>
            </Menu.Target>
            <Menu.Dropdown>
              {searchable && (
                <TextInput
                  size="xs"
                  mb={4}
                  placeholder="Search secrets"
                  leftSection={<IconSearch size={14} />}
                  value={query}
                  onChange={(event) => setQuery(event.currentTarget.value)}
                />
              )}
              {names.length === 0 ? (
                <Menu.Item disabled>The keyring holds no secrets yet</Menu.Item>
              ) : (
                <ScrollArea.Autosize mah={220} type="auto">
                  {matching.length === 0 ? (
                    <Menu.Item disabled>No secret of that name</Menu.Item>
                  ) : (
                    matching.map((name) =>
                      isReferenceable(name) ? (
                        <Menu.Item
                          key={name}
                          onClick={() => onChange(secretReference(name))}
                        >
                          {name}
                        </Menu.Item>
                      ) : (
                        <Menu.Item
                          key={name}
                          disabled
                          title={
                            'A name holding a space or a closing brace ' +
                            'cannot be referenced'
                          }
                        >
                          {name}
                        </Menu.Item>
                      )
                    )
                  )}
                </ScrollArea.Autosize>
              )}
              {onOpenSecrets && (
                <>
                  <Menu.Divider />
                  <Menu.Item onClick={onOpenSecrets}>Manage secrets</Menu.Item>
                </>
              )}
            </Menu.Dropdown>
          </Menu>
        </Group>
      }
    />
  );
};
