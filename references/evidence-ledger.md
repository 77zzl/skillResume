# Evidence ledger

The evidence ledger is the anti-hallucination layer. It is an internal working artifact, not a second resume. Every factual claim that survives into a resume should be traceable to one or more ledger records.

## Record shape

Use JSON or an equivalent table with these fields:

```json
{
  "id": "E-001",
  "fact": "Built and deployed a Django service with JWT authentication",
  "source": "project_notes.docx, section 2, paragraph 4",
  "kind": "project | education | employment | skill | metric | portfolio",
  "date_start": "2024-09",
  "date_end": "2025-03",
  "confidence": "high | medium | low",
  "ownership": "独立完成 | 主导 | 参与 | unknown",
  "allowed_claim": "独立完成 Django 服务开发与部署",
  "forbidden_inference": "不得推断为生产级高并发系统",
  "role_tags": ["python", "backend", "api"],
  "status": "verified | needs_confirmation | conflict | excluded"
}
```

## Evidence rules

- `high` means the fact is explicit in a supplied source or directly confirmed by the user. `medium` means the source is clear but ownership, scale, or outcome is incomplete. `low` is a lead only and cannot support a strong claim without confirmation.
- A source can support a narrower statement than the agent might naturally write. Preserve the narrower statement.
- Metrics need their own record or an explicit source citation. Never turn vague language such as “明显提升” into a percentage.
- “Used technology X” does not prove “expert in X”; “read a paper” does not prove “implemented the method”; “coursework” does not prove professional experience.
- When sources conflict, keep both records, mark the conflict, and use neither disputed value until resolved.
- For project bullets, record both the technical method and the observable artifact/result. If only the method is evidenced, write a method-focused bullet.
- Internal names should be paired with a human-readable category, for example `HiCAF-Net` → “轻量卷积骨干与多尺度特征融合”. Do not put an unexplained internal name in the headline or first bullet.

## Claim compilation

Before writing a bullet, form a trace such as:

```text
bullet B-03 -> E-004 (method) + E-006 (scope) + E-009 (metric)
```

If one link is missing, weaken the wording or omit that part. Keep the trace in the compiled manifest/audit report so a reviewer can answer “这句话来自哪里？” without rereading the whole source set.

