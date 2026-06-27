export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

export async function apiGet<TResponse>(path: string): Promise<TResponse> {
  let response: Response;

  try {
    response = await fetch(buildUrl(path), {
      method: "GET",
      headers: {
        Accept: "application/json"
      }
    });
  } catch (error) {
    throw new ApiClientError(error instanceof Error ? error.message : "Network request failed.");
  }

  if (!response.ok) {
    throw new ApiClientError(`Request failed with status ${response.status}.`, response.status);
  }

  return (await response.json()) as TResponse;
}
