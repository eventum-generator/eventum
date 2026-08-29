import { AnimationSequence, stagger } from 'motion/react';
import { FC } from 'react';

import { ANSWER, BEAT, FADE, HOLD, OPEN, PRESS, TRAVEL } from './beats';
import {
  Adornment,
  Badge,
  Browser,
  Button,
  Card,
  Chip,
  Conduit,
  Cursor,
  Diagram,
  Download,
  Dropzone,
  Field,
  Fill,
  Flash,
  Glyph,
  Group,
  Headline,
  Label,
  Layer,
  Log,
  MenuItem,
  Meter,
  Notice,
  Packet,
  Pane,
  Plate,
  Popover,
  Row,
  Scene,
  Stack,
  Stale,
  Switch,
  Tab,
  Ticks,
  Typed,
} from './scene';
import { Journey, part, travel } from './take';

/**
 * The scenes of the 2.8.0 release.
 *
 * Each one is a condensed recording of the feature being used in Studio:
 * the pointer crosses to a real control, presses it, the interface
 * answers, and the next step follows. What is drawn is the fragment of
 * the screen the gesture touches - the catalog row and its Install
 * button, the password field and the keyring behind its key - set larger
 * than life and cleared of the chrome the point does not need.
 *
 * Every step names when it starts against the step before it, so what
 * answers cannot drift off what was pressed.
 */

/** A point of the scene, in per cent of it. */
type At = [number, number];

type Step = AnimationSequence[number];

/** The pointer arriving on screen, at the point it first has to reach. */
const enter = (at: At): Step[] => [
  [part('cursor'), { left: `${at[0]}%`, top: `${at[1]}%` }, { duration: 0.01 }],
  [part('cursor'), { opacity: [0, 1] }, { duration: 0.28 }],
];

/** The pointer crossing to a control. */
const moveTo = (at: At, when = BEAT): Step => [
  part('cursor'),
  { left: `${at[0]}%`, top: `${at[1]}%` },
  { ...TRAVEL, at: when },
];

/** The press itself: the ring the pointer leaves on the control. */
const press = (when = '<+0.46'): Step => [
  part('cursor-tap'),
  { opacity: [0, 0.85, 0], scale: [0.4, 1.3] },
  { ...PRESS, at: when },
];

/** The pointer leaving, once there is nothing left to press. */
const leave = (when = HOLD): Step => [
  part('cursor'),
  { opacity: 0 },
  { ...FADE, at: when },
];

/* ========== The plate the reel opens on ========== */

/** The bars of the ribbon, as a share of its height. */
const RIBBON = [
  0.26, 0.4, 0.31, 0.54, 0.43, 0.68, 0.5, 0.36, 0.6, 0.74, 0.57, 0.88, 0.65,
  0.47, 0.8, 0.94, 0.7, 0.52, 0.85, 0.63, 0.97, 0.76, 0.58, 0.9, 0.68, 0.44,
];

/**
 * The opening card: the release names itself over a ribbon of the events
 * it generates. Nothing enters or leaves - the only motion is the wave
 * running along the ribbon, so the loop has no seam to notice.
 */
const openingTake = (): AnimationSequence => [
  [
    part('ribbon-bar'),
    { scaleY: [1, 0.38, 1] },
    { duration: 2.9, delay: stagger(0.06), ease: 'easeInOut' },
  ],
];

export const OpeningScene: FC = () => (
  <Scene
    title="Eventum 2.8.0, released 29 August 2026"
    take={openingTake}
    bleed
  >
    <Plate />

    <Ticks
      name="ribbon"
      x={50}
      y={20}
      w={56}
      h={70}
      bars={RIBBON}
      weight={0.46}
      blend
      fade
    />

    <Fill x={44} y={90} w={62} h={0.5} />

    <Label x={6} y={28} caps>
      Eventum
    </Label>
    <Headline x={6} y={50}>
      2.8.0
    </Headline>
    <Fill x={6} y={69} w={11} h={1.1} tone="accent" />
    <Label x={6} y={80} mono>
      Released 29 August 2026
    </Label>
  </Scene>
);

/* ========== Installing from a repository catalog ========== */

const CATALOG = [
  { id: 'web-nginx-access', name: 'Nginx Access Logs', size: '61.2KB', y: 46 },
  { id: 'linux-auditd', name: 'Linux auditd', size: '48.4KB', y: 65 },
  { id: 'windows-sysmon', name: 'Windows Sysmon', size: '84.9KB', y: 84 },
];

/**
 * The catalog a connected repository publishes, and one entry of it
 * being installed: the pointer picks the row, presses Install, the
 * button answers, and Studio says what the instance now holds.
 */
