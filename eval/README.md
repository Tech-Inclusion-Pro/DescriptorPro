# Caption accuracy evaluation (Phase 1, spec §4)

Word error rate (WER) measured **per speaker group**, because an average
over everyone hides how a model treats the people it serves worst.

## What Rocco assembles (the gold set)

Put short clips (30 seconds to 3 minutes each) under `eval/gold/`, one
folder per speaker group, with a plain-text reference transcript next to
each clip:

```
eval/gold/
├── adult-typical/
│   ├── clip-01.mp4          # or .wav, .mov, .m4a — anything FFmpeg reads
│   └── clip-01.txt          # what was actually said, verbatim
├── accented-english/
├── child-speech/
├── aac-device-speech/
├── disfluent-speech/
└── spanish/
```

Group names are yours — the folder name is the report label. Three to five
clips per group is enough to start. Reference transcripts are verbatim:
include false starts and repetitions, skip filler punctuation. Nothing in
this folder is committed to git (see `eval/.gitignore`) — clips of real
people stay on this machine.

## Running it

```bash
.venv/bin/python eval/score_wer.py                 # whisper (settings model)
.venv/bin/python eval/score_wer.py --engine parakeet
.venv/bin/python eval/score_wer.py --engine whisper --model medium
```

Output: a per-group WER table plus overall, and `eval/results/<timestamp>-
<engine>.json` with per-clip numbers so regressions are traceable.

A group whose WER is far above the rest is a finding, not a footnote: it
goes in the phase report, and model/configuration choices get revisited
before ship.
