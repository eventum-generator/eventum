import { useCallback, useState } from 'react';

export function useHighlightState() {
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(
    null
  );
  const [highlightedEdgeId, setHighlightedEdgeId] = useState<string | null>(
    null
  );

  const highlightNode = useCallback((nodeId: string | null) => {
    setHighlightedNodeId(nodeId);
    setHighlightedEdgeId(null);
  }, []);

  const highlightEdge = useCallback((edgeId: string | null) => {
    setHighlightedEdgeId(edgeId);
    setHighlightedNodeId(null);
  }, []);

  const clearHighlight = useCallback(() => {
    setHighlightedNodeId(null);
    setHighlightedEdgeId(null);
  }, []);

  return {
    highlightedNodeId,
    highlightedEdgeId,
    highlightNode,
    highlightEdge,
    clearHighlight,
  };
}
