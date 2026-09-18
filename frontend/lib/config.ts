import { defineChain, isAddress, type Chain } from "viem";

const publicEnvironment = {
  NEXT_PUBLIC_GENLAYER_RPC: process.env.NEXT_PUBLIC_GENLAYER_RPC,
  NEXT_PUBLIC_GENLAYER_CHAIN_ID: process.env.NEXT_PUBLIC_GENLAYER_CHAIN_ID,
  NEXT_PUBLIC_GENLAYER_NETWORK_NAME: process.env.NEXT_PUBLIC_GENLAYER_NETWORK_NAME,
  NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_NAME: process.env.NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_NAME,
  NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_SYMBOL: process.env.NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_SYMBOL,
  NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_DECIMALS: process.env.NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_DECIMALS,
  NEXT_PUBLIC_GENLAYER_EXPLORER_URL: process.env.NEXT_PUBLIC_GENLAYER_EXPLORER_URL,
  NEXT_PUBLIC_ACCORD402_CONTRACT_ADDRESS: process.env.NEXT_PUBLIC_ACCORD402_CONTRACT_ADDRESS,
  NEXT_PUBLIC_ACCORD402_REGISTRY_ADDRESS: process.env.NEXT_PUBLIC_ACCORD402_REGISTRY_ADDRESS,
  NEXT_PUBLIC_ACCORD402_ADJUDICATOR_ADDRESS: process.env.NEXT_PUBLIC_ACCORD402_ADJUDICATOR_ADDRESS,
  NEXT_PUBLIC_ACCORD402_VAULT_ADDRESS: process.env.NEXT_PUBLIC_ACCORD402_VAULT_ADDRESS,
  NEXT_PUBLIC_ACCORD402_SOURCE_FINGERPRINT: process.env.NEXT_PUBLIC_ACCORD402_SOURCE_FINGERPRINT,
  NEXT_PUBLIC_ACCORD402_COVENANT_ID: process.env.NEXT_PUBLIC_ACCORD402_COVENANT_ID,
  NEXT_PUBLIC_ACCORD402_REPLAY_SCOPE: process.env.NEXT_PUBLIC_ACCORD402_REPLAY_SCOPE,
  NEXT_PUBLIC_ACCORD402_REPAIR_ALLOWED_FIELD_MASK: process.env.NEXT_PUBLIC_ACCORD402_REPAIR_ALLOWED_FIELD_MASK,
  NEXT_PUBLIC_ACCORD402_MAX_REPAIR_MASK: process.env.NEXT_PUBLIC_ACCORD402_MAX_REPAIR_MASK,
  NEXT_PUBLIC_ACCORD402_MAX_CRITERIA: process.env.NEXT_PUBLIC_ACCORD402_MAX_CRITERIA,
  NEXT_PUBLIC_ACCORD402_MAX_AUTHORITIES: process.env.NEXT_PUBLIC_ACCORD402_MAX_AUTHORITIES,
  NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE: process.env.NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE,
  NEXT_PUBLIC_ACCORD402_MAX_STRING_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_STRING_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_ID_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_ID_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_CRITERION_ID_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_CRITERION_ID_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_CRITERION_TEXT_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_CRITERION_TEXT_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_AUTHORITY_ID_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_AUTHORITY_ID_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_ROLE_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_ROLE_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_KIND_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_KIND_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_VALUE_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_VALUE_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_SOURCE_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_SOURCE_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_VERSION_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_VERSION_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_PAYLOAD_BYTES: process.env.NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_PAYLOAD_BYTES,
  NEXT_PUBLIC_ACCORD402_MAX_REVIEW_GENERATIONS: process.env.NEXT_PUBLIC_ACCORD402_MAX_REVIEW_GENERATIONS,
  NEXT_PUBLIC_ACCORD402_MAX_CORROBORATORS: process.env.NEXT_PUBLIC_ACCORD402_MAX_CORROBORATORS,
  NEXT_PUBLIC_ACCORD402_MIN_ACCEPTANCE_LEAD_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MIN_ACCEPTANCE_LEAD_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_ACCEPTANCE_LEAD_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_ACCEPTANCE_LEAD_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_LEAD_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_LEAD_SECONDS,
  NEXT_PUBLIC_ACCORD402_MIN_CHALLENGE_DURATION_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MIN_CHALLENGE_DURATION_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_CHALLENGE_DURATION_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_CHALLENGE_DURATION_SECONDS,
  NEXT_PUBLIC_ACCORD402_MIN_REPAIR_WINDOW_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MIN_REPAIR_WINDOW_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_REPAIR_WINDOW_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_REPAIR_WINDOW_SECONDS,
  NEXT_PUBLIC_ACCORD402_MIN_RETRY_WINDOW_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MIN_RETRY_WINDOW_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_RETRY_WINDOW_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_RETRY_WINDOW_SECONDS,
  NEXT_PUBLIC_ACCORD402_MIN_EVIDENCE_AGE_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MIN_EVIDENCE_AGE_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_AGE_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_AGE_SECONDS,
  NEXT_PUBLIC_ACCORD402_MAX_ABSOLUTE_HORIZON_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_MAX_ABSOLUTE_HORIZON_SECONDS,
  NEXT_PUBLIC_ACCORD402_REVIEW_GUARD_SECONDS: process.env.NEXT_PUBLIC_ACCORD402_REVIEW_GUARD_SECONDS,
} as const;

