export const FINISHED_WITH_RETURN = 1;

export type TransactionStatusResult = {
  status: string;
  statusCode: number;
};

export type TransactionReceipt = {
  id: string;
  status: number;
  previousStatus: number;
  txExecutionResult: number;
  result?: unknown;
  resultHash?: string;
  validUntil?: number | string;
  fees?: unknown;
  [key: string]: unknown;
};

export type CanonicalTransactionObservation = {
  txId: string;
  consensusStatus: string;
  consensusStatusCode: number;
  finalized: boolean;
  txExecutionResult: number;
  executionSucceeded: boolean;
  canonicalSuccess: boolean;
  receipt: TransactionReceipt;
};

export function classifyTransaction(
  txId: string,
  status: TransactionStatusResult,
  receipt: TransactionReceipt,
): CanonicalTransactionObservation {
  const finalized =
    status.status.toLowerCase() === "finalized";

  const executionSucceeded =
    receipt.txExecutionResult === FINISHED_WITH_RETURN;

  return {
    txId,
    consensusStatus: status.status,
    consensusStatusCode: status.statusCode,
    finalized,
    txExecutionResult: receipt.txExecutionResult,
    executionSucceeded,
    canonicalSuccess:
      finalized && executionSucceeded,
    receipt,
  };
}
