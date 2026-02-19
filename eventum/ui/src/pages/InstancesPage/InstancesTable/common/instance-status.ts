import { DefaultMantineColor } from '@mantine/core';

import { GeneratorStatus } from '@/api/routes/generators/schemas';

export function describeInstanceStatus(status: GeneratorStatus): {
  text: string;
  color: DefaultMantineColor;
  processing: boolean;
} {
  let text = 'Inactive';
  let color: DefaultMantineColor = 'gray.6';
  let processing = false;

  if (status.is_initializing) {
    text = 'Starting';
    color = 'yellow.7';
    processing = true;
  } else if (status.is_stopping) {
    text = 'Stopping';
    color = 'yellow.7';
    processing = true;
  } else if (status.is_running) {
    text = 'Active';
    color = 'green.6';
  } else if (status.is_ended_up) {
    if (status.is_ended_up_successfully) {
      text = 'Finished';
      color = '#1c5427';
    } else {
      text = 'Failed';
      color = '#910606';
    }
  }

  return { text, color, processing };
}
