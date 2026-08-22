# ML, AI, and LLM coverage baseline

Use this as a completeness map, then personalize it. It is not a single mandatory order and it should not be taught as a checklist.

## Target profiles

- **LLM application builder**: emphasize computing, selected mathematics/data, deep learning, LLM foundations/applications, and production safety.
- **ML engineer**: emphasize computing, mathematics, data/evaluation, classical ML, deep learning, and production evidence.
- **AI systems builder**: add state-space search, constraint/planning, knowledge representation, and sequential decision-making to the ML engineering base.
- **LLM engineer**: include training/inference systems, application engineering, evaluation, and safety.
- **Research path**: complete the prerequisites of the chosen claim, then add paper replication and ablation evidence.

## 0. Computing foundations

- Python semantics, functions, classes, typing, packaging, environments.
- NumPy arrays, vectorization, broadcasting, indexing, numerical stability.
- Git, command line, debugging, tests, profiling, and reproducible experiments.
- Data formats, SQL basics, APIs, Linux/process basics, CPU/GPU/memory mental models.

Evidence: implement and test a small numerical/data pipeline; diagnose shape, environment, and performance failures.

## 1. Mathematical foundations

- Linear algebra: vectors, matrices, basis, rank, projections, eigen/SVD, norms.
- Calculus: derivatives, partials, gradients, chain rule, Jacobians, computational graphs.
- Probability: random variables, conditional probability, Bayes, expectation, variance, common distributions.
- Statistics: sampling, estimators, confidence, hypothesis testing, bias/variance, leakage.
- Optimization: gradient methods, convexity intuition, constraints, conditioning, regularization.
- Information theory: entropy, cross-entropy, KL divergence, mutual information intuition.

Evidence: translate among geometric, algebraic, probabilistic, and executable representations; derive and numerically check gradients.

## 2. Classical artificial intelligence

- State spaces, uninformed and heuristic search, cost, admissibility, and adversarial search.
- Constraint satisfaction and planning representations, heuristics, failure, and complexity.
- Symbolic and probabilistic knowledge representation with explicit inference assumptions.
- Markov decision processes, value and policy methods, exploration, rewards, and reinforcement-learning evaluation.

Evidence: implement and compare search or decision procedures, diagnose a faulty representation or heuristic, and transfer the method to changed costs, observations, or constraints.

## 3. Data and experimentation

- Problem framing, target definition, baselines, data provenance and licensing.
- Cleaning, missingness, sampling, imbalance, splits, leakage, augmentation.
- Metrics, uncertainty, calibration, error analysis, experiment tracking, reproducibility.
- Causal versus predictive claims; offline versus online evaluation.

Evidence: design a valid experiment, identify leakage, justify metrics, and perform slice-based error analysis.

## 4. Classical machine learning

- Linear/logistic models, losses, regularization, optimization.
- Trees, random forests, gradient boosting; bias/variance and ensembles.
- Nearest neighbors, kernels/SVM intuition, Naive Bayes where appropriate.
- Clustering, PCA/dimensionality reduction, anomaly detection.
- Feature engineering, pipelines, cross-validation, hyperparameter search, interpretability limits.

Evidence: choose a baseline, implement/evaluate a pipeline, explain trade-offs, and debug overfit or leakage.

## 5. Deep learning

- Tensors, modules, initialization, forward/backward pass, autodiff.
- MLPs, activations, normalization, regularization, optimizers, schedules.
- CNN/spatial inductive bias; sequence models and recurrence as historical context.
- Attention, embeddings, residual streams, normalization, masking.
- Training dynamics, mixed precision, batching, checkpointing, distributed-compute intuition.

Evidence: implement a small network, inspect gradients/activations, overfit a tiny batch, and diagnose training failure.

## 6. Transformers and foundation models

