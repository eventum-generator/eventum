import { Button, Group, Modal, Text } from '@mantine/core';
import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';

import { CONFIRM } from '@/theme/copy';

interface UnsavedChangesPromptProps {
  /** When true, leaving the page is guarded. Reflect the page's dirty state. */
  when: boolean;
  message?: string;
}

/**
 * Guards a page against losing unsaved changes. Intercepts in-app navigation
 * (sidebar, links, the back button) with a confirm modal, and warns on
 * browser unload (refresh / tab close) via the browser's native prompt.
 * Render it inside the page, passing the page's dirty state as `when`.
 */
export function UnsavedChangesPrompt({
  when,
  message = CONFIRM.unsavedChanges.body,
}: Readonly<UnsavedChangesPromptProps>) {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      when && currentLocation.pathname !== nextLocation.pathname
  );

  // Refresh / tab close: only the browser's native prompt is possible here.
  useEffect(() => {
    if (!when) {
      return;
    }
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    globalThis.addEventListener('beforeunload', handler);
    return () => globalThis.removeEventListener('beforeunload', handler);
  }, [when]);

  const blocked = blocker.state === 'blocked';

  return (
    <Modal
      opened={blocked}
      onClose={() => blocker.reset?.()}
      title={CONFIRM.unsavedChanges.title}
    >
      <Text size="sm">{message}</Text>
      <Group justify="flex-end" mt="lg">
        <Button variant="default" onClick={() => blocker.reset?.()}>
          Stay
        </Button>
        <Button onClick={() => blocker.proceed?.()}>Leave</Button>
      </Group>
    </Modal>
  );
}
