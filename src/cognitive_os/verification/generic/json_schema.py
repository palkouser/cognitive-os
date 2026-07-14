"""JSON Schema Draft 2020-12 verifier."""

import jsonschema

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.problems import CriterionType
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest, VerificationSubjectType

from ..base import BaseVerifier
from .common import generic_descriptor


class JsonSchemaVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(
            generic_descriptor(
                "generic.json_schema",
                VerificationSubjectType.STRUCTURED_VALUE,
                CriterionType.SCHEMA,
            )
        )

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        schema = request.configuration.get("schema")
        if not isinstance(schema, dict):
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(
                    code="invalid_schema", message="JSON Schema configuration is missing"
                ),
            )
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema).validate(request.subject.inline_value)
        except jsonschema.SchemaError:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_schema", message="configured JSON Schema is invalid"),
            )
        except jsonschema.ValidationError:
            return self.result(
                request,
                VerifierStatus.FAILED,
                code="generic.json_schema.invalid",
                message="subject does not satisfy the configured JSON Schema",
                score=0,
            )
        return self.result(request, VerifierStatus.PASSED, score=1)
