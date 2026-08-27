import { render, screen } from '@testing-library/react';
import { AnimationSequence } from 'motion/react';
import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  InstanceResourcesScene,
  LogChannelsScene,
  MonitoringScene,
  ProjectArchiveScene,
  QueueBytesScene,
} from './scenes';

const animate: Mock = vi.fn(() => ({ stop: vi.fn() }));
const reducedMotion = { current: false };

// Only the two hooks are stood in for; the helpers a take is written
// with are the real ones, so what the scenes hand over is what Motion
// would receive.
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useAnimate: () => [vi.fn(), animate],
  useReducedMotion: () => reducedMotion.current,
}));

const SCENES = [
  ['Monitoring', MonitoringScene],
  ['ProjectArchive', ProjectArchiveScene],
  ['LogChannels', LogChannelsScene],
  ['QueueBytes', QueueBytesScene],
  ['InstanceResources', InstanceResourcesScene],
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  reducedMotion.current = false;
});

/**
 * Each scene of a release panel is a sketch of Studio that plays on a
 * loop. Two things have to hold for every one of them: it says what it
 * shows, since it is an image to anyone who cannot see it, and every
 * step of its take addresses a part the scene actually draws - a step
 * pointed at a name that is not there animates nothing, and the scene
 * sits half-still with no error anywhere.
 */
describe('the scenes of a release', () => {
  it.each(SCENES)('%s says what it shows', (_name, Scene) => {
    render(<Scene />);

    const image = screen.getByRole('img');

    expect(image).toHaveAccessibleName(/\w+/);
  });

  it.each(SCENES)('%s plays its take on a loop', (_name, Scene) => {
    render(<Scene />);

    expect(animate).toHaveBeenCalledTimes(1);
    expect(animate.mock.calls[0]?.[1]).toEqual({
      repeat: Number.POSITIVE_INFINITY,
    });
  });

  it.each(SCENES)('%s addresses only parts it draws', (_name, Scene) => {
    const { container } = render(<Scene />);

    const sequence = animate.mock.calls[0]?.[0] as unknown as AnimationSequence;
    const addressed = new Set<string>();

    for (const step of sequence) {
      const target = Array.isArray(step) ? step[0] : step;

      if (typeof target === 'string' && target.startsWith('[data-part=')) {
        addressed.add(target);
      }
    }

    expect(addressed.size).toBeGreaterThan(0);

    const missing = [...addressed].filter(
      (selector) => container.querySelector(selector) === null
    );

    expect(missing).toEqual([]);
  });

  it.each(SCENES)(
    '%s holds still when no motion was asked for',
    (_name, Scene) => {
      reducedMotion.current = true;

      render(<Scene />);

      expect(animate).not.toHaveBeenCalled();
    }
  );
});
