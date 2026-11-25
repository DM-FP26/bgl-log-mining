# Blockers

## S06: local BGL data unavailable

This checkout has no `data/raw/BGL.log` or `data/interim/parsed.parquet`, which S06 needs to align the embeddings with alert labels and timestamps. The Zenodo download failed because `zenodo.org` could not be resolved from this machine.

**Question for Nafi:** Can you provide/copy the existing BGL log or parsed parquet into this checkout, or restore network access to Zenodo so S01/S02 can prepare the S06 metadata?