function read(name: keyof typeof publicEnvironment) {
  return publicEnvironment[name]?.trim() || "";
}

function readInteger(name: keyof typeof publicEnvironment, errors: string[], minimum = 0) {
  const value = read(name);
  const parsed = Number(value);
  if (!value || !Number.isSafeInteger(parsed) || parsed < minimum) {
    errors.push(`${name} must be a safe integer >= ${minimum}.`);
    return minimum;
  }
  return parsed;
}

function readAddress(name: keyof typeof publicEnvironment, errors: string[]) {
  const value = read(name);
  if (!isAddress(value)) errors.push(`${name} must be a valid EVM address.`);
  return value;
}

function readHttpsUrl(name: keyof typeof publicEnvironment, errors: string[], required = true) {
  const value = read(name).replace(/\/+$/, "");
  if (!value && !required) return "";
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:") throw new Error("not https");
  } catch {
    errors.push(`${name} must be an HTTPS URL.`);
  }
  return value;
}

const configurationErrors: string[] = [];
const rpcUrl = readHttpsUrl("NEXT_PUBLIC_GENLAYER_RPC", configurationErrors);
const explorerUrl = readHttpsUrl("NEXT_PUBLIC_GENLAYER_EXPLORER_URL", configurationErrors);
const networkName = read("NEXT_PUBLIC_GENLAYER_NETWORK_NAME");
const nativeCurrencyName = read("NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_NAME");
const nativeCurrencySymbol = read("NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_SYMBOL");
const chainId = readInteger("NEXT_PUBLIC_GENLAYER_CHAIN_ID", configurationErrors, 1);
const nativeCurrencyDecimals = readInteger(
  "NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_DECIMALS",
  configurationErrors,
  0,
);

if (nativeCurrencyDecimals > 255) {
  configurationErrors.push("NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_DECIMALS must be <= 255.");
}

if (!networkName) configurationErrors.push("NEXT_PUBLIC_GENLAYER_NETWORK_NAME is required.");
if (!nativeCurrencyName) configurationErrors.push("NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_NAME is required.");
if (!nativeCurrencySymbol) configurationErrors.push("NEXT_PUBLIC_GENLAYER_NATIVE_CURRENCY_SYMBOL is required.");

const coreAddress = readAddress("NEXT_PUBLIC_ACCORD402_CONTRACT_ADDRESS", configurationErrors);
const registryAddress = readAddress("NEXT_PUBLIC_ACCORD402_REGISTRY_ADDRESS", configurationErrors);
const adjudicatorAddress = readAddress("NEXT_PUBLIC_ACCORD402_ADJUDICATOR_ADDRESS", configurationErrors);
const vaultAddress = readAddress("NEXT_PUBLIC_ACCORD402_VAULT_ADDRESS", configurationErrors);
const sourceFingerprint = read("NEXT_PUBLIC_ACCORD402_SOURCE_FINGERPRINT");
const defaultCovenantId = read("NEXT_PUBLIC_ACCORD402_COVENANT_ID");
const replayScope = read("NEXT_PUBLIC_ACCORD402_REPLAY_SCOPE");
const repairAllowedFieldMask = readInteger(
  "NEXT_PUBLIC_ACCORD402_REPAIR_ALLOWED_FIELD_MASK",
  configurationErrors,
  0,
);
const expectedRepairAllowedFieldMask = readInteger(
  "NEXT_PUBLIC_ACCORD402_MAX_REPAIR_MASK",
  configurationErrors,
  1,
);

if (!sourceFingerprint) configurationErrors.push("NEXT_PUBLIC_ACCORD402_SOURCE_FINGERPRINT is required.");
if (replayScope !== "COVENANT") configurationErrors.push("NEXT_PUBLIC_ACCORD402_REPLAY_SCOPE must be COVENANT.");
if (repairAllowedFieldMask !== expectedRepairAllowedFieldMask) configurationErrors.push("NEXT_PUBLIC_ACCORD402_REPAIR_ALLOWED_FIELD_MASK must match the configured deployed Core repair mask.");
if (defaultCovenantId && !/^[0-9]+$/.test(defaultCovenantId)) {
  configurationErrors.push("NEXT_PUBLIC_ACCORD402_COVENANT_ID must be an unsigned integer when provided.");
}

