import { CSSProperties } from 'react';

export type StudioPanel = 'explorer' | 'editor' | 'inspector';

/**
 * Viewports wide enough for the three panels to share one row.
 *
 * Side by side they need around 810px between them before the editor is
 * squeezed below a width code can be read at, and nothing under Mantine's
 * `lg` breakpoint has that to spare once the navigation column and the page
 * padding are taken out. Narrower than this the panels take turns.
 */
export const WIDE_LAYOUT_QUERY = '(min-width: 75em)';

/**
 * Width each panel keeps for itself while the row is shared. The docks are
 * held to the width their resize handles stop at, so a narrowing window
 * takes it out of them until they reach it - and out of the editor only
 * after that.
 */
export const PANEL_MIN_WIDTH: Record<StudioPanel, number> = {
  explorer: 190,
  editor: 360,
  inspector: 260,
};

interface PanelLayout {
  /** Panel holding the row alone, or `null` while all of them share it. */
  active: StudioPanel | null;
  /** Width the panel's resize handle currently stands at, if it has one. */
  size?: number;
}

/**
 * Panel the switcher settles on when `selected` is not available.
 *
 * Recovery mode drops the inspector, so a switcher left pointing at it would
 * show nothing at all.
 */
export function resolvePanel(
  selected: StudioPanel,
  hasInspector: boolean
): StudioPanel {
  return selected === 'inspector' && !hasInspector ? 'editor' : selected;
}

/**
 * Style that places `panel` in the layout described by `layout`.
 *
 * Panels that are off screen are hidden rather than dropped, so the editor
 * keeps its open tabs and their unsaved text and the inspector keeps its
 * forms while another panel is on screen.
 */
export function panelStyle(
  panel: StudioPanel,
  layout: PanelLayout
): CSSProperties {
  if (layout.active === null) {
    return panel === 'editor'
      ? { minWidth: PANEL_MIN_WIDTH.editor }
      : {
          width: layout.size,
          flex: '0 1 auto',
          minWidth: PANEL_MIN_WIDTH[panel],
        };
  }

  return panel === layout.active ? { flex: '1 1 auto' } : { display: 'none' };
}
