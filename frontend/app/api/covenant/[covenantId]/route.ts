import { createPublicClient, http, type Address } from "viem";
import { testnetBradbury } from "genlayer-js/chains";
import { NextResponse } from "next/server";

import { accord402ReadAbi, accord402RegistryReadAbi } from "@/lib/accord402-abi";
import { configuredContractAddress } from "@/lib/client";

const COVENANT_ID = /^(?:0|[1-9][0-9]*)$/;
const REGISTRY_ADDRESS = "0x5A622C41BAe12c4BFB1B6465af5ac1a3087497D7" as Address;

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

function unpackFields(value: string, count: number) {
  const fields: string[] = [];
  let offset = 0;
  for (let index = 0; index < count; index += 1) {
    const separator = value.indexOf(":", offset);
    if (separator < 0) throw new Error("Malformed packed criterion");
    const length = Number(value.slice(offset, separator));
    const start = separator + 1;
    if (!Number.isSafeInteger(length) || length < 0) throw new Error("Malformed packed criterion length");
    fields.push(value.slice(start, start + length));
    offset = start + length;
  }
  return fields;
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

    let criteria: Array<{ criterionId: string; criterionText: string }> = [];
    try {
      const count = Number(await client.readContract({
        address: REGISTRY_ADDRESS,
        abi: accord402RegistryReadAbi,
        functionName: "getCriterionCount",
        args: [configuredContractAddress as Address, BigInt(covenantId)],
      }));
      const packed = await Promise.all(Array.from({ length: count }, (_, index) => client.readContract({
        address: REGISTRY_ADDRESS,
        abi: accord402RegistryReadAbi,
        functionName: "getCriterionPacked",
        args: [configuredContractAddress as Address, BigInt(covenantId), BigInt(index)],
      })));
      criteria = packed.map((record) => {
        const [criterionId, criterionText] = unpackFields(record, 2);
        return { criterionId, criterionText };
      });
    } catch {
      criteria = [];
    }

    return NextResponse.json(
      { covenant: jsonSafe(covenant), criteria },
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
