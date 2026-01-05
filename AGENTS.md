# DXF Parser: Coding Guidelines for AI Agents

## 1. Project Overview
Python-based tool for extracting and converting parking space information from DXF CAD files, with AI-assisted layer standardization.

## 2. Development Environment Setup

### Prerequisites
- Python 3.9+
- Virtual environment recommended
- Install dependencies: `pip install -r requirements.txt`

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Testing and Build Commands

### Running Tests
```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_api.py

# Run a single specific test
pytest tests/test_api.py::test_convert_parking_spaces

# Run with verbose output
pytest -v tests/test_api.py

# Run with coverage report
pytest --cov=src tests/
```

### Linting and Code Quality
```bash
# Run flake8 for code style checks
flake8 src/ tests/

# Run mypy for static type checking
mypy src/

# Run black for code formatting
black --check src/ tests/

# Auto-fix formatting
black src/ tests/
```

### Running the Application
```bash
# Start FastAPI server
uvicorn src.presentation.main:app --reload

# Run CLI conversion tool
python3 dxf_parking_extractor.py input.dxf
```

## 4. Code Style Guidelines

### 4.1 Import Order
```python
# 1. Standard library imports
import os
import sys

# 2. Third-party library imports
import ezdxf
import fastapi

# 3. Local project imports
from src.core.dxf_parser import DXFParser
from src.domain.entities.classification import Classification
```

### 4.2 Naming Conventions
- **Classes**: PascalCase (`DXFParser`, `LayerClassifier`)
- **Functions**: snake_case (`extract_parking_spaces`, `convert_dxf_to_csv`)
- **Variables**: snake_case (`parking_layer`, `total_spaces`)
- **Constants**: UPPERCASE (`MAX_BLOCK_DEPTH = 10`)
- **Private methods/vars**: Leading underscore (`_internal_method`, `_cache_key`)

### 4.3 Type Annotations
```python
def extract_parking_spaces(
    dxf_file: str, 
    floor: Optional[str] = None
) -> List[ParkingSpace]:
    """Mandatory type annotations for all functions."""
    pass
```

### 4.4 Docstring Guidelines
```python
def transform_coordinates(
    vertices: List[Tuple[float, float]], 
    transform_matrix: np.ndarray
) -> List[Tuple[float, float]]:
    """
    Transform vertices using a transformation matrix.

    Args:
        vertices: List of (x, y) coordinate tuples
        transform_matrix: 3x3 transformation matrix

    Returns:
        Transformed list of (x, y) coordinate tuples

    Raises:
        ValueError: If input vertices are invalid
    """
```

### 4.5 Error Handling
```python
# Use specific, custom exceptions
from src.domain.exceptions import (
    DXFParseError, 
    LayerExtractionError
)

try:
    result = parse_dxf_file(file_path)
except DXFParseError as e:
    logger.error(f"Failed to parse DXF: {e}")
    raise
```

## 5. Architecture Principles
- Follow Clean Architecture principles
- Separate concerns: domain, application, infrastructure layers
- Dependency Inversion: depend on abstractions
- Immutability and type safety are key

## 6. Performance Considerations
- Use list comprehensions over loops
- Prefer generator expressions for large datasets
- Use `functools.lru_cache` for memoization
- Leverage `typing.Protocol` for polymorphism

## 7. AI-Assisted Development
- Use Claude for complex classification logic
- Implement deterministic fallback mechanisms
- Always provide rule-based alternatives to AI features

## 8. Security Considerations
- Sanitize all file inputs
- Use `pathlib` for safe file path handling
- Implement rate limiting for API endpoints
- Never log sensitive information

## 9. Contribution Workflow
1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD approach)
3. Implement feature
4. Run linters and type checkers
5. Submit pull request with detailed description

## 10. Advanced Development Notes
- Support multiple DXF standards
- Implement flexible layer mapping
- Generate comprehensive conversion reports
- Profile and optimize critical paths