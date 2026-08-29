import { render, screen } from '@testing-library/react';
import { AnimationSequence } from 'motion/react';
import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  Badge,
  Button,
  Chip,
  Conduit,
  Cursor,
  Diagram,
  Download,
  Field,
  Flash,
  Glyph,
  Label,
  Layer,
  Log,
  Meter,
  Packet,
  Pane,
  Row,
  Scene,
  Stack,
  Stale,
  Ticks,
  Typed,
} from './scene';
import { Journey, part, travel } from './take';

const animate: Mock = vi.fn(() => ({ stop: vi.fn() }));
const reducedMotion = { current: false };

vi.mock('motion/react', () => ({
  useAnimate: () => [vi.fn(), animate],
  useReducedMotion: () => reducedMotion.current,
}));

const TAKE = (): AnimationSequence =>
  [[part('row'), { opacity: 1 }]] as AnimationSequence;

const HANDOVER: Journey = { from: [10, 20], to: [80, 60] };

beforeEach(() => {
  vi.clearAllMocks();
  reducedMotion.current = false;
});

/**
 * A release scene is a recording of Studio being used that plays on a
 * loop, and it is the one illustration in the app that moves on its own.
 * Two things make it safe to ship: it says what it shows for anyone who
 * cannot see it, and it holds still for a reader who asked for no
 * motion.
 */
describe('Scene', () => {
  it('announces what it shows', () => {
    render(
      <Scene title="An instance starting" take={TAKE}>
        <Row name="row" x={10} y={20} w={30} h={4} />
      </Scene>
    );

    // The whole scene is one image as far as a reader is concerned - its
    // parts are strokes of it, not content of their own.
    expect(
      screen.getByRole('img', { name: 'An instance starting' })
    ).toBeInTheDocument();
  });

  it('plays its take on a loop', () => {
    render(
      <Scene title="A take" take={TAKE}>
        <Row name="row" x={0} y={0} />
      </Scene>
    );

    expect(animate).toHaveBeenCalledTimes(1);
    expect(animate).toHaveBeenCalledWith(TAKE(), {
      repeat: Number.POSITIVE_INFINITY,
    });
  });

  it('holds still for a reader who asked for no motion', () => {
    reducedMotion.current = true;

    render(
      <Scene title="A take" take={TAKE}>
        <Row name="row" x={0} y={0} />
      </Scene>
    );

    // The stylesheet paints the resting state, so nothing is animated
    // rather than animated once and stopped.
    expect(animate).not.toHaveBeenCalled();
  });

  it('stops its take when it leaves the screen', () => {
    const stop = vi.fn();
    animate.mockReturnValue({ stop });

    const { unmount } = render(
      <Scene title="A take" take={TAKE}>
        <Row name="row" x={0} y={0} />
      </Scene>
    );

    unmount();

    expect(stop).toHaveBeenCalledTimes(1);
  });
});

/**
 * Every part is placed against the scene in per cent, so a scene scales
 * with the panel it sits in. The two ways of placing differ: a pane
 * hangs from its top edge, while anything that has to line up with a row
 * is centred on the line it names.
 */
describe('the parts of a scene', () => {
  it('hangs a pane from its top edge', () => {
    const { container } = render(
      <Pane name="pane" x={5} y={10} w={90} h={70} />
    );
    const pane = container.querySelector<HTMLElement>('.ev-pane');

    expect(pane?.style.left).toBe('5%');
    expect(pane?.style.top).toBe('10%');
    expect(pane?.style.width).toBe('90%');
    expect(pane?.style.height).toBe('70%');
  });

  it('centres a chip on the line it names', () => {
    const { container } = render(
      <Chip name="chip" x={20} y={30} h={6}>
        Active
      </Chip>
    );
    const chip = container.querySelector<HTMLElement>('.ev-chip');

    // Half its height above the line, so its middle sits on it.
    expect(chip?.style.top).toBe('27%');
  });

  it('leaves a part without a height hanging from the line', () => {
    const { container } = render(
      <Label x={20} y={30}>
        Written
      </Label>
    );
    const label = container.querySelector<HTMLElement>('.ev-label');

    expect(label?.style.top).toBe('30%');
    expect(label?.style.height).toBe('');
  });

  it('names its parts the way a take addresses them', () => {
    const { container } = render(
      <Row name="first-row" x={0} y={0} w={50} h={4} />
    );

    // The selector the sequence uses has to find the part the scene
    // drew, or the step animates nothing and the scene sits still.
    expect(container.querySelector(part('first-row'))).not.toBeNull();
  });

  it('gives the cursor a tap of its own to play', () => {
    const { container } = render(<Cursor at={[40, 50]} />);

    expect(container.querySelector(part('cursor'))).not.toBeNull();
    expect(container.querySelector(part('cursor-tap'))).not.toBeNull();
  });

  it('carries a tone through to the part that paints it', () => {
    const { container } = render(
      <Badge name="state" tone="green" x={0} y={10}>
        reachable
      </Badge>
    );

    expect(container.querySelector(part('state'))).toHaveAttribute(
      'data-tone',
      'green'
    );
  });
});

