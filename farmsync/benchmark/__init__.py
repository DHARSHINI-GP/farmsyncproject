"""
FARMSYNC Benchmark & Empirical Evaluation Suite.
Provides reproducible 50-query head-to-head benchmarking comparing:
1. FARMSYNC Adaptive Orchestration (Router + Deterministic GIS + Trust Engine)
2. Premium-Only Commercial VLM Baseline (Pure GPT-4o)
3. Static Pipeline Baseline (Fixed Routing without Trust Verification)
"""

from farmsync.benchmark.evaluator import BenchmarkEvaluator, run_benchmark_evaluation
