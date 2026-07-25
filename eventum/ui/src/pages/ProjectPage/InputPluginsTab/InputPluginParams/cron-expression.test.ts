import { describe, expect, it } from 'vitest';

import { summarizeCronExpression } from './cron-expression';

const RANDOM_HINT = 'Random values are resolved when the generator runs';
const PARAMETER_HINT = 'Schedule is set by a parameter at run time';

describe('summarizeCronExpression', () => {
  describe('field order', () => {
    it.each([
      ['* * * * *', 'Every minute'],
      ['35 10 * * *', 'At 10:35 AM'],
      ['35 10 * * * 3', 'At 10:35:03 AM'],
      ['35 10 * * * 3 2027', 'At 10:35:03 AM, only in 2027'],
      ['@daily', 'At 12:00 AM'],
    ])('describes %s as %s', (expression, hint) => {
      expect(summarizeCronExpression(expression)).toEqual({
        valid: true,
        hint,
      });
    });

    it('reads the seconds of a six-field expression as the last field', () => {
      // The generator fires at 10:35:03 daily; taking the seconds first
      // would read the same expression as "35 seconds past the minute, on
      // Wednesdays".
      expect(summarizeCronExpression('35 10 * * * 3').hint).not.toContain(
        'Wednesday'
      );
    });

    it('keeps extra whitespace out of the way', () => {
      expect(summarizeCronExpression('   35   10 * * *  ').hint).toBe(
        'At 10:35 AM'
      );
    });
  });

  describe('random values', () => {
    it.each([
      '0 0 R * *',
      '0 0 r * *',
      'R(1-30) 0 * * *',
      'R/2 * * * *',
      '* * * * * R',
      'R R * * *',
    ])('accepts %s without describing the schedule', (expression) => {
      expect(summarizeCronExpression(expression)).toEqual({
        valid: true,
        hint: RANDOM_HINT,
      });
    });

    it('leaves month and weekday names alone', () => {
      expect(summarizeCronExpression('0 0 * MAR *')).toEqual({
        valid: true,
        hint: 'At 12:00 AM, only in March',
      });
    });

    it.each(['R-30 0 * * *', '1,R,5 * * * *'])(
      'rejects %s, which the generator rejects too',
      (expression) => {
        expect(summarizeCronExpression(expression).valid).toBe(false);
      }
    );
  });

  describe('substitution tokens', () => {
    it.each([
      '${params.schedule}',
      '*/${params.step} * * * *',
      '${secrets.schedule}',
      '${ params.schedule }',
    ])('accepts %s without describing the schedule', (expression) => {
      expect(summarizeCronExpression(expression)).toEqual({
        valid: true,
        hint: PARAMETER_HINT,
      });
    });

    it('leaves the rest of the expression to the generator', () => {
      // The substituted value decides whether the expression parses, so
      // there is nothing to judge here.
      expect(summarizeCronExpression('${params.minute} nonsense').valid).toBe(
        true
      );
    });
  });

  describe('rejected input', () => {
    it.each([
      ['', 'empty'],
      ['   ', 'whitespace'],
      ['nonsense', 'a word'],
      ['0 0 * *', 'four fields'],
      ['0 0 1 1 * 2027', 'a year in the seconds field'],
      ['99 * * * *', 'a minute out of range'],
    ])('rejects %s (%s)', (expression) => {
      expect(summarizeCronExpression(expression)).toEqual({
        valid: false,
        hint: '',
      });
    });
  });
});
