import { autocompletion } from '@codemirror/autocomplete';
import { jinja } from '@codemirror/lang-jinja';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { python } from '@codemirror/lang-python';
import { yaml } from '@codemirror/lang-yaml';
import { Extension } from '@codemirror/state';

import { jinjaCompletion } from './completions';

/**
 * Editor extensions for the language of `filePath`: its syntax mode, and
 * the completion source where the language has one. A file the editor has
 * no mode for opens as plain text.
 */
export function languageExtensions(filePath: string): Extension[] {
  if (filePath.endsWith('.jinja')) {
    return [jinja(), autocompletion({ override: [jinjaCompletion] })];
  }

  if (filePath.endsWith('.py')) {
    return [python()];
  }

  if (filePath.endsWith('.json')) {
    return [json()];
  }

  if (/\.ya?ml$/.test(filePath)) {
    return [yaml()];
  }

  if (filePath.endsWith('.md')) {
    return [markdown()];
  }

  return [];
}
