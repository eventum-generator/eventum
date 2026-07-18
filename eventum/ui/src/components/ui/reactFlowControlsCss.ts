/**
 * CSS for the ReactFlow zoom/fit Controls, themed to Mantine tokens. Inject via
 * a `<style>` tag next to any `<ReactFlow><Controls /></ReactFlow>` - shared by
 * the pipeline graph and the scenario data-flow diagram.
 */
export const REACT_FLOW_CONTROLS_CSS = `
  .react-flow__controls button {
    background-color: var(--mantine-color-body);
    color: var(--mantine-color-text);
    border-color: var(--mantine-color-default-border);
  }
  .react-flow__controls button:hover {
    background-color: var(--mantine-color-default-hover);
  }
  .react-flow__controls button svg {
    fill: var(--mantine-color-text);
  }
`;
