export function getValueType(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}

export function formatValuePreview(value: unknown): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') return `"${value}"`;
  if (typeof value === 'number') return `${value}`;
  if (typeof value === 'boolean') return `${value}`;
  if (Array.isArray(value)) return `[${value.length} items]`;
  if (typeof value === 'object') {
    return `{${Object.keys(value).length} keys}`;
  }
  return JSON.stringify(value);
}

export function isSimpleValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  const type = typeof value;
  return type === 'string' || type === 'number' || type === 'boolean';
}

const TYPE_BADGE_COLORS: Record<string, string> = {
  string: 'green',
  number: 'blue',
  boolean: 'orange',
  object: 'violet',
  array: 'cyan',
  null: 'gray',
};

export function typeBadgeColor(type: string): string {
  return TYPE_BADGE_COLORS[type] ?? 'gray';
}
