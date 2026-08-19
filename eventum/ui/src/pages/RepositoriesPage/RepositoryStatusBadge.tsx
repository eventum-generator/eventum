import { Badge, Tooltip } from '@mantine/core';
import { FC } from 'react';

import { RepositoryStatus } from '@/api/routes/repositories/schemas';

interface RepositoryStatusBadgeProps {
  status: RepositoryStatus;
  isChecking: boolean;
}

/**
 * Whether the repository answered the last time it was asked. Every
 * repository on this page is connected, so what the badge adds is
 * whether the remote behind it is there: it is checked when connected
 * and whenever the page is opened.
 */
export const RepositoryStatusBadge: FC<RepositoryStatusBadgeProps> = ({
  status,
  isChecking,
}) => {
  if (isChecking) {
    return (
      <Badge size="sm" variant="light" color="gray">
        Checking
      </Badge>
    );
  }

  if (status.state === 'available') {
    return (
      <Tooltip
        label={
          status.checked_at
            ? `Checked ${new Date(status.checked_at).toLocaleString()}`
            : 'The repository answered'
        }
      >
        <Badge size="sm" variant="light" color="green">
          Reachable
        </Badge>
      </Tooltip>
    );
  }

  if (status.state === 'unavailable') {
    return (
      <Tooltip
        label={status.reason ?? 'The repository did not answer'}
        multiline
        w={320}
      >
        <Badge size="sm" variant="light" color="red">
          Unreachable
        </Badge>
      </Tooltip>
    );
  }

  return (
    <Badge size="sm" variant="light" color="gray">
      Not checked
    </Badge>
  );
};
