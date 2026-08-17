/**
 * Defaults the backend applies to the generation parameters it receives
 * without them. A configuration is read back without its unset fields, so
 * the form never sees these values and has to hold its own copy.
 */

/** Byte limit of the events queue. */
export const DEFAULT_MAX_EVENT_BYTES = 268_435_456;