export const protocolLimits = {
  maxCriteria: readInteger("NEXT_PUBLIC_ACCORD402_MAX_CRITERIA", configurationErrors, 1),
  maxAuthorities: readInteger("NEXT_PUBLIC_ACCORD402_MAX_AUTHORITIES", configurationErrors, 1),
  maxEvidence: readInteger("NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE", configurationErrors, 1),
  maxStringBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_STRING_BYTES", configurationErrors, 1),
  maxEvidenceIdBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_ID_BYTES", configurationErrors, 1),
  maxCriterionIdBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_CRITERION_ID_BYTES", configurationErrors, 1),
  maxCriterionTextBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_CRITERION_TEXT_BYTES", configurationErrors, 1),
  maxAuthorityIdBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_AUTHORITY_ID_BYTES", configurationErrors, 1),
  maxRoleBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_ROLE_BYTES", configurationErrors, 1),
  maxIdentityKindBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_KIND_BYTES", configurationErrors, 1),
  maxIdentityValueBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_IDENTITY_VALUE_BYTES", configurationErrors, 1),
  maxSourceBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_SOURCE_BYTES", configurationErrors, 1),
  maxVersionBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_VERSION_BYTES", configurationErrors, 1),
  maxDeliveryPayloadBytes: readInteger("NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_PAYLOAD_BYTES", configurationErrors, 1),
  maxReviewGenerations: readInteger("NEXT_PUBLIC_ACCORD402_MAX_REVIEW_GENERATIONS", configurationErrors, 1),
  maxCorroborators: readInteger("NEXT_PUBLIC_ACCORD402_MAX_CORROBORATORS", configurationErrors, 1),
  minAcceptanceLeadSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MIN_ACCEPTANCE_LEAD_SECONDS", configurationErrors, 1),
  maxAcceptanceLeadSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_ACCEPTANCE_LEAD_SECONDS", configurationErrors, 1),
  maxDeliveryLeadSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_DELIVERY_LEAD_SECONDS", configurationErrors, 1),
  minChallengeDurationSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MIN_CHALLENGE_DURATION_SECONDS", configurationErrors, 1),
  maxChallengeDurationSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_CHALLENGE_DURATION_SECONDS", configurationErrors, 1),
  minRepairWindowSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MIN_REPAIR_WINDOW_SECONDS", configurationErrors, 1),
  maxRepairWindowSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_REPAIR_WINDOW_SECONDS", configurationErrors, 1),
  minRetryWindowSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MIN_RETRY_WINDOW_SECONDS", configurationErrors, 1),
  maxRetryWindowSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_RETRY_WINDOW_SECONDS", configurationErrors, 1),
  minEvidenceAgeSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MIN_EVIDENCE_AGE_SECONDS", configurationErrors, 1),
  maxEvidenceAgeSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_EVIDENCE_AGE_SECONDS", configurationErrors, 1),
  maxAbsoluteHorizonSeconds: readInteger("NEXT_PUBLIC_ACCORD402_MAX_ABSOLUTE_HORIZON_SECONDS", configurationErrors, 1),
  reviewGuardSeconds: readInteger("NEXT_PUBLIC_ACCORD402_REVIEW_GUARD_SECONDS", configurationErrors, 1),
} as const;

export const accord402Config = {
  rpcUrl,
  explorerUrl,
  networkName,
  chainId,
  chainIdHex: `0x${chainId.toString(16)}`,
  nativeCurrencyName,
  nativeCurrencySymbol,
  nativeCurrencyDecimals,
  coreAddress,
  registryAddress,
  adjudicatorAddress,
  vaultAddress,
  sourceFingerprint,
  defaultCovenantId,
  replayScope,
  repairAllowedFieldMask,
  expectedRepairAllowedFieldMask,
  protocolLimits,
} as const;

export const accord402Chain: Chain = defineChain({
  id: chainId,
  name: networkName,
  nativeCurrency: {
    name: nativeCurrencyName,
    symbol: nativeCurrencySymbol,
    decimals: nativeCurrencyDecimals,
  },
  rpcUrls: {
    default: { http: rpcUrl ? [rpcUrl] : [] },
  },
  blockExplorers: explorerUrl
    ? { default: { name: `${networkName} Explorer`, url: explorerUrl } }
    : undefined,
});

export const isConfigured = configurationErrors.length === 0;
export const configurationErrorMessage = configurationErrors.join(" ");

export function assertConfiguration() {
  if (!isConfigured) {
    throw new Error(`Accord402 frontend configuration is incomplete. ${configurationErrorMessage}`);
  }
}
