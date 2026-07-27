import { search, setSearchQuery } from '@codemirror/search';
import { Extension } from '@codemirror/state';
import { EditorView, Panel, ViewUpdate } from '@codemirror/view';

/**
 * A search panel currently open in an editor. The extension owns the host
 * element and the editor view; the controls are rendered into the host by
 * React so they can read the app theme.
 */
export interface SearchPanelHandle {
  readonly view: EditorView;
  readonly dom: HTMLElement;
  /** Register a listener for the updates the controls have to redraw for. */
  subscribe: (listener: () => void) => () => void;
}

export interface SearchPanelHooks {
  onOpen: (handle: SearchPanelHandle) => void;
  onClose: (handle: SearchPanelHandle) => void;
}

// Keeps the match the search jumps to clear of the panel floating over the
// top-right corner of the editor.
const SCROLL_MARGIN = 48;

class SearchPanelHost implements Panel {
  readonly dom: HTMLElement;
  readonly top = true;
  readonly view: EditorView;

  private readonly hooks: SearchPanelHooks;
  private readonly listeners = new Set<() => void>();

  constructor(view: EditorView, hooks: SearchPanelHooks) {
    this.view = view;
    this.hooks = hooks;
    this.dom = document.createElement('div');
    this.dom.className = 'ev-cm-search';
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  };

  // Both run inside the editor update the panel was added to or removed in,
  // so the controls mount with the panel and unmount with it.
  mount() {
    this.hooks.onOpen(this);
  }

  destroy() {
    this.hooks.onClose(this);
  }

  update(update: ViewUpdate) {
    const requeried = update.transactions.some((transaction) =>
      transaction.effects.some((effect) => effect.is(setSearchQuery))
    );

    // The query drives the fields, the document and the selection drive the
    // match counter; nothing else on screen depends on the editor.
    if (update.docChanged || update.selectionSet || requeried) {
      for (const listener of this.listeners) {
        listener();
      }
    }
  }
}

/**
 * Search extension that replaces the stock panel with the Studio one.
 *
 * The search keymap alone (bundled with the editor's basic setup) would open
 * the library's own panel, so the whole extension is configured here instead.
 */
export function searchPanel(hooks: SearchPanelHooks): Extension {
  return search({
    createPanel: (view) => new SearchPanelHost(view, hooks),
    scrollToMatch: (range) =>
      EditorView.scrollIntoView(range, {
        y: 'nearest',
        yMargin: SCROLL_MARGIN,
      }),
  });
}
