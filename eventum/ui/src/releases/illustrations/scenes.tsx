import { AnimationSequence, stagger } from 'motion/react';
import { FC } from 'react';

import {
  Chip,
  Cursor,
  Fill,
  Group,
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

/** Repositories: a generator of a connected catalog becomes a project. */
const repositoriesTake = (): AnimationSequence => [
  [part('cursor'), { left: '16%', top: '58%', opacity: [0, 1] }, REACH],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('row'), { opacity: 1 }, { duration: 0.28, at: '<' }],
  [part('cursor'), { left: '50%', top: '58%' }, { ...REACH, at: '+0.45' }],
  [
    part('cursor-tap'),
    { scale: [0.4, 1.7], opacity: [0.85, 0] },
    { ...TAP, at: '-0.1' },
  ],
  [part('install'), { opacity: 1 }, { duration: 0.25, at: '<' }],
  [part('project'), { opacity: 1, x: [16, 0] }, { ...ANSWER, at: '<+0.12' }],
  [
    part('project-line'),
    { scaleX: [0.1, 1] },
    { duration: 0.55, at: '<+0.08', delay: stagger(0.12) },
  ],
  [part('project'), { opacity: 0, x: 16 }, { duration: 0.35, at: HOLD }],
  [part('install'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('row'), { opacity: 0 }, { duration: 0.3, at: '<' }],
  [part('cursor'), { opacity: 0 }, { duration: 0.3, at: '<' }],
];

export const RepositoriesScene: FC = () => (
  <Scene
    title="Installing a generator of a connected repository as a project"
    take={repositoriesTake}
  >
    <Pane x={3} y={8} w={62} h={84}>
      <Label x={5} y={16} tone="accent">
        content-packs
      </Label>

      <Label x={5} y={42}>
        web-nginx
      </Label>

      <Row x={2} y={60} w={96} h={18} name="row" />
      <Label x={5} y={60} tone="accent">
        linux-auditd
      </Label>
      <Chip x={58} y={60} w={36} h={15} name="install">
        Install
      </Chip>

      <Label x={5} y={80}>
        cloud-s3
      </Label>
    </Pane>

    <Layer x={68} y={8} w={29} h={84} name="project">
      <Pane x={0} y={0} w={100} h={100}>
        <Label x={10} y={16} tone="accent">
          linux-auditd
        </Label>
        <Label x={10} y={36}>
          installed
        </Label>
        <Fill x={10} y={52} w={72} h={6} tone="accent" name="project-line" />
        <Fill x={10} y={68} w={56} h={6} name="project-line" />
        <Fill x={10} y={84} w={64} h={6} name="project-line" />
      </Pane>
    </Layer>

    <Cursor at={[20, 108]} name="cursor" />
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
