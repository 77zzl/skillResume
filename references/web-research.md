# Current web research: hiring signals and visual references

Use this reference whenever a JD or intended role is available. Web research is a decision aid, not candidate evidence.

## Research goals

Answer two separate questions:

1. What do employers for this role currently ask for or screen for?
2. What visual conventions make the same truthful content easy to scan and parse?

Do not collapse these into a generic claim such as “HR likes beautiful resumes”. Hiring signals depend on role family, seniority, market, company type, and the exact vacancy.

## Search order

Prefer sources in this order:

1. The target company's own careers page and the exact JD.
2. Three to five recent postings for the same role family and market, ideally across at least two relevant platforms.
3. University career offices, professional associations, and recruiter/hiring-manager guidance for writing conventions.
4. Template galleries only for layout inspiration; check whether a template is ATS-safe, licensed, editable, and suitable for the target market.

## China-market route

Run this route when the JD is in Chinese, the target location is mainland China, the company recruits primarily in China, or the user explicitly asks for domestic hiring signals. Do not assume that an English-language source set represents the Chinese market.

### Domestic source tiers

Use public pages and search results that can be reviewed without logging into a personal account. The platform list is a routing aid, not a ranking:

| Source | Best use | Official domain |
| --- | --- | --- |
| BOSS直聘 | 社招、互联网、技术、产品、运营；观察职位关键词和招聘方表述 | [zhipin.com](https://www.zhipin.com/) |
| 猎聘 | 中高端、专业岗位、猎头和企业招聘信息 | [liepin.com](https://www.liepin.com/) |
| 智联招聘 | 综合社招、传统行业、全国和城市职位 | [zhaopin.com](https://www.zhaopin.com/) |
| 前程无忧 51Job | 综合社招、校园招聘和行业职位 | [51job.com](https://www.51job.com/) |
| 拉勾 | 互联网、科技、产品和运营岗位；含校园招聘频道 | [lagou.com](https://www.lagou.com/) |
| 牛客 | 校招、实习、互联网技术、笔试面试和企业招聘动态 | [nowcoder.com](https://www.nowcoder.com/) |
| 实习僧 | 实习、校招和转正机会 | [shixiseng.com](https://www.shixiseng.com/) |
| 应届生求职网 | 应届生、校招、国企/银行/咨询等校园职位 | [yingjiesheng.com](https://www.yingjiesheng.com/) |
| 国聘 | 国企、央企和公共招聘场景 | [iguopin.com](https://www.iguopin.com/) |
| 国家大学生就业服务平台 | 高校毕业生、全国联合招聘和官方校园就业信息 | [ncss.cn](https://www.ncss.cn/) |

Choose sources by role and candidate stage rather than querying every platform. For example:

- 互联网技术/产品/运营：目标公司官网 + BOSS直聘/拉勾/牛客 + 一个综合平台；
- 校招/实习：目标公司校招页 + 牛客/实习僧/应届生求职网 + 国家大学生就业服务平台；
- 国企/央企/事业单位相关岗位：目标单位官网 + 国聘 + 国家大学生就业服务平台或当地公共就业平台；
- 中高端专业岗位：目标公司官网 + 猎聘 + 一个综合平台。

If a platform blocks access, requires login, renders content dynamically, or exposes only stale/duplicate pages, record that limitation and use an accessible source. Never claim to have surveyed a platform that was not actually accessible.

Use the host's web search capability. Search only the role, industry, location, level, and general resume terms; do not put phone numbers, email addresses, or private source text into a query.

## Query patterns

```text
"<role title>" "job description" <city or market>
"<role title>" hiring manager resume skills <year>
"<role title>" ATS keywords resume <industry>
ATS-friendly one-page resume template <role family>
technical research resume template one page
```

For China-market research, also test Chinese queries and site filters:

```text
<岗位名称> <城市> 招聘 岗位职责 任职要求
<岗位名称> <行业> 招聘 技能 要求 <年份>
site:zhipin.com <岗位名称> <城市>
site:liepin.com <岗位名称> <城市>
site:zhaopin.com <岗位名称> <城市>
site:51job.com <岗位名称> <城市>
site:lagou.com <岗位名称> <城市>
site:nowcoder.com <岗位名称> 校招 OR 实习
site:shixiseng.com <岗位名称> 实习
site:yingjiesheng.com <岗位名称> 校招
site:iguopin.com <岗位名称> 国企 OR 央企
site:ncss.cn <岗位名称> 招聘
```

Use Chinese synonyms only when they preserve the role meaning, such as `算法工程师/机器学习工程师`, `后端开发/服务端开发`, or `产品经理/产品负责人`. Keep the exact wording found in the JD separately from normalized synonyms.

For the user's likely AI/Python/vision directions, also test role-specific terms such as `Python`, `PyTorch`, `deployment`, `API`, `Docker`, `LLM`, `RAG`, `agentic AI`, `evaluation`, `computer vision`, and `medical imaging` only when the JD makes them relevant.

## What to extract

For each source, record:

```json
{
  "title": "Source title",
  "url": "https://example.org/source",
  "retrieved_at": "2026-09-16",
  "source_type": "employer_jd | domestic_platform_posting | official_campus | public_employment | recent_posting | career_guide | template_reference",
  "market": "中国大陆 | international | mixed",
  "scope": "AI application roles in China",
  "signals": [
    {
      "signal": "Python application development and deployment",
      "frequency_or_strength": "explicit must-have",
      "decision": "move proven Python delivery into summary and first project"
    }
  ]
}
```

Separate `observed` from `inferred`: “the exact JD asks for Python and Docker” is observed; “this employer probably values production reliability” is an inference and must be labeled as such. Do not invent frequency counts from a single posting.

## Hiring-signal synthesis

Use web research to decide:

- which proven skills belong in the headline, summary, and first three bullets;
- which exact terms should be preserved for ATS matching;
- which outcomes matter, such as deployment, validation, maintainability, research translation, or user impact;
- whether a gap should be stated honestly rather than hidden;
- whether a role-specific variant is justified.

Current guidance commonly rewards action-led, specific, outcome-aware bullets and meaningful job-specific terminology. Treat those as writing conventions, not guarantees. A claim still needs candidate evidence.

For domestic postings, compare the exact JD and several recent public postings before summarizing a hiring signal. Separate:

- `observed`: wording explicitly present in one or more accessible postings;
- `repeated`: a term or requirement appearing across multiple independent postings;
- `inferred`: a cautious interpretation of what the repeated requirement may imply;
- `platform_limited`: a signal affected by a platform's category, stale listing, duplicate listing, or search visibility.

Do not turn platform marketing claims, anonymous forum comments, a single recruiter post, or a single vacancy into a universal statement about what Chinese HR prefers. Preserve the company's own wording when it is available.

## Template research and style selection

Search for at least two contrasting references when the user requests multiple styles. Extract design principles, not copied markup:

- `ats`: single column, standard section headings, ordinary text, no graphics or text boxes;
- `modern`: restrained color, stronger hierarchy, optional sidebar, still text-first;
- `research`: calm typography, method/outcome emphasis, publications or research sections when evidenced.

Render all requested styles from the same manifest. Compare density, reading order, contrast, and parser safety. If no preference is given, recommend `ats` for portal uploads and `modern` or `research` for direct human review based on the role.

## Audit requirement

The final audit must include source URLs, retrieval date, extracted signals, decisions changed, styles rendered, selected style, and any uncertainty. Never cite an external template as proof that the candidate has a qualification.

## Initial reference set used for this Skill

These are starting references, not a permanent substitute for fresh research:

- MIT CAPD, [Make your resume ATS-friendly](https://capd.mit.edu/resources/make-your-resume-ats-friendly/): use readable fonts, standard text, meaningful job-specific terms, and avoid formatting that may be distorted by an ATS.
- MIT CAPD, [Career toolkit: Crafting an effective resume](https://capd.mit.edu/resources/career-toolkit-crafting-an-effective-resume/): start bullets with action verbs, use project/action/result logic, preserve readable margins, and do not shrink text just to fit more content.
- University of Pennsylvania Career Services, [Resume Guide for Graduate Students and Postdocs](https://careerservices.upenn.edu/resources/resume-guide-for-graduate-students-and-postdocs/): use the Skill-Context-Outcome pattern and tailor the resume for the role.
- Harvard FAS Mignone Center, [Create impactful resumes and cover letters](https://careerservices.fas.harvard.edu/resources/hes-create-impactful-resumes-and-cover-letters/): use action-oriented language and avoid passive, vague descriptions.
- Laterite, [AI Developer job description](https://www.laterite.com/wp-content/uploads/2026/01/Laterite_AI_Developer_Job_Description_Dec2025_JD.pdf): an example of a current AI application role emphasizing Python, LLM/RAG/agentic AI, validation, deployment, GitHub, Docker, and translating research needs into technical solutions.
- Overleaf, [Academic CV Template](https://www.overleaf.com/latex/templates/academic-cv-template/gmyytjmdbvdm) and Canva, [Resume templates](https://www.canva.com/resumes/): examples of academic and modern visual directions. Reuse design principles, not third-party assets.
- BOSS直聘, [招聘信息](https://www.zhipin.com/zhaopin/index.html): public domestic job-search and employer-posting entry point; use individual accessible postings for role signals.
- 猎聘, [关于猎聘](https://ir.liepin.com/knowledge): company-provided description of its professional and higher-end recruitment focus; do not treat platform positioning as a candidate or hiring guarantee.
- 智联招聘, [招聘网](https://www.zhaopin.com/): public domestic job-search entry point with role and city categories.
- 前程无忧, [51Job](https://www.51job.com/): public comprehensive recruitment and campus-recruitment entry point.
- 拉勾, [校园招聘](https://campus.lagou.com/): public technology and campus recruitment entry point.
- 牛客, [招聘动态与求职工具](https://www.nowcoder.com/?lang=zh): public technology recruitment, campus recruitment, and interview-preparation entry point.
- 实习僧, [实习与校招](https://www.shixiseng.com/): public internship and campus-recruitment entry point.
- 应届生求职网, [校园招聘](https://web.yingjiesheng.com/): public graduate and campus-recruitment entry point.
- 国聘, [官网](https://www.iguopin.com/): public recruitment entry point for the Guopin platform.
- 国家大学生就业服务平台, [全国网络联合招聘](https://www.ncss.cn/student/jobfair/joint.html): official higher-education graduate employment and joint-recruitment source.
