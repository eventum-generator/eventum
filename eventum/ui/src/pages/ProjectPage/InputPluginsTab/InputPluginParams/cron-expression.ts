import cronstrue from 'cronstrue';

/**
 * A `${params.*}` or `${secrets.*}` token. Such tokens are substituted before
 * the generator parses the expression, so their value is unknown here.
 */
const SUBSTITUTION_TOKEN = /\$\{[^}]*\}/;

/**
 * A field the generator fills with a random value - `R`, `R(1-30)`, `R/2`.
 * Random values extend the standard syntax and mean nothing to cronstrue.
 */
const RANDOM_FIELD = /^R(\([^)]*\))?(\/\d+)?$/i;

export interface CronExpressionSummary {
  /** Whether the generator would accept the expression. */
  valid: boolean;
  /**
   * The schedule in words, or a note on why it cannot be spelled out. Empty
   * for an expression the generator would reject.
   */
  hint: string;
}

/**
 * Translate fields from the generator's order into the one cronstrue expects.
 *
 * The generator puts seconds last - `minute hour day month weekday [second]
 * [year]` - while cronstrue puts them first - `[second] minute hour day month
 * weekday [year]`. Without the swap a 6- or 7-field expression is described as
 * a completely different schedule.
 *
 * Anything that is not 6 or 7 fields (a plain 5-field expression, a `@daily`
 * keyword, an unfinished input) needs no swap.
 */
function toCronstrueOrder(fields: string[]): string {
  if (fields.length !== 6 && fields.length !== 7) {
    return fields.join(' ');
  }

  return [fields[5], ...fields.slice(0, 5), ...fields.slice(6)].join(' ');
}

/**
 * Summarize a cron expression for the form: whether the generator would accept
 * it, and what to show under the field.
 *
 * The generator accepts more than cronstrue can describe, so acceptance and
 * description are answered separately - an expression carrying a substitution
 * token or a random value is usable but cannot be spelled out.
 */
export function summarizeCronExpression(
  expression: string
): CronExpressionSummary {
  if (SUBSTITUTION_TOKEN.test(expression)) {
    return { valid: true, hint: 'Schedule is set by a parameter at run time' };
  }

  const fields = expression.trim().split(/\s+/);
  const hasRandomValues = fields.some((field) => RANDOM_FIELD.test(field));

  const resolvedFields = hasRandomValues
    ? fields.map((field) =>
        RANDOM_FIELD.test(field) ? field.replace(/^R(\([^)]*\))?/i, '*') : field
      )
    : fields;

  let description: string;
  try {
    description = cronstrue.toString(toCronstrueOrder(resolvedFields));
  } catch {
    return { valid: false, hint: '' };
  }

  return {
    valid: true,
    hint: hasRandomValues
      ? 'Random values are resolved when the generator runs'
      : description,
  };
}