- Tokenization and vocabulary trade-offs; embeddings and positional information.
- Self-attention, multi-head attention, causal masks, transformer blocks.
- Language-model objectives, pretraining data, scaling, contamination, emergent behavior caveats.
- Decoding: greedy, beam, temperature, top-k/top-p, repetition and stop conditions.
- Fine-tuning, instruction tuning, preference optimization, PEFT/adapters, catastrophic forgetting.
- Context windows, KV cache, quantization, batching, speculative/parallel decoding intuition.
- Capabilities and limits: hallucination, reasoning reliability, tool dependence, multimodality.

Evidence: trace tensor shapes through a transformer, implement a miniature attention block, compare decoding settings, and evaluate an adapted model.

## 7. LLM application engineering

- Prompt and context design; structured outputs and schema validation.
- Embeddings, retrieval, chunking, indexing, reranking, grounding, citations.
- Tool calling, workflow/state machines, agents, memory boundaries, human approval.
- Code generation and execution safety; prompt injection and untrusted content.
- Multimodal input/output where the target requires it.

Evidence: build a grounded tool-using system, test failure cases, measure retrieval and end-task quality, and explain when a simpler workflow is better than an agent.

## 8. Evaluation, safety, and production

- Outcome-specific eval design, golden sets, model graders, human review, statistical confidence.
- Robustness, adversarial testing, prompt injection, data exfiltration, authorization boundaries.
- Bias/fairness, privacy, consent, copyright/provenance, transparency, and misuse analysis.
- Latency, throughput, tokens/cost, caching, routing, fallbacks, observability, incident response.
- Versioning, deployment, monitoring, drift, rollback, and reproducible release gates.

Evidence: produce an eval suite and threat model, run a failure analysis, and operate a small service against explicit reliability/cost constraints.

## 9. Research practice

- Read papers by claim, method, assumptions, evidence, limitations, and relation to prior work.
- Reproduce a result; inspect data/code; control seeds and compute; document deviations.
- Design baselines, ablations, sensitivity tests, and negative results.
- Write a defensible research report and distinguish observation from speculation.

Evidence: reproduce or falsify a scoped claim and defend the experimental design.

## Capstone ladder

1. Train and evaluate a small classical model with reproducible data handling.
2. Implement and debug a compact neural model.
3. Build a grounded LLM application with structured tools and citations.
4. Add evals, attack tests, observability, and deployment constraints.
5. Defend architecture, limitations, costs, safety choices, and next experiments orally or in writing.

## Recommended open materials

Use current editions and verify licenses before redistribution:

- [Dive into Deep Learning](https://d2l.ai/) for executable mathematics and deep learning.
- [An Introduction to Statistical Learning](https://www.statlearning.com/) for classical ML and statistical foundations.
- [scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html) for algorithms, model selection, and pipelines.
- [PyTorch documentation and tutorials](https://pytorch.org/tutorials/) for implementation.
- [UC Berkeley CS188](https://inst.eecs.berkeley.edu/~cs188/) for search, planning, probabilistic inference, and sequential decision-making.
- [Hugging Face LLM Course](https://huggingface.co/learn/llm-course/) for tokenizers, transformers, fine-tuning, and ecosystem practice.
- [Stanford CS336: Language Modeling from Scratch](https://cs336.stanford.edu/) for data, model, training, scaling, and systems; use the current offering and respect its coursework/AI policy.
- [Full Stack Deep Learning](https://fullstackdeeplearning.com/) for production ML/LLM systems.
- [OpenAI developer documentation](https://developers.openai.com/) and [Cookbook](https://cookbook.openai.com/) for current API/tool/evaluation patterns when OpenAI products are in scope.
- Original papers for claims about architectures or methods; use course material for navigation, not as sole authority.

## Coverage exclusions to decide explicitly

Advanced computer vision, speech, causal inference, robotics/control, graph neural networks, hardware kernels, and advanced distributed training are optional unless required by the target. The baseline includes reinforcement-learning foundations but not advanced deep-RL specialization. Record the decision instead of silently omitting it.
