"""
AST Serialization to JSON format.

Provides functions to serialize Verilog AST to JSON and deserialize back.
Useful for debugging, visualization, and tool integration.
"""

from __future__ import annotations
import json
from typing import Any
from fpga_synth.hdl_parser.ast_nodes import *


def ast_to_dict(node: ASTNode) -> dict[str, Any]:
    """
    Convert an AST node to a dictionary representation.

    The dictionary includes:
    - _type: The node's class name
    - All node attributes (excluding private ones)
    - Nested nodes are recursively converted

    Args:
        node: The AST node to convert

    Returns:
        Dictionary representation of the node
    """
    if node is None:
        return None

    result = {"_type": node.__class__.__name__}

    # Get all attributes from dataclass fields
    for field_name in dir(node):
        # Skip private attributes and methods
        if field_name.startswith('_'):
            continue

        value = getattr(node, field_name, None)

        # Skip methods and None values
        if callable(value) or value is None:
            continue

        # Convert value based on type
        if isinstance(value, ASTNode):
            result[field_name] = ast_to_dict(value)
        elif isinstance(value, list):
            result[field_name] = [
                ast_to_dict(item) if isinstance(item, ASTNode) else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[field_name] = {
                k: ast_to_dict(v) if isinstance(v, ASTNode) else v
                for k, v in value.items()
            }
        else:
            # Primitive types (str, int, bool, etc.)
            result[field_name] = value

    return result


def ast_to_json(node: ASTNode, indent: int = 2) -> str:
    """
    Convert an AST node to JSON string.

    Args:
        node: The AST node to convert
        indent: Number of spaces for indentation (default: 2)

    Returns:
        JSON string representation of the AST
    """
    data = ast_to_dict(node)
    return json.dumps(data, indent=indent)


def dict_to_ast(data: dict[str, Any]) -> ASTNode:
    """
    Convert a dictionary back to an AST node.

    Args:
        data: Dictionary representation of an AST node

    Returns:
        Reconstructed AST node

    Raises:
        ValueError: If the node type is unknown
    """
    if data is None:
        return None

    node_type = data.get("_type")
    if not node_type:
        raise ValueError("Missing _type field in AST dictionary")

    # Get the node class
    try:
        node_class = globals()[node_type]
    except KeyError:
        raise ValueError(f"Unknown AST node type: {node_type}")

    # Create empty node
    node = node_class()

    # Set all fields
    for field_name, value in data.items():
        if field_name == "_type":
            continue

        # Convert value based on type
        if isinstance(value, dict) and "_type" in value:
            # Nested AST node
            setattr(node, field_name, dict_to_ast(value))
        elif isinstance(value, list):
            # List of items (may contain AST nodes)
            converted_list = []
            for item in value:
                if isinstance(item, dict) and "_type" in item:
                    converted_list.append(dict_to_ast(item))
                else:
                    converted_list.append(item)
            setattr(node, field_name, converted_list)
        else:
            # Primitive type
            setattr(node, field_name, value)

    return node


def json_to_ast(json_str: str) -> ASTNode:
    """
    Convert a JSON string back to an AST node.

    Args:
        json_str: JSON string representation of an AST node

    Returns:
        Reconstructed AST node
    """
    data = json.loads(json_str)
    return dict_to_ast(data)


def ast_to_json_file(node: ASTNode, filename: str, indent: int = 2):
    """
    Save an AST node to a JSON file.

    Args:
        node: The AST node to save
        filename: Output file path
        indent: Number of spaces for indentation (default: 2)
    """
    with open(filename, 'w') as f:
        f.write(ast_to_json(node, indent=indent))


def ast_from_json_file(filename: str) -> ASTNode:
    """
    Load an AST node from a JSON file.

    Args:
        filename: Input file path

    Returns:
        Reconstructed AST node
    """
    with open(filename, 'r') as f:
        return json_to_ast(f.read())


class CompactJSONEncoder(json.JSONEncoder):
    """
    JSON encoder that produces more compact output for AST nodes.

    This encoder:
    - Puts simple nodes on single lines
    - Reduces whitespace for better readability
    - Keeps complex nested structures indented
    """

    def encode(self, obj):
        if isinstance(obj, dict):
            # Check if this is a simple node (no nested objects)
            is_simple = all(
                not isinstance(v, (dict, list)) or (isinstance(v, list) and len(v) == 0)
                for v in obj.values()
            )

            if is_simple and len(str(obj)) < 100:
                # Put simple nodes on one line
                return json.dumps(obj, separators=(',', ':'))

        return super().encode(obj)


def ast_to_compact_json(node: ASTNode, indent: int = 2) -> str:
    """
    Convert an AST node to compact JSON string.

    Similar to ast_to_json but produces more readable output
    by putting simple nodes on single lines.

    Args:
        node: The AST node to convert
        indent: Number of spaces for indentation (default: 2)

    Returns:
        Compact JSON string representation of the AST
    """
    data = ast_to_dict(node)
    return json.dumps(data, indent=indent, cls=CompactJSONEncoder)
