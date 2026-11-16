# Review calibration

Use these cases when changing the review method or second-opinion adjudication.
Ordinary reviews do not need them.

| Case | Expected disposition |
| --- | --- |
| Renaming the open review leaves its old name in the URL; reopening the tab works. | Finding: normal use produces a wrong result, even with a workaround. |
| A failed send, then two reviews exchanging names before one snapshot, misroutes a queued operation. No real workflow or field report supports the whole sequence. | Drop: reproducible but contrived. New workflow or field evidence can change this. |
| A reviewer claims overlapping calls, but every production caller awaits the previous call. | Drop from caller evidence; do not build a simulator or add pause hooks. |
| Supported concurrent tabs overwrite accounting data with no app recovery. Proving it is cheap, but fixing it needs an unrequested store, schema/API changes, and about 800 lines including tests. | Finding plus Open, proved; REVISE. Report cost and needed scope decision; stop that work. |
| The same fix and regression fixture are explicitly authorized. | Accept and fix, validate, then re-review. Size alone does not stop authorized work. |
| Proving a suspected ordinary-use defect needs a separate test service beyond scope. Both reviewers say LAND but one leaves it open. | Open, suspected; REVISE. Do not build the service or treat empty findings as resolution. |

When testing the method, pin the source revision and run the relevant tests.
Give an independent evaluator the method, task, source, and test evidence;
withhold expected outcomes. Include a known worthwhile regression and record
the work spent. If discovery misses a candidate, ask about it separately and
label that result candidate adjudication.
