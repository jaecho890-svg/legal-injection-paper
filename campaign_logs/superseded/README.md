# Superseded error records

Usage-limit error records moved out of `results_v2/` on 2026-11-06 so the analysis does not count
them as API errors. None is a failed model reply: each is a call refused by the subscription's
5-hour usage limit, for a job that is no longer in the plan. MANIFEST.jsonl lists every file,
where it came from and why it was moved. Nothing here is read by any analysis.
