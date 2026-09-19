# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import hashlib
from genlayer import *

CORE_SOURCE_SHA256 = "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
CORE_SOURCE_BYTES = 51757
CHUNK_SIZE = 14336
CHUNK_COUNT = 4
FINAL_CHUNK_SIZE = 8749


class Accord402CoreChunkDeployer(gl.Contract):
    owner: Address
    settlement_vault: Address
    chunks: DynArray[str]
    child_address: str
    sealed: bool

    def __init__(
        self,
        settlement_vault: Address,
    ):
        self.owner = gl.message.sender_address
        self.settlement_vault = settlement_vault

    def _only_owner(self) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError("OWNER_ONLY")

    @gl.public.write
    def append_chunk(
        self,
        index: u32,
        chunk: str,
    ) -> None:
        self._only_owner()

        if self.sealed:
            raise gl.vm.UserError("DEPLOYER_SEALED")

        current = len(self.chunks)

        if int(index) != current:
            raise gl.vm.UserError("CHUNK_INDEX_MISMATCH")

        if current >= CHUNK_COUNT:
            raise gl.vm.UserError("TOO_MANY_CHUNKS")

        raw = chunk.encode(
            "ascii",
            errors="strict",
        )

        expected_size = (
            FINAL_CHUNK_SIZE
            if current == CHUNK_COUNT - 1
            else CHUNK_SIZE
        )

        if len(raw) != expected_size:
            raise gl.vm.UserError("CHUNK_SIZE_MISMATCH")

        self.chunks.append(chunk)

    @gl.public.write
    def deploy_core(self) -> None:
        self._only_owner()

        if self.sealed:
            raise gl.vm.UserError("DEPLOYER_SEALED")

        if len(self.chunks) != CHUNK_COUNT:
            raise gl.vm.UserError("CHUNKS_INCOMPLETE")

        source = ""

        for chunk in self.chunks:
            source += chunk

        source_bytes = source.encode(
            "ascii",
            errors="strict",
        )

        if len(source_bytes) != CORE_SOURCE_BYTES:
            raise gl.vm.UserError("SOURCE_LENGTH_MISMATCH")

        digest = hashlib.sha256(
            source_bytes
        ).hexdigest()

        if digest != CORE_SOURCE_SHA256:
            raise gl.vm.UserError("SOURCE_SHA256_MISMATCH")

        child = gl.deploy_contract(
            code=source_bytes,
            args=[
                self.settlement_vault
            ],
            salt_nonce=u256(1),
            on="finalized",
        )

        self.child_address = child.as_hex
        self.sealed = True

    @gl.public.view
    def get_chunk_count(self) -> u32:
        return u32(
            len(self.chunks)
        )

    @gl.public.view
    def get_child_address(self) -> str:
        return self.child_address
