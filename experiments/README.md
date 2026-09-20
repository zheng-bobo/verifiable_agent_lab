# Experiments

Each experiment should live in its own directory and include:

- `README.md`: hypothesis, setup, commands and conclusion
- a versioned configuration file
- raw metric output or a link to the corresponding artifact
- plots or tables generated from the raw output
- failure cases and known limitations

Suggested first experiment: compare pass@k, majority vote and oracle coverage under repeated sampling.

Implemented experiments:

- `week01-gridworld`: dynamic programming and tabular RL foundations.
- `week02-rag-sampling`: minimal RAG and repeated-sampling evaluation.
- `week03-minimal-harness`: framework-free observe-decide-act loop with host-enforced controls.
