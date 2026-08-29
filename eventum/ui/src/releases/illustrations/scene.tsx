import { AnimationSequence } from 'motion/react';
import { CSSProperties, FC, ReactNode } from 'react';

import './scene.css';
import { useTake } from './take';

/**
 * The parts a release scene is drawn from, and the take that plays them.
 *
 * A scene is a sketch of Studio itself - a pane, rows, chips, a cursor
 * that moves in and clicks - so a panel shows the feature being used
 * rather than an abstraction of it. The choreography is one Motion
 * sequence per scene: every step names when it starts relative to the
 * one before it, which is what keeps the answer of the interface on the
 * beat of the click.
 *
 * Everything is laid out in container units against the inset box, so a
 * scene scales with the modal, and every part paints itself from a
 * Mantine variable.
 */

type Tone = 'accent' | 'yellow' | 'red' | 'green';

interface Box {
  /** Position and size, in per cent of the scene. */
  x: number;
  y: number;
  w?: number;
  h?: number;
}

interface Part {
  /** Names the part for the sequence: `part('row')` selects it. */
  name?: string;
}

/** A pane, a layer, a group: `y` is its top edge. */
function placeBox({ x, y, w, h }: Box): CSSProperties {
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: w === undefined ? undefined : `${w}%`,
    height: h === undefined ? undefined : `${h}%`,
  };
}

/**
 * A row, a bar, a chip, a word: `y` is the line it sits on.
 *
 * Positions are per cent of the height of the scene while type is sized
 * against its width, so anything that has to line up with a row has to
 * be centred on that line rather than hung from its top edge.
 */
function placeLine({ x, y, w, h }: Box): CSSProperties {
  return {
    left: `${x}%`,
    top: h === undefined ? `${y}%` : `${y - h / 2}%`,
    width: w === undefined ? undefined : `${w}%`,
    height: h === undefined ? undefined : `${h}%`,
  };
}

interface SceneProps {
  /** What the scene shows, for anyone who cannot see it. */
  title: string;
  /** The take, addressed at the named parts of the scene. */
  take: () => AnimationSequence;
  children: ReactNode;
}

/** The surface a scene is drawn on, and the stage its take plays over. */
export const Scene: FC<SceneProps> = ({ title, take, children }) => {
  const scope = useTake(take);

  return (
    <div className="ev-scene" role="img" aria-label={title}>
      <div className="ev-scene-inset" ref={scope}>
        {children}
      </div>
    </div>
  );
};

interface PaneProps extends Box, Part {
  children?: ReactNode;
}

/** A pane of the application - the frame everything else sits in. */
export const Pane: FC<PaneProps> = ({ name, children, ...box }) => (
  <div className="ev-pane" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

interface RowProps extends Box, Part {
  children?: ReactNode;
}

/** A row of a table. Its highlight is a layer of its own, so selecting
 *  it is a fade rather than a colour to interpolate. */
export const Row: FC<RowProps> = ({ name, children, ...box }) => (
  <div className="ev-row" style={placeLine(box)}>
    <span className="ev-row-glow" data-part={name} />
    {children}
  </div>
);

interface FillProps extends Box, Part {
  tone?: Tone;
}

/** A blank of content - a label, a value, a bar. */
export const Fill: FC<FillProps> = ({ name, tone, ...box }) => (
  <div
    className="ev-fill"
    data-part={name}
    data-tone={tone}
    style={placeLine(box)}
  />
);

interface LabelProps extends Box, Part {
  tone?: Tone;
  /** Right-aligned to `x` instead of left-aligned. */
  end?: boolean;
  /** Centred on `x` instead of left-aligned. */
  center?: boolean;
  children: ReactNode;
}

/** A word of the interface, at the size the interface would set it. */
export const Label: FC<LabelProps> = ({
  name,
  tone,
  end,
  center,
  children,
  ...box
}) => (
  <div
    className={`ev-label${end ? ' ev-label-end' : ''}${
      center ? ' ev-label-center' : ''
    }`}
    data-part={name}
    data-tone={tone}
    style={placeLine(box)}
  >
    {children}
  </div>
);

interface HeadlineProps extends Box, Part {
  tone?: Tone;
  /** Centred on `x` rather than set from it. */
  center?: boolean;
  children: ReactNode;
}

/** A title at the size a title is set - for the scene that opens a reel
 *  by naming the release instead of sketching a screen. */
export const Headline: FC<HeadlineProps> = ({
  name,
  tone,
  center,
  children,
  ...box
}) => (
  <div
    className={`ev-headline${center ? ' ev-headline-center' : ''}`}
    data-part={name}
    data-tone={tone}
    style={placeLine(box)}
  >
    {children}
  </div>
);

interface ChipProps extends Box, Part {
  tone?: Tone;
  children: ReactNode;
}

/** A control that can be picked - a filter, a channel, a column. The
 *  picked state is a second copy laid over the first, so picking is a
 *  crossfade of two finished states rather than three interpolations. */
export const Chip: FC<ChipProps> = ({ name, tone, children, ...box }) => (
  <div className="ev-chip" data-tone={tone} style={placeLine(box)}>
    <span className="ev-chip-face">{children}</span>
    <span className="ev-chip-face ev-chip-on" data-part={name}>
      {children}
    </span>
  </div>
);

interface GroupProps extends Box, Part {
  children?: ReactNode;
}

/** A set of parts the take brings in: hidden until it says otherwise. */
export const Layer: FC<GroupProps> = ({ name, children, ...box }) => (
  <div className="ev-layer" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

/** A set of parts the take replaces: gone once the click lands, and
 *  therefore absent in the still a reader with no motion sees. */
export const Stale: FC<GroupProps> = ({ name, children, ...box }) => (
  <div className="ev-group ev-stale" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

/** A set of parts that are simply there, placed against one box. */
export const Group: FC<GroupProps> = ({ name, children, ...box }) => (
  <div className="ev-group" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

interface CursorProps extends Part {
  /** Where it waits before the take begins, in per cent. */
  at: [number, number];
}

/** The pointer: it moves in, clicks, and the interface answers. */
export const Cursor: FC<CursorProps> = ({ name = 'cursor', at }) => (
  <div
    className="ev-cursor"
    data-part={name}
    style={{ left: `${at[0]}%`, top: `${at[1]}%` }}
  >
    <svg viewBox="0 0 12 16" className="ev-cursor-arrow" aria-hidden="true">
      <path d="M1 1 L1 13 L4.2 10.2 L6.4 15 L8.6 14 L6.4 9.4 L10.6 9.4 Z" />
    </svg>
    <span className="ev-cursor-tap" data-part={`${name}-tap`} />
  </div>
);
