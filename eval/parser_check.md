# Prompt 1 parser check

Run on 2026-10-19 with `claude-sonnet-5-5`, against the six made-up resumes in `backend/tests/fixtures/resumes/` (every person is fictional). Each parse validated on the first try; average about 3,900 input and 1,350 output tokens per resume.

| Resume | is_stem | City and state | Major | Grad date | Role types | Dates and warnings |
| --- | --- | --- | --- | --- | --- | --- |
| CS (PDF) | Pass: true | Pass | Pass | Pass: May 2028 to 2028-05 | Pass: software | Pass |
| ME (PDF) | Pass: true | Pass | Pass | Pass: Spring 2028 to 2028-05 | Pass: mechanical, industrial_manufacturing | Pass: "Fall 2024" start to 2024-09, "Summer 2025" start to 2025-06, both flagged |
| EE (PDF) | Pass: true | Pass: street address and ZIP dropped, with a warning | Pass | Pass: 12/2027 to 2027-12 | Pass: embedded_firmware, electrical, computer_hardware | Pass |
| Biology (PDF) | Pass: true | Pass: "Massachusetts" to MA, flagged | Pass | Pass | Pass: biology_lab | Pass |
| Chemistry (DOCX) | Pass: true | Pass | Pass | Pass: Winter 2027 to 2027-03, flagged | Pass: chemistry_lab, chemical | Pass: "Summer 2025" start to 2025-06, flagged |
| Marketing (PDF) | Pass: false, with a warning | Pass | Pass | Pass | Pass: none, explained in a warning | Pass |

Class standing was estimated from the grad date for all six and flagged each time, as rule 5 asks.
