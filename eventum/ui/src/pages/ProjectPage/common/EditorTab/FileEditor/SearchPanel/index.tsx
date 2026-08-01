import {
  SearchQuery,
  closeSearchPanel,
  findNext,
  findPrevious,
  getSearchQuery,
  replaceAll,
  replaceNext,
  selectMatches,
  setSearchQuery,
} from '@codemirror/search';
import { EditorView, runScopeHandlers } from '@codemirror/view';
import {
  ActionIcon,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import {
  IconAB,
  IconChevronDown,
  IconChevronRight,
  IconChevronUp,
  IconLetterCase,
  IconRegex,
  IconReplace,
  IconReplaceFilled,
  IconSelectAll,
  IconX,
} from '@tabler/icons-react';
import {
  FC,
  KeyboardEvent,
  ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react';

import { SearchPanelHandle } from './extension';
import { MatchInfo, countMatches, formatMatchCount } from './matches';

const FIELD_WIDTH = 190;
const COUNTER_WIDTH = 54;
const ICON_SIZE = 15;

type SearchFlag = 'caseSensitive' | 'regexp' | 'wholeWord';

type QueryChanges = Partial<{
  search: string;
  replace: string;
  caseSensitive: boolean;
  regexp: boolean;
  wholeWord: boolean;
}>;

const FLAGS: { flag: SearchFlag; label: string; icon: typeof IconAB }[] = [
  { flag: 'caseSensitive', label: 'Match case', icon: IconLetterCase },
  { flag: 'regexp', label: 'Regular expression', icon: IconRegex },
  { flag: 'wholeWord', label: 'Whole word', icon: IconAB },
];

interface Snapshot {
  query: SearchQuery;
  matches: MatchInfo | null;
}

function readSnapshot(view: EditorView): Snapshot {
  const query = getSearchQuery(view.state);

  return { query, matches: countMatches(view.state, query) };
}

function withChanges(query: SearchQuery, changes: QueryChanges): SearchQuery {
  return new SearchQuery({
    search: query.search,
    caseSensitive: query.caseSensitive,
    literal: query.literal,
    regexp: query.regexp,
    replace: query.replace,
    wholeWord: query.wholeWord,
    ...changes,
  });
}

function flagChange(query: SearchQuery, flag: SearchFlag): QueryChanges {
  const changes: QueryChanges = {};
  changes[flag] = !query[flag];

  return changes;
}

function runOnEnter(event: KeyboardEvent<HTMLInputElement>, run: () => void) {
  if (event.key === 'Enter') {
    event.preventDefault();
    run();
  }
}

interface PanelIconProps {
  label: string;
  /** Set on toggles only - it also marks the control as pressed. */
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}

const PanelIcon: FC<PanelIconProps> = ({
  label,
  active,
  disabled,
  onClick,
  children,
}) => (
  <Tooltip label={label} withArrow>
    <ActionIcon
      variant={active ? 'light' : 'subtle'}
      size="sm"
      color={active ? 'primary' : 'var(--mantine-color-dimmed)'}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </ActionIcon>
  </Tooltip>
);

export interface SearchPanelProps {
  handle: SearchPanelHandle;
}

export const SearchPanel: FC<SearchPanelProps> = ({ handle }) => {
  const { view, subscribe } = handle;

  const [{ query, matches }, setSnapshot] = useState(() => readSnapshot(view));
  const [replacing, setReplacing] = useState(false);

  const queryField = useRef<HTMLInputElement>(null);

  // The editor owns the query: every edit here is dispatched to it and comes
  // back through this subscription, which also carries the changes made
  // outside the panel (selecting the next occurrence, reopening the panel).
  useEffect(
    () => subscribe(() => setSnapshot(readSnapshot(view))),
    [subscribe, view]
  );

  // Opening the panel selects the previous query so typing replaces it, and
  // marks the field CodeMirror focuses when Ctrl/Cmd-F is pressed with the
  // panel already open. The stock panel does both from its mount hook, which
  // runs before React has rendered the field into the panel.
  useEffect(() => {
    const field = queryField.current;

    if (field) {
      field.setAttribute('main-field', 'true');
      field.focus();
      field.select();
    }
  }, []);

  function commit(changes: QueryChanges) {
    view.dispatch({ effects: setSearchQuery.of(withChanges(query, changes)) });
  }

  // Keeps Escape, F3 and Ctrl/Cmd-F working while the focus is in the panel.
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (runScopeHandlers(view, event.nativeEvent, 'search-panel')) {
      event.preventDefault();
    }
  }

  const malformed = query.regexp && query.search !== '' && !query.valid;

  return (
    <Paper withBorder p={6} onKeyDown={handleKeyDown}>
      <Group gap={6} align="flex-start" wrap="nowrap">
        <ActionIcon
          variant="subtle"
          size="sm"
          color="var(--mantine-color-dimmed)"
          aria-label={replacing ? 'Hide replace' : 'Show replace'}
          aria-expanded={replacing}
          onClick={() => setReplacing((shown) => !shown)}
        >
          {replacing ? (
            <IconChevronDown size={ICON_SIZE} />
          ) : (
            <IconChevronRight size={ICON_SIZE} />
          )}
        </ActionIcon>

        {/* Squeezed rather than clipped when the editor is narrow: the rows
            wrap, the fields give up width and the close control stays in
            reach. */}
        <Stack gap={6} miw={0}>
          <Group gap="xs">
            <TextInput
              ref={queryField}
              size="xs"
              w={FIELD_WIDTH}
              miw={0}
              placeholder="Find"
              aria-label="Find"
              error={malformed}
              value={query.search}
              onChange={(event) =>
                commit({ search: event.currentTarget.value })
              }
              onKeyDown={(event) =>
                runOnEnter(event, () =>
                  (event.shiftKey ? findPrevious : findNext)(view)
                )
              }
              // Kept mounted so the field does not reflow as the count
              // appears and disappears.
              rightSection={
                <Text size="xs" c="dimmed">
                  {matches && formatMatchCount(matches)}
                </Text>
              }
              rightSectionWidth={COUNTER_WIDTH}
              rightSectionPointerEvents="none"
            />

            <Group gap={2} wrap="nowrap">
              {FLAGS.map(({ flag, label, icon: Icon }) => (
                <PanelIcon
                  key={flag}
                  label={label}
                  active={query[flag]}
                  onClick={() => commit(flagChange(query, flag))}
                >
                  <Icon size={ICON_SIZE} />
                </PanelIcon>
              ))}
            </Group>

            <Group gap={2} wrap="nowrap">
              <PanelIcon
                label="Previous match"
                disabled={!query.valid}
                onClick={() => findPrevious(view)}
              >
                <IconChevronUp size={ICON_SIZE} />
              </PanelIcon>
              <PanelIcon
                label="Next match"
                disabled={!query.valid}
                onClick={() => findNext(view)}
              >
                <IconChevronDown size={ICON_SIZE} />
              </PanelIcon>
              <PanelIcon
                label="Select all matches"
                disabled={!query.valid}
                // The selection is only useful to type over, so hand the
                // focus back to the editor along with it.
                onClick={() => {
                  selectMatches(view);
                  view.focus();
                }}
              >
                <IconSelectAll size={ICON_SIZE} />
              </PanelIcon>
            </Group>
          </Group>

          {replacing && (
            <Group gap="xs">
              <TextInput
                size="xs"
                w={FIELD_WIDTH}
                miw={0}
                placeholder="Replace"
                aria-label="Replace"
                value={query.replace}
                onChange={(event) =>
                  commit({ replace: event.currentTarget.value })
                }
                onKeyDown={(event) =>
                  runOnEnter(event, () => replaceNext(view))
                }
              />

              <Group gap={2} wrap="nowrap">
                <PanelIcon
                  label="Replace match"
                  disabled={!query.valid}
                  onClick={() => replaceNext(view)}
                >
                  <IconReplace size={ICON_SIZE} />
                </PanelIcon>
                <PanelIcon
                  label="Replace all matches"
                  disabled={!query.valid}
                  onClick={() => replaceAll(view)}
                >
                  <IconReplaceFilled size={ICON_SIZE} />
                </PanelIcon>
              </Group>
            </Group>
          )}
        </Stack>

        <PanelIcon label="Close search" onClick={() => closeSearchPanel(view)}>
          <IconX size={ICON_SIZE} />
        </PanelIcon>
      </Group>
    </Paper>
  );
};
