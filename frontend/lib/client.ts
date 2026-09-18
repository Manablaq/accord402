export {
  accord402Chain,
  accord402Config,
  configurationErrorMessage,
  isConfigured,
  protocolLimits,
} from "@/lib/config";

import { accord402Config, isConfigured } from "@/lib/config";

export const bradburyRpc = accord402Config.rpcUrl;
export const configuredContractAddress = accord402Config.coreAddress;
export const configuredRegistryAddress = accord402Config.registryAddress;
export const configuredAdjudicatorAddress = accord402Config.adjudicatorAddress;
export const configuredVaultAddress = accord402Config.vaultAddress;
export const configuredExplorerUrl = accord402Config.explorerUrl;
export const configuredCovenantId = accord402Config.defaultCovenantId;
export const configuredContractSha = accord402Config.sourceFingerprint;
export const isConfiguredContractAddress = isConfigured;
