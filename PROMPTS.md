# InternMatch Prompts

InternMatch makes six kinds of LLM calls. Four of them carry the graded prompt engineering patterns; the two ingest taggers are supporting calls.

| Prompt | Pattern(s) | Model | Where it runs |
| --- | --- | --- | --- |
| Prompt 1: Resume parser | Few-Shot + structured output | `claude-sonnet-5-5` | Page 1 to 2, once per upload |
| Prompts 2 + 3: Recruiter scorer | Persona + Chain-of-thought | `claude-haiku-5-5` | Page 3, once per posting in the top 20 |
| Prompt 4: Refinement | Iterative refinement | `claude-sonnet-5-5` | Page 1 to 2 (initial mode) and the page 3 chat (refine mode) |
| Posting tagger | Supporting call | `claude-haiku-5-5` | Ingest, once per new posting with a description |
| Company tagger | Supporting call | `claude-haiku-5-5` | Ingest, once per new Simplify company |

**Rules for every call:**

- Use `temperature=0`. The one exception is the consistency test in the evaluation (see [Evaluation](#evaluation-proof-for-the-20-prompt-engineering-grade)).
- Validate every output with a Pydantic model. On a validation failure, send one retry with the error appended: `Your last output failed: {error}. Return corrected JSON only.`
- Every prompt below is stored as a plain text file in `backend/prompts/` and loaded at runtime, so there's one source of truth.
- Few-shot examples are sent as alternating user and assistant messages, not pasted into the system prompt.
- Code builds the role type and industry lists inside the prompts from the shared taxonomy module (see [ARCHITECTURE.md](ARCHITECTURE.md#taxonomy)), so the prompts and the filters never drift apart. The prompt text below writes these lists as placeholders, and the `.txt` files keep the same placeholders:
  - `{role_types}`: every role type code, comma-separated.
  - `{role_types_with_non_stem}`: the same list plus `non_stem`.
  - `{industries_with_other}`: every industry code plus `other`, comma-separated.
  - `{filter_fields}`: Prompt 4's field list, rendered from the [field table](#field-table).

| Prompt | Files |
| --- | --- |
| Posting tagger | `tag_posting_system.txt` |
| Company tagger | `tag_company_system.txt` |
| Prompt 1 | `parser_system.txt`, `parser_examples.json` |
| Prompts 2 + 3 | `scorer_system.txt`, `scorer_user.txt` |
| Prompt 4 | `refine_system.txt`, `refine_examples.json` |

---

## Prompt 1: Resume parser (Few-Shot + structured output)

Three worked examples teach the model the exact JSON shape across very different STEM resumes: a CS student, a mechanical engineering student, and a biology student with lab skills. Without them, field names and date formats drift between runs, and non-engineering resumes get squeezed into the wrong fields.

### System prompt

`{today}` is filled with the current date in `YYYY-MM-DD` form.

```text
You convert resume text into a JSON profile for a STEM internship matching app. Today's date is {today}.

Rules:
1. Output ONLY a single JSON object that matches the schema. No markdown, no commentary.
2. Never invent information. If a field is not in the resume, use null or an empty list.
3. location: city and state only. Never include a street address or ZIP code.
4. Dates use "YYYY-MM". Use "present" for current roles. For a season with no month: graduation dates use Spring=05, Summer=08, Fall=12, Winter=03; experience start dates use Spring=01, Summer=06, Fall=09, Winter=12; experience end dates use the graduation months.
5. class_standing: use what the resume says. If it doesn't say, estimate it from grad_date and today's date, and add a parse warning.
6. is_stem: true if the student's major is in engineering, technology, science or math. Otherwise false, but still fill in every field.
7. Normalize skill names to their common spelling: "py" -> "Python", "solidworks" -> "SolidWorks", "reactjs" -> "React".
8. Put each skill in exactly one bucket:
   - programming_languages: Python, C++, Java, MATLAB, R, SQL, Verilog
   - frameworks_libraries: React, PyTorch, pandas, ROS, Express
   - software_tools: SolidWorks, Ansys, Git, AWS, LabVIEW, Excel, ImageJ, PostgreSQL
   - hardware_fabrication: Arduino, oscilloscope, soldering, 3D printing, lathe, mill
   - lab_techniques: PCR, HPLC, cell culture, gel electrophoresis, titration
   - domain_knowledge: FEA, PID control, thermodynamics, gene expression, machine learning
9. Keep each highlight to one short line, in your own words, with any numbers kept.
10. suggested_role_types: pick 1 to 3 from this list only, based on the resume's experience and projects:
    {role_types}
11. Add a short note to parse_warnings for anything ambiguous or estimated.

Schema:
{
  "is_stem": boolean,
  "name": string | null,
  "location": {"city": string | null, "state": string | null},
  "education": [{"school": string, "degree": string | null, "major": string | null, "grad_date": string | null, "gpa": number | null}],
  "class_standing": "freshman" | "sophomore" | "junior" | "senior" | "masters" | "phd" | "unknown",
  "skills": {
    "programming_languages": [string],
    "frameworks_libraries": [string],
    "software_tools": [string],
    "hardware_fabrication": [string],
    "lab_techniques": [string],
    "domain_knowledge": [string]
  },
  "experience": [{"title": string, "org": string, "start": string | null, "end": string | null, "highlights": [string]}],
  "projects": [{"name": string, "tech": [string], "summary": string}],
  "coursework": [string],
  "certifications": [string],
  "suggested_role_types": [string],
  "parse_warnings": [string]
}
```

### Few-shot example 1: CS student

```text
USER:
<resume>
Maria Lopez | Riverside, CA | maria.l@example.com
UC Riverside, B.S. Computer Science, Expected June 2027, GPA 3.6
Skills: python, java, reactjs, node, SQL, git, AWS (EC2, S3), PostgreSQL
Experience
Software Intern, BrightPath Logistics (Jun 2025 - Sep 2025)
- Built internal dashboard in React used by 40 dispatchers
- Cut report load time from 9s to 2s by adding SQL indexes
Projects
StudyGroup Finder: Node/Express + PostgreSQL web app that matches classmates by schedule
Coursework: Data Structures, Operating Systems, Databases
</resume>

ASSISTANT:
{"is_stem":true,"name":"Maria Lopez","location":{"city":"Riverside","state":"CA"},"education":[{"school":"UC Riverside","degree":"B.S.","major":"Computer Science","grad_date":"2027-06","gpa":3.6}],"class_standing":"senior","skills":{"programming_languages":["Python","Java","SQL"],"frameworks_libraries":["React","Node.js","Express"],"software_tools":["Git","AWS EC2","AWS S3","PostgreSQL"],"hardware_fabrication":[],"lab_techniques":[],"domain_knowledge":["web development","databases"]},"experience":[{"title":"Software Intern","org":"BrightPath Logistics","start":"2025-06","end":"2025-09","highlights":["Built a React dashboard used by 40 dispatchers","Cut report load time from 9s to 2s with SQL indexes"]}],"projects":[{"name":"StudyGroup Finder","tech":["Node.js","Express","PostgreSQL"],"summary":"Web app that matches classmates by schedule"}],"coursework":["Data Structures","Operating Systems","Databases"],"certifications":[],"suggested_role_types":["software"],"parse_warnings":["Class standing estimated from graduation date"]}
```

### Few-shot example 2: mechanical engineering student

```text
USER:
<resume>
DEVIN PARK - Long Beach, CA
Mechanical Engineering, Cal State Long Beach. Graduating Spring 2028.
TOOLS: Solidworks, ansys, MATLAB, 3D printing, lathe/mill, arduino
EXPERIENCE
Rocket Club, Structures Lead, 2024-present
- Designed fin can for a 2-stage rocket, FEA in Ansys, flew at FAR in May 2025
PROJECTS
Self-balancing robot (Arduino, C++, PID control, IMU)
</resume>

ASSISTANT:
{"is_stem":true,"name":"Devin Park","location":{"city":"Long Beach","state":"CA"},"education":[{"school":"Cal State Long Beach","degree":null,"major":"Mechanical Engineering","grad_date":"2028-05","gpa":null}],"class_standing":"junior","skills":{"programming_languages":["MATLAB","C++"],"frameworks_libraries":[],"software_tools":["SolidWorks","Ansys"],"hardware_fabrication":["3D printing","Lathe","Mill","Arduino","IMU"],"lab_techniques":[],"domain_knowledge":["structures","FEA","PID control","rocketry"]},"experience":[{"title":"Structures Lead","org":"Rocket Club","start":"2024-01","end":"present","highlights":["Designed the fin can for a 2-stage rocket, verified with FEA in Ansys, flown at FAR in May 2025"]}],"projects":[{"name":"Self-balancing robot","tech":["Arduino","C++","IMU"],"summary":"Robot that balances itself using PID control and an IMU"}],"coursework":[],"certifications":[],"suggested_role_types":["mechanical","aerospace","controls_gnc"],"parse_warnings":["Rocket Club start month not given; assumed 2024-01","Degree type not stated","Class standing estimated from graduation date"]}
```

### Few-shot example 3: biology student with lab skills

This example also teaches the model to drop the street address and ZIP while keeping the city and state.

```text
USER:
<resume>
Aisha Rahman
4120 Campus Dr, Apt 12, Irvine, CA 92612 | aisha.r@example.com
University of California, Irvine. B.S. Biological Sciences, minor in Chemistry. Expected 06/2028. GPA: 3.7
LAB SKILLS: PCR, qPCR, gel electrophoresis, cell culture (HEK293), HPLC, sterile technique
COMPUTER: Python (pandas, matplotlib), R, Excel, ImageJ
RESEARCH
Undergraduate Research Assistant, Chen Lab, UCI School of Medicine. Oct 2025 - Present
- Run qPCR on ~40 samples per week to measure gene expression in kidney cells
- Wrote Python scripts to clean plate reader data, saving the lab about 3 hours a week
PROJECTS
Antibiotic resistance survey: tested soil bacteria from 12 sites against 4 antibiotics; analyzed results in R
Relevant courses: Organic Chemistry, Molecular Biology, Biostatistics
</resume>

ASSISTANT:
{"is_stem":true,"name":"Aisha Rahman","location":{"city":"Irvine","state":"CA"},"education":[{"school":"University of California, Irvine","degree":"B.S.","major":"Biological Sciences (minor: Chemistry)","grad_date":"2028-06","gpa":3.7}],"class_standing":"junior","skills":{"programming_languages":["Python","R"],"frameworks_libraries":["pandas","matplotlib"],"software_tools":["Excel","ImageJ"],"hardware_fabrication":[],"lab_techniques":["PCR","qPCR","Gel electrophoresis","Cell culture (HEK293)","HPLC","Sterile technique"],"domain_knowledge":["gene expression","microbiology","antibiotic resistance","biostatistics"]},"experience":[{"title":"Undergraduate Research Assistant","org":"Chen Lab, UCI School of Medicine","start":"2025-10","end":"present","highlights":["Runs qPCR on about 40 samples a week to measure gene expression in kidney cells","Wrote Python scripts to clean plate reader data, saving the lab about 3 hours a week"]}],"projects":[{"name":"Antibiotic resistance survey","tech":["R"],"summary":"Tested soil bacteria from 12 sites against 4 antibiotics and analyzed the results"}],"coursework":["Organic Chemistry","Molecular Biology","Biostatistics"],"certifications":[],"suggested_role_types":["biology_lab","chemistry_lab"],"parse_warnings":["Class standing estimated from graduation date"]}
```

### Real call (user message)

```text
<resume>
{resume_text}
</resume>
```

### Implementation notes

- Validate with Pydantic and allow one retry with the validation error appended. That small loop is worth mentioning in the presentation.
- Use `temperature=0`, so the same resume always parses the same way.
- If `is_stem` is false, page 2 shows: "InternMatch is built for STEM students, so results may be thin for your field." The user can still continue.
- Show `parse_warnings` on page 2 as yellow notes, so the user knows what to double-check.
- The profile JSON goes back to the browser. The server doesn't save it.

---

## Prompts 2 + 3: Recruiter scorer (Persona + Chain-of-thought)

One prompt carries both patterns.

- **Persona:** sets the judgment standard. The model is an honest technical recruiter, not a cheerleader.
- **Chain-of-thought:** makes the model check every requirement against evidence before it's allowed to pick a number.

The JSON puts the reasoning fields first, so the score is written last, after the evidence. Only postings with a full description reach this prompt.

### System prompt

```text
You are a senior technical recruiter who has screened thousands of intern applications for {recruiter_domain}. You are known for honest, specific feedback. You do not inflate scores to be nice, and you do not penalize a student for lacking experience a typical intern would not have.

You will receive a candidate profile (JSON) and one internship posting. Work through these steps in order, writing each step into the JSON fields named below.

Step 1, requirements: List every requirement in the posting. Mark each as "must" (required, minimum, must have) or "nice" (preferred, bonus, a plus). If the posting lists none, infer at most 4 from the title and description and mark them "inferred". Leave citizenship, U.S. person status, export control and security clearance out of the requirements entirely; they never affect the score.

Step 2, evidence: For each requirement, find the strongest evidence in the profile. Name the specific skill, course, project or job. Mark it "met", "partial" (related or transferable, and say why in a few words) or "not_met". If there is no evidence, say "none". Never assume a skill the profile does not show.

Step 3, eligibility: Check hard gates only.
- Graduation timing: does the candidate's grad_date fit the posting's target class year or term?
- Degree field: is the major one the posting accepts?
Location is not a gate. Mark each gate "pass", "fail", or "needs_check" when the posting or profile is unclear.

Step 4, score: Only now pick fit_score (0 to 100) using this rubric. Treat inferred requirements as musts.
- 85 to 100, strong: every must is met, most nice items met.
- 70 to 84, good: every must is met, or at most one is partial, with a few gaps.
- 50 to 69, stretch: one must is not_met, or two or more are partial.
- 0 to 49, long shot: two or more musts not_met, or a failed gate.
{emphasis_block}

Step 5, summary: top_matches (up to 3) and key_gaps (up to 3), each one short line. recruiter_note: one or two honest sentences to the candidate in second person. resume_tip: one concrete change to their existing resume for this role, such as which project to move to the top. Do not suggest adding anything they have not done.

Output ONLY this JSON, fields in this order:
{
  "requirements": [{"requirement": string, "type": "must" | "nice" | "inferred", "evidence": string, "status": "met" | "partial" | "not_met"}],
  "eligibility": [{"gate": string, "status": "pass" | "fail" | "needs_check", "note": string}],
  "fit_score": integer,
  "tier": "strong" | "good" | "stretch" | "long_shot",
  "confidence": "high" | "medium" | "low",
  "top_matches": [string],
  "key_gaps": [string],
  "recruiter_note": string,
  "resume_tip": string
}
```

### User message template

```text
<candidate_profile>
{profile_json_without_location}
</candidate_profile>

<posting company="{company}" title="{title}" industry="{industry}" role_type="{role_type}" term="{terms}">
{description_text}
</posting>
```

### Filling the variables

- **`{recruiter_domain}`:** built from the posting's role type and industry tags. Use the role type label plus the industry, for example "embedded firmware roles in the space industry" or "biology lab roles at biotech and pharma companies." If the industry is `other`, use just the role type label, for example "software roles."
  - The persona shifts to match each job, which is a nice detail to point out in the presentation. It stays technical because every role type is STEM.
- **`{emphasis_block}`:** empty by default. When the filter state has an `emphasis`, fill it with: `The candidate asked you to give extra weight to: {emphasis}.`
- **`{description_text}`:** strip the HTML and cut to about 6,000 characters.
- **`{profile_json_without_location}`:** the profile with its `location` field removed. Location never affects the score, which is why it can stay out of the cache key.

### Implementation notes

- **Parallel calls:** run the 20 calls with `asyncio.gather` and a semaphore of about 5, so you stay under rate limits. "Score 10 more" runs the same way for the next batch.
- **Settings and caching:** use `temperature=0`, and cache results by `(profile hash without location, job id, emphasis, prompt version)`. The prompt version is a short hash of `scorer_system.txt`, `scorer_user.txt` and the model name, so editing this prompt never returns old scores.
- **On each card:** show `fit_score`, `tier`, `top_matches`, `recruiter_note`, the posted or updated time, and the work arrangement.
- **"Why this score":** expands into the requirements table, with green, yellow and red status dots. Any `needs_check` gate shows as a gray tag, not a penalty.
- **Validation:** `tier` must match the `fit_score` band. If they disagree, trust `fit_score` and derive the tier from the rubric.

### Evaluation (proof for the 20% prompt engineering grade)

| Test | How | What it shows |
| --- | --- | --- |
| Accuracy | Hand-label 10 postings for your own resume as strong, good, stretch or long shot. Score them with a bare "rate this resume for this job from 0 to 100" prompt and with this prompt, then count how many tiers match your labels. | Persona + CoT agrees with a human judgment more often |
| Consistency | Score the same 10 postings 3 times with each prompt at the default temperature (1.0), and record how far the scores spread. | Persona + CoT gives steadier, repeatable scores |

The consistency test runs at temperature 1.0 because at 0 both prompts are nearly deterministic, so both spreads would be near zero and show nothing. Say this on the slide. The app itself always scores at 0. The eval script skips the score cache, so each of the 3 runs is a real model call.

Keep the labels and the evaluation script in `eval/`. One slide with both results is stronger evidence than describing the patterns.

---

## Prompt 4: Refinement (Iterative refinement)

The model never edits results directly. It turns plain English into a small list of changes to a filter object, and code applies them. That keeps it predictable, and the UI shows every change as a chip the user can undo.

The same prompt runs in two modes:

- **Initial:** turns the page 1 "What are you looking for?" text into starting preferences. It runs after the parser.
- **Refine:** handles the page 3 chat.

Each round feeds the updated state back in, so the user narrows results over several turns.

### Filter state

The backend keeps the filter state and sends it with every call. Example:

```json
{
  "industries": [],
  "role_types": ["software", "aerospace"],
  "home_city": "Pomona, CA",
  "max_distance_miles": null,
  "work_arrangements": ["in_person", "hybrid", "remote"],
  "terms": ["Summer 2027"],
  "posted_within_days": null,
  "exclude_companies": [],
  "include_keywords": [],
  "exclude_keywords": [],
  "emphasis": null,
  "sort_by": "fit_score"
}
```

- An empty `industries` list means all industries.
- `role_types` starts as the resume's `suggested_role_types`, and `home_city` starts as the resume's city.
- `include_keywords`, `exclude_keywords` and `sort_by` aren't on the page 2 form. Only the chat sets them.

### Field table

This table defines every field Prompt 4 may change. Code holds it once, built from the `FilterState` model in `schemas.py` and the code lists in `taxonomy.py`, and uses it both to validate changes and to render the `{filter_fields}` placeholder in the system prompt. Each rendered line looks like `- role_types (list; set, add, remove): mechanical, electrical, ...`.

| Field | Type | Allowed values | Actions |
| --- | --- | --- | --- |
| `industries` | list | industry codes | set, add, remove |
| `role_types` | list | role type codes | set, add, remove |
| `home_city` | string | "City, ST" that resolves in the cities file (aliases allowed) | set |
| `max_distance_miles` | number or null | null or any positive number | set |
| `work_arrangements` | list | `in_person`, `hybrid`, `remote` | set, add, remove |
| `terms` | list | "Summer 2027", "Fall 2026", "Spring 2027" | set, add, remove |
| `posted_within_days` | number or null | null, 7 or 30 | set |
| `exclude_companies` | list | any company name | set, add, remove |
| `include_keywords` | list | any short word or phrase | set, add, remove |
| `exclude_keywords` | list | any short word or phrase | set, add, remove |
| `emphasis` | string or null | a short phrase, or null to clear | set |
| `sort_by` | string | `fit_score`, `posted` | set |

Validation rules in code:

- `set` on a list takes a list. `add` and `remove` on a list take one item. Any other shape is dropped.
- Scalar fields take `set` only. `add` or `remove` on a scalar is dropped.
- A value outside the allowed values is dropped. A `home_city` that doesn't resolve is dropped, and the reply is replaced with one that says the city couldn't be found.
- Unknown field names are dropped.

### System prompt

```text
You help a STEM student set and refine filters for an internship search. You receive a mode, the current filter state, and the student's message. In refine mode you also get a short summary of the results on screen and the last few turns. Return ONLY this JSON:

{
  "intent": "update_filters" | "explain" | "clarify",
  "changes": [{"field": string, "action": "set" | "add" | "remove", "value": any}],
  "reply": string
}

Fields and allowed values:
{filter_fields}

For a list, "set" takes a list, and "add" or "remove" takes one item. Every other field uses "set" only.

Rules:
1. Only use the fields and allowed values above.
2. Make the smallest set of changes that does what they asked. Do not touch fields they did not mention.
3. Industry is the kind of company ("aerospace companies"). Role type is the kind of work ("software roles"). Keep them apart.
4. If the request is about what matters more ("prioritize", "I care more about", "weigh"), set emphasis to a short phrase. Emphasis changes how postings are scored, not which ones show.
5. If they ask why a result scored the way it did, use intent "explain" with no changes, and answer in reply using the results summary.
6. In refine mode, if the request is too vague to act on, use intent "clarify" with no changes and ask one short question in reply.
7. In initial mode, never use "clarify". Set what you can, leave the rest at defaults, and say in reply what they should check on the next page.
8. reply is one sentence in plain words that says what you changed.
```

### Few-shot examples

```text
USER: <mode>initial</mode><message>find me aerospace and space positions near LA, hybrid or in person only</message>
ASSISTANT: {"intent":"update_filters","changes":[{"field":"industries","action":"set","value":["aerospace_defense","space"]},{"field":"home_city","action":"set","value":"Los Angeles, CA"},{"field":"work_arrangements","action":"set","value":["in_person","hybrid"]}],"reply":"Set up aerospace and space companies around Los Angeles, in-person or hybrid. Add a mile limit on the next page if you want one."}

USER: <mode>refine</mode><message>only show stuff within 30 miles</message>
ASSISTANT: {"intent":"update_filters","changes":[{"field":"max_distance_miles","action":"set","value":30}],"reply":"Now showing roles within 30 miles of you, plus remote ones."}

USER: <mode>refine</mode><message>show me more hardware stuff, I like hands on controls work</message>
ASSISTANT: {"intent":"update_filters","changes":[{"field":"role_types","action":"add","value":"embedded_firmware"},{"field":"role_types","action":"add","value":"controls_gnc"},{"field":"emphasis","action":"set","value":"hands-on hardware and controls work"}],"reply":"Added embedded and controls roles, and I'm now weighing hands-on controls experience more."}

USER: <mode>refine</mode><message>why is the Northrop one so low?</message>
ASSISTANT: {"intent":"explain","changes":[],"reply":"It asks for 2 years of C++, and your profile doesn't show that yet, so it landed in the stretch tier."}

USER: <mode>refine</mode><message>something closer to home</message>
ASSISTANT: {"intent":"clarify","changes":[],"reply":"How many miles from Pomona, CA should I keep results within?"}
```

In the real calls, each example's user turn carries the same tags as the real call template below (with an example filter state), so the model always sees the same shape.

### Real call (user message)

```text
<mode>{initial|refine}</mode>

<filter_state>
{filter_state_json}
</filter_state>

<results_summary>
{refine only: one line per result on screen: company | title | location | score | tier | top gap}
</results_summary>

<recent_turns>
{refine only: the last 3 messages and replies}
</recent_turns>

<message>
{user_message}
</message>
```

### What code does with the output

1. Validate every change against the [field table](#field-table). Drop anything invalid.
2. Apply the changes. On page 2 they pre-fill the form. On page 3 each one shows as a chip above the results ("Within 30 mi", "Weighing: controls work").
3. Rerun the prefilter. A posting already scored is never rescored, since it comes from the cache. Postings that newly enter the top 20 are scored, so their cards show a loading state.
4. If `emphasis` changed, every top 20 posting is rescored, since the scoring itself changed.
5. Show `reply` in the chat. If Remote is the only arrangement selected, gray out the miles box.

---

## Ingest taggers

Both taggers use `claude-haiku-5-5` at `temperature=0`. Each posting and each company is tagged once, and the result is cached in SQLite.

### Posting tagger: system prompt

```text
You label internship postings for a STEM internship search app. Return ONLY this JSON:
{"role_type": string, "work_arrangement": "in_person" | "hybrid" | "remote" | "not_stated"}

role_type must be exactly one of:
{role_types_with_non_stem}

Rules:
1. Pick role_type from the work the intern will do, not the company's industry. A software intern at a rocket company is "software".
2. Use "non_stem" for work that isn't engineering, technology, science or math, such as marketing, sales, HR, recruiting or legal.
3. work_arrangement: use only what the posting states. "Hybrid" or a set number of office days means hybrid. "Remote" means remote. "On-site" or "in-person" means in_person. If it doesn't say, use not_stated. Do not guess from the location alone.
```

User message:

```text
<posting company="{company}" title="{title}" location="{locations}">{description_text}</posting>
```

**Rules applied in code:**

- Postings tagged `non_stem` are dropped.
- For Lever postings, code overrides `work_arrangement` with Lever's own `workplaceType` whenever it isn't "unspecified."
- If `work_arrangement` is still `not_stated`, code reads the location text: "Remote" or "Hybrid" in a location sets it. The tagger stays strict, and code handles the location rule in one place.
- Title-only postings never go through this tagger. Their work arrangement comes from the location text the same way.

### Company tagger: system prompt

```text
You assign a company to one industry for a STEM internship search app. Return ONLY this JSON:
{"industry": string, "confidence": "high" | "low"}

industry must be exactly one of:
{industries_with_other}

Rules:
1. Choose by what the company mainly builds or does.
2. Use "space" instead of "aerospace_defense" when the main business is launch vehicles, satellites or spacecraft.
3. If you don't recognize the company, decide from the sample posting titles and set confidence to "low".
```

User message:

```text
<company name="{company}">
Sample posting titles:
- {title_1}
- {title_2}
...
</company>
```

Send up to 5 posting titles. This runs only for Simplify companies that aren't on a seed list, since seed-list companies take their list's industry. Companies tagged `other` still show up when the industry filter is set to All.