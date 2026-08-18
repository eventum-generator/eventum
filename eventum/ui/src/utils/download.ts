/**
 * Save a blob to the user's machine under the given file name.
 *
 * The object URL has to outlive the click that starts the download, so
 * it is revoked once the current task is done rather than right away.
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = filename;

  document.body.append(anchor);
  anchor.click();
  anchor.remove();

  setTimeout(() => URL.revokeObjectURL(url), 0);
}
