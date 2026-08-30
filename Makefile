.PHONY: test benchmark smoke compile research1-audit analyze-graph

test:
	PYTHONPATH=src python3 -m pytest

compile:
	python3 -m compileall -q src ros_ws/src

benchmark:
	PYTHONPATH=src python3 scripts/build_benchmark_manifest.py

smoke:
	PYTHONPATH=src python3 scripts/run_graph_campaign.py --partition development --routes 2 --seeds 2 --output reports/graph_smoke.jsonl

research1-audit:
	PYTHONPATH=src python3 scripts/check_research1_integration.py

analyze-graph:
	PYTHONPATH=src python3 scripts/analyze_graph_results.py \
		--development reports/graph_development_v1.0.jsonl \
		--validation reports/graph_validation_v1.0.jsonl \
		--output reports/research3_graph_analysis_v1.0.json
