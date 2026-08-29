/**
 * The tempo a scene is cut to.
 *
 * A scene is a recording of three to five real steps, and what makes it
 * readable is the rest between them: the pointer arrives, the press
 * lands, the interface answers, and only then does the next step begin.
 * These are the durations every take is timed with, so the whole reel
 * moves at one pace.
 */

/** The pointer crossing the scene to the control it is going to press. */
export const TRAVEL = { duration: 0.66, ease: [0.33, 1, 0.68, 1] } as const;

/** The ring a press leaves behind it. */
export const PRESS = { duration: 0.5, ease: 'easeOut' } as const;

/** A menu, a tray, a notification coming open. */
export const OPEN = { duration: 0.3, ease: [0.16, 1, 0.3, 1] } as const;

/** What the interface answers with once the press has landed. */
export const ANSWER = { duration: 0.36, ease: [0.22, 0.9, 0.24, 1] } as const;

/** Something going, or coming back, without being the point. */
export const FADE = { duration: 0.3 } as const;

/** Long enough for a reader to take in what just happened. */
export const BEAT = '+0.42';

/** The pause on the finished state before the take runs again. */
export const HOLD = '+2.2';
