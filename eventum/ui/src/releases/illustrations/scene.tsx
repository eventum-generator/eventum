import { AnimationSequence } from 'motion/react';
import { CSSProperties, FC, ReactNode } from 'react';

import './scene.css';
import { Journey, useTake } from './take';

/**
 * The parts a release scene is drawn from, and the take that plays them.
 *
 * A scene is a condensed recording of somebody using the feature: the
 * surfaces Studio actually draws, the control the gesture lands on, and
 * the answer the interface gives back. It is not a screenshot - the
 * chrome the point does not need is gone, the type is set larger than
 * life and the one thing that matters is exaggerated - and it is not a
 * diagram either: nothing here stands in for an idea. The choreography
 * is one Motion sequence per scene, and every step names when it starts
 * relative to the one before it, so what answers stays on the beat of
 * what was clicked.
 *
 * Everything is laid out in container units against the inset box, so a
 * scene scales with the modal, and every part paints itself from a
 * Mantine variable.
 */

type Tone = 'accent' | 'cyan' | 'yellow' | 'red' | 'green';

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

/**
 * A state a take switches on, and whether the still ends up in it.
 *
 * Nothing plays for a reader who asked for no motion, so a scene has to
 * read as one frame. `rest` is the scene saying that this is the frame:
 * the control that ends up picked carries it, and the one the pointer
 * only passed over does not.
 */
