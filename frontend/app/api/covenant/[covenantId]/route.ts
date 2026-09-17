import { createPublicClient, http, type Address } from "viem";
import { testnetBradbury } from "genlayer-js/chains";
import { NextResponse } from "next/server";

import { accord402ReadAbi } from "@/lib/accord402-abi";
import { configuredContractAddress } from "@/lib/client";

const COVENANT_ID = /^(?:0|[1-9][0-9]*)$/;

function jsonSafe(value: unknown): unknown {
  if (typeof value === "bigint") return value.toString();
  if (Array.isArray(value)) return value.map(jsonSafe);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, jsonSafe(entry)]),
    );
  }
  return value;
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ covenantId: string }> },
) {
  const { covenantId } = await context.params;

  if (!COVENANT_ID.test(covenantId)) {
    return NextResponse.json({ error: "INVALID_COVENANT_ID" }, { status: 400 });
  }

  try {
    const client = createPublicClient({
      chain: testnetBradbury,
      transport: http(
        process.env.NEXT_PUBLIC_GENLAYER_RPC?.trim() ||
          "https://rpc-bradbury.genlayer.com",
      ),
    });
    const covenant = await client.readContract({
      address: configuredContractAddress as Address,
      abi: accord402ReadAbi,
      functionName: "getCovenant",
      args: [BigInt(covenantId)],
    });

    if (!covenant.exists) {
      return NextResponse.json(
        { error: "COVENANT_NOT_FOUND", covenantId },
        { status: 404 },
      );
    }

    return NextResponse.json(
      { covenant: jsonSafe(covenant) },
      { headers: { "cache-control": "no-store" } },
    );
  } catch (error) {
    return NextResponse.json(
      {
        error: "BRADBURY_COVENANT_READ_FAILED",
        message:
          error instanceof Error
            ? error.message
            : "Unknown Bradbury covenant read failure",
      },
      { status: 502 },
    );
  }
}
