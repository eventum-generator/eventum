import { Alert, List, NumberInput } from '@mantine/core';
import { IconCalculator } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useState } from 'react';

import { DEFAULT_MAX_EVENT_BYTES } from './defaults';
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

  const eventsBytes =
    batchSize && queueParams?.max_event_batches
      ? batchSize * queueParams.max_event_batches * eventSize
      : undefined;
  // An unset limit is not an absent one - the backend applies its own.
  const maxEventBytes =
    queueParams?.max_event_bytes === null
      ? undefined
      : (queueParams?.max_event_bytes ?? DEFAULT_MAX_EVENT_BYTES);
  const capped =
    eventsBytes !== undefined &&
    maxEventBytes !== undefined &&
    eventsBytes > maxEventBytes;

  return (
    <Alert
      variant="default"
      icon={<IconCalculator color="var(--mantine-color-blue-text)" />}
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
            {eventsBytes !== undefined
              ? bytes(eventsBytes, { decimalPlaces: 2 })
              : ' unknown'}
          </b>
          {capped && (
            <>
              , held to <b>{bytes(maxEventBytes, { decimalPlaces: 2 })}</b> by
              the byte limit
            </>
          )}
        </List.Item>
      </List>
    </Alert>
  );
};
