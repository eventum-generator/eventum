import { AnimationSequence, stagger } from 'motion/react';
import { FC } from 'react';

import {
  Chip,
  Cursor,
  Fill,
  Group,
  Headline,
  Label,
  Layer,
  Pane,
  Row,
  Scene,
  Stale,
} from './scene';
import { part } from './take';

/**
 * The scenes of the 2.8.0 release.
 *
 * Each one sketches the part of Studio the change lives in and plays one
 * take over it: the cursor lands, the interface answers, the result
 * holds, and everything leaves together. Every step of a take names when
 * it starts against the step before it, so the answer never drifts off
 * the click.
 */

/** How the cursor travels: quick to leave, settled on arrival. */
const REACH = { duration: 0.85, ease: [0.32, 0.72, 0, 1] } as const;
const TAP = { duration: 0.55, ease: 'easeOut' } as const;
const ANSWER = { duration: 0.42, ease: [0.22, 0.9, 0.24, 1] } as const;

/** The pause on the result before the scene resets. */
const HOLD = '+1.7';

/** The card the reel opens on: the release names itself. */
const openingTake = (): AnimationSequence => [
  [part('mark'), { opacity: [0, 1], y: [10, 0] }, { duration: 0.5 }],
  [
    part('version'),
    { opacity: [0, 1], scale: [0.94, 1] },
    { duration: 0.6, at: '<+0.1' },
  ],
  [
    part('theme'),
    { opacity: 1 },
    { duration: 0.4, at: '<+0.3', delay: stagger(0.13) },
  ],
  [part('theme'), { opacity: 0 }, { duration: 0.35, at: HOLD }],
  [part('version'), { opacity: 0, scale: 0.97 }, { duration: 0.35, at: '<' }],
  [part('mark'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const OPENING_THEMES = [
  { id: 'repositories', x: 2.6, w: 27.6 },
  { id: 'archives', x: 32.2, w: 20.4 },
  { id: 'secrets', x: 54.6, w: 18.6 },
  { id: 'resources', x: 75.2, w: 22.2 },
];

export const OpeningScene: FC = () => (
  <Scene title="Eventum 2.8.0, and what it brought" take={openingTake}>
    <Label x={50} y={18} name="mark" center>
      Eventum
    </Label>
    <Headline x={50} y={45} name="version" center>
      2.8.0
    </Headline>

    {OPENING_THEMES.map((theme) => (
      <Chip key={theme.id} x={theme.x} y={84} w={theme.w} h={16} name="theme">
        {theme.id}
      </Chip>
    ))}
  </Scene>
);

/** Repositories: a card of the catalog is installed into the workspace. */
const repositoriesTake = (): AnimationSequence => [
  [part('cursor'), { left: '54%', top: '56%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('install'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('picked'), { opacity: 1 }, { duration: 0.3, at: '<+0.04' }],
  [part('landed'), { opacity: 1, y: [-10, 0] }, { ...ANSWER, at: '<+0.18' }],
  [part('landed'), { opacity: 0, y: -6 }, { duration: 0.35, at: HOLD }],
  [part('picked'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('install'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const CATALOG_CARDS = [
  { id: 'web-nginx', x: 0, picked: false },
  { id: 'linux-auditd', x: 34.5, picked: true },
  { id: 'cloud-s3', x: 69, picked: false },
];

export const RepositoriesScene: FC = () => (
  <Scene
    title="Installing a generator of a repository catalog as a project"
    take={repositoriesTake}
  >
    <Label x={1} y={5}>
      content-packs
    </Label>

    {CATALOG_CARDS.map((card) => (
      <Pane key={card.id} x={card.x} y={16} w={31} h={46}>
        <Label x={11} y={26} tone={card.picked ? 'accent' : undefined}>
          {card.id}
        </Label>
        <Fill x={11} y={54} w={62} h={7} />
        <Fill x={11} y={76} w={44} h={7} />
      </Pane>
    ))}

    <Group x={34.5} y={16} w={31} h={46}>
      <Layer x={0} y={0} w={100} h={100} name="picked">
        <Chip x={11} y={82} w={78} h={20} name="install">
          Install
        </Chip>
      </Layer>
    </Group>

    <Layer x={0} y={70} w={100} h={30} name="landed">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={4} y={50}>
          workspace
        </Label>
        <Chip x={40} y={50} w={38} h={40} tone="green">
          linux-auditd
        </Chip>
      </Pane>
    </Layer>

    <Cursor at={[54, 108]} name="cursor" />
  </Scene>
);

/** Discover: GitHub is searched for the topic that marks a repository. */
const discoverTake = (): AnimationSequence => [
  [part('query'), { opacity: [0, 1] }, { duration: 0.35 }],
  [
    part('found'),
    { opacity: [0, 1], y: [10, 0] },
    { duration: 0.45, at: '<+0.2', delay: stagger(0.11) },
  ],
  [part('cursor'), { left: '85%', top: '47%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('connect'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('connect'), { opacity: 0 }, { duration: 0.3, at: HOLD }],
  [part('found'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('query'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const DISCOVERED = [
  { id: 'content-packs', y: 47, stars: 34 },
  { id: 'acme-packs', y: 70, stars: 21 },
  { id: 'lab-sources', y: 90, stars: 12 },
];

export const DiscoverScene: FC = () => (
  <Scene
    title="Searching GitHub for the repositories that publish generators"
    take={discoverTake}
  >
    <Pane x={2} y={4} w={96} h={92}>
      <Chip x={4} y={14} w={44} h={16}>
        github.com
      </Chip>
      <Label x={52} y={14} tone="accent" name="query">
        topic:eventum-generators
      </Label>

      <Group x={0} y={0} w={100} h={100}>
        {DISCOVERED.map((repo) => (
          <Group key={repo.id} x={0} y={0} w={100} h={100} name="found">
            <Label x={5} y={repo.y}>
              {repo.id}
            </Label>
            <Label x={50} y={repo.y}>
              ★ {repo.stars}
            </Label>
          </Group>
        ))}
      </Group>

      <Chip x={76} y={47} w={20} h={16} name="connect">
        Connect
      </Chip>
    </Pane>

    <Cursor at={[84, 108]} name="cursor" />
  </Scene>
);

/** Secrets: a password field is filled from the keyring by name. */
const keyringTake = (): AnimationSequence => [
  [part('cursor'), { left: '86%', top: '34%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('key'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('list'), { opacity: 1, y: [-8, 0] }, { ...ANSWER, at: '<+0.06' }],
  [part('cursor'), { left: '55%', top: '65%' }, { ...REACH, at: '+0.4' }],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('pick'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('list'), { opacity: 0 }, { duration: 0.3, at: '+0.35' }],
  [part('masked'), { opacity: 0 }, { duration: 0.25, at: '<' }],
  [part('filled'), { opacity: [0, 1] }, { duration: 0.4, at: '<+0.05' }],
  [part('filled'), { opacity: 0 }, { duration: 0.35, at: HOLD }],
  [part('masked'), { opacity: 1 }, { duration: 0.3, at: '<' }],
  [part('key'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('pick'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const KEYRING_SECRETS = [
  { id: 'gh_token', y: 24, pick: true },
  { id: 'ch_password', y: 52, pick: false },
  { id: 'os_api_key', y: 80, pick: false },
];

export const KeyringPickerScene: FC = () => (
  <Scene
    title="Filling a password field with a secret picked from the keyring"
    take={keyringTake}
  >
    <Label x={2} y={8}>
      Password
    </Label>

    <Pane x={2} y={20} w={96} h={30}>
      <Stale x={0} y={0} w={100} h={100} name="masked">
        <Label x={4} y={50}>
          ••••••••••
        </Label>
      </Stale>
      <Layer x={0} y={0} w={100} h={100} name="filled">
        <Label x={4} y={50} tone="accent">
          {'${secrets.gh_token}'}
        </Label>
      </Layer>
      <Chip x={80} y={50} w={16} h={54} name="key">
        key
      </Chip>
    </Pane>

    <Layer x={44} y={54} w={54} h={46} name="list">
      <Pane x={0} y={0} w={100} h={100}>
        {KEYRING_SECRETS.map((secret) => (
          <Label
            key={secret.id}
            x={8}
            y={secret.y}
            tone={secret.pick ? 'accent' : undefined}
          >
            {secret.id}
          </Label>
        ))}
        <Row x={3} y={24} w={94} h={24} name="pick" />
      </Pane>
    </Layer>

    <Cursor at={[82, 108]} name="cursor" />
  </Scene>
);

/** Global state: a script reaches the keys a template already shared. */
const globalStateTake = (): AnimationSequence => [
  [part('template'), { opacity: [0.35, 1] }, { duration: 0.4 }],
  [part('template-wire'), { scaleX: [0, 1] }, { duration: 0.5, at: '<+0.05' }],
  [part('script'), { opacity: [0.35, 1] }, { duration: 0.4, at: '<+0.25' }],
  [part('script-wire'), { scaleX: [0, 1] }, { duration: 0.5, at: '<+0.05' }],
  [
    part('state-key'),
    { opacity: [0, 1], x: [-8, 0] },
    { duration: 0.4, at: '<+0.12', delay: stagger(0.12) },
  ],
  [part('state-key'), { opacity: 0 }, { duration: 0.35, at: HOLD }],
  [part('script-wire'), { scaleX: 0 }, { duration: 0.3, at: '<' }],
  [part('template-wire'), { scaleX: 0 }, { duration: 0.3, at: '<' }],
  [part('script'), { opacity: 0.35 }, { duration: 0.3, at: '<' }],
  [part('template'), { opacity: 0.35 }, { duration: 0.3, at: '<' }],
];

const GLOBAL_KEYS = ['session.id', 'host.seq', 'user.pool'];

export const GlobalStateScene: FC = () => (
  <Scene
    title="A template and a script writing to the state they share"
    take={globalStateTake}
  >
    <Group x={0} y={6} w={34} h={40} name="template">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={14} y={50}>
          template
        </Label>
      </Pane>
    </Group>
    <Fill x={34} y={18} w={14} h={4} tone="accent" name="template-wire" />

    <Group x={0} y={56} w={34} h={40} name="script">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={18} y={50} tone="accent">
          script
        </Label>
      </Pane>
    </Group>
    <Fill x={34} y={72} w={14} h={4} tone="accent" name="script-wire" />

    <Pane x={48} y={6} w={52} h={90}>
      <Label x={8} y={16}>
        globals
      </Label>
      {GLOBAL_KEYS.map((key, index) => (
        <Label
          key={key}
          x={8}
          y={40 + index * 22}
          name="state-key"
          tone="accent"
        >
          {key}
        </Label>
      ))}
    </Pane>
  </Scene>
);

/** Monitoring: a row opens the details of the instance behind the load. */
const monitoringTake = (): AnimationSequence => [
  [part('cursor'), { left: '34%', top: '58%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('row'), { opacity: 1 }, { duration: 0.28, at: '<' }],
  [part('details'), { opacity: 1, x: [16, 0] }, { ...ANSWER, at: '<+0.06' }],
  [
    part('detail-bar'),
    { scaleX: [0.1, 1] },
    { duration: 0.55, at: '<+0.08', delay: stagger(0.12) },
  ],
  [part('details'), { opacity: 0, x: 16 }, { duration: 0.35, at: HOLD }],
  [part('row'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

export const MonitoringScene: FC = () => (
  <Scene
    title="Clicking an instance row opens its details beside the table"
    take={monitoringTake}
  >
    <Pane x={3} y={8} w={62} h={84}>
      <Chip x={4} y={15} w={28} h={17}>
        3 running
      </Chip>
      <Chip x={36} y={15} w={28} h={17}>
        1.2k eps
      </Chip>
      <Chip x={68} y={15} w={28} h={17} tone="red">
        2 failing
      </Chip>

      <Label x={7} y={42}>
        gen-01
      </Label>
      <Fill x={48} y={42} w={11} h={5} />

      <Row x={3} y={60} w={94} h={16} name="row" />
      <Label x={7} y={60} tone="accent">
        gen-02
      </Label>
      <Fill x={48} y={60} w={38} h={5} tone="accent" />

      <Label x={7} y={78}>
        gen-03
      </Label>
      <Fill x={48} y={78} w={7} h={5} />
    </Pane>

    <Layer x={68} y={8} w={29} h={84} name="details">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={10} y={12} tone="accent">
          gen-02
        </Label>
        <Label x={10} y={32}>
          errors
        </Label>
        <Fill x={10} y={45} w={56} h={6} tone="red" name="detail-bar" />
        <Label x={10} y={64}>
          queue
        </Label>
        <Fill x={10} y={77} w={60} h={6} tone="yellow" name="detail-bar" />
      </Pane>
    </Layer>

    <Cursor at={[30, 108]} name="cursor" />
  </Scene>
);

/** Projects: one is picked, exported, and handed over as an archive. */
const archiveTake = (): AnimationSequence => [
  [part('cursor'), { left: '15%', top: '50%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('row'), { opacity: 1 }, { duration: 0.28, at: '<' }],
  [part('cursor'), { left: '46%', top: '50%' }, { ...REACH, at: '+0.45' }],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('export'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [
    part('archive'),
    { opacity: 1, scale: [0.92, 1] },
    { ...ANSWER, at: '<+0.12' },
  ],
  [part('progress'), { scaleX: [0, 1] }, { duration: 0.9, at: '<+0.1' }],
  [part('archive'), { opacity: 0, scale: 0.96 }, { duration: 0.35, at: HOLD }],
  [part('export'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('row'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

export const ProjectArchiveScene: FC = () => (
  <Scene
    title="Exporting a project from its row hands over an archive"
    take={archiveTake}
  >
    <Pane x={3} y={10} w={56} h={80}>
      <Label x={6} y={22}>
        web-access
      </Label>

      <Row x={3} y={50} w={94} h={24} name="row" />
      <Label x={6} y={50} tone="accent">
        auth-events
      </Label>
      <Chip x={58} y={50} w={36} h={17} name="export">
        Export
      </Chip>

      <Label x={6} y={78}>
        dns-traffic
      </Label>
    </Pane>

    <Layer x={64} y={22} w={32} h={56} name="archive">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={12} y={26} tone="accent">
          auth-events.zip
        </Label>
        <Fill x={12} y={52} w={76} h={7} />
        <Fill x={12} y={52} w={76} h={7} tone="accent" name="progress" />
        <Label x={12} y={76}>
          ready
        </Label>
      </Pane>
    </Layer>

    <Cursor at={[18, 108]} name="cursor" />
  </Scene>
);

/** Logging: the viewer switches to the channel of one component. */
const logChannelsTake = (): AnimationSequence => [
  [part('cursor'), { left: '38%', top: '20%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('server'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('before'), { opacity: 0 }, { duration: 0.25, at: '<' }],
  [part('lines'), { opacity: 1 }, { duration: 0.01, at: '<+0.08' }],
  [
    part('after'),
    { opacity: [0, 1], y: [8, 0] },
    { duration: 0.4, at: '<', delay: stagger(0.06) },
  ],
  [part('lines'), { opacity: 0 }, { duration: 0.3, at: HOLD }],
  [part('before'), { opacity: 1 }, { duration: 0.3, at: '<' }],
  [part('server'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const BEFORE_LINES = [62, 78, 48, 70, 40];
const AFTER_LINES = [84, 56, 72, 44, 66];

export const LogChannelsScene: FC = () => (
  <Scene
    title="Switching the log viewer to the channel of a component"
    take={logChannelsTake}
  >
    <Pane x={3} y={8} w={94} h={84}>
      <Chip x={3} y={15} w={20} h={16}>
        main
      </Chip>
      <Chip x={26} y={15} w={22} h={16} name="server">
        server
      </Chip>
      <Chip x={51} y={15} w={22} h={16}>
        access
      </Chip>
      <Chip x={76} y={15} w={20} h={16}>
        mcp
      </Chip>
    </Pane>

    <Stale x={3} y={8} w={94} h={84} name="before">
      {BEFORE_LINES.map((width, index) => (
        <Fill key={width} x={3} y={38 + index * 11} w={width * 0.9} h={6} />
      ))}
    </Stale>

    <Layer x={3} y={8} w={94} h={84} name="lines">
      {AFTER_LINES.map((width, index) => (
        <Fill
          key={width}
          x={3}
          y={38 + index * 11}
          w={width * 0.9}
          h={6}
          tone={index === 0 ? 'accent' : undefined}
          name="after"
        />
      ))}
    </Layer>

    <Cursor at={[14, 108]} name="cursor" />
  </Scene>
);

/** The events queue, held at a size rather than at a count of batches. */
const queueTake = (): AnimationSequence => [
  [part('level'), { scaleX: [0.08, 0.92] }, { duration: 1.9, ease: 'easeOut' }],
  [part('limit'), { opacity: [0.35, 1] }, { duration: 0.35, at: '-0.35' }],
  [part('held'), { opacity: [0, 1] }, { duration: 0.4, at: '<' }],
  [part('held'), { opacity: 0 }, { duration: 0.4, at: HOLD }],
  [part('limit'), { opacity: 0.35 }, { duration: 0.4, at: '<' }],
];

export const QueueBytesScene: FC = () => (
  <Scene
    title="An events queue filling up to the size it is allowed"
    take={queueTake}
  >
    <Pane x={6} y={14} w={88} h={72}>
      <Label x={5} y={18}>
        events queue
      </Label>
      <Label x={95} y={18} tone="yellow" end name="limit">
        256 MiB
      </Label>

      <Fill x={5} y={50} w={90} h={11} />
      <Fill x={5} y={50} w={83} h={11} tone="yellow" name="level" />
      <Fill x={88} y={50} w={0.7} h={30} tone="yellow" name="limit" />

      <Label x={5} y={80}>
        10 batches
      </Label>
      <Label x={95} y={80} end name="held">
        held in memory
      </Label>
    </Pane>
  </Scene>
);

/** Resources: the running instances rank by what they occupy. */
const resourcesTake = (): AnimationSequence => [
  [part('cursor'), { left: '43%', top: '19%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('cpu'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('row'), { opacity: 1 }, { duration: 0.3, at: '<+0.05' }],
  [
    part('bar'),
    { scaleX: [0.06, 1] },
    { duration: 0.6, at: '<', delay: stagger(0.05) },
  ],
  [part('row'), { opacity: 0 }, { duration: 0.3, at: HOLD }],
  [part('cpu'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

const RESOURCE_ROWS = [
  { id: 'gen-02', y: 39, cpu: 19, wait: 12, disk: 9, lead: true },
  { id: 'gen-01', y: 61, cpu: 8, wait: 4, disk: 7 },
  { id: 'gen-03', y: 83, cpu: 4, wait: 2, disk: 4 },
];

export const InstanceResourcesScene: FC = () => (
  <Scene
    title="Sorting the running instances by the processor they take"
    take={resourcesTake}
  >
    <Pane x={3} y={8} w={94} h={84}>
      <Label x={4} y={13}>
        instance
      </Label>
      <Chip x={34} y={13} w={18} h={15} name="cpu">
        cpu
      </Chip>
      <Label x={60} y={13}>
        wait
      </Label>
      <Label x={80} y={13}>
        disk
      </Label>

      {RESOURCE_ROWS.map((row) => (
        <Row
          key={row.id}
          x={2}
          y={row.y}
          w={96}
          h={18}
          name={row.lead ? 'row' : undefined}
        />
      ))}
    </Pane>

    <Group x={3} y={8} w={94} h={84}>
      {RESOURCE_ROWS.map((row) => (
        <Label
          key={row.id}
          x={4}
          y={row.y}
          tone={row.lead ? 'accent' : undefined}
        >
          {row.id}
        </Label>
      ))}
      {RESOURCE_ROWS.map((row) => (
        <Fill
          key={`cpu-${row.id}`}
          x={34}
          y={row.y}
          w={row.cpu}
          h={6}
          tone={row.lead ? 'accent' : undefined}
          name="bar"
        />
      ))}
      {RESOURCE_ROWS.map((row) => (
        <Fill
          key={`wait-${row.id}`}
          x={60}
          y={row.y}
          w={row.wait}
          h={6}
          name="bar"
        />
      ))}
      {RESOURCE_ROWS.map((row) => (
        <Fill
          key={`disk-${row.id}`}
          x={80}
          y={row.y}
          w={row.disk}
          h={6}
          name="bar"
        />
      ))}
    </Group>

    <Cursor at={[24, 108]} name="cursor" />
  </Scene>
);
