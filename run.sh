#!/bin/bash
# Run Atomik with suppressed ALSA/JACK error messages
exec python3 main.py 2>&1 | grep -v -E "(ALSA lib|Cannot connect to server|jack server|JackShm|Expression '.*' failed|paInvalidSampleRate)"
