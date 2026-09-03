import { NumberInput, Select, Stack } from '@mantine/core';
import { FC } from 'react';

import { ProjectFileSelect } from '../../../components/ProjectFileSelect';
import {
  EncoderConfig,
  Encoding,
  JSON_LINES_COMPRESSIONS,
  MAX_GZIP_COMPRESSION_LEVEL,
  MAX_ZSTD_COMPRESSION_LEVEL,
  PARQUET_COMPRESSIONS,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/s3';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface S3EncoderParamsProps {
  value: EncoderConfig | undefined;
  onChange: (config: EncoderConfig | undefined) => void;
}

/** Sub-form of the `encoder` field of the s3 output plugin. */

/** Maximum compression level the selected algorithm takes. */
function maxCompressionLevel(compression: string | undefined): number {
  return compression === 'gzip'
    ? MAX_GZIP_COMPRESSION_LEVEL
    : MAX_ZSTD_COMPRESSION_LEVEL;
}

export const S3EncoderParams: FC<S3EncoderParamsProps> = ({
  value,
  onChange,
}) => {
  const compression =
    typeof value?.compression === 'string' ? value.compression : undefined;

  return (
    <Stack gap="xs">
      <Select
        label={
          <LabelWithTooltip
            label="Encoding"
            tooltip="Encoding of object bodies, JSON Lines is used by default"
          />
        }
        placeholder="encoding"
        data={[Encoding.JSONLines, Encoding.Parquet]}
        clearable
        value={value?.encoding ?? null}
        onChange={(encoding) => {
          if (encoding === null) {
            // eslint-disable-next-line unicorn/no-useless-undefined
            onChange(undefined);
            return;
          }

          onChange({ encoding } as EncoderConfig);
        }}
      />

      {value?.encoding === Encoding.JSONLines && (
        <>
          <Select
            label={
              <LabelWithTooltip
                label="Compression"
                tooltip="Compression applied to the whole object, the extension
                of the key follows it"
              />
            }
            data={[...JSON_LINES_COMPRESSIONS]}
            value={compression ?? 'none'}
            onChange={(selected) =>
              onChange({
                encoding: value.encoding,
                compression:
                  (selected as (typeof JSON_LINES_COMPRESSIONS)[number]) ??
                  undefined,
              })
            }
          />

          {compression !== undefined && compression !== 'none' && (
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Compression level"
                  tooltip="Compression level, the default level of the selected
                  algorithm is used when not set"
                />
              }
              placeholder="number"
              min={1}
              max={maxCompressionLevel(compression)}
              step={1}
              allowDecimal={false}
              value={
                typeof value.compression_level === 'number'
                  ? value.compression_level
                  : ''
              }
              onChange={(level) =>
                onChange({
                  ...value,
                  compression_level:
                    typeof level === 'number' ? level : undefined,
                })
              }
            />
          )}
        </>
      )}

      {value?.encoding === Encoding.Parquet && (
        <>
          <Select
            label={
              <LabelWithTooltip
                label="Compression"
                tooltip="Compression applied to the columns inside the file,
                snappy is used by default"
              />
            }
            data={[...PARQUET_COMPRESSIONS]}
            value={compression ?? 'snappy'}
            onChange={(selected) =>
              onChange({
                ...value,
                compression:
                  (selected as (typeof PARQUET_COMPRESSIONS)[number]) ??
                  undefined,
              })
            }
          />

          <NumberInput
            label={
              <LabelWithTooltip
                label="Row group size"
                tooltip="Maximum number of rows in a row group of the file,
                default value is 100000"
              />
            }
            placeholder="number"
            min={1}
            step={1}
            allowDecimal={false}
            value={
              typeof value.row_group_size === 'number'
                ? value.row_group_size
                : ''
            }
            onChange={(size) =>
              onChange({
                ...value,
                row_group_size: typeof size === 'number' ? size : undefined,
              })
            }
          />

          <ProjectFileSelect
            label={
              <LabelWithTooltip
                label="Schema file"
                tooltip="File with one representative event, the schema of every
                object is taken from it, otherwise it is inferred from the first
                batch of events and kept for the rest of the run"
              />
            }
            placeholder=".json"
            extensions={['.json']}
            clearable
            searchable
            value={value.schema_path ?? null}
            onChange={(path) =>
              onChange({ ...value, schema_path: path ?? undefined })
            }
          />
        </>
      )}
    </Stack>
  );
};
