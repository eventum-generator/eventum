import { fold, validateProjectName } from '../ProjectsPage/project-name';

/**
 * Propose a project name for a published generator that the workspace
 * does not hold yet.
 *
 * Installing a generator already installed writes another project
 * beside the first rather than replacing it, so the name proposed for
 * it is a free one - the dialog opens ready to submit instead of
 * opening on an error about a name the user did not choose.
 */
export function proposeProjectName(
  entryName: string,
  existingProjectNames: string[]
): string {
  const base = fold(entryName);

  if (!base) return base;

  if (validateProjectName(base, existingProjectNames) === null) {
    return base;
  }

  for (let suffix = 2; suffix <= 100; suffix++) {
    const candidate = `${base}-${suffix}`;

    if (validateProjectName(candidate, existingProjectNames) === null) {
      return candidate;
    }
  }

  return base;
}
