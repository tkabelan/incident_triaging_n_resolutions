import type {
  ProcessErrorRequest,
  ProcessErrorResponse,
  ProcessStreamEvent,
} from "../types/agent";

const configuredBackendOrigin = import.meta.env.VITE_BACKEND_ORIGIN?.trim() ?? "";
const apiBaseUrl = import.meta.env.DEV ? "" : configuredBackendOrigin.replace(/\/+$/, "");
const PROCESS_ERROR_URL = `${apiBaseUrl}/api/v1/errors/process`;
const PROCESS_ERROR_STREAM_URL = `${apiBaseUrl}/api/v1/errors/process/stream`;

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

export async function processErrorStream(
  payload: ProcessErrorRequest,
  onEvent: (event: ProcessStreamEvent) => void,
): Promise<void> {
  const response = await fetch(PROCESS_ERROR_STREAM_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = (await response.json()) as { detail?: string };
    throw new ProcessErrorApiError(body.detail ?? "The backend request failed.", response.status);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("The browser could not read the streaming response.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const dataLine = chunk
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (!dataLine) {
        continue;
      }
      const payloadText = dataLine.slice(6);
      onEvent(JSON.parse(payloadText) as ProcessStreamEvent);
    }
  }
}