/**
 * The state a take switches on, and whether the still ends up in it.
 *
 * A scene has to read as one frame for a reader who asked for no motion,
 * and that frame is the end of the take. `rest` is how a scene says
 * which states belong to it: the control the take left switched on
 * carries it, and the one the pointer only passed over does not - so the
 * stylesheet can light the first and leave the second alone.
 */
describe('the frame a scene comes to rest in', () => {
  it('marks the control the take leaves switched on', () => {
    const { container } = render(
      <Button name="install" x={0} y={0} w={20} h={10} answer="Installed" rest>
        Install
      </Button>
    );

    expect(container.querySelector(part('install'))).toHaveAttribute(
      'data-rest',
      'true'
    );
  });

  it('leaves the state a take only passes through unmarked', () => {
    const { container } = render(
      <Button name="hover" x={0} y={0} w={20} h={10}>
        Install
      </Button>
    );

    expect(container.querySelector(part('hover'))).not.toHaveAttribute(
      'data-rest'
    );
  });

  it('tells a layer that stays from one that is taken back', () => {
    const { container } = render(
      <>
        <Layer name="stays" x={0} y={0} w={10} h={10} />
        <Flash name="passes" x={0} y={0} w={10} h={10} />
      </>
    );

    // Both wait hidden; only the one that is taken back is a flash, and
    // that is what keeps it out of the still.
    expect(container.querySelector(part('stays'))).not.toHaveClass('ev-flash');
    expect(container.querySelector(part('passes'))).toHaveClass('ev-flash');
  });

  it('keeps what a take replaces out of the still', () => {
    const { container } = render(<Stale name="masked" x={0} y={0} />);

    expect(container.querySelector(part('masked'))).toHaveClass('ev-stale');
  });
});

/**
 * The vocabulary a scene is drawn from: the parts Studio itself draws.
 * Each answers to the name a take addresses it by, and a control that
 * changes under a press carries both of its readings at once, so the
 * change is a crossfade of two finished states.
 */
