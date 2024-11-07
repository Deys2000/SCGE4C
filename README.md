# Static Call Graph Analysis for C Codebases

## Overview
This script performs static call graph analysis on C codebases. It collects information about function calls, includes, and extern declarations, and outputs a call graph in Graphviz's dot format.

##  Usage
- Clone the repository and navigate to the SCGE4C directory.
- Run the script using Python: python static_cg.py
- Specify the directory containing the C codebase as an argument: python static_cg.py /path/to/codebase
- The script will output a call graph in Graphviz's dot format to a file named call_graph.dot in the current directory.

## Features
- Collects C files from a specified directory
- Analyzes includes and function definitions
- Builds a call graph by analyzing function calls within and between files
- Outputs the call graph in Graphviz's dot format

## Requirements
- Python 3.x
- tree_sitter library for parsing C code
- pydot library for generating Graphviz dot files

## Output
The script outputs a call graph in Graphviz's dot format to a file named call_graph.dot. This file can be visualized using Graphviz tools, such as dot or neato.

## Example Use Case
Suppose you have a C codebase in a directory called my_codebase. You can run the script to analyze the call graph as follows:
```python static_cg.py /path/to/my_codebase```

This will output a call graph in Graphviz's dot format to a file named call_graph.dot in the current directory. You can then visualize the call graph using Graphviz tools.

## Note
This script is designed for static analysis of C codebases. It does not perform dynamic analysis or execute the code in any way.