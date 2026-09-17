import { createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

export const bradburyClient = createClient({
  chain: testnetBradbury,
});

export const bradburyRpc =
  process.env.NEXT_PUBLIC_GENLAYER_RPC?.trim() ||
  "https://rpc-bradbury.genlayer.com";

export const configuredContractAddress =
  process.env.NEXT_PUBLIC_ACCORD402_CONTRACT_ADDRESS?.trim() ||
  "0xA1a2125B3C7D03b868628B4C79832B33B7af4923";

export const configuredTransactionId =
  process.env.NEXT_PUBLIC_ACCORD402_TRANSACTION_ID?.trim() || "";

export const isConfiguredContractAddress =
  /^0x[0-9a-fA-F]{40}$/.test(configuredContractAddress);
