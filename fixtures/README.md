# Experiment Fixtures

`project_alpha/` is the clean baseline workspace. `run_experiments.py` copies it
for every trial, then applies one overlay from `scenario_overlays/` when an
attack scenario is active.

The overlays materialize files that the mocked GitHub PR diff claims are added
or changed. This keeps each run isolated while preventing agents from stopping
only because a verification script from the active PR is absent on disk.
