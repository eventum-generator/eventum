import { CodeHighlight } from '@mantine/code-highlight';
import {
  Anchor,
  Badge,
  Box,
  Code,
  Collapse,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconArrowDownLeft, IconArrowUpRight } from '@tabler/icons-react';
import { FC, Fragment, ReactNode } from 'react';

import { ReportedExchange, describeAPIError } from '@/api/errorReport';
import { APIError, ValidationIssue } from '@/api/errors';

export interface APIErrorModalContentProps {
  error: unknown;
}

const HEAD_ICON = { size: 16, stroke: 1.6 };

/** Uppercase muted field heading, matching the app-wide grammar. */
const FieldLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);

/** Stands in for a payload there is nothing to highlight in. */
const PayloadNote: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="sm" c="dimmed" fs="italic">
    {children}
  </Text>
);

// Clipping a payload earns its place only when it is long enough to
// bury the rest of the dialog.
const COLLAPSE_LINES = 12;

const JSONBlock: FC<{ value: unknown }> = ({ value }) => {
  const code = JSON.stringify(value, undefined, 2);
  const long = code.split('\n').length > COLLAPSE_LINES;

  return (
    <CodeHighlight
      language="json"
      code={code}
      withExpandButton={long}
      defaultExpanded={!long}
      expandCodeLabel="Expand"
      collapseCodeLabel="Collapse"
    />
  );
};

// A payload that travels as text is re-indented when it is JSON, and
// shown as it came when it is not.
const TextPayload: FC<{ text: string }> = ({ text }) => {
  try {
    return <JSONBlock value={JSON.parse(text) as unknown} />;
  } catch {
    return <Code block>{text}</Code>;
  }
};

// The request body is already serialized by the time the error carries
// it. Anything the client streams instead - a form, a file - has no
// text to show.
const RequestBody: FC<{ data: unknown }> = ({ data }) => {
  if (data === undefined) {
    return <PayloadNote>Empty</PayloadNote>;
  }

  return typeof data === 'string' ? (
    <TextPayload text={data} />
  ) : (
    <PayloadNote>Form or file upload</PayloadNote>
  );
};

// The response body arrives parsed, unless the request asked for text.
const ResponseBody: FC<{ data: unknown }> = ({ data }) => {
  if (data === undefined || data === '') {
    return <PayloadNote>Empty</PayloadNote>;
  }

  return typeof data === 'string' ? (
    <TextPayload text={data} />
  ) : (
    <JSONBlock value={data} />
  );
};

const IssueList: FC<{ issues: ValidationIssue[] }> = ({ issues }) => (
  <Stack gap="2px">
    {issues.map((issue, index) => (
      <Text size="sm" key={`${index}:${issue.path}`}>
        {issue.path === '' ? (
          issue.message
        ) : (
          <>
            <Code>{issue.path}</Code> {issue.message}
          </>
        )}
      </Text>
    ))}
  </Stack>
);

/** Header pairs as they went over the wire, key beside value. */
const HeaderGrid: FC<{ headers: unknown }> = ({ headers }) => {
  const entries =
    typeof headers === 'object' && headers !== null
      ? Object.entries(headers as Record<string, unknown>)
      : [];

  if (entries.length === 0) {
    return <PayloadNote>None</PayloadNote>;
  }

  return (
    <Box
      style={{
        display: 'grid',
        gridTemplateColumns: 'auto minmax(0, 1fr)',
        columnGap: 'var(--mantine-spacing-md)',
        rowGap: '2px',
      }}
    >
      {entries.map(([name, value]) => (
        <Fragment key={name}>
          <Text size="xs" ff="monospace" c="dimmed">
            {name}
          </Text>
          <Text size="xs" ff="monospace" style={{ wordBreak: 'break-all' }}>
            {typeof value === 'string' ? value : JSON.stringify(value)}
          </Text>
        </Fragment>
      ))}
    </Box>
  );
};

/** The request line: what was called, and how. */
const RequestLine: FC<{ exchange: ReportedExchange }> = ({ exchange }) => (
  <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
    <Badge variant="default" size="sm">
      {exchange.method ?? 'Request'}
    </Badge>
    <Text size="sm" ff="monospace" style={{ wordBreak: 'break-all' }}>
      {exchange.url ?? '-'}
    </Text>
  </Group>
);

