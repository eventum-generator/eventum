import { afterEach, describe, expect, it, vi } from 'vitest';

import { downloadUrl } from './download';

const URL = '/api/generator-configs/demo/file/out.log?download=true';

// The anchor the call builds is captured at creation, so what it carries and
// where it sits can be read without letting jsdom act on the click.
function captureAnchor(): HTMLAnchorElement {
  const anchor = document.createElement('a');

  vi.spyOn(document, 'createElement').mockReturnValueOnce(anchor);

  return anchor;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('downloadUrl', () => {
  it('saves the URL under the given name', () => {
    const anchor = captureAnchor();
    const click = vi.spyOn(anchor, 'click').mockImplementation(vi.fn());

    downloadUrl(URL, 'out.log');

    expect(click).toHaveBeenCalledOnce();
    expect(anchor.getAttribute('href')).toBe(URL);
    expect(anchor.download).toBe('out.log');
  });

  it('holds the anchor in the document while it is clicked', () => {
    // Firefox ignores a click on an anchor that is not connected.
    const anchor = captureAnchor();
    let connected: boolean | null = null;
    vi.spyOn(anchor, 'click').mockImplementation(() => {
      connected = anchor.isConnected;
    });

    downloadUrl(URL, 'out.log');

    expect(connected).toBe(true);
  });

  it('leaves the document as it found it', () => {
    // The anchor is a means of starting the transfer, not a control the
    // user is meant to find on the page afterwards.
    const anchor = captureAnchor();
    vi.spyOn(anchor, 'click').mockImplementation(vi.fn());

    downloadUrl(URL, 'out.log');

    expect(anchor.isConnected).toBe(false);
    expect(document.body.querySelector('a')).toBeNull();
  });
});
