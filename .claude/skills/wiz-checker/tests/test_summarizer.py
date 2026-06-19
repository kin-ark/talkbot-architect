import pytest
from wizcheck.summarizer import build_summary_tree, build_markdown_summary

def test_build_summary_tree():
    # Mocking WizFile is complex, so we will test the empty state or mock.
    class MockWizFile:
        pass
    
    wf = MockWizFile()
    assert build_summary_tree(wf) == {}
