from pathlib import Path

from language_nav.benchmark.corpus import write_corpus_manifest


if __name__ == "__main__":
    target = Path("data/manifests/instruction_benchmark_v0.1.json")
    write_corpus_manifest(target)
    print(target)

