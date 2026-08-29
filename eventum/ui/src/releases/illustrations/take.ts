import {
  AnimationScope,
  AnimationSequence,
  DOMKeyframesDefinition,
  useAnimate,
  useReducedMotion,
} from 'motion/react';
import { useEffect } from 'react';

/**
 * The take of a scene: one Motion sequence, played for as long as the
 * scene is on screen.
 */

/** The selector a sequence step addresses a named part with. */
export function part(name: string): string {
  return `[data-part='${name}']`;
}

/** Where something sets off from and where it lands, in per cent of the
 *  scene it crosses. */
export interface Journey {
  from: [number, number];
  to: [number, number];
}

/**
 * The keyframes that carry a part along a journey.
 *
 * The scene places the part at the start and the take moves it to the
 * end, so both read the one pair of points and cannot drift apart.
 */
export function travel({ from, to }: Journey): DOMKeyframesDefinition {
  return {
    left: [`${from[0]}%`, `${to[0]}%`],
    top: [`${from[1]}%`, `${to[1]}%`],
  };
}

/**
 * Play the take of a scene for as long as it is on screen.
 *
 * The sequence is rebuilt on every run, so it must not close over
 * anything that changes. A reader who asked for no motion gets the
 * resting state the stylesheet paints instead.
 */
export function useTake(build: () => AnimationSequence): AnimationScope {
  const [scope, animate] = useAnimate();
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) {
      return;
    }

    const take = animate(build(), { repeat: Number.POSITIVE_INFINITY });

    return () => take.stop();
    // `build` is a literal of the scene module, so it never changes what
    // it returns; leaving it out keeps the take from restarting on every
    // render of the panel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animate, prefersReducedMotion]);

  return scope;
}
