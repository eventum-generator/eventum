import { AxiosResponse } from 'axios';
import { ZodError, ZodType, z } from 'zod';

import { APIError } from '@/api/errors';

export async function validateResponse<S extends ZodType>(
  schema: S,
  promise: Promise<AxiosResponse>
): Promise<z.infer<S>> {
  const response = await promise;

  try {
    return await schema.parseAsync(response.data);
  } catch (error) {
    if (error instanceof ZodError) {
      throw new APIError({
        message: 'Unexpected server response',
        details:
          'Server respond with body that does not match to defined schema',
        responseValidationErrors: error.issues.map((issue) => ({
          path: issue.path.join('.'),
          message: issue.message,
        })),
      });
    }
    throw error;
  }
}
