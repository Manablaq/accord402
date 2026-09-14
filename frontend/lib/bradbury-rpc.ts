const DEFAULT_RPC = "https://rpc-bradbury.genlayer.com";

type JsonRpcError = {
  code: number;
  message: string;
  data?: unknown;
};

type JsonRpcEnvelope<T> = {
  jsonrpc: "2.0";
  id: number;
  result?: T;
  error?: JsonRpcError;
};

export async function bradburyRpcRequest<T>(
  method: string,
  params: unknown[],
): Promise<T> {
  const rpc =
    process.env.NEXT_PUBLIC_GENLAYER_RPC?.trim() ||
    DEFAULT_RPC;

  const response = await fetch(rpc, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method,
      params,
      id: 19,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `Bradbury RPC HTTP ${response.status}`,
    );
  }

  const payload =
    (await response.json()) as JsonRpcEnvelope<T>;

  if (payload.error) {
    throw new Error(
      `Bradbury RPC ${payload.error.code}: ${payload.error.message}`,
    );
  }

  if (payload.result === undefined) {
    throw new Error(
      `Bradbury RPC ${method} returned no result`,
    );
  }

  return payload.result;
}
