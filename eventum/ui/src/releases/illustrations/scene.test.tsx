import { render, screen } from '@testing-library/react';
import { AnimationSequence } from 'motion/react';
import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';

import { Chip, Cursor, Label, Pane, Row, Scene } from './scene';
import { part } from './take';

const animate: Mock = vi.fn(() => ({ stop: vi.fn() }));
const reducedMotion = { current: false };

vi.mock('motion/react', () => ({
  useAnimate: () => [vi.fn(), animate],
  useReducedMotion: () => reducedMotion.current,
}));

const TAKE = (): AnimationSequence =>
  [[part('row'), { opacity: 1 }]] as AnimationSequence;

beforeEach(() => {
  vi.clearAllMocks();
  reducedMotion.current = false;
});

/**
 * A release scene is a sketch of Studio that plays on a loop, and it is
 * the one illustration in the app that moves on its own. Two things make
 * it safe to ship: it says what it shows for anyone who cannot see it,
 * and it holds still for a reader who asked for no motion.
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
      <Chip name="chip" tone="green" x={0} y={10} h={4}>
        Finished
      </Chip>
    );

    expect(container.querySelector('.ev-chip')).toHaveAttribute(
      'data-tone',
      'green'
    );
  });
});
