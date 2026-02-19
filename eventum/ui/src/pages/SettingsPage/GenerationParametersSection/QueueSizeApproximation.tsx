import { Alert, Box, List, NumberInput } from '@mantine/core';
import { IconCalculator } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useState } from 'react';

import { QueueParameters } from '@/api/routes/instance/schemas';

interface QueueSizeApproximationProps {
  batchSize: number | null | undefined;
  queueParams: QueueParameters | undefined;
}

export const QueueSizeApproximation: FC<QueueSizeApproximationProps> = ({
  batchSize,
  queueParams,
}) => {
  const [eventSize, setEventSize] = useState<number>(1000);

  return (
    <Alert
      variant="default"
      icon={<Box c="blue" component={IconCalculator}></Box>}
      title="Size approximation"
    >
      With event size{' '}
      <NumberInput
        w="80px"
        allowDecimal={false}
        value={eventSize}
        onChange={(value) =>
          setEventSize(typeof value === 'number' ? value : 0)
        }
        min={1}
        step={1}
        display="inline-block"
        size="xs"
        mx="4px"
        hideControls
        variant="filled"
        style={{
          input: {
            textAlign: 'right',
          },
        }}
      />{' '}
      bytes full queues for one generator will consume:
      <List size="sm">
        <List.Item>
          Timestamps queue ~
          <b>
            {batchSize && queueParams?.max_timestamp_batches
              ? bytes(batchSize * queueParams.max_timestamp_batches * 16, {
                  decimalPlaces: 2,
                })
              : ' unknown'}
          </b>
        </List.Item>
        <List.Item>
          Events queue ~
          <b>
            {batchSize && queueParams?.max_event_batches
              ? bytes(batchSize * queueParams.max_event_batches * eventSize, {
                  decimalPlaces: 2,
                })
              : ' unknown'}
          </b>
        </List.Item>
      </List>
    </Alert>
  );
};