const repositoriesTake = (): AnimationSequence => [
  ...enter([34, 88]),
  moveTo([26, 65], '<+0.3'),
  [part('hover'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.34' }],
  moveTo([86, 65]),
  press(),
  [part('install'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.24' }],
  [
    part('notice'),
    { opacity: [0, 1], y: ['30%', '0%'] },
    { ...OPEN, at: '<+0.3' },
  ],
  leave(),
  [part('notice'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('install'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('hover'), { opacity: 0 }, { ...FADE, at: '<' }],
];

export const RepositoriesScene: FC = () => (
  <Scene
    title="A generator of a repository catalog being installed as a project"
    take={repositoriesTake}
  >
    <Pane x={0} y={0} w={100} h={100}>
      <Glyph kind="repo" at={[4, 12]} />
      <Label x={8} y={12} strong>
        content-packs
      </Label>
      <Badge x={30} y={12} tone="green">
        reachable
      </Badge>
      <Label x={97} y={12} mono small end>
        54 generators
      </Label>

      <Fill x={3} y={22} w={94} h={0.7} />

      <Label x={4} y={30} caps>
        generator
      </Label>

      <Row x={1.5} y={65} w={97} h={16} name="hover" rest />

      {CATALOG.map((entry) => (
        <Group key={entry.id} x={0} y={0} w={100} h={100}>
          <Label x={4} y={entry.y} strong>
            {entry.name}
          </Label>
          <Label x={34} y={entry.y} mono small>
            {entry.id}
          </Label>
          <Label x={70} y={entry.y} mono small end>
            {entry.size}
          </Label>
        </Group>
      ))}

      <Button x={74} y={46} w={23} h={13}>
        Install
      </Button>
      <Button
        name="install"
        x={74}
        y={65}
        w={23}
        h={13}
        tone="green"
        glyph="check"
        answer="Installed"
        rest
      >
        Install
      </Button>
      <Button x={74} y={84} w={23} h={13}>
        Install
      </Button>
    </Pane>

    <Notice
      name="notice"
      x={36}
      y={72}
      w={62}
      h={24}
      tone="green"
      note="linux-auditd is now a project"
      rest
    >
      Installed
    </Notice>

    <Cursor at={[34, 88]} />
  </Scene>
);

/* ========== Finding a repository on GitHub ========== */

const PUBLISHED = [
  { id: 'eventum-generator/content-packs', y: 50, official: true },
  { id: 'acme-labs/eventum-packs', y: 70, official: false },
  { id: 'nordsec/lab-sources', y: 90, official: false },
];

/**
 * The Discover tab of the Repositories page: the pointer opens it, what
 * GitHub publishes under the topic comes back, and the first of them is
 * connected without leaving the list.
 */
const discoverTake = (): AnimationSequence => [
  ...enter([18, 40]),
  moveTo([30, 11], '<+0.3'),
  press(),
  [part('discover'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.2' }],
  [
    part('found'),
    { opacity: [0, 1], y: ['26%', '0%'] },
    { ...OPEN, delay: stagger(0.14), at: '<+0.16' },
  ],
  [part('connect'), { opacity: [0, 1] }, { ...OPEN, at: '<' }],
  [part('count'), { opacity: [0, 1] }, { ...FADE, at: '<+0.34' }],
  moveTo([84, 50]),
  press(),
  [part('connect-on'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.24' }],
  leave(),
  [part('connect-on'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('connect'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('count'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('found'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('discover'), { opacity: 0 }, { ...FADE, at: '<' }],
];

export const DiscoverScene: FC = () => (
  <Scene
    title="The Discover tab listing the repositories GitHub publishes under the topic"
    take={discoverTake}
  >
    <Pane x={0} y={0} w={100} h={100}>
      <Tab x={4} y={11} w={18} h={14}>
        Connected
      </Tab>
      <Tab name="discover" x={24} y={11} w={16} h={14} rest>
        Discover
      </Tab>
      <Fill x={4} y={19.5} w={93} h={0.7} />

      <Field x={4} y={30} w={40} h={14}>
        <Glyph kind="search" at={[7, 50]} />
        <Label x={14} y={50} mono small>
          eventum-generators
        </Label>
      </Field>

      <Layer x={0} y={0} w={100} h={100} name="count">
        <Label x={97} y={30} mono small end>
          3 repositories found
        </Label>
      </Layer>

      {PUBLISHED.map((repo) => (
        <Layer key={repo.id} x={0} y={0} w={100} h={100} name="found">
          <Card x={2} y={repo.y - 8} w={96} h={16} />
          <Glyph kind="repo" at={[6, repo.y]} />
          <Label x={10} y={repo.y} mono small tone="accent">
            {repo.id}
          </Label>
          {repo.official && (
            <Badge x={55} y={repo.y} tone="accent">
              official
            </Badge>
          )}
          <Button x={72} y={repo.y} w={24} h={12}>
            Connect
          </Button>
        </Layer>
      ))}

      <Layer x={0} y={0} w={100} h={100} name="connect">
        <Button
          name="connect-on"
          x={72}
          y={50}
          w={24}
          h={12}
          tone="green"
          answer="Connected"
          rest
        >
          Connect
        </Button>
      </Layer>
    </Pane>

    <Cursor at={[18, 40]} />
  </Scene>
);

/* ========== Exporting and importing a project ========== */

/** Out of the tray the browser dropped it into, onto the instance that
 *  is going to read it. */
const HANDOVER: Journey = { from: [20, 82], to: [77, 42] };

/**
 * A project leaving one instance and arriving at another: Export is
 * pressed, the browser saves the archive and shows it saved, the archive
 * is carried onto the import dialog of a second instance, and that
 * instance reads the project name out of it.
 */
const archiveTake = (): AnimationSequence => [
  ...enter([26, 56]),
  moveTo([32, 66], '<+0.3'),
  press(),
  [part('export'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.22' }],
  [
    part('saving'),
    { opacity: [0, 1], y: ['70%', '0%'] },
    { ...OPEN, at: '<+0.2' },
  ],
  [
    part('saving-arc'),
    { strokeDashoffset: [1, 0] },
    { duration: 1.1, at: '<' },
  ],
  [part('saving-done'), { opacity: [0, 1] }, { ...ANSWER, at: '-0.12' }],
  moveTo([20, 82]),
  press(),
  [part('carry'), { opacity: [0, 1] }, { duration: 0.2, at: '<+0.24' }],
  [
    part('carry'),
    travel(HANDOVER),
    { duration: 1, ease: TRAVEL.ease, at: '<' },
  ],
  [
    part('cursor'),
    { left: `${HANDOVER.to[0]}%`, top: `${HANDOVER.to[1]}%` },
    { duration: 1, ease: TRAVEL.ease, at: '<' },
  ],
  [part('accepting'), { opacity: [0, 1] }, { ...ANSWER, at: '-0.36' }],
  [part('carry'), { opacity: 0 }, { duration: 0.18, at: '-0.14' }],
  [part('empty'), { opacity: 0 }, { duration: 0.18, at: '<' }],
  [
    part('dropped'),
    { opacity: [0, 1], scale: [0.9, 1] },
    { ...ANSWER, at: '<' },
  ],
  [part('accepting'), { opacity: 0 }, { ...FADE, at: '<+0.6' }],
  [part('named'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  moveTo([84, 88]),
  press(),
  [part('import'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.24' }],
  leave(),
  [part('import'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('named'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('dropped'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('empty'), { opacity: 1 }, { ...FADE, at: '<' }],
  [part('saving-done'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('saving'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('export'), { opacity: 0 }, { ...FADE, at: '<' }],
];

export const ProjectArchiveScene: FC = () => (
  <Scene
    title="A project saved as an archive by the browser and imported on another instance"
    take={archiveTake}
  >
    <Browser x={0} y={2} w={46} h={96} address="127.0.0.1:9474/projects">
      <Label x={8} y={30} caps>
        export project
      </Label>

      <Glyph kind="file" at={[10, 43]} />
      <Label x={18} y={43} mono small>
        generator.yml
      </Label>
      <Glyph kind="folder" at={[10, 54]} />
      <Label x={18} y={54} mono small>
        templates
      </Label>

      <Button name="export" x={52} y={66} w={40} h={13} variant="filled" rest>
        Export
      </Button>

      <Download name="saving" x={6} y={80} file="auth-events.zip" rest />
    </Browser>

    <Pane x={54} y={2} w={46} h={96}>
      <Label x={8} y={12} caps>
        import project
      </Label>

      <Dropzone x={7} y={21} w={86} h={32} name="accepting">
        <Stale x={0} y={0} w={100} h={100} name="empty">
          <Glyph kind="upload" at={[50, 34]} />
          <Label x={50} y={70} center small>
            Drop the archive
          </Label>
        </Stale>
        <Layer x={0} y={0} w={100} h={100} name="dropped">
          <Glyph kind="archive" at={[50, 34]} tone="accent" />
          <Label x={50} y={70} center mono small tone="accent">
            auth-events.zip
          </Label>
        </Layer>
      </Dropzone>

      <Label x={8} y={61} small>
        Project name
      </Label>
      <Field x={7} y={72} w={86} h={14}>
        <Layer x={0} y={0} w={100} h={100} name="named">
          <Label x={6} y={50} mono small>
            auth-events
          </Label>
        </Layer>
      </Field>

      <Button
        name="import"
        x={58}
        y={88}
        w={35}
        h={13}
        variant="filled"
        tone="green"
        answer="Imported"
        rest
      >
        Import
      </Button>
    </Pane>

    <Packet name="carry" journey={HANDOVER} glyph="archive">
      auth-events.zip
    </Packet>

    <Cursor at={[26, 56]} />
  </Scene>
);

/* ========== Picking a secret from the keyring ========== */

/**
 * The password field of a plugin form: the key beside it offers what the
 * keyring holds, the entry that is picked is written into the field as a
 * reference, and the configuration under it names the secret rather than
 * carrying one.
 */
const keyringTake = (): AnimationSequence => [
  ...enter([40, 18]),
  moveTo([50, 41], '<+0.3'),
  [part('key-lit'), { opacity: [0, 1] }, { ...FADE, at: '<+0.46' }],
  press('<+0.06'),
  [
    part('menu'),
    { opacity: [0, 1], scale: [0.92, 1], y: ['-10%', '0%'] },
    { ...OPEN, at: '<+0.16' },
  ],
  [
    part('entry'),
    { opacity: [0, 1], x: ['-3%', '0%'] },
    { duration: 0.24, delay: stagger(0.08), at: '<+0.08' },
  ],
  moveTo([26, 62]),
  [part('pick'), { opacity: [0, 1] }, { ...FADE, at: '<+0.46' }],
  press('<+0.1'),
  [part('masked'), { opacity: 0 }, { duration: 0.2, at: '<+0.16' }],
  [part('filled'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.04' }],
  [part('eye'), { opacity: 0 }, { ...FADE, at: '<' }],
  [
    part('written'),
    { opacity: [0, 1], x: ['5%', '0%'] },
    { ...ANSWER, at: '<+0.34' },
  ],
  leave(),
  [part('written'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('menu'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('key-lit'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('pick'), { opacity: 0 }, { duration: 0.01, at: '+0.05' }],
  [part('entry'), { opacity: 0 }, { duration: 0.01, at: '<' }],
  [part('filled'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('masked'), { opacity: 1 }, { ...FADE, at: '<' }],
  [part('eye'), { opacity: 1 }, { ...FADE, at: '<' }],
];

export const KeyringPickerScene: FC = () => (
  <Scene
    title="A password field taking a secret from the keyring by name"
    take={keyringTake}
  >
    <Pane x={0} y={0} w={100} h={50}>
      <Label x={3} y={16} caps>
        opensearch output
      </Label>
      <Fill x={3} y={32} w={94} h={1.2} />

      <Label x={3} y={54} small>
        Password
      </Label>
      <Field x={3} y={82} w={52} h={28}>
        <Stale x={0} y={0} w={100} h={100} name="masked">
          <Label x={5} y={50} mono>
            &bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;
          </Label>
        </Stale>
        <Layer x={0} y={0} w={100} h={100} name="filled">
          <Label x={5} y={50} mono tone="accent">
            {'${secrets.gh_token}'}
          </Label>
        </Layer>
        <Stale x={0} y={0} w={100} h={100} name="eye">
          <Adornment at={[80, 50]} glyph="eye" />
        </Stale>
        <Adornment name="key-lit" at={[91, 50]} glyph="key" tone="accent" />
      </Field>

      <Label x={60} y={54} small>
        Index
      </Label>
      <Field x={60} y={82} w={37} h={28}>
        <Label x={8} y={50} mono small>
          events
        </Label>
      </Field>
    </Pane>

    <Popover name="menu" x={16} y={52} w={40} h={46} rest>
      <MenuItem name="pick" x={4} y={20} w={92} h={26} mono tone="accent" rest>
        gh_token
      </MenuItem>
      <Group x={0} y={0} w={100} h={100} name="entry">
        <MenuItem x={4} y={50} w={92} h={26} mono>
          ch_password
        </MenuItem>
      </Group>
      <Group x={0} y={0} w={100} h={100} name="entry">
        <MenuItem x={4} y={80} w={92} h={26} mono>
          os_api_key
        </MenuItem>
      </Group>
    </Popover>

    <Layer x={61} y={56} w={38} h={40} name="written">
      <Card x={0} y={0} w={100} h={100} />
      <Label x={8} y={22} caps>
        generator.yml
      </Label>
      <Label x={8} y={58} mono small>
        password:
      </Label>
      <Label x={8} y={82} mono small tone="accent">
        {'${secrets.gh_token}'}
      </Label>
    </Layer>

    <Cursor at={[40, 18]} />
  </Scene>
);

/* ========== The global state a scenario shares ========== */

/**
 * The scenario data flow: an instance card is opened, and the template
 * and the script inside it are seen reaching the same key of the global
 * state - the template writing it, the script reading it back.
 */
const globalStateTake = (): AnimationSequence => [
  ...enter([14, 32]),
  moveTo([4.5, 20], '<+0.3'),
  press(),
  [part('shut'), { opacity: 0 }, { duration: 0.2, at: '<+0.18' }],
  [part('open'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [
    part('plugin'),
    { opacity: [0, 1], y: ['-26%', '0%'] },
    { ...OPEN, delay: stagger(0.14), at: '<+0.04' },
  ],
  leave('<+0.4'),
  [part('writes'), { scale: [1, 1.18, 1] }, { duration: 0.5, at: BEAT }],
  [
    part('write-link'),
    { '--ev-draw': [1, 0] },
    { duration: 0.62, at: '<+0.14' },
  ],
  [part('key-lit'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.22' }],
  [part('before'), { opacity: 0 }, { duration: 0.22, at: '<' }],
  [part('after'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.04' }],
  [part('reads'), { scale: [1, 1.18, 1] }, { duration: 0.5, at: BEAT }],
  [
    part('read-link'),
    { '--ev-draw': [1, 0] },
    { duration: 0.62, at: '<+0.14' },
  ],
  [part('key-lit'), { opacity: [1, 0.4, 1] }, { duration: 0.6, at: '<+0.2' }],
  [part('after'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('before'), { opacity: 1 }, { ...FADE, at: '<' }],
  [part('key-lit'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('read-link'), { '--ev-draw': 1 }, { ...FADE, at: '<' }],
  [part('write-link'), { '--ev-draw': 1 }, { ...FADE, at: '<' }],
  [part('plugin'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('open'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('shut'), { opacity: 1 }, { ...FADE, at: '<' }],
];

const GLOBAL_KEYS = [
  { key: 'active_sessions', value: '{9 keys}', y: 68 },
  { key: 'user.pool', value: '[12 items]', y: 88 },
];

export const GlobalStateScene: FC = () => (
  <Scene
    title="A template and a script of one scenario reaching the same key of the global state"
    take={globalStateTake}
  >
    <Card x={0} y={8} w={42} h={80}>
      <Stale x={0} y={0} w={100} h={100} name="shut">
        <Glyph kind="chevron" at={[6, 15]} />
      </Stale>
      <Layer x={0} y={0} w={100} h={100} name="open">
        <Glyph kind="caret" at={[6, 15]} />
      </Layer>
      <Label x={13} y={15} strong>
        corp-edge-firewall
      </Label>

      <Fill x={5} y={30} w={90} h={0.9} />

      <Layer x={0} y={0} w={100} h={100} name="plugin">
        <Glyph kind="template" at={[7, 46]} tone="accent" />
        <Label x={15} y={46} mono small>
          template #1
        </Label>
        <Badge name="writes" x={95} y={46} tone="accent" end>
          writes
        </Badge>
      </Layer>

      <Layer x={0} y={0} w={100} h={100} name="plugin">
        <Glyph kind="script" at={[7, 72]} tone="cyan" />
        <Label x={15} y={72} mono small>
          firewall.py
        </Label>
        <Badge name="reads" x={95} y={72} tone="cyan" end>
          reads
        </Badge>
      </Layer>
    </Card>

    <Diagram>
      <Conduit
        name="write-link"
        d="M 42 44.8 H 55.4"
        tone="accent"
        hidden
        rest
      />
      <Conduit
        name="write-link"
        d="M 53.6 43.3 L 56 44.8 L 53.6 46.3"
        tone="accent"
        hidden
        rest
      />
      <Conduit
        name="read-link"
        d="M 56 44.8 C 49 44.8, 49 65.6, 42.6 65.6"
        tone="cyan"
        hidden
        rest
      />
      <Conduit
        name="read-link"
        d="M 45 64.1 L 42.6 65.6 L 45 67.1"
        tone="cyan"
        hidden
        rest
      />
    </Diagram>

    <Pane x={56} y={8} w={44} h={80}>
      <Glyph kind="store" at={[7, 14]} />
      <Label x={14} y={14} strong>
        Global state
      </Label>
      <Badge x={95} y={14} mono end>
        3 keys
      </Badge>

      <Fill x={5} y={28} w={90} h={0.9} />

      <Row x={2} y={46} w={96} h={17} name="key-lit" rest />
      <Label x={6} y={46} mono small tone="accent">
        flagged_ips
      </Label>
      <Stale x={0} y={0} w={100} h={100} name="before">
        <Label x={95} y={46} mono small end>
          [15 items]
        </Label>
      </Stale>
      <Layer x={0} y={0} w={100} h={100} name="after">
        <Label x={95} y={46} mono small tone="accent" end>
          [16 items]
        </Label>
      </Layer>

      {GLOBAL_KEYS.map((entry) => (
        <Group key={entry.key} x={0} y={0} w={100} h={100}>
          <Label x={6} y={entry.y} mono small>
            {entry.key}
          </Label>
          <Label x={95} y={entry.y} mono small end>
            {entry.value}
          </Label>
        </Group>
      ))}
    </Pane>

    <Cursor at={[14, 32]} />
  </Scene>
);

/* ========== Monitoring, built around the instances ========== */

/** A dozen instances sharing the load, and the three a search leaves. */
const LOAD_ALL = [
  [0.12, 0.14, 0.11, 0.15, 0.12, 0.14, 0.11, 0.14, 0.12],
  [0.09, 0.08, 0.11, 0.09, 0.12, 0.1, 0.11, 0.09, 0.11],
  [0.14, 0.12, 0.15, 0.13, 0.14, 0.17, 0.14, 0.12, 0.15],
  [0.08, 0.11, 0.09, 0.11, 0.08, 0.1, 0.11, 0.09, 0.08],
  [0.16, 0.14, 0.13, 0.16, 0.18, 0.15, 0.16, 0.18, 0.15],
];

const LOAD_FOUND = [
  [0.16, 0.2, 0.17, 0.23, 0.19, 0.22, 0.18, 0.21, 0.19],
  [0.24, 0.2, 0.27, 0.22, 0.29, 0.24, 0.3, 0.26, 0.28],
  [0.11, 0.15, 0.12, 0.1, 0.14, 0.12, 0.16, 0.13, 0.14],
];

const ALL_ROWS = [
  { id: 'auditd-fleet', rate: '5.00/s', y: 63 },
  { id: 'corp-auth-service', rate: '3.00/s', y: 73 },
  { id: 'corp-web-proxy', rate: '7.80/s', y: 83 },
  { id: 'dns-sensor', rate: '5.00/s', y: 93 },
];

const FOUND_ROWS = [
  { id: 'corp-auth-service', rate: '3.00/s', y: 65 },
  { id: 'corp-web-proxy', rate: '7.80/s', y: 78 },
  { id: 'corp-edge-firewall', rate: '10.0/s', y: 91 },
];

/**
 * The instances section of Monitoring: a word typed into the search
 * narrows the load chart and the table under it together, and picking a
 * row brings that instance's band forward in the chart.
 */
const monitoringTake = (): AnimationSequence => [
  ...enter([56, 40]),
  moveTo([64, 10], '<+0.3'),
  press(),
  [part('search'), { opacity: [0, 1] }, { ...FADE, at: '<+0.16' }],
  [
    part('typed'),
    { opacity: [0, 1] },
    { duration: 0.1, delay: stagger(0.16), at: '<+0.1' },
  ],
  [
    part('typed-caret'),
    { opacity: [1, 0] },
    { duration: 0.1, delay: stagger(0.16), at: '<+0.16' },
  ],
  [part('all'), { opacity: 0 }, { ...ANSWER, at: '<+0.3' }],
  [part('found'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.06' }],
  moveTo([30, 78]),
  press(),
  [part('picked'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.2' }],
  [part('load-lead'), { opacity: [0.42, 0.92] }, { ...ANSWER, at: '<' }],
  leave(),
  [part('picked'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('found'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('all'), { opacity: 1 }, { ...FADE, at: '<' }],
  [part('search'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('typed'), { opacity: 0 }, { ...FADE, at: '<' }],
];

export const MonitoringScene: FC = () => (
  <Scene
    title="A search narrowing the Monitoring load chart and the instance table together"
    take={monitoringTake}
  >
    <Pane x={0} y={0} w={100} h={100}>
      <Chip x={3} y={10} w={20} h={13} rest>
        By instance
      </Chip>
      <Chip x={25} y={10} w={17} h={13}>
        By stage
      </Chip>

      <Field name="search" x={48} y={10} w={30} h={14}>
        <Glyph kind="search" at={[8, 50]} />
        <Typed name="typed" x={17} y={50} rest>
          corp
        </Typed>
      </Field>

      <Stale x={0} y={0} w={100} h={100} name="all">
        <Label x={97} y={10} mono small end>
          12 running
        </Label>
        <Stack x={3} y={23} w={94} h={31} bands={LOAD_ALL} />
        {ALL_ROWS.map((row, index) => (
          <Group key={row.id} x={0} y={0} w={100} h={100}>
            <Fill x={3} y={row.y} w={1.4} h={2.6} step={index / 3} />
            <Label x={7} y={row.y} mono small>
              {row.id}
            </Label>
            <Label x={97} y={row.y} mono small end>
              {row.rate}
            </Label>
          </Group>
        ))}
      </Stale>

      <Layer x={0} y={0} w={100} h={100} name="found">
        <Label x={97} y={10} mono small end>
          3 running
        </Label>
        <Stack
          name="load"
          x={3}
          y={23}
          w={94}
          h={31}
          bands={LOAD_FOUND}
          lead={1}
        />
        <Row x={1} y={78} w={98} h={11} name="picked" rest />
        {FOUND_ROWS.map((row, index) => (
          <Group key={row.id} x={0} y={0} w={100} h={100}>
            <Fill x={3} y={row.y} w={1.4} h={2.6} step={index / 2} />
            <Label x={7} y={row.y} mono small>
              {row.id}
            </Label>
            <Label x={97} y={row.y} mono small end>
              {row.rate}
            </Label>
          </Group>
        ))}
      </Layer>
    </Pane>

    <Cursor at={[56, 40]} />
  </Scene>
);

/* ========== What an instance occupies ========== */

/** The instances, in the order the queue column leaves them, and where
 *  each of them sits before the two sorts that get them there. */
const RESOURCES = [
  {
    id: 'corp-auth-service',
    cpu: '0.6%',
    wait: '0.1%',
    disk: '1.3KB/s',
    net: '4B/s',
    queue: '88MB',
    threads: '7',
    slots: ['0%', '48%'],
  },
  {
    id: 'dns-sensor',
    cpu: '0.2%',
    wait: '0.1%',
    disk: '9.2KB/s',
    net: '4B/s',
    queue: '46MB',
    threads: '7',
    slots: ['16%', '-16%'],
  },
  {
    id: 'corp-web-proxy',
    cpu: '0.4%',
    wait: '0.1%',
    disk: '4.0KB/s',
    net: '4B/s',
    queue: '12MB',
    threads: '7',
    slots: ['-16%', '0%'],
  },
  {
    id: 'pg-audit',
    cpu: '0.2%',
    wait: '0.2%',
    disk: '6.8KB/s',
    net: '4B/s',
    queue: '4MB',
    threads: '8',
    slots: ['0%', '-32%'],
  },
];

/** The columns of the table, at the edge each is read back from. */
const COLUMNS = [
  { id: 'cpu', end: 38 },
  { id: 'wait', end: 47 },
  { id: 'disk', end: 59 },
  { id: 'net', end: 68 },
  { id: 'queue', end: 80 },
  { id: 'threads', end: 96 },
];

/**
 * Carry one row of the table from the line it sits on to another.
 *
 * A sort happens at once, so the rows that move do not fly through one
 * another: they fade together, take their new line while none of them
 * is drawn, and come back. Two rows of figures over each other read as
 * neither, and no travel means no crossing to mistime. A row whose line
 * does not change stays lit throughout, which is what makes the sort
 * legible: the table settles around the rows that held their place.
 */
const reseat = (index: number, from: string, to: string): Step => [
  part(`row-${index}`),
  {
    y: [from, from, to, to],
    opacity: from === to ? [1, 1, 1, 1] : [1, 0, 0, 1],
  },
  { ...ANSWER, duration: 0.62, times: [0, 0.3, 0.34, 1], at: '<' },
];

/**
 * The instance table of Monitoring, ranked by one resource and then by
 * another: what a run occupies is a column, and every column sorts the
 * instances that are running.
 */
const resourcesTake = (): AnimationSequence => [
  ...RESOURCES.map(
    (row, index): Step => [
      part(`row-${index}`),
      { y: [row.slots[0] ?? '0%', row.slots[0] ?? '0%'] },
      { duration: 0.01, at: 0 },
    ]
  ),
  ...enter([44, 34]),
  moveTo([54, 12], '<+0.3'),
  press(),
  [part('disk-sort'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.18' }],
  ...RESOURCES.map(
    (row, index): Step =>
      reseat(index, row.slots[0] ?? '0%', row.slots[1] ?? '0%')
  ),
  moveTo([75, 12]),
  press(),
  [part('disk-sort'), { opacity: 0 }, { ...FADE, at: '<+0.18' }],
  [part('queue-sort'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  ...RESOURCES.map(
    (row, index): Step => reseat(index, row.slots[1] ?? '0%', '0%')
  ),
  leave(),
  [part('queue-sort'), { opacity: 0 }, { ...FADE, at: HOLD }],
];

export const InstanceResourcesScene: FC = () => (
  <Scene
    title="The instance table of Monitoring ranked by disk and then by queue memory"
    take={resourcesTake}
  >
    <Pane x={0} y={0} w={100} h={100}>
      <Label x={4} y={11} caps>
        instance
      </Label>
      {COLUMNS.map((column) => (
        <Label key={column.id} x={column.end} y={11} caps end>
          {column.id}
        </Label>
      ))}

      <Flash x={0} y={0} w={100} h={100} name="disk-sort">
        <Label x={59} y={11} caps end tone="accent">
          disk
        </Label>
        <Fill x={52.7} y={16} w={6.3} h={0.9} tone="accent" />
      </Flash>

      <Layer x={0} y={0} w={100} h={100} name="queue-sort">
        <Label x={80} y={11} caps end tone="accent">
          queue
        </Label>
        <Fill x={72.1} y={16} w={7.9} h={0.9} tone="accent" />
      </Layer>

      <Fill x={3} y={21} w={94} h={0.7} />

      {RESOURCES.map((row, index) => (
        <Group key={row.id} x={0} y={0} w={100} h={100} name={`row-${index}`}>
          <Fill x={3} y={34 + index * 16} w={1.4} h={2.6} step={index / 3} />
          <Label x={6} y={34 + index * 16} mono small>
            {row.id}
          </Label>
          <Label x={38} y={34 + index * 16} mono small end>
            {row.cpu}
          </Label>
          <Label x={47} y={34 + index * 16} mono small end>
            {row.wait}
          </Label>
          <Label x={59} y={34 + index * 16} mono small end>
            {row.disk}
          </Label>
          <Label x={68} y={34 + index * 16} mono small end>
            {row.net}
          </Label>
          <Label x={80} y={34 + index * 16} mono small end>
            {row.queue}
          </Label>
          <Label x={96} y={34 + index * 16} mono small end>
            {row.threads}
          </Label>
        </Group>
      ))}
    </Pane>

    <Cursor at={[44, 34]} />
  </Scene>
);

/* ========== A log file per component ========== */

const MAIN_LINES = [
  { level: 'info' as const, text: 'Starting application', from: 'eventum.app' },
  {
    level: 'info' as const,
    text: 'Loading generators list',
    from: 'eventum.app',
  },
  {
    level: 'info' as const,
    text: 'Generators are running',
    from: 'eventum.app',
  },
  { level: 'info' as const, text: 'Starting Server', from: 'eventum.app' },
  { level: 'info' as const, text: 'Startup completed', from: 'eventum.app' },
];

const SERVER_LINES = [
  { level: 'info' as const, text: 'Application startup', from: 'uvicorn' },
  { level: 'info' as const, text: 'Serving on 0.0.0.0:9474', from: 'uvicorn' },
  { level: 'info' as const, text: 'Fetching repository', from: 'eventum.api' },
  {
    level: 'info' as const,
    text: 'Repository catalog is read',
    from: 'eventum.api',
  },
  {
    level: 'warn' as const,
    text: 'Token is close to expiry',
    from: 'eventum.api',
  },
];

const INSTANCE_LINES = [
  { level: 'info' as const, text: 'Starting generator', from: 'eventum.core' },
  {
    level: 'info' as const,
    text: 'Initializing plugins',
    from: 'eventum.core',
  },
  {
    level: 'info' as const,
    text: 'Initialization completed',
    from: 'eventum.core',
  },
  { level: 'info' as const, text: 'Starting execution', from: 'eventum.core' },
  {
    level: 'error' as const,
    text: 'Failed to render template',
    from: 'eventum.core',
  },
];

/**
 * The log of the application, paged by the part that wrote it: the
 * channels of the Management page, and past the divider the instance
 * that keeps a file of its own.
 */
const logChannelsTake = (): AnimationSequence => [
  ...enter([40, 34]),
  moveTo([34, 11], '<+0.3'),
  press(),
  [part('server-tab'), { opacity: [0, 1] }, { ...ANSWER, at: '<+0.18' }],
  [part('main-tab'), { opacity: 0 }, { duration: 0.2, at: '<' }],
  [part('main-lines'), { opacity: 0 }, { duration: 0.2, at: '<' }],
  [
    part('server-lines'),
    { opacity: [0, 1], x: ['1.2%', '0%'] },
    { ...ANSWER, at: '<+0.06' },
  ],
  moveTo([79, 11]),
  press(),
  [part('server-tab'), { opacity: 0 }, { ...FADE, at: '<+0.18' }],
  [part('instance-tab'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [part('instance-file'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [part('server-lines'), { opacity: 0 }, { duration: 0.2, at: '<' }],
  [
    part('instance-lines'),
    { opacity: [0, 1], x: ['1.2%', '0%'] },
    { ...ANSWER, at: '<+0.06' },
  ],
  leave(),
  [part('instance-lines'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('instance-file'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('instance-tab'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('main-tab'), { opacity: 1 }, { ...FADE, at: '<' }],
  [part('main-lines'), { opacity: 1 }, { ...FADE, at: '<' }],
];

export const LogChannelsScene: FC = () => (
  <Scene
    title="The log of the application paged by the component that wrote it"
    take={logChannelsTake}
  >
    <Pane x={0} y={0} w={100} h={100}>
      <Glyph kind="logs" at={[4, 11]} />
      <Label x={8} y={11} caps>
        logs
      </Label>

      <Chip x={18} y={11} w={9} h={13}>
        Main
      </Chip>
      <Stale x={0} y={0} w={100} h={100} name="main-tab">
        <Chip x={18} y={11} w={9} h={13} lit>
          Main
        </Chip>
      </Stale>
      <Chip name="server-tab" x={28} y={11} w={12} h={13}>
        Server
      </Chip>
      <Chip x={41} y={11} w={12} h={13}>
        Access
      </Chip>
      <Chip x={54} y={11} w={9} h={13}>
        MCP
      </Chip>
      <Fill x={65} y={11} w={0.3} h={9} />
      <Chip name="instance-tab" x={67} y={11} w={24} h={13} rest>
        corp-web-proxy
      </Chip>

      <Stale x={0} y={0} w={100} h={100} name="main-lines">
        <Log x={4} y={26} w={92} h={54} lines={MAIN_LINES} />
      </Stale>

      <Flash x={0} y={0} w={100} h={100} name="server-lines">
        <Log x={4} y={26} w={92} h={54} lines={SERVER_LINES} />
      </Flash>

      <Layer x={0} y={0} w={100} h={100} name="instance-lines">
        <Log x={4} y={26} w={92} h={54} lines={INSTANCE_LINES} />
      </Layer>

      <Glyph kind="file" at={[5, 89]} />
      <Stale x={0} y={0} w={100} h={100} name="main-lines">
        <Label x={10} y={89} mono small>
          logs/main.log
        </Label>
      </Stale>
      <Flash x={0} y={0} w={100} h={100} name="server-lines">
        <Label x={10} y={89} mono small>
          logs/server.log
        </Label>
      </Flash>
      <Layer x={0} y={0} w={100} h={100} name="instance-file">
        <Label x={10} y={89} mono small tone="accent">
          logs/generator_corp-web-proxy.log
        </Label>
      </Layer>
    </Pane>

    <Cursor at={[40, 34]} />
  </Scene>
);

/* ========== The memory the events queue is allowed ========== */

/**
 * What an instance holds in memory, filling to the limit it is given:
 * the events queue reaches the bytes it is allowed, the timestamps queue
 * behind it backs up, and the setting that sets the limit sits beside
 * them.
 */
const queueTake = (): AnimationSequence => [
  [part('events-fill'), { scaleX: [0, 1] }, { duration: 2.1, ease: 'easeOut' }],
  [
    part('events-count'),
    { opacity: [0, 1, 1, 0] },
    { duration: 0.78, delay: stagger(0.5), at: 0.15 },
  ],
  [part('events-capped'), { opacity: [0, 1] }, { ...ANSWER, at: '-0.14' }],
  [part('events-bytes'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [part('capped'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [
    part('limited'),
    { opacity: [0, 1], scale: [0.8, 1] },
    { ...ANSWER, at: '<+0.1' },
  ],
  [
    part('stamps-fill'),
    { scaleX: [0.22, 1] },
    { duration: 1, ease: 'easeOut', at: BEAT },
  ],
  [part('stamps-count'), { opacity: [0, 1] }, { ...ANSWER, at: '-0.26' }],
  [part('stamps-capped'), { opacity: [0, 1] }, { ...ANSWER, at: '<' }],
  [part('limited'), { opacity: 0 }, { ...FADE, at: HOLD }],
  [part('stamps-capped'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('stamps-count'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('capped'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('events-bytes'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('events-capped'), { opacity: 0 }, { ...FADE, at: '<' }],
  [part('events-fill'), { scaleX: 0 }, { ...FADE, at: '<' }],
  [part('stamps-fill'), { scaleX: 0.22 }, { ...FADE, at: '<' }],
];

/** The figures the events queue climbs through before it is full. */
const QUEUE_STEPS = ['3', '6', '9'];

export const QueueBytesScene: FC = () => (
  <Scene
    title="An events queue filling to the memory it is allowed, beside the setting that allows it"
    take={queueTake}
  >
    <Pane x={0} y={6} w={52} h={88}>
      <Glyph kind="queue" at={[8, 12]} />
      <Label x={15} y={12} caps>
        memory in queues
      </Label>
      <Fill x={6} y={25} w={88} h={0.8} />

      <Label x={6} y={38} small>
        Timestamps
      </Label>
      <Layer x={0} y={0} w={100} h={100} name="stamps-count">
        <Label x={94} y={38} mono small end tone="yellow">
          10 / 10
        </Label>
      </Layer>
      <Meter x={6} y={48} w={88} h={3.5} level={1} name="stamps-fill" />
      <Layer x={0} y={0} w={100} h={100} name="stamps-capped">
        <Meter x={6} y={48} w={88} h={3.5} level={1} tone="yellow" />
      </Layer>

      <Label x={6} y={64} small>
        Events
      </Label>
      {QUEUE_STEPS.map((count) => (
        <Flash key={count} x={0} y={0} w={100} h={100} name="events-count">
          <Label x={94} y={64} mono small end>
            {count} / 10
          </Label>
        </Flash>
      ))}
      <Layer x={0} y={0} w={100} h={100} name="events-capped">
        <Label x={94} y={64} mono small end tone="yellow">
          10 / 10
        </Label>
      </Layer>
      <Meter x={6} y={74} w={88} h={3.5} level={1} name="events-fill" />
      <Layer x={0} y={0} w={100} h={100} name="capped">
        <Meter x={6} y={74} w={88} h={3.5} level={1} tone="yellow" />
      </Layer>

      <Layer x={0} y={0} w={100} h={100} name="events-bytes">
        <Label x={6} y={89} mono small tone="yellow">
          256MB / 256MB
        </Label>
      </Layer>
      <Layer x={0} y={0} w={100} h={100} name="limited">
        <Badge x={94} y={89} tone="yellow" end>
          at the limit
        </Badge>
      </Layer>
    </Pane>

    <Pane x={58} y={20} w={42} h={60}>
      <Label x={9} y={14} caps>
        queue
      </Label>
      <Fill x={8} y={28} w={84} h={1} />

      <Switch x={8} y={46} w={13} h={8} on />
      <Label x={25} y={46} small>
        Limit memory
      </Label>

      <Label x={8} y={68} small>
        Maximum event bytes
      </Label>
      <Field x={8} y={86} w={84} h={16}>
        <Label x={7} y={50} mono small>
          268 435 456
        </Label>
      </Field>
    </Pane>
  </Scene>
);
