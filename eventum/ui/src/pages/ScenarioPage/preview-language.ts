/**
 * Pick the shiki grammar a previewed generator file is highlighted with.
 *
 * Languages the app's shiki adapter loads (see App.tsx). Anything else falls
 * back to plaintext so CodeHighlight never throws on an unregistered grammar.
 */
const LOADED_LANGS = new Set([
  'csv',
  'jinja',
  'json',
  'log',
  'markdown',
  'python',
  'toml',
  'tsv',
  'xml',
  'yaml',
]);

const LANG_ALIAS: Record<string, string> = {
  yml: 'yaml',
  md: 'markdown',
  py: 'python',
  txt: 'log',
};

/** Highlight `.jinja` templates with the jinja grammar (so the state logic
 *  reads as code); fall back to the file's base format otherwise, or
 *  plaintext for anything shiki does not load. */
export function previewLanguage(path: string): string {
  if (/\.jinja$/i.test(path)) return 'jinja';
  const dot = path.lastIndexOf('.');
  const ext = dot !== -1 ? path.slice(dot + 1).toLowerCase() : '';
  const lang = LANG_ALIAS[ext] ?? ext;
  return LOADED_LANGS.has(lang) ? lang : 'text';
}
