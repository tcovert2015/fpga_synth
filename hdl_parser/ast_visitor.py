"""
AST Visitor Pattern for traversing and transforming Verilog AST.

Provides base classes for implementing visitors that can traverse the AST
and perform various operations like analysis, transformation, or code generation.
"""

from __future__ import annotations
from typing import Any, Optional
from fpga_synth.hdl_parser.ast_nodes import *


class ASTVisitor:
    """
    Base class for AST visitors using the visitor pattern.

    Subclasses can override visit_* methods to implement custom behavior
    for specific node types. The default implementation recursively visits
    all children.

    Usage:
        class MyVisitor(ASTVisitor):
            def visit_Module(self, node: Module) -> Any:
                print(f"Visiting module: {node.name}")
                return self.generic_visit(node)

        visitor = MyVisitor()
        visitor.visit(ast)
    """

    def visit(self, node: ASTNode) -> Any:
        """
        Visit a node by dispatching to the appropriate visit_* method.
        """
        if node is None:
            return None

        method_name = f'visit_{node.__class__.__name__}'
        visitor_method = getattr(self, method_name, self.generic_visit)
        return visitor_method(node)

    def generic_visit(self, node: ASTNode) -> Any:
        """
        Default visitor that recursively visits all children.
        Override this to provide default behavior for all nodes.
        """
        # Visit all child nodes
        for field_name in dir(node):
            if field_name.startswith('_'):
                continue

            value = getattr(node, field_name, None)

            # Visit list of nodes
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self.visit(item)

            # Visit single node
            elif isinstance(value, ASTNode):
                self.visit(value)

        return None

    # Convenience methods for visiting lists
    def visit_list(self, nodes: list[ASTNode]) -> list[Any]:
        """Visit a list of nodes and return list of results."""
        return [self.visit(node) for node in nodes]


class ASTTransformer(ASTVisitor):
    """
    Base class for AST transformers that modify the AST.

    Like ASTVisitor, but visitor methods should return a node
    (possibly modified or replaced). If None is returned, the
    node is removed from the tree.

    Usage:
        class RenameIdentifiers(ASTTransformer):
            def visit_Identifier(self, node: Identifier) -> Identifier:
                node.name = node.name.upper()
                return node
    """

    def generic_visit(self, node: ASTNode) -> Optional[ASTNode]:
        """
        Default transformer that recursively transforms all children.
        """
        # Transform all child nodes
        for field_name in dir(node):
            if field_name.startswith('_'):
                continue

            value = getattr(node, field_name, None)

            # Transform list of nodes
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ASTNode):
                        new_item = self.visit(item)
                        if new_item is not None:
                            new_list.append(new_item)
                    else:
                        new_list.append(item)
                setattr(node, field_name, new_list)

            # Transform single node
            elif isinstance(value, ASTNode):
                new_value = self.visit(value)
                setattr(node, field_name, new_value)

        return node


class ASTDumper(ASTVisitor):
    """
    Visitor that dumps the AST structure as formatted text.
    Useful for debugging and understanding the AST structure.
    """

    def __init__(self, indent: str = "  "):
        self.indent = indent
        self.level = 0
        self.output = []

    def dump(self, node: ASTNode) -> str:
        """Dump the AST and return as string."""
        self.output = []
        self.level = 0
        self.visit(node)
        return "\n".join(self.output)

    def generic_visit(self, node: ASTNode) -> Any:
        """Dump this node and recursively dump children."""
        indent_str = self.indent * self.level
        node_type = node.__class__.__name__

        # Get important attributes to display
        attrs = []
        if hasattr(node, 'name') and isinstance(node.name, str):
            attrs.append(f"name='{node.name}'")
        if hasattr(node, 'op') and isinstance(node.op, str):
            attrs.append(f"op='{node.op}'")
        if hasattr(node, 'value') and not isinstance(node.value, ASTNode):
            value_str = str(node.value)
            if len(value_str) > 30:
                value_str = value_str[:27] + "..."
            attrs.append(f"value={value_str}")

        attr_str = f" ({', '.join(attrs)})" if attrs else ""
        self.output.append(f"{indent_str}{node_type}{attr_str}")

        # Visit children with increased indentation
        self.level += 1
        super().generic_visit(node)
        self.level -= 1

        return None


class ModuleCollector(ASTVisitor):
    """
    Visitor that collects all modules in the AST.
    """

    def __init__(self):
        self.modules = []

    def visit_Module(self, node: Module) -> Any:
        self.modules.append(node)
        return self.generic_visit(node)


class IdentifierCollector(ASTVisitor):
    """
    Visitor that collects all identifier names used in the AST.
    """

    def __init__(self):
        self.identifiers = set()

    def visit_Identifier(self, node: Identifier) -> Any:
        self.identifiers.add(node.name)
        return None


class StatisticsVisitor(ASTVisitor):
    """
    Visitor that collects statistics about the AST.
    """

    def __init__(self):
        self.node_counts = {}
        self.total_nodes = 0

    def generic_visit(self, node: ASTNode) -> Any:
        node_type = node.__class__.__name__
        self.node_counts[node_type] = self.node_counts.get(node_type, 0) + 1
        self.total_nodes += 1
        return super().generic_visit(node)

    def report(self) -> str:
        """Generate a statistics report."""
        lines = [f"Total nodes: {self.total_nodes}"]
        lines.append("\nNode type counts:")
        for node_type in sorted(self.node_counts.keys()):
            count = self.node_counts[node_type]
            lines.append(f"  {node_type}: {count}")
        return "\n".join(lines)


class AlwaysBlockCollector(ASTVisitor):
    """
    Visitor that collects all always blocks and categorizes them.
    """

    def __init__(self):
        self.combinational = []  # always @(*)
        self.sequential = []     # always @(posedge clk)
        self.other = []

    def visit_AlwaysBlock(self, node: AlwaysBlock) -> Any:
        if node.is_star:
            self.combinational.append(node)
        elif any(item.edge in ('posedge', 'negedge') for item in node.sensitivity):
            self.sequential.append(node)
        else:
            self.other.append(node)
        return self.generic_visit(node)
