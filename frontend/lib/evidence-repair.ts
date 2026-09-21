"use client";

import { protocolLimits } from "@/lib/config";

const UINT32_MAX = 4294967295;
const UINT64_MAX = BigInt("18446744073709551615");
const RAW_GITHUB_PREFIX = "https://raw.githubusercontent.com/";

function readString(
  item: Record<string, unknown>,
  field: string,
  index: number,
  maximum: number,
) {
  const value = item[field];
  if (typeof value !== "string" || !value) {
    throw new Error(`Repair record ${index + 1} is missing ${field}.`);
  }
  if (new TextEncoder().encode(value).length > maximum) {
    throw new Error(`Repair record ${index + 1} has an oversized ${field}.`);
  }
  return value;
}

function readUint64(value: unknown, field: string, index: number) {
  try {
    const parsed = BigInt(String(value));
    if (parsed < BigInt(0) || parsed > UINT64_MAX) throw new Error();
    return parsed;
  } catch {
    throw new Error(`Repair record ${index + 1} has an invalid ${field}.`);
  }
}

function validateImmutableGithubSource(
  source: string,
  version: string,
  index: number,
) {
  if (!/^[0-9a-f]{40}$/.test(version)) {
    throw new Error(
      `Repair record ${index + 1} needs a 40-character lowercase commit version.`,
    );
  }
  if (
    !source.startsWith(RAW_GITHUB_PREFIX) ||
    /[?#%\\]/.test(source) ||
    /[^\x20-\x7e]/.test(source)
  ) {
    throw new Error(
      `Repair record ${index + 1} needs an immutable raw.githubusercontent.com source.`,
    );
  }
  const path = source.slice(RAW_GITHUB_PREFIX.length).split("/");
  if (path.length < 4 || path.some((segment) => !segment || segment === "." || segment === "..")) {
    throw new Error(`Repair record ${index + 1} has an invalid immutable source path.`);
  }
  if (path[2] !== version) {
    throw new Error(
      `Repair record ${index + 1} canonicalSource must contain immutableVersionOrRecordId.`,
    );
  }
}

export function parseEvidenceRepairJson(raw: string) {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Repair evidence must be valid JSON.");
  }

  if (
    !Array.isArray(parsed) ||
    parsed.length === 0 ||
    parsed.length > protocolLimits.maxEvidence
  ) {
    throw new Error(
      `Repair evidence must contain 1 to ${protocolLimits.maxEvidence} replacement records.`,
    );
  }

  const replacements = parsed.map((value, index) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error(`Repair record ${index + 1} is not an object.`);
    }
    const item = value as Record<string, unknown>;

    const replacesEvidenceId = readString(
      item,
      "replacesEvidenceId",
      index,
      protocolLimits.maxEvidenceIdBytes,
    );
    const evidenceId = readString(
      item,
      "evidenceId",
      index,
      protocolLimits.maxEvidenceIdBytes,
    );
    const authorityId = readString(
      item,
      "authorityId",
      index,
      protocolLimits.maxAuthorityIdBytes,
    );
    const subject = readString(item, "subject", index, protocolLimits.maxStringBytes);
    const kind = readString(item, "kind", index, protocolLimits.maxStringBytes);
    const sourceKind = readString(
      item,
      "sourceKind",
      index,
      protocolLimits.maxStringBytes,
    );
    const canonicalSource = readString(
      item,
      "canonicalSource",
      index,
      protocolLimits.maxSourceBytes,
    );
    const immutableVersionOrRecordId = readString(
      item,
      "immutableVersionOrRecordId",
      index,
      protocolLimits.maxVersionBytes,
    );

    if (replacesEvidenceId === evidenceId) {
      throw new Error(`Repair record ${index + 1} must use a new evidenceId.`);
    }

    const authorityRevision = Number(item.authorityRevision);
    if (
      !Number.isSafeInteger(authorityRevision) ||
      authorityRevision < 0 ||
      authorityRevision > UINT32_MAX
    ) {
      throw new Error(`Repair record ${index + 1} has an invalid authorityRevision.`);
    }

    if (sourceKind !== "IMMUTABLE") {
      throw new Error(`Repair record ${index + 1} sourceKind must be IMMUTABLE.`);
    }

    validateImmutableGithubSource(
      canonicalSource,
      immutableVersionOrRecordId,
      index,
    );

    const publishedAt = readUint64(item.publishedAt, "publishedAt", index);
    const observedAt = readUint64(item.observedAt, "observedAt", index);
    const expiresAt = readUint64(item.expiresAt, "expiresAt", index);

    if (publishedAt > observedAt || expiresAt <= observedAt) {
      throw new Error(`Repair record ${index + 1} has invalid evidence timestamps.`);
    }

    const contentDigest =
      typeof item.contentDigest === "string" ? item.contentDigest : "";
    if (
      !/^0x[0-9a-fA-F]{64}$/.test(contentDigest) ||
      /^0x0{64}$/i.test(contentDigest)
    ) {
      throw new Error(`Repair record ${index + 1} needs a non-zero 32-byte contentDigest.`);
    }

    if (typeof item.isPrimary !== "boolean") {
      throw new Error(`Repair record ${index + 1} has an invalid isPrimary value.`);
    }

    return {
      replacesEvidenceId,
      evidenceId,
      authorityId,
      authorityRevision,
      subject,
      kind,
      sourceKind,
      canonicalSource,
      immutableVersionOrRecordId,
      publishedAt,
      observedAt,
      expiresAt,
      contentDigest: contentDigest as `0x${string}`,
      isPrimary: item.isPrimary,
    };
  });

  const replacedIds = replacements.map((record) => record.replacesEvidenceId);
  const newIds = replacements.map((record) => record.evidenceId);

  if (new Set(replacedIds).size !== replacedIds.length) {
    throw new Error("Each authorized evidence record may be replaced only once.");
  }
  if (new Set(newIds).size !== newIds.length) {
    throw new Error("Every replacement evidenceId must be unique.");
  }

  return replacements;
}
