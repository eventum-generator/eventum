import { InstanceInfo } from '@/api/routes/instance/schemas';

export interface GilState {
  /** How the interpreter was built, in the words the docs use. */
  build: 'free-threaded' | 'standard';
  /** Value shown against the GIL label. */
  value: string;
  /** Color of that value, or `undefined` to leave it neutral. */
  color?: string;
  /** What the state means, shown on hover. */
  hint: string;
  /** Whether the state deserves an alert glyph next to the value. */
  warning: boolean;
}

/**
 * Describe what the GIL is doing on the interpreter the instance runs on.
 *
 * Eventum runs every generator and every pipeline stage on threads, so a
 * free-threaded build is the setup that lets them run in parallel. On such
 * a build the GIL can still come back after startup - an extension module
 * imported by a plugin is enough - which costs that parallelism silently.
 * That is the one state worth flagging: on a standard build the GIL is
 * always on and nothing is out of order.
 */
export function describeGilState(
  info: Pick<InstanceInfo, 'python_free_threaded' | 'python_gil_enabled'>
): GilState {
  if (!info.python_free_threaded) {
    return {
      build: 'standard',
      value: 'Enabled',
      hint: 'Standard build - the GIL is always enabled. Install a free-threaded build to run generators in parallel.',
      warning: false,
    };
  }

  if (info.python_gil_enabled) {
    return {
      build: 'free-threaded',
      value: 'Enabled',
      color: 'var(--mantine-color-yellow-text)',
      hint: 'Free-threaded build with the GIL enabled back - generators no longer run in parallel. It is re-enabled by PYTHON_GIL=1, by -X gil=1, or by an imported extension module without free-threading support.',
      warning: true,
    };
  }

  return {
    build: 'free-threaded',
    value: 'Disabled',
    color: 'var(--mantine-color-green-text)',
    hint: 'Free-threaded build with the GIL disabled - generators run in parallel.',
    warning: false,
  };
}
