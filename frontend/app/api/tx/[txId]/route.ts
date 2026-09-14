import { NextResponse } from "next/server";

import { bradburyRpcRequest } from "@/lib/bradbury-rpc";
import {
  classifyTransaction,
  type TransactionReceipt,
  type TransactionStatusResult,
} from "@/lib/transaction";

const TX_ID = /^0x[0-9a-fA-F]{64}$/;

export async function GET(
  _request: Request,
  context: {
    params: Promise<{
      txId: string;
    }>;
  },
) {
  const { txId } = await context.params;

  if (!TX_ID.test(txId)) {
    return NextResponse.json(
      {
        error: "INVALID_TRANSACTION_ID",
      },
      {
        status: 400,
      },
    );
  }

  try {
    const [
      status,
      receipt,
    ] = await Promise.all([
      bradburyRpcRequest<TransactionStatusResult>(
        "gen_getTransactionStatus",
        [{ txId }],
      ),
      bradburyRpcRequest<TransactionReceipt>(
        "gen_getTransactionReceipt",
        [{ txId }],
      ),
    ]);

    return NextResponse.json(
      classifyTransaction(
        txId,
        status,
        receipt,
      ),
      {
        headers: {
          "cache-control": "no-store",
        },
      },
    );
  } catch (error) {
    return NextResponse.json(
      {
        error: "BRADBURY_OBSERVATION_FAILED",
        message:
          error instanceof Error
            ? error.message
            : "Unknown Bradbury observation failure",
      },
      {
        status: 502,
      },
    );
  }
}
