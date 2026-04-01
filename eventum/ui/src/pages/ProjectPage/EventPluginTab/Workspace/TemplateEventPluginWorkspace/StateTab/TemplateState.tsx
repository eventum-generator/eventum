import { FC } from 'react';

import { KeyValueTable } from '@/components/state';

export interface TemplateStateProps {
  stateName: string;
  data: Record<string, unknown> | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isSuccess: boolean;
  refetch: () => void;
  onUpdateKey: (key: string, value: unknown) => void;
  onDeleteKey: (key: string) => void;
  onClear: () => void;
  isClearPending: boolean;
}

export const TemplateState: FC<TemplateStateProps> = ({
  stateName,
  data,
  isLoading,
  isError,
  error,
  isSuccess,
  refetch,
  onUpdateKey,
  onDeleteKey,
  onClear,
  isClearPending,
}) => {
  return (
    <KeyValueTable
      data={data}
      isLoading={isLoading}
      isError={isError}
      error={error}
      isSuccess={isSuccess}
      onRefetch={() => void refetch()}
      onUpdateKey={onUpdateKey}
      onDeleteKey={onDeleteKey}
      onAddKey={onUpdateKey}
      onClear={onClear}
      title={stateName}
      titleOrder={6}
      isClearPending={isClearPending}
      errorTitle="Failed to load state, ensure debugger is started"
      compact
    />
  );
};