// A status names its own severity: a rejected request is a warning,
// a server that failed is not.
function statusColor(status: number): string {
  if (status >= 500) {
    return 'red';
  }

  return status >= 400 ? 'yellow' : 'green';
}

/** The status line: what came back, and what it is called. */
const StatusLine: FC<{ status: number; title: string }> = ({
  status,
  title,
}) => (
  <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
    <Badge variant="light" color={statusColor(status)} size="sm">
      {status}
    </Badge>
    <Text size="sm">{title}</Text>
  </Group>
);

/** One direction of the exchange: its line, its headers, its body. */
const ExchangeCard: FC<{
  icon: ReactNode;
  line: ReactNode;
  headers: unknown;
  body: ReactNode;
}> = ({ icon, line, headers, body }) => (
  <Paper withBorder p="sm">
    <Stack gap="xs">
      <Group gap="xs" wrap="nowrap" align="center">
        <Box c="dimmed" style={{ display: 'flex' }}>
          {icon}
        </Box>
        {line}
      </Group>

      <Divider />

      <Stack gap="4px">
        <FieldLabel>Headers</FieldLabel>
        <HeaderGrid headers={headers} />
      </Stack>

      <Stack gap="4px">
        <FieldLabel>Body</FieldLabel>
        {body}
      </Stack>
    </Stack>
  </Paper>
);

const RawExchange: FC<{
  error: APIError;
  exchange: ReportedExchange;
  opened: boolean;
  onToggle: () => void;
}> = ({ error, exchange, opened, onToggle }) => {
  const requestConfig = error.requestConfig;
  const response = error.response;

  const label =
    requestConfig === undefined
      ? 'raw response'
      : response === undefined
        ? 'raw request'
        : 'raw request and response';

  return (
    <Stack gap="4px">
      <Group>
        <Anchor component="button" type="button" size="sm" onClick={onToggle}>
          {opened ? `Hide ${label}` : `Show ${label}`}
        </Anchor>
      </Group>

      <Collapse in={opened}>
        <Stack gap="sm" pt="4px">
          {requestConfig !== undefined && (
            <ExchangeCard
              icon={<IconArrowUpRight {...HEAD_ICON} />}
              line={<RequestLine exchange={exchange} />}
              headers={requestConfig.headers}
              body={<RequestBody data={requestConfig.data as unknown} />}
            />
          )}

          {response !== undefined && (
            <ExchangeCard
              icon={<IconArrowDownLeft {...HEAD_ICON} />}
              line={
                <StatusLine status={response.status} title={error.message} />
              }
              headers={response.headers}
              body={<ResponseBody data={response.data as unknown} />}
            />
          )}
        </Stack>
      </Collapse>
    </Stack>
  );
};

const APIErrorReport: FC<{ error: APIError }> = ({ error }) => {
  const report = describeAPIError(error);
  const exchange = report.exchange;
  const [rawOpened, { toggle: toggleRaw }] = useDisclosure(false);

  return (
    <Stack gap="sm">
      <Stack gap="4px">
        <Text size="sm">{report.reported}</Text>
        {report.details !== undefined && (
          <Text size="sm" c="dimmed">
            {report.details}
          </Text>
        )}
      </Stack>

      {report.context !== undefined && <JSONBlock value={report.context} />}

      {report.issues.length > 0 && <IssueList issues={report.issues} />}

      {exchange !== undefined && !rawOpened && (
        <Text size="sm" c="dimmed">
          <Code>
            {exchange.method ?? '-'} {exchange.url ?? '-'}
          </Code>{' '}
          {exchange.status === undefined
            ? 'did not respond'
            : `responded ${exchange.status}${
                exchange.title === undefined ? '' : ` ${exchange.title}`
              }`}
        </Text>
      )}

      {exchange !== undefined && (
        <RawExchange
          error={error}
          exchange={exchange}
          opened={rawOpened}
          onToggle={toggleRaw}
        />
      )}
    </Stack>
  );
};

export const APIErrorModalContent: FC<APIErrorModalContentProps> = ({
  error,
}) => {
  if (error instanceof APIError) {
    return <APIErrorReport error={error} />;
  } else if (error instanceof Error) {
    return <>{error.message}</>;
  } else {
    return <>Unknown error: {typeof error}</>;
  }
};
