import { notifications } from '@mantine/notifications';

import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export function showSuccessNotification(title: string, message: string) {
  notifications.show({ title, message, color: 'green' });
}

export function showErrorNotification(title: string, error: Error) {
  notifications.show({
    title,
    message: (
      <>
        {title}
        <ShowErrorDetailsAnchor error={error} prependDot />
      </>
    ),
    color: 'red',
  });
}
