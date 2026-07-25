import { Text } from '@mantine/core';
import { CSSProperties, FC, ReactNode } from 'react';

/**
 * Shared layout grammar for console debug tools.
 *
 * Every tool is a `ToolShell`: a dense toolbar pinned on top (parameters +
 * the primary run action) over a result surface that fills the console
 * height and splits into side-by-side `ToolPane`s - so the tools use the
 * console's width instead of scrolling everything vertically.
 */

interface ToolShellProps {
  toolbar: ReactNode;
  children: ReactNode;
}

export const ToolShell: FC<ToolShellProps> = ({ toolbar, children }) => (
  <div className="tool">
    <div className="tool-toolbar">{toolbar}</div>
    {children}
  </div>
);

/** Pushes trailing toolbar items (the run action) to the right edge. */
export const ToolSpacer: FC = () => <div className="tool-toolbar-spacer" />;

interface ToolBodyProps {
  children: ReactNode;
  /** Center a single message instead of laying out panes. */
  empty?: boolean;
}

export const ToolBody: FC<ToolBodyProps> = ({ children, empty = false }) => (
  <div className={`tool-body${empty ? ' tool-body-empty' : ''}`}>
    {children}
  </div>
);

interface ToolPaneProps {
  /** Omit for a headerless surface (e.g. a component with its own title). */
  title?: ReactNode;
  actions?: ReactNode;
  /** Body padding; disable for edge-to-edge content like charts. */
  pad?: boolean;
  /** Make the body a flex column that clips instead of scrolls - for a single
   *  child that fills the height (a chart). Default is a scrolling block. */
  fill?: boolean;
  /** Flex grow ratio relative to sibling panes (default 1). */
  grow?: number;
  /** Fixed flex-basis width in px (with grow 0) for a non-elastic pane. */
  basis?: number;
  children: ReactNode;
}

export const ToolPane: FC<ToolPaneProps> = ({
  title,
  actions,
  pad = true,
  fill = false,
  grow,
  basis,
  children,
}) => {
  const style: CSSProperties = {};
  if (grow !== undefined) style.flexGrow = grow;
  if (basis !== undefined) style.flexBasis = basis;

  return (
    <div className="tool-pane" style={style}>
      {title !== undefined && (
        <div className="tool-pane-header">
          <span className="tool-pane-title">{title}</span>
          {actions && <div className="tool-pane-actions">{actions}</div>}
        </div>
      )}
      <div className="tool-pane-body" data-pad={pad} data-fill={fill}>
        {children}
      </div>
    </div>
  );
};

interface ToolEmptyProps {
  icon?: ReactNode;
  children: ReactNode;
}

export const ToolEmpty: FC<ToolEmptyProps> = ({ icon, children }) => (
  <div className="tool-empty">
    {icon && <div className="tool-empty-icon">{icon}</div>}
    <Text size="sm" c="dimmed" ta="center" maw={340}>
      {children}
    </Text>
  </div>
);
