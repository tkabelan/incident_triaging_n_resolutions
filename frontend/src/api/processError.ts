import type { ProcessErrorRequest, ProcessErrorResponse } from "../types/agent";

const PROCESS_ERROR_URL = "/api/v1/errors/process";

export class ProcessErrorApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ProcessErrorApiError";
    this.status = status;
  }
}

export async function processError(
  payload: ProcessErrorRequest,
): Promise<ProcessErrorResponse> {
  const response = await fetch(PROCESS_ERROR_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = (await response.json()) as ProcessErrorResponse | { detail?: string };

  if (!response.ok) {
    const message =
      typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string"
        ? body.detail
        : "The backend request failed.";
    throw new ProcessErrorApiError(message, response.status);
  }

  return body as ProcessErrorResponse;
}