interface Switchable extends Part {
  /** The still shows this state switched on. */
  rest?: boolean;
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

/**
 * The brand gradient used as an ordinal key.
 *
 * `step` runs from 0 at the purple end to 1 at the cyan one, so a set of
 * siblings - the bands of a load chart, the bars of a ribbon - can tell
 * itself apart without borrowing a colour that already means danger,
 * warning or success.
 */
function tint(step: number | undefined): Record<string, string> {
  if (step === undefined) {
    return {};
  }

  const share = Math.round(Math.min(Math.max(step, 0), 1) * 100);

  return {
    '--ev-tint': `color-mix(in srgb, var(--mantine-color-cyan-4) ${share}%, var(--mantine-color-primary-5))`,
  };
}

/** Custom properties a part is placed or tinted with. */
function withVars(
  style: CSSProperties,
  vars: Record<string, string>
): CSSProperties {
  return { ...style, ...vars } as CSSProperties;
}

/** The second face of a control - the state a take switches on. */
function restOf({ rest }: Switchable): 'true' | undefined {
  return rest === true ? 'true' : undefined;
}

interface SceneProps {
  /** What the scene shows, for anyone who cannot see it. */
  title: string;
  /** The take, addressed at the named parts of the scene. */
  take: () => AnimationSequence;
  /** Draw over the whole stage instead of the inset the panels share. */
  bleed?: boolean;
  children: ReactNode;
}

/** The surface a scene is drawn on, and the stage its take plays over. */
export const Scene: FC<SceneProps> = ({ title, take, bleed, children }) => {
  const scope = useTake(take);

  return (
    <div className="ev-scene" role="img" aria-label={title}>
      <div className="ev-scene-inset" data-bleed={bleed} ref={scope}>
        {children}
      </div>
    </div>
  );
};

/* ========== Surfaces ========== */

interface PaneProps extends Box, Part {
  children?: ReactNode;
}

/** A panel of the application - the frame everything else sits in. */
export const Pane: FC<PaneProps> = ({ name, children, ...box }) => (
  <div className="ev-pane" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

interface CardProps extends Box, Switchable {
  children?: ReactNode;
}

/** A card inside a panel - a repository in a list, an instance in a
 *  scenario, a tile of readings. Its lit state is a layer of its own, so
 *  a pointer resting on it is a fade rather than a colour to
 *  interpolate. */
export const Card: FC<CardProps> = ({ name, rest, children, ...box }) => (
  <div className="ev-card" style={placeBox(box)}>
    <span
      className="ev-card-lit"
      data-part={name}
      data-rest={restOf({ rest })}
    />
    {children}
  </div>
);

interface PopoverProps extends Box, Switchable {
  children?: ReactNode;
}

/** A surface that opens over the page: a menu, a notification, the tray
 *  a browser drops a download into. It waits closed, so a take has to
 *  open it and the still only holds it open when the scene says so. */
export const Popover: FC<PopoverProps> = ({ name, rest, children, ...box }) => (
  <div
    className="ev-popover"
    data-part={name}
    data-rest={restOf({ rest })}
    style={placeBox(box)}
  >
    {children}
  </div>
);

/** The field the opening plate is drawn on: the one scene that is not a
 *  recording, and the one surface that carries a wash of its own. */
export const Plate: FC = () => <div className="ev-plate" />;

interface RowProps extends Box, Switchable {
  /** Already picked, for a selection a take moves rather than makes. */
  lit?: boolean;
  children?: ReactNode;
}

/** A row of a table. Its highlight is a layer of its own, so selecting
 *  it is a fade rather than a colour to interpolate. */
export const Row: FC<RowProps> = ({ name, lit, rest, children, ...box }) => (
  <div className="ev-row" data-lit={lit} style={placeLine(box)}>
    <span
      className="ev-row-glow"
      data-part={name}
      data-rest={restOf({ rest })}
    />
    {children}
  </div>
);

interface GroupProps extends Box, Part {
  children?: ReactNode;
}

/** A set of parts the take brings in and leaves there: hidden until it
 *  says otherwise, and part of the frame the still holds. */
export const Layer: FC<GroupProps> = ({ name, children, ...box }) => (
  <div className="ev-layer" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

/** A set of parts a take shows on its way through and takes back: an
 *  intermediate state, gone by the end, and therefore absent from the
 *  frame the still holds. */
export const Flash: FC<GroupProps> = ({ name, children, ...box }) => (
  <div className="ev-layer ev-flash" data-part={name} style={placeBox(box)}>
    {children}
  </div>
);

/** A set of parts the take replaces: gone once the answer lands, and
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

/* ========== Marks ========== */

/** The marks the interface names things by. */
const GLYPHS = {
  repo: (
    <>
      <circle cx="6" cy="6" r="2.6" />
      <circle cx="6" cy="18" r="2.6" />
      <circle cx="18" cy="7" r="2.6" />
      <path d="M6 8.6v6.8" />
      <path d="M15.6 8.4c-2.6 3-5.6 3.9-9.4 6.6" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.2" />
      <path d="M15.2 15.2 20.5 20.5" />
    </>
  ),
  archive: (
    <>
      <rect x="3.2" y="4" width="17.6" height="4.6" rx="1.2" />
      <path d="M5.4 8.6v9.6a2.2 2.2 0 0 0 2.2 2.2h8.8a2.2 2.2 0 0 0 2.2-2.2V8.6" />
      <path d="M10.2 12.6h3.6" />
    </>
  ),
  key: (
    <>
      <circle cx="7.4" cy="12" r="3.8" />
      <path d="M11.2 12h9.4" />
      <path d="M17.4 12v3.2" />
      <path d="M20.6 12v2.4" />
    </>
  ),
  eye: (
    <>
      <path d="M2.4 12c2.6-4.4 5.8-6.6 9.6-6.6s7 2.2 9.6 6.6c-2.6 4.4-5.8 6.6-9.6 6.6S5 16.4 2.4 12Z" />
      <circle cx="12" cy="12" r="2.8" />
    </>
  ),
  template: (
    <>
      <path d="M9.2 6.6 4.6 12l4.6 5.4" />
      <path d="M14.8 6.6 19.4 12l-4.6 5.4" />
    </>
  ),
  script: (
    <>
      <path d="M5.6 7.6 9.8 12l-4.2 4.4" />
      <path d="M12.4 16.4h6.2" />
    </>
  ),
  store: (
    <>
      <ellipse cx="12" cy="6.4" rx="7.2" ry="3" />
      <path d="M4.8 6.4v11.2c0 1.7 3.2 3 7.2 3s7.2-1.3 7.2-3V6.4" />
      <path d="M4.8 12c0 1.7 3.2 3 7.2 3s7.2-1.3 7.2-3" />
    </>
  ),
  folder: (
    <>
      <path d="M3.4 7.4a2 2 0 0 1 2-2h3.3l2.1 2.8h7.8a2 2 0 0 1 2 2v8.4a2 2 0 0 1-2 2H5.4a2 2 0 0 1-2-2Z" />
    </>
  ),
  file: (
    <>
      <path d="M13.6 3.4H7.8a2 2 0 0 0-2 2v13.2a2 2 0 0 0 2 2h8.4a2 2 0 0 0 2-2V8.2Z" />
      <path d="M13.6 3.4v4.8h4.6" />
    </>
  ),
  logs: (
    <>
      <path d="M4 6.4h16" />
      <path d="M4 12h16" />
      <path d="M4 17.6h10" />
    </>
  ),
  queue: (
    <>
      <rect x="3.6" y="5" width="16.8" height="4.2" rx="1.4" />
      <rect x="3.6" y="14.8" width="16.8" height="4.2" rx="1.4" />
      <path d="M12 9.2v5.6" />
    </>
  ),
  check: (
    <>
      <path d="M4.6 12.6 9.6 17.6 19.4 6.8" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16.4V5.2" />
      <path d="M7.2 10 12 5.2l4.8 4.8" />
      <path d="M4 19.4h16" />
    </>
  ),
  chevron: (
    <>
      <path d="M9 5.6 15.4 12 9 18.4" />
    </>
  ),
  caret: (
    <>
      <path d="M5.6 9 12 15.4 18.4 9" />
    </>
  ),
} as const;

type GlyphKind = keyof typeof GLYPHS;

interface GlyphProps extends Part {
  kind: GlyphKind;
  tone?: Tone;
  /** Centred on this point of the box when given; inline in its row if
   *  not. */
  at?: [number, number];
}

/**
 * The mark that names something without spending a word on it.
 *
 * A placed mark hangs in a spot of its own, and the mark inside it
 * carries nothing but its own drawing - so a take can turn it, as the
 * chevron of a card turns when the card opens, without knocking it off
 * the point it was centred on.
 */
export const Glyph: FC<GlyphProps> = ({ name, kind, tone, at }) => {
  const mark = (
    <svg
      className="ev-glyph"
      data-part={name}
      data-tone={tone}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      {GLYPHS[kind]}
    </svg>
  );

  if (at === undefined) {
    return mark;
  }

  return (
    <span className="ev-spot" style={{ left: `${at[0]}%`, top: `${at[1]}%` }}>
      {mark}
    </span>
  );
};

/* ========== Controls ========== */

interface FieldProps extends Box, Part {
  /** Focused already, for a field a take does not have to click. */
  lit?: boolean;
  children?: ReactNode;
}

/** A text input: the box a value is typed or written into. */
export const Field: FC<FieldProps> = ({ name, lit, children, ...box }) => (
  <div className="ev-field" data-lit={lit} style={placeLine(box)}>
    <span className="ev-field-ring" data-part={name} />
    {children}
  </div>
);

interface AdornmentProps extends Switchable {
  /** Where it sits inside the field, in per cent of it. */
  at: [number, number];
  glyph: GlyphKind;
  tone?: Tone;
}

/** The icon button inside a field - the eye that unmasks a password, the
 *  key that offers the keyring. */
export const Adornment: FC<AdornmentProps> = ({
  name,
  at,
  glyph,
  tone,
  rest,
}) => (
  <span
    className="ev-adornment"
    style={{ left: `${at[0]}%`, top: `${at[1]}%` }}
  >
    <span
      className="ev-adornment-lit"
      data-part={name}
      data-rest={restOf({ rest })}
    />
    <Glyph kind={glyph} tone={tone} />
  </span>
);

interface ButtonProps extends Box, Switchable {
  /** `filled` is the call to action; `default` is everything else. */
  variant?: 'filled' | 'default';
  tone?: Tone;
  glyph?: GlyphKind;
  /** What the button reads once the take has switched it on. */
  answer?: ReactNode;
  children: ReactNode;
}

/** A button. Its pressed state is a second face laid over the first, so
 *  a press is a crossfade of two finished states, and a button that
 *  changes what it says carries both readings at once. */
export const Button: FC<ButtonProps> = ({
  name,
  variant = 'default',
  tone,
  glyph,
  answer,
  rest,
  children,
  ...box
}) => (
  <div
    className="ev-button"
    data-variant={variant}
    data-tone={tone}
    style={placeLine(box)}
  >
    <span className="ev-button-face">{children}</span>
    <span
      className="ev-button-face ev-button-on"
      data-part={name}
      data-rest={restOf({ rest })}
    >
      {glyph !== undefined && <Glyph kind={glyph} />}
      {answer ?? children}
    </span>
  </div>
);

interface TabProps extends Box, Switchable {
  children: ReactNode;
}

/** A tab of the underlined kind, the way the Repositories page sets
 *  them. The active face carries the rule under the word. */
export const Tab: FC<TabProps> = ({ name, rest, children, ...box }) => (
  <div className="ev-tab" style={placeLine(box)}>
    <span className="ev-tab-face">{children}</span>
    <span
      className="ev-tab-face ev-tab-on"
      data-part={name}
      data-rest={restOf({ rest })}
    >
      {children}
      <span className="ev-tab-rule" />
    </span>
  </div>
);

interface ChipProps extends Box, Switchable {
  /** Already picked, for the segment a take moves away from. */
  lit?: boolean;
  children: ReactNode;
}

/** A segment of a segmented control - a filter, a log channel, a way of
 *  grouping a chart. */
export const Chip: FC<ChipProps> = ({ name, lit, rest, children, ...box }) => (
  <div className="ev-chip" data-lit={lit} style={placeLine(box)}>
    <span className="ev-chip-face">{children}</span>
    <span
      className="ev-chip-face ev-chip-on"
      data-part={name}
      data-rest={restOf({ rest })}
    >
      {children}
    </span>
  </div>
);

interface BadgeProps extends Box, Part {
  tone?: Tone;
  /** Right-aligned to `x` instead of left-aligned. */
  end?: boolean;
  /** Set in the monospace face, for a key or a count. */
  mono?: boolean;
  children: ReactNode;
}

/** A badge: the mark a card wears - official, connected, at the limit.
 *  It is sized by what it says, so it never outgrows its row. */
export const Badge: FC<BadgeProps> = ({
  name,
  tone,
  end,
  mono,
  children,
  ...box
}) => (
  <div
    className={`ev-badge${end ? ' ev-badge-end' : ''}`}
    style={placeLine(box)}
  >
    <span
      className="ev-badge-face"
      data-part={name}
      data-tone={tone}
      data-mono={mono}
    >
      {children}
    </span>
  </div>
);

interface SwitchProps extends Box, Switchable {
  /** Already on, for a switch a take does not have to throw. */
  on?: boolean;
}

/** The toggle a setting is turned on with. */
export const Switch: FC<SwitchProps> = ({ name, on, rest, ...box }) => (
  <div className="ev-switch" data-on={on} style={placeLine(box)}>
    <span
      className="ev-switch-on"
      data-part={name}
      data-rest={restOf({ rest })}
    />
    <span className="ev-switch-knob" />
  </div>
);

interface DropzoneProps extends Box, Switchable {
  children?: ReactNode;
}

/** The dashed area a file is dropped onto. Its accepting state is a
 *  layer of its own, so a take can light it as the file arrives. */
export const Dropzone: FC<DropzoneProps> = ({
  name,
  rest,
  children,
  ...box
}) => (
  <div className="ev-dropzone" style={placeBox(box)}>
    <span
      className="ev-dropzone-lit"
      data-part={name}
      data-rest={restOf({ rest })}
    />
    {children}
  </div>
);

interface MenuItemProps extends Box, Switchable {
  tone?: Tone;
  /** Set in the monospace face: a secret name, a key, a path. */
  mono?: boolean;
  children: ReactNode;
}

/** An entry of a dropdown. */
export const MenuItem: FC<MenuItemProps> = ({
  name,
  tone,
  mono,
  rest,
  children,
  ...box
}) => (
  <div className="ev-menu-item" data-tone={tone} style={placeLine(box)}>
    <span className="ev-menu-item-face" data-mono={mono}>
      {children}
    </span>
    <span
      className="ev-menu-item-face ev-menu-item-on"
      data-part={name}
      data-rest={restOf({ rest })}
      data-mono={mono}
    >
      {children}
    </span>
  </div>
);

interface TypedProps extends Box, Switchable {
  tone?: Tone;
  /** What is typed. One character is one part, so a take reveals them
   *  in turn and the caret runs along with them. */
  children: string;
}

/** A word being typed into a field, letter by letter, with the caret
 *  that follows it. Every character carries the name, so one step of a
 *  sequence types the whole word; the carets are named `<name>-caret`
 *  and go out behind it. */
export const Typed: FC<TypedProps> = ({
  name,
  tone,
  rest,
  children,
  ...box
}) => (
  <div className="ev-typed" data-tone={tone} style={placeLine(box)}>
    {[...children].map((character, index) => (
      <span
        // A word is typed in one order and no other, so where a
        // character sits in it is what tells it from the same letter
        // somewhere else.

        key={index}
        className="ev-typed-char"
        data-part={name}
        data-rest={restOf({ rest })}
      >
        {character}
        <span
          className="ev-typed-caret"
          data-part={name === undefined ? undefined : `${name}-caret`}
        />
      </span>
    ))}
  </div>
);

/* ========== Chrome ========== */

interface BrowserProps extends Box, Part {
  /** What the address bar reads. */
  address: string;
  children?: ReactNode;
}

/** The browser the application is being used in - drawn only when the
 *  browser itself is part of the story, as it is for a download. */
export const Browser: FC<BrowserProps> = ({
  name,
  address,
  children,
  ...box
}) => (
  <div className="ev-browser" data-part={name} style={placeBox(box)}>
    <span className="ev-browser-bar">
      <span className="ev-browser-dot" />
      <span className="ev-browser-dot" />
      <span className="ev-browser-dot" />
      <span className="ev-browser-address">{address}</span>
    </span>
    {children}
  </div>
);

interface DownloadProps extends Box, Switchable {
  /** The file the browser is saving. */
  file: string;
}

/** What a browser shows while it saves a file: a pill carrying the name,
 *  a ring that closes as the bytes arrive, and a tick when they have. A
 *  take slides it up into place, so `y` is its top edge rather than the
 *  line it sits on. */
export const Download: FC<DownloadProps> = ({ name, file, rest, ...box }) => (
  <div
    className="ev-download"
    data-part={name}
    data-rest={restOf({ rest })}
    style={placeLine(box)}
  >
    <Glyph kind="archive" />
    <span className="ev-download-name">{file}</span>
    <svg className="ev-download-ring" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="ev-download-track" cx="12" cy="12" r="9" />
      <circle
        className="ev-download-arc"
        data-part={name === undefined ? undefined : `${name}-arc`}
        cx="12"
        cy="12"
        r="9"
        pathLength={1}
      />
    </svg>
    <span
      className="ev-download-done"
      data-part={name === undefined ? undefined : `${name}-done`}
      data-rest="true"
    >
      <Glyph kind="check" tone="green" />
    </span>
  </div>
);

interface NoticeProps extends Box, Switchable {
  tone?: Tone;
  glyph?: GlyphKind;
  /** The line under the title. */
  note?: ReactNode;
  children: ReactNode;
}

/** The notification Studio raises when something it was asked to do is
 *  done. */
export const Notice: FC<NoticeProps> = ({
  name,
  tone,
  glyph = 'check',
  note,
  rest,
  children,
  ...box
}) => (
  <div
    className="ev-notice"
    data-part={name}
    data-rest={restOf({ rest })}
    data-tone={tone}
    style={placeBox(box)}
  >
    <span className="ev-notice-mark">
      <Glyph kind={glyph} />
    </span>
    <span className="ev-notice-words">
      <span className="ev-notice-title">{children}</span>
      {note !== undefined && <span className="ev-notice-note">{note}</span>}
    </span>
  </div>
);

/* ========== Conduits ========== */

interface DiagramProps {
  children: ReactNode;
}

/** The layer the links are drawn on: one square of user units over the
 *  box it covers, stretched to it, with hairlines that keep their width
 *  whatever the modal is scaled to. */
export const Diagram: FC<DiagramProps> = ({ children }) => (
  <svg
    className="ev-diagram"
    viewBox="0 0 100 100"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    {children}
  </svg>
);

interface ConduitProps extends Switchable {
  tone?: Tone;
  /** Drawn as the data flow diagram draws an edge. */
  dashed?: boolean;
  /** Waits undrawn, for a link the take draws as it is followed. */
  hidden?: boolean;
  /** The path, in the hundredths the diagram is measured in. */
  d: string;
}

/** The link between two things the interface already shows: the edge of
 *  a data flow, the line from a control to what it changed. */
export const Conduit: FC<ConduitProps> = ({
  name,
  tone,
  dashed,
  hidden,
  rest,
  d,
}) => (
  <path
    className="ev-conduit"
    data-part={name}
    data-rest={restOf({ rest })}
    data-tone={tone}
    data-dashed={dashed}
    data-hidden={hidden}
    d={d}
    vectorEffect="non-scaling-stroke"
  />
);

interface PacketProps extends Part {
  /** The journey the take carries it along; it waits at the start. */
  journey: Journey;
  glyph?: GlyphKind;
  children?: ReactNode;
}

/** A file being carried from one place to another - the one thing on a
 *  scene that is only ever in flight, so it stays out of the still: what
 *  it delivered is already drawn there. */
export const Packet: FC<PacketProps> = ({ name, journey, glyph, children }) => (
  <div
    className="ev-packet"
    data-part={name}
    style={withVars(
      {},
      {
        '--ev-from-x': `${journey.from[0]}%`,
        '--ev-from-y': `${journey.from[1]}%`,
      }
    )}
  >
    <span className="ev-packet-body">
      {glyph !== undefined && <Glyph kind={glyph} />}
      {children}
    </span>
  </div>
);

/* ========== Readings ========== */

interface FillProps extends Box, Part {
  tone?: Tone;
  /** Its place along the brand gradient, from 0 to 1. */
  step?: number;
}

/** A blank of content - a rule, a divider, a marker, a swatch. */
export const Fill: FC<FillProps> = ({ name, tone, step, ...box }) => (
  <div
    className="ev-fill"
    data-part={name}
    data-tone={tone}
    style={withVars(placeLine(box), tint(step))}
  />
);

interface MeterProps extends Box, Part {
  /** How full the track is, from 0 to 1. */
  level: number;
  tone?: Tone;
}

/** A track and what fills it: a share of a processor, of a disk, of the
 *  memory a queue is allowed to hold. */
export const Meter: FC<MeterProps> = ({ name, level, tone, ...box }) => (
  <div className="ev-meter" style={placeLine(box)}>
    <span
      className="ev-meter-level"
      data-part={name}
      data-tone={tone}
      style={{ width: `${level * 100}%` }}
    />
  </div>
);

interface TicksProps extends Box, Part {
  /** The height of each bar, from 0 to 1 of the box. */
  bars: number[];
  tone?: Tone;
  /** Carry the run from the brand purple to its cyan, bar by bar. */
  blend?: boolean;
  /** The share of its slot a bar takes up. */
  weight?: number;
  /** Fade the run in where it starts, for a ribbon with no beginning. */
  fade?: boolean;
}

/** A run of bars against a baseline: the events a release let through.
 *  The bars are named `<name>-bar`, so a take can travel along them
 *  while the run itself stays put. */
export const Ticks: FC<TicksProps> = ({
  name,
  bars,
  tone,
  blend,
  weight = 0.55,
  fade,
  ...box
}) => {
  const slot = 100 / bars.length;

  return (
    <div
      className="ev-ticks"
      data-part={name}
      data-fade={fade}
      style={placeBox(box)}
    >
      {bars.map((height, index) => (
        <span
          // The run is a fixed pattern of the scene, so its order is its
          // identity - two bars of one height are not the same bar.

          key={index}
          className="ev-tick"
          data-part={name === undefined ? undefined : `${name}-bar`}
          data-tone={tone}
          style={withVars(
            {
              left: `${index * slot}%`,
              width: `${slot * weight}%`,
              height: `${height * 100}%`,
            },
            tint(
              blend === true ? index / Math.max(bars.length - 1, 1) : undefined
            )
          )}
        />
      ))}
    </div>
  );
};

interface StackProps extends Box, Part {
  /** One run of readings per instance, drawn one on top of the last. */
  bands: number[][];
  /** The band drawn in the brand colour; the rest keep the gradient. */
  lead?: number;
}

/**
 * The load chart of Monitoring: a band per running instance, stacked.
 *
 * The bands are named `<name>-band`, so a take can bring one forward
 * without redrawing the chart around it.
 */
/** The band a take brings forward answers to a name of its own. */
function bandPart(
  name: string | undefined,
  isLead: boolean
): string | undefined {
  return name === undefined ? undefined : `${name}-${isLead ? 'lead' : 'band'}`;
}

export const Stack: FC<StackProps> = ({ name, bands, lead, ...box }) => {
  const running: number[] = Array.from(
    { length: bands[0]?.length ?? 0 },
    () => 0
  );

  return (
    <svg
      className="ev-stack"
      data-part={name}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={placeBox(box)}
      aria-hidden="true"
    >
      {bands.map((band, index) => {
        const under = [...running];

        for (const [step, value] of band.entries()) {
          running[step] = (running[step] ?? 0) + value;
        }

        const top = running
          .map((value, step) => {
            const x = (step / Math.max(running.length - 1, 1)) * 100;

            return `${x.toFixed(2)},${(100 - value * 100).toFixed(2)}`;
          })
          .join(' ');

        // Back along the top of the band under this one, which is what
        // closes the shape without a second run of points.
        const bottom = under
          .map((_, step) => {
            const back = under.length - 1 - step;
            const value = under[back] ?? 0;
            const x = (back / Math.max(under.length - 1, 1)) * 100;

            return `${x.toFixed(2)},${(100 - value * 100).toFixed(2)}`;
          })
          .join(' ');

        return (
          <polygon
            // A band belongs to an instance, and its order in the stack
            // is what tells it from the one above it.

            key={index}
            className="ev-stack-band"
            data-part={bandPart(name, lead === index)}
            data-lead={lead === index ? 'true' : undefined}
            style={withVars({}, tint(index / Math.max(bands.length - 1, 1)))}
            points={`${top} ${bottom}`}
          />
        );
      })}
    </svg>
  );
};

interface LogProps extends Box, Part {
  /** The records on screen, newest last. */
  lines: { level: 'info' | 'warn' | 'error'; text: string; from: string }[];
}

/** The log viewer: a gutter of line numbers and the records beside it. */
export const Log: FC<LogProps> = ({ name, lines, ...box }) => (
  <div className="ev-log" data-part={name} style={placeBox(box)}>
    {lines.map((line, index) => (
      <span
        // A record is identified by where it sits in the file, which is
        // exactly its position in the run.

        key={index}
        className="ev-log-line"
      >
        <span className="ev-log-number">{index + 1}</span>
        <span className="ev-log-level" data-level={line.level}>
          [{line.level}]
        </span>
        <span className="ev-log-text">{line.text}</span>
        <span className="ev-log-from">{line.from}</span>
      </span>
    ))}
  </div>
);

/* ========== Words ========== */

interface LabelProps extends Box, Part {
  tone?: Tone;
  /** Right-aligned to `x` instead of left-aligned. */
  end?: boolean;
  /** Centred on `x` instead of left-aligned. */
  center?: boolean;
  /** Set in the monospace face: names, keys, paths, figures. */
  mono?: boolean;
  /** Set as an eyebrow: small, spaced, upper case. */
  caps?: boolean;
  /** Set as the name of a thing rather than as a note about it. */
  strong?: boolean;
  /** Set at the size a table of figures is read at. */
  small?: boolean;
  children: ReactNode;
}

/** A word of the interface, at the size the interface would set it. */
export const Label: FC<LabelProps> = ({
  name,
  tone,
  end,
  center,
  mono,
  caps,
  strong,
  small,
  children,
  ...box
}) => (
  <div
    className={`ev-label${end ? ' ev-label-end' : ''}${
      center ? ' ev-label-center' : ''
    }`}
    data-part={name}
    data-tone={tone}
    data-mono={mono}
    data-caps={caps}
    data-strong={strong}
    data-small={small}
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
 *  by naming the release instead of showing it being used. */
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

interface CursorProps extends Part {
  /** Where it waits before the take begins, in per cent. */
  at: [number, number];
}

/** The pointer. Every scene whose subject is a gesture has one, and it
 *  is the thing the take is choreographed around. */
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