describe('the vocabulary of a scene', () => {
  it('gives a button the reading it answers with', () => {
    render(
      <Button name="install" x={0} y={0} w={20} h={10} answer="Installed">
        Install
      </Button>
    );

    expect(screen.getByText('Install')).toBeInTheDocument();
    expect(screen.getByText('Installed')).toBeInTheDocument();
  });

  it('names the ring of a field, so a take can focus it', () => {
    const { container } = render(
      <Field name="search" x={0} y={0} w={30} h={10} />
    );

    expect(container.querySelector(part('search'))).toHaveClass(
      'ev-field-ring'
    );
  });

  it('types a word one character at a time, caret and all', () => {
    const { container } = render(
      <Typed name="query" x={0} y={0}>
        corp
      </Typed>
    );

    // One step of a sequence types the whole word, because every
    // character answers to the one name.
    expect(container.querySelectorAll(part('query'))).toHaveLength(4);
    expect(container.querySelectorAll(part('query-caret'))).toHaveLength(4);
  });

  it('names the ring and the tick of a download apart from the pill', () => {
    const { container } = render(
      <Download name="saving" x={0} y={0} file="auth-events.zip" />
    );

    expect(container.querySelector(part('saving'))).not.toBeNull();
    expect(container.querySelector(part('saving-arc'))).not.toBeNull();
    expect(container.querySelector(part('saving-done'))).not.toBeNull();
  });

  it('sizes a badge by what it says', () => {
    const { container } = render(
      <Badge x={0} y={0} tone="green">
        reachable
      </Badge>
    );

    // A badge marks a row it shares with other content, so it takes the
    // width of its word rather than a width of its own.
    expect(
      container.querySelector('.ev-badge')?.getAttribute('style')
    ).not.toContain('width');
  });

  it('waits a packet at the start of its journey', () => {
    const { container } = render(
      <Packet name="zip" journey={HANDOVER}>
        project.zip
      </Packet>
    );
    const packet = container.querySelector<HTMLElement>(part('zip'));

    expect(packet?.style.getPropertyValue('--ev-from-x')).toBe('10%');
    expect(packet?.style.getPropertyValue('--ev-from-y')).toBe('20%');
  });

  it('carries a packet along the journey it waits on', () => {
    // The scene and its take read the one pair of points, so a packet
    // cannot set off from somewhere it was never drawn.
    expect(travel(HANDOVER)).toEqual({
      left: ['10%', '80%'],
      top: ['20%', '60%'],
    });
  });

  it('names what fills a meter, apart from the track behind it', () => {
    const { container } = render(
      <Meter name="queue" x={0} y={50} w={60} h={4} level={0.4} />
    );

    const level = container.querySelector<HTMLElement>(part('queue'));

    expect(container.querySelector('.ev-meter')).not.toBeNull();
    expect(level?.style.width).toBe('40%');
  });

  it('carries the ordinal key of a run through to what paints it', () => {
    const { container } = render(
      <Ticks name="fan" x={0} y={0} w={50} h={40} bars={[1, 1, 1]} blend />
    );
    const bars = container.querySelectorAll<HTMLElement>(part('fan-bar'));

    // The first bar sits at the purple end of the brand gradient and the
    // last at the cyan one, so a set tells itself apart without taking a
    // colour that already means danger, warning or success.
    expect(bars[0]?.style.getPropertyValue('--ev-tint')).toContain('0%');
    expect(bars[2]?.style.getPropertyValue('--ev-tint')).toContain('100%');
  });

  it('names the bars of a run apart from the run itself', () => {
    const { container } = render(
      <Ticks name="ribbon" x={0} y={0} w={50} h={40} bars={[0.4, 0.8, 0.6]} />
    );

    expect(container.querySelector(part('ribbon'))).not.toBeNull();
    expect(container.querySelectorAll(part('ribbon-bar'))).toHaveLength(3);
  });

  it('stacks a band per instance and names the one in front', () => {
    const { container } = render(
      <Stack
        name="load"
        x={0}
        y={0}
        w={100}
        h={100}
        bands={[
          [0.2, 0.2],
          [0.3, 0.3],
        ]}
        lead={1}
      />
    );

    // A band is read against the one under it, so the chart is one shape
    // per instance rather than one line per instance.
    expect(container.querySelectorAll(part('load-band'))).toHaveLength(1);
    expect(container.querySelector(part('load-lead'))).not.toBeNull();
  });

  it('numbers the records of a log the way the viewer does', () => {
    render(
      <Log
        x={0}
        y={0}
        w={100}
        h={40}
        lines={[
          { level: 'info', text: 'Starting Server', from: 'eventum.app' },
          { level: 'error', text: 'Failed to render', from: 'eventum.core' },
        ]}
      />
    );

    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Failed to render')).toBeInTheDocument();
  });

  it('marks a link a take has to draw', () => {
    const { container } = render(
      <Diagram>
        <Conduit name="write-link" d="M 0 50 H 100" hidden />
        <Conduit name="feed" d="M 0 20 H 100" />
      </Diagram>
    );

    // A link the take draws waits with its dash run off, which is what
    // the stylesheet paints it by; one that is simply there does not.
    expect(container.querySelector(part('write-link'))).toHaveAttribute(
      'data-hidden',
      'true'
    );
    expect(container.querySelector(part('feed'))).not.toHaveAttribute(
      'data-hidden'
    );
  });

  it('draws the mark a control is named by', () => {
    const { container } = render(<Glyph kind="key" tone="accent" />);

    expect(container.querySelector('.ev-glyph')).toHaveAttribute(
      'data-tone',
      'accent'
    );
  });

  it('gives the opening plate the whole stage', () => {
    const { container } = render(
      <Scene title="A release plate" take={TAKE} bleed>
        <Row name="row" x={0} y={0} />
      </Scene>
    );

    expect(container.querySelector('.ev-scene-inset')).toHaveAttribute(
      'data-bleed',
      'true'
    );
  });
});
