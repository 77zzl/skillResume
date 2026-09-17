# Non-blocking required-information intake

Use this reference at the beginning of every resume run. Its purpose is to improve truthfulness and completeness without turning missing information into a blocker.

## Operating rule

Ask for missing information once, in one grouped message, then continue with the facts already available. The user may skip any question. Do not repeatedly ask for the same field, and do not wait for a reply before producing a draft.

If the user later supplies an answer, merge it into the evidence ledger, revise affected bullets, and rerun the final audit. Never treat silence as confirmation.

## Information tiers

### Ask every run when missing

These fields materially affect the target or the ability to contact the candidate:

- target job title and the complete JD, if available;
- candidate display name;
- at least one contact method, if the user wants it shown;
- target city/region and work mode when they affect the role or when company recommendations are requested;
- education institution, degree, major, and graduation date or expected graduation date;
- each relevant employment, internship, or project: organization/context, role, date range, responsibility, and deliverable;
- the preferred resume language and output format when unclear.

### Ask when relevant to a claim

These fields improve prioritization and wording but must not block generation:

- ownership: independently completed, led, collaborated, or unknown;
- scale: users, data volume, team size, traffic, budget, or scope;
- outcome: metric, artifact, deployment, publication, award, test result, or other verifiable result;
- technical details: tools, versions, methods, environment, and what the candidate personally used;
- portfolio, GitHub, publication, competition, or certificate links;
- availability, internship duration, or expected start date when the JD asks for it.

### Do not proactively request by default

Do not request or place sensitive personal information in the resume unless the user volunteers it and explicitly wants it included: ID number, home address, account credentials, phone verification codes, health information, marital/fertility information, political or religious information, and other unrelated private data. Do not infer age, gender, or family status from a name, photo, school, or employment dates.

## Suggested first message

Use a short Chinese checklist such as:

```text
我会先根据现有材料开始分析和生成，不会因信息缺失而停止。为了让结果更准确，你可以一次性补充以下内容；不方便提供的项目可以跳过：

1. 目标岗位、公司、期望就业城市/地区、工作模式和完整 JD；
2. 简历中希望显示的姓名、邮箱/电话/城市；
3. 教育经历：学校、学历、专业、毕业或预计毕业时间；
4. 工作/实习/项目的组织或场景、角色、时间、个人负责部分；
5. 可核实的成果：数据、用户规模、交付物、论文、奖项、部署或测试结果；
6. 使用过的技术、工具和方法，以及熟练程度；
7. GitHub、作品集、论文或证书链接；
8. 简历语言、页数和希望的排版风格。

即使你暂时不补充，我也会先用已有事实生成一版草稿，并在最后列出需要补充或确认的内容。
```

Do not ask these questions one by one. Ask only the fields that are absent or ambiguous in the supplied materials.

## Safe fallback when information remains missing

Generate the strongest truthful draft that the available evidence supports, and record the gap separately:

| Missing field | Resume behavior | Audit behavior |
| --- | --- | --- |
| Name | Use a neutral draft label such as “候选人”, or omit the name in a content preview | Mark `name` as `missing` |
| Contact | Omit the contact line | Mark `contact` as `missing`; remind the user before submission |
| Target JD | Use the stated target title; otherwise organize around the strongest evidenced role family | Mark role research as `limited` and do not pretend the result is JD-specific |
| Desired employment city/region | Resume generation continues; company recommendations are labeled “待确定城市” and are not claimed to be city-specific | Ask once, mark `desired_city` as `missing`, and record that the domestic/international route could not be selected precisely |
| Dates | Show only confirmed dates or omit the date | Mark the date field as `needs_confirmation` |
| Metrics | Use a method, scope, artifact, or deliverable without inventing a number | Add a suggested verification question |
| Education | Omit the section if no education fact is available | Mark `education` as `missing` |
| Organization or ownership | Use a neutral project description only when the material supports it; otherwise omit the claim | Mark the fact as `unknown` or `needs_confirmation` |
| Links | Omit the link | Mark as optional and missing |

Missing information must not be written into the final resume as fake content. A draft can be generated with omitted sections and a separate completion checklist.

## Intake record

Store the state in the manifest audit when possible:

```json
{
  "intake": {
    "asked": true,
    "generation_mode": "full | partial_draft | structure_only",
    "fields": [
      {"field": "target_jd", "status": "provided | missing | skipped | needs_confirmation", "impact": "high"},
      {"field": "contact", "status": "missing", "impact": "medium"}
    ],
    "missing_critical": ["target_jd"],
    "missing_high_value": ["project_metric"],
    "follow_up_questions": ["请确认项目上线后的用户规模"]
  }
}
```

`generation_mode` describes completeness, not permission: `partial_draft` and `structure_only` are still valid outputs, but they must be clearly labeled as drafts and must not conceal missing evidence.
