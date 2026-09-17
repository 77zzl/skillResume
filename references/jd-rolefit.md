# JD parsing and role-fit selection

Convert a job description into a compact demand matrix before selecting resume content.

## Demand matrix

```json
{
  "jd_id": "JD-2026-001",
  "role_title": "Python / AI 应用工程师",
  "seniority": "校招 | 初级 | 中级 | unknown",
  "must_have": [
    {"demand": "Python", "synonyms": ["Django", "FastAPI"], "evidence_needed": "proven"}
  ],
  "preferred": [],
  "outcomes": ["deliver APIs", "collaborate with algorithms"],
  "keywords": ["Python", "Docker", "LLM", "API"],
  "risk_flags": ["要求生产经验但候选人只有课程项目"]
}
```

Classify demands as:

- `must_have`: explicit requirements or responsibilities that are likely screening gates.
- `preferred`: useful differentiators that should be included only when evidence is strong.
- `outcome`: what the hire is expected to deliver; use these to order projects and bullets.
- `keyword`: exact or near-exact searchable language; include naturally when truthful.
- `risk_flag`: a possible mismatch, ambiguity, or claim that needs conservative wording.

## Heuristic score

Use this transparent prioritization score, not a hiring prediction:

```text
role_fit = 0.35 * must_have_coverage
         + 0.25 * evidence_strength
         + 0.15 * outcome_alignment
         + 0.15 * keyword_coverage
         + 0.10 * recency_or_level_fit
```

Score each component from 0 to 100. Evidence strength is highest for direct, recent, source-backed work and lowest for an unconfirmed lead. A missing must-have should lower the score and trigger an honest gap note; it must not be hidden by keyword stuffing.

## Variant policy

Create a second variant only when at least one of these is true:

1. The target roles have different dominant outcomes, such as computer vision research versus backend delivery.
2. The top evidence sets differ substantially, or the top keyword families have less than roughly 60% overlap.
3. A role-specific experience would otherwise be crowded out of a one-page resume.

Limit to three variants. Name each by role family, not by vague labels such as “优化版”. Keep shared facts identical across variants and record only the reordered/rewritten parts in the audit report.

## Bullet language

Prefer:

```text
动作 + 技术类型/方法 + 工作对象或规模 + 结果、交付物或可验证产出
```

Examples of honest translations:

- “使用 WSI 多实例学习与图卷积建模切片级空间关系，完成病理图像分类项目。”
- “基于 Django、JWT 与 REST API 实现登录鉴权和业务接口，完成可运行服务交付。”

Avoid unexplained internal module names, generic adjectives (“精通”“显著提升”), and a long technology inventory without a demonstrated use.

