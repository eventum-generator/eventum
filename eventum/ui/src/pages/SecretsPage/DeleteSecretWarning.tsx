import { Code, Text } from '@mantine/core';
import { FC } from 'react';

import { SecretReferenceList } from './SecretReferenceList';
import { CONFIRM } from '@/theme/copy';

interface DeleteSecretWarningProps {
  secretName: string;
}

/**
 * Body of the delete confirmation: what the removal is about to break.
 *
 * Removing a secret is irreversible and cannot repoint anything, so
 * the list is the whole point of the dialog - both kinds of referrer
 * keep the name and stop working once the value behind it is gone.
 */
export const DeleteSecretWarning: FC<DeleteSecretWarningProps> = ({
  secretName,
}) => (
  <>
    <Text size="sm" mb="sm">
      {CONFIRM.deleteSecret.body(secretName)}
    </Text>

    <SecretReferenceList
      secretName={secretName}
      projectsNote={
        <>
          These projects read the secret as{' '}
          <Code>{`\${secrets.${secretName}}`}</Code> and fail to load until a
          secret of that name exists again.
        </>
      }
      repositoriesNote={
        <>
          These connected repositories authenticate with the secret and stop
          answering until a secret of that name exists again.
        </>
      }
      noneNote="Nothing reads this secret."
    />
  </>
);
