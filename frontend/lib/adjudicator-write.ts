"use client";

import { createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { CalldataAddress } from "genlayer-js/types";
import { hexToBytes, isAddress, type Address } from "viem";
import { accord402Config } from "@/lib/config";

type GenLayerProvider = NonNullable<
  NonNullable<Parameters<typeof createClient>[0]>["provider"]
>;

const TX_ID = /^0x[0-9a-fA-F]{64}$/;
const COVENANT_ID = /^[0-9]+$/;

export async function submitAdjudicationWrite({
  provider,
  account,
  coreAddress,
  covenantId,
}: {
  provider: unknown;
  account: string;
  coreAddress: string;
  covenantId: string;
}) {
  if (accord402Config.chainId !== testnetBradbury.id) {
    throw new Error(
      `Adjudication writes require Bradbury chain ${testnetBradbury.id}.`,
    );
  }
  if (!isAddress(account)) {
    throw new Error("Connect a valid wallet before adjudicating.");
  }
  if (!isAddress(coreAddress)) {
    throw new Error("The configured Accord402 Core address is invalid.");
  }
  if (!isAddress(accord402Config.adjudicatorAddress)) {
    throw new Error("The configured Accord402 Adjudicator address is invalid.");
  }
  if (!COVENANT_ID.test(covenantId)) {
    throw new Error("Load a valid covenant before adjudicating.");
  }

  const client = createClient({
    chain: testnetBradbury,
    endpoint: accord402Config.rpcUrl,
    account: account as Address,
    provider: provider as GenLayerProvider,
  });

  const txId = await client.writeContract({
    address: accord402Config.adjudicatorAddress as Address,
    functionName: "adjudicate",
    args: [
      new CalldataAddress(hexToBytes(coreAddress as Address)),
      BigInt(covenantId),
    ],
    value: BigInt(0),
  });

  if (typeof txId !== "string" || !TX_ID.test(txId)) {
    throw new Error("GenLayer returned an invalid adjudication transaction ID.");
  }

  return txId as `0x${string}`;
}
