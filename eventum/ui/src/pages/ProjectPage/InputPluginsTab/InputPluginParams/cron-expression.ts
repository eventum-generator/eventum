import cronstrue from 'cronstrue';

/**
 * Translate an expression from the engine's field order into the one
 * cronstrue expects.
 *
 * The engine (croniter) puts seconds last - `minute hour day month weekday
 * [second] [year]` - while cronstrue puts them first - `[second] minute hour
 * day month weekday [year]`. Without the swap a 6- or 7-field expression is
 * described as a completely different schedule.
 *
 * Anything that is not 6 or 7 fields (a plain 5-field expression, a `@daily`
 * keyword, an unfinished input) needs no swap and is passed through as is.
 */
function toCronstrueOrder(expression: string): string {
  const fields = expression.trim().split(/\s+/);

  if (fields.length !== 6 && fields.length !== 7) {
    return expression;
  }

  return [fields[5], ...fields.slice(0, 5), ...fields.slice(6)].join(' ');
}

/**
 * Describe a cron expression in human-readable form, returning `null` when
 * the expression cannot be parsed.
 */
export function describeCronExpression(expression: string): string | null {
  try {
    return cronstrue.toString(toCronstrueOrder(expression));
  } catch {
    return null;
  }
}
