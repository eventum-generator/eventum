export const VALID_PROJECT_NAME_PATTERN = /^[A-Za-z0-9_-]+$/;

export const PROJECT_NAME_PATTERN_ERROR =
  'Only letters, digits and symbols "-" and "_" are allowed';

export function validateProjectName(
  value: string,
  existingProjectNames: string[]
): string | null {
  if (!value) return 'Project name is required';

  if (!VALID_PROJECT_NAME_PATTERN.test(value)) {
    return PROJECT_NAME_PATTERN_ERROR;
  }

  if (existingProjectNames.includes(value)) {
    return 'Project with such name already exists';
  }

  return null;
}

/** Fold everything a project name cannot hold into a single dash. */
function fold(value: string): string {
  return value.split(/\W/).filter(Boolean).join('-');
}

/**
 * Derive a project name from the file name of an imported archive.
 *
 * The extension is dropped and everything a project name cannot hold
 * is folded into a single dash, so a name proposed from an archive is
 * one the form accepts. An archive named entirely out of unsupported
 * characters yields an empty string, and the user names the project
 * themselves.
 */
export function projectNameFromArchive(filename: string): string {
  return fold(filename.replace(/\.[^./\\]+$/, ''));
}

/**
 * Derive a project name from the directory an archive carries the
 * project in. Unlike a file name, it holds no extension to drop.
 */
export function projectNameFromDirectory(directory: string): string {
  return fold(directory);
}
