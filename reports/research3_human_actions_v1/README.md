# How to complete the Research 3 human decision packet

Your 60-item pilot review and amendment R3-CA-20260911-01 are already accepted.
Do not repeat them. This packet collects all remaining human responsibilities,
but only the decisions with sufficient information are actionable now.

## Complete now

1. Read `DECISION_GUIDE.md`, then open `YOUR_RESPONSE.md` in a text editor.
2. Enter your name, role and the actual date. For each numbered item, replace
   `PENDING` with your answer and a short reason. You may write `DEFER` and explain
   what you need. Do not guess technical values or approve unseen evidence.
3. Return `YOUR_RESPONSE.md` directly through this conversation or your agreed
   private sharing channel. Alternatively, with Python 3.10 or newer installed,
   run `python3 return_packet.py` inside the extracted packet and send the new
   `research3-human-decisions-return.zip`. On Windows, `py return_packet.py` works
   when Python is installed through the Windows launcher.

No ROS, Gazebo, GPU, pip installation or Git checkout is required. No simulation
or automatic upload occurs. Plain Markdown submission does not require Python.

## What your response can unblock

The study's primary comparison, secondary-comparison policy, meaningful effect,
statistical design targets, and review coordination can be settled before new
outcomes exist. These are human scientific choices, not claims that tests passed.
Your response is preserved and translated into a pinned proposed protocol, with
any unresolved or conflicting choices flagged rather than silently overridden.

## What cannot be completed now

`HUMAN_GATES.md` lists every later human gate, its prerequisite evidence and what
the agent must prepare first. There are no new observation images in this packet.
Do not spend time looking for them or interpreting raw world files as photographs.

The 40 sphere worlds are only static-checked candidates; rendered evidence and
the 40 occlusion worlds are unfinished. The accepted amendment requires diagnostic
asset review before collection. It has not been silently amended to remove that
gate. Human labels follow captures; calibration approval follows labels and fitting;
final interpretation follows the live comparative and held-out results.

Consequently, returning this packet cannot by itself close the research. Later
reviews will be bundled when their evidence is ready. Validation labels must stay
out of model selection even when all observation reviews share one handoff.

## Verification and troubleshooting

The return command checks all fixed packet files against `manifest.json`, accepts
an edited response, and creates a new ZIP without overwriting an earlier return.
It prints `RETURN PACKAGED; NOT AN EXECUTION OR CALIBRATION APPROVAL`.

- If a fixed file has changed, extract a fresh packet and copy only your response.
- If a return ZIP exists, preserve it and use
  `python3 return_packet.py --output research3-human-decisions-return-2.zip`.
- If you cannot run Python, return just the response document. I can validate and
  preserve it here. A hash verifies bytes, not identity or scientific correctness.
- You can return partial decisions; leave unanswered items `PENDING`. Packaging
  success does not mean every question was answered or accepted.

Keep the response private: it includes your name and scientific decisions.
No approval has been filled in for you, and no blanket future approval is requested.
