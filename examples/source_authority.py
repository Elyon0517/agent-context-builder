"""Differentiate a missing authoritative row from an unavailable source."""

from contextkit import ContextCompiler, ContextSource, Fact, Scope, SourceResult, SourceStatus
from contextkit.adapters import InMemoryStore


def main() -> None:
    status = SourceStatus.AVAILABLE

    def primary(scope: Scope) -> SourceResult:
        if status != SourceStatus.AVAILABLE:
            return SourceResult(status)
        return SourceResult(
            status,
            "3",
            (Fact("delivery.preference", "Detailed", ("settings:3",), kind="preference"),),
        )

    legacy = ContextSource(
        "legacy",
        10,
        ("delivery.preference",),
        lambda scope: SourceResult(
            SourceStatus.AVAILABLE,
            "1",
            (Fact("delivery.preference", "Short", ("profile:1",), kind="preference"),),
        ),
    )
    compiler = ContextCompiler(
        InMemoryStore(),
        sources=(
            legacy,
            ContextSource("settings", 100, ("delivery.preference",), primary),
        ),
    )
    scope = Scope("helpdesk", "customer-42")
    available = compiler.compile(scope).to_dict()
    assert available["facts"][0]["value"] == "Detailed"
    print("Available authority:", available["facts"][0]["value"])
    status = SourceStatus.ABSENT
    absent = compiler.compile(scope).to_dict()
    assert absent["facts"][0]["value"] == "Short"
    print("Absent authority permits fallback:", absent["facts"][0]["value"])
    status = SourceStatus.FAILED
    failed = compiler.compile(scope).to_dict()
    assert failed["facts"] == []
    print("Failed authority blocks fallback:", failed["blocked_keys"])


if __name__ == "__main__":
    main()
