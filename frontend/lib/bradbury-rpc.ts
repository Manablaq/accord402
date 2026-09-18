import { accord402Config, assertConfiguration } from "@/lib/config";

type JsonRpcError = {
  code: number;
  message: string;
  data?: unknown;
};

type JsonRpcEnvelope<T> = {
  jsonrpc: "2.0";
  id: string | number;
  result?: T;
  error?: JsonRpcError;
};

export async function bradburyRpcRequest<T>(
  method: string,
  params: unknown[],
): Promise<T> {
  assertConfiguration();

  const response = await fetch(accord402Config.rpcUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method,
      params,
      id: crypto.randomUUID(),
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `${accord402Config.networkName} RPC HTTP ${response.status}`,
    );
  }

  const payload =
    (await response.json()) as JsonRpcEnvelope<T>;

  if (payload.error) {
    throw new Error(
      `${accord402Config.networkName} RPC ${payload.error.code}: ${payload.error.message}`,
    );
  }

  if (payload.result === undefined) {
    throw new Error(
      `${accord402Config.networkName} RPC ${method} returned no result`,
    );
  }

  return payload.result;
}
