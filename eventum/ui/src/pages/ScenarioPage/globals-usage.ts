/**
 * Collect all unique global state keys from a globals usage map.
 * Shared between DataFlowDiagram (node layout) and ScenarioPage (conditional rendering).
 */
export function collectGlobalKeys(
  globalsUsageMap: Map<
    string,
    { writes: { key: string }[]; reads: { key: string }[] } | undefined
  >,
): string[] {
  const keys = new Set<string>();
  for (const usage of globalsUsageMap.values()) {
    if (!usage) continue;
    for (const ref of usage.writes) keys.add(ref.key);
    for (const ref of usage.reads) keys.add(ref.key);
  }
  return [...keys].sort((a, b) => a.localeCompare(b));
}
