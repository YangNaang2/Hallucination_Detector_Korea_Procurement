"""Create explicitly synthetic input files to try the pipeline without the collected corpus."""
from pathlib import Path
from test_pipeline import fixture

if __name__=='__main__':
    root=Path('example_input')
    root.mkdir(exist_ok=True)
    fixture(root)
    print('example_input/manifest.jsonl (8 fictional notices)')
