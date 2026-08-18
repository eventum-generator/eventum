/**
 * Save a URL to disk through a download navigation.
 *
 * A download navigation is used rather than assigning `location`: the current
 * page stays where it is, and a request that fails ends as a failed download
 * instead of replacing the application with the server's error body.
 *
 * @param url - Same-origin URL to download from.
 * @param filename - Name to suggest for the saved file.
 */
export function downloadUrl(url: string, filename: string): void {
  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = filename;
  anchor.rel = 'noopener';
  anchor.style.display = 'none';

  // Firefox dispatches the click only for an anchor that is in the document.
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}
