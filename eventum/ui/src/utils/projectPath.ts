import { basename, dirname, isAbsolute } from 'pathe';

/**
 * The project an instance runs, read off the path of its configuration.
 *
 * An instance stores a path, not a project, and the path is reported
 * relative to the workspace whenever the configuration lies inside it -
 * `web/generator.yml` for the project `web`. A generator registered
 * from elsewhere on the host keeps its absolute path instead, and the
 * directory it sits in is then no project of the workspace.
 */
export function projectOfConfig(configPath: string): {
  /** Name of the directory holding the configuration. */
  name: string;
  /** Whether that directory is a project of this workspace. */
  inWorkspace: boolean;
} {
  const directory = dirname(configPath);

  return {
    // The whole directory is the name only while it is a single
    // segment: an absolute path would otherwise read as a project
    // named after the machine it sits on.
    name: basename(directory),
    inWorkspace:
      !isAbsolute(directory) && directory !== '.' && dirname(directory) === '.',
  };
}
