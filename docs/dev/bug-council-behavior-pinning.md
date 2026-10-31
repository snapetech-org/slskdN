# Bug Council Behavior-Pinning Pattern

The remediation baseline (`scripts/check-remediation-baseline.sh`) currently asserts the **textual presence** of fix symbols. That gate is fast and cheap, but it can be defeated by a refactor that renames the symbol, splits its body, or replaces it with an equivalent that does the wrong thing. Behavior pinning closes that gap by requiring a behavior-anchored test next to every text-anchored gate.

## Pattern

For every `require_pattern "Foo"` in `scripts/check-remediation-baseline.sh`:

1. There must exist a unit test (or a small focused integration test) whose name asserts the **behavior** the symbol implements.
2. The test must fail if the symbol is renamed and its body deleted, even if the renamed symbol is still present.

## Examples

Text gate:

```
require_pattern "ValidateMessageLength" "src/Network" "frame length validation is wired"
```

Pinned by:

```csharp
// tests/Soulseek.Tests.Unit/Network/MessageFrameValidatorTests.cs
[Fact]
public void Rejects_Length_Above_Max_Message_Length()
{
    Assert.Throws<MessageException>(() =>
        MessageFrameValidator.ValidateMessageLength(MessageFrameValidator.MaxMessageLength + 1));
}
```

Renaming `ValidateMessageLength` to `CheckMessageLength` would fail the text gate. Deleting the throw inside `ValidateMessageLength` would fail the behavior gate. Both must hold.

Text gate:

```
require_pattern "count < 0" "src/Messaging/Messages/Server/ProtocolCountReader.cs" "count reader rejects negative counts"
```

Pinned by `tests/Soulseek.Tests.Unit/Messaging/Messages/ProtocolCountHardeningTests.cs`, e.g. `Read_Validated_Count_Throws_On_Negative`.

## Authoring rule

When a sweep row is closed as Fixed, the closing rationale lists:

- The text gate added or already present.
- The behavior test added or already present.

If a behavior test cannot exist (e.g. the gate is purely structural — file existence, doc presence), the rationale records that explicitly with a one-line reason.

## What this pattern does not do

This pattern does not catch every behavior regression. It is a forcing function: every fix has at least one named test that asserts the runtime behavior of the fix. Broader source and dependency scanning belongs to Semgrep and Trivy; focused fuzz tests preserve hostile inputs that reproduce known failures.

## Why this matters

The council has accumulated 30+ `require_pattern` lines. Every one of them is a single point of textual fragility. A single refactor that renames a validator can pass the text gate (if the new name still contains the regex) while removing the actual check. Behavior pinning makes the test the source of truth and the text gate the smoke alarm that fires when the test's anchor moves.
