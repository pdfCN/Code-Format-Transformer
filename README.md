# Code Format Transformer

This tool addresses the "Hidden Cost of Readability" in LLM processing by providing bidirectional transformation between human-readable (formatted) code and token-efficient (unformatted) code for LLM consumption.

## Overview

When processing code through Large Language Models (LLMs), formatting elements like indentation, spaces, and newlines significantly increase token consumption while providing minimal benefits for SOTA models. This tool allows you to:

1. Convert formatted code to unformatted code for efficient LLM processing (token reduction of 22-42%)
2. Convert unformatted code back to formatted code for human readability

The transformation preserves complete program semantics while only removing formatting elements that don't affect execution.

## Installation

### Prerequisites

- Python 3.10+
- Uncrustify (for C-family languages: C++, Java, C#)
- YAPF (for Python)

### Installing Uncrustify

#### On Ubuntu/Debian:
```bash
sudo apt-get install uncrustify
```

#### On macOS:
```bash
brew install uncrustify
```

#### On Windows:
```bash
# Using Chocolatey
choco install uncrustify

# Or download the binary from https://sourceforge.net/projects/uncrustify/
```


### Installing the tool:
```bash
cd The-hidden-cost
pip install -r requirements.txt
```

## Usage

The main interface is through the `format_manager.py` script:

```bash
python format_manager.py [input_file] [output_file] [direction] [--config-dir CONFIG_DIR]
```

### Parameters:

- `input_file`: Path to the source code file
- `output_file`: Path where the transformed code will be saved
- `direction`: Processing direction
  - `format`: Convert unformatted code to formatted code (for human readability)
  - `unformat`: Convert formatted code to unformatted code (for LLM efficiency)
- `--config-dir`: Directory containing configuration files (default: "cfg")

### Examples:

#### Convert formatted Java code to unformatted code for LLM processing:
```bash
python format_manager.py MyCode.java MyCode.unformatted.java unformat
```

#### Convert unformatted C++ code back to formatted code for human readability:
```bash
python format_manager.py solution.unformatted.cpp solution.formatted.cpp format
```

## Supported Languages

- Java
- C++
- C#
- Python

## Configuration

The tool uses language-specific formatters with configurations stored in the `cfg` directory:

- C-family languages use Uncrustify with custom configuration files
- Python uses YAPF with custom configuration

## Performance

- AST preservation: 100% semantic equivalence verified across the McEval dataset
- Average transformation speed: 76ms per code sample
- Token reduction: 22-42% for input code (language dependent)

## Benefits for LLM Applications

- Reduced token consumption for API-based LLMs (direct cost savings)
- Faster processing times
- Improved inference efficiency without compromising model performance
