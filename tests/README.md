# Test Suite

This directory contains all tests for the Universal Web Scraping System (UWSS).

## Directory Structure

```
tests/
├── __init__.py
├── README.md
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for multiple components
└── e2e/            # End-to-end tests for full pipeline
```

## Test Organization

### Unit Tests (`tests/unit/`)
- Test individual functions, classes, and modules
- Fast execution, isolated tests
- Examples:
  - `test_score.py` - Test scoring functions
  - `test_extractors.py` - Test metadata extractors
  - `test_models.py` - Test database models

### Integration Tests (`tests/integration/`)
- Test interactions between multiple components
- Test data flow between modules
- Examples:
  - `test_phase2_full.py` - Full Phase 2 pipeline test
  - `test_phase2_components.py` - Phase 2 component tests
  - `analyze_phase2_data.py` - Data analysis utilities

### End-to-End Tests (`tests/e2e/`)
- Test complete workflows from discovery to export
- Test with real or mock data
- Examples:
  - `test_full_pipeline.py` - Complete pipeline test
  - `test_multi_source.py` - Multi-source integration test

## Running Tests

### Run all tests
```bash
python -m pytest tests/
```

### Run specific test category
```bash
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/
```

### Run specific test file
```bash
python -m pytest tests/integration/test_phase2_full.py
```

## Test Data

Test data should be stored in `tests/data/` or use temporary databases.
Do not commit large test data files to the repository.

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Clean up test data after tests
3. **Naming**: Use descriptive test names
4. **Documentation**: Document complex test scenarios
5. **Performance**: Keep unit tests fast (<1s each)


