"""Execute one pure built-in verifier request from a JSON contract file."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.domain.verifiers import VerificationRequest
from cognitive_os.verification.factory import build_builtin_registry


async def _run(request: VerificationRequest) -> int:
    verifier = build_builtin_registry().require(request.verifier_id, request.verifier_version)
    result = await verifier.verify(request)
    print(result.model_dump_json(indent=2))
    return 0 if result.status.value == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--request-file", type=Path, required=True)
    args = parser.parse_args()
    request = VerificationRequest.model_validate_json(args.request_file.read_bytes())
    if request.verifier_id != args.verifier:
        raise ValueError("request verifier ID does not match --verifier")
    return asyncio.run(_run(request))


if __name__ == "__main__":
    raise SystemExit(main())
