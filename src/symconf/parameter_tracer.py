"""Parameter chain tracing module for **kwargs analysis."""

import ast
import importlib
import inspect
import textwrap
from collections import defaultdict
from typing import Any, Callable, Dict, Optional, Type

from .exceptions import CircularKwargsChainError
from .utils import OBJECT_TYPE, import_object


class ParameterChainTracer:
    """Traces parameter chains through **kwargs passing for validation and help display."""

    def trace_parameter_chain(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Trace parameter chain through kwargs passing.

        Args:
            obj: Object to trace parameter chain for

        Returns:
            Dict mapping object names to their parameter signatures  # (nested dict structure)
        """
        # Initialize tracing state
        self._current_chain = []
        return self._trace_recursive(obj)

    def get_all_parameters(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Any]]:
        """Get all parameters in the parameter chain.

        Args:
            obj: Object to get parameters for
        Returns:
            Dict mapping parameter names to their informations  # (parameter name -> parameter metadata)
        """
        param_chain = self.trace_parameter_chain(obj)
        all_params = {}  # Dict[str, Dict[str, Any]] (parameter name -> parameter info)

        # Child class parameters should take precedence over parent class parameters
        for obj_name, signature in param_chain.items():
            # Only add parameters that don't already exist (first occurrence wins)
            for param_name, param_info in signature.items():
                if param_name not in all_params:
                    all_params[param_name] = param_info
        return all_params

    def format_help_display(self, obj: OBJECT_TYPE) -> str:
        """Format parameter chain for help display.

        Args:
            obj: Object to display help for

        Returns:
            Formatted help string showing parameter chain  # (multi-line string for console output)
        """
        param_chain = self.trace_parameter_chain(obj)
        lines = []  # List[str] (formatted lines for display)

        # Process each object in the parameter chain
        for i, (obj_name, signature) in enumerate(param_chain.items()):
            # Format object name
            if i == 0:
                lines.append(f"{obj_name}:")
            else:
                lines.append(f"→ {obj_name}:")

            # Format parameters for this object
            for param_name, param_info in signature.items():
                if param_info["kind"] == inspect.Parameter.VAR_KEYWORD:
                    continue  # Skip **kwargs

                param_line = f"    {param_name}"

                # Add type annotation
                if param_info["annotation"] != inspect.Parameter.empty:
                    type_str = self._format_type_for_display(param_info["annotation"])
                    param_line += f"({type_str}"

                    # Add default value
                    if param_info["default"] != inspect.Parameter.empty:
                        default_str = self._format_default_for_display(param_info["default"])
                        param_line += f", default={default_str}"

                    param_line += ")"

                # Add docstring if available
                docstring = self._get_parameter_docstring(obj, param_name)
                if docstring:
                    param_line += f": {docstring}"

                lines.append(param_line)

        return "\n".join(lines)

    def _trace_recursive(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Recursively trace parameter chain.

        Args:
            obj: Object to trace

        Returns:
            Parameter chain mapping  # (nested dict with object signatures)
        """
        obj_name = self._get_object_full_name(obj)

        # Prevent infinite loops
        if obj_name in self._current_chain:
            raise CircularKwargsChainError(self._current_chain, obj_name)

        self._current_chain.append(obj_name)  # Track chain for cycle detection

        chain = {}  # Dict[str, Dict[str, Dict[str, Any]]] (object name -> parameter signatures)
        signature = self._get_object_signature(obj)
        chain[obj_name] = signature

        # Find callees called with **kwargs in the object's implementation
        callee_to_hardcodeds = KwargsTargetResolver().get_kwargs_targets(obj)

        # Process each resolved kwargs target
        for callee, hardcoded_args in callee_to_hardcodeds.items():
            # Trace the target callable
            target_chain = self._trace_recursive(callee)

            # Filter out hardcoded parameters from the traced chain
            callee_name = next(iter(target_chain.keys()))
            for hardcoded_arg in hardcoded_args:
                target_chain[callee_name].pop(hardcoded_arg, None)

            chain.update(target_chain)

        # Cleanup: remove from tracking
        self._current_chain.pop()
        return chain

    def _get_object_signature(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Any]]:
        """Get object signature.

        Args:
            obj: Object to get signature for

        Returns:
            Dict mapping parameter names to parameter info  # (parameter name -> parameter metadata)
        """
        # Determine the function to inspect
        if inspect.isclass(obj):
            func = obj.__init__
        elif inspect.ismethod(obj) or inspect.isfunction(obj):
            func = obj
        else:
            return {}

        # Extract signature information
        sig = inspect.signature(func)
        result = {}  # Dict[str, Dict[str, Any]] (parameter name -> parameter info)

        # Process each parameter
        for index, (name, param) in enumerate(sig.parameters.items()):
            if index == 0 and name in ["self", "cls"]:
                continue
            result[name] = {"annotation": param.annotation, "default": param.default, "kind": param.kind}

        return result

    def _get_object_full_name(self, obj: OBJECT_TYPE) -> str:
        """Get full name of object.

        Args:
            obj: Object to get name for

        Returns:
            Full name including module  # (module.ClassName format)
        """
        if hasattr(obj, "__module__") and hasattr(obj, "__qualname__"):
            return f"{obj.__module__}.{obj.__qualname__}"
        elif hasattr(obj, "__name__"):
            return obj.__name__
        else:
            return str(obj)

    def _get_object_display_name(self, obj: OBJECT_TYPE) -> str:
        """Get display name for object.

        Args:
            obj: Object to get display name for

        Returns:
            Display name for error messages  # (formatted name for user display)
        """
        if hasattr(obj, "__name__") and hasattr(obj, "__module__"):
            return f"{obj.__module__}.{obj.__name__}"
        elif hasattr(obj, "__name__"):
            return obj.__name__
        return str(obj)

    def _format_type_for_display(self, type_annotation: Any) -> str:
        """Format type annotation for display.

        Args:
            type_annotation: Type annotation to format

        Returns:
            Formatted type string  # (human-readable type string)
        """
        if type_annotation in (int, float, str, bool):
            return type_annotation.__name__
        elif hasattr(type_annotation, "__name__"):
            return type_annotation.__name__
        else:
            return str(type_annotation)

    def _format_default_for_display(self, default_value: Any) -> str:
        """Format default value for display.

        Args:
            default_value: Default value to format

        Returns:
            Formatted default string  # (human-readable default value)
        """
        if isinstance(default_value, str):
            return f"'{default_value}'"
        else:
            return str(default_value)

    def _get_parameter_docstring(self, obj: OBJECT_TYPE, param_name: str) -> Optional[str]:
        """Get docstring for a parameter.

        Args:
            obj: Object containing the parameter
            param_name: Name of the parameter

        Returns:
            Parameter docstring if found, None otherwise  # (extracted parameter documentation)
        """
        try:
            # Get the function to inspect
            if inspect.isclass(obj):
                func = obj.__init__
            elif inspect.ismethod(obj) or inspect.isfunction(obj):
                func = obj
            else:
                return None

            docstring = inspect.getdoc(func)
            if not docstring:
                return None

            # Simple docstring parsing for Args section
            # This is a basic implementation - could be enhanced with proper docstring parsing
            lines = docstring.split("\n")
            in_args_section = False

            # Parse docstring to find parameter descriptions
            for line in lines:
                line = line.strip()
                if line.startswith("Args:"):
                    in_args_section = True
                    continue
                elif line and not line.startswith(" ") and in_args_section:
                    # End of args section
                    break
                elif in_args_section and line.startswith(f"{param_name}"):
                    # Found parameter documentation
                    # Extract description after colon
                    if ":" in line:
                        return line.split(":", 1)[1].strip()

            return None
        except Exception:
            return None


class KwargsTargetResolver(ast.NodeVisitor):
    """AST visitor to find **kwargs calls and resolve their targets directly."""

    def get_kwargs_targets(self, obj: OBJECT_TYPE) -> dict[Callable, set[str]]:
        """Get the resolved method/functions the **kwargs passed to, and hardcoded arguments in the method/functions call.

        Returns:
            dict mapping resolved callee function that kwargs passed to, to hardcoded arguments during the call
        """
        # Set source
        self.source_obj = obj
        self.source_class = self._infer_source_class()

        # Parse the source code to find **kwargs calls
        self.callee_to_hardcodeds: dict[Callable, set[str]] = defaultdict(set)
        self._parse_source_function(obj)

        return self.callee_to_hardcodeds

    def _infer_source_class(self) -> Optional[Type[Any]]:
        """Infer the context class from the given object.

        Returns:
            Inferred context class or None
        """
        if inspect.isclass(self.source_obj):
            return self.source_obj
        elif inspect.ismethod(self.source_obj) or inspect.isfunction(self.source_obj):
            # Try to get the class that defines this method
            if hasattr(self.source_obj, "__qualname__") and "." in self.source_obj.__qualname__:
                class_name = self.source_obj.__qualname__.rsplit(".", 1)[0]
                module = inspect.getmodule(self.source_obj)
                if module and hasattr(module, class_name):
                    return getattr(module, class_name)
        return None

    def _parse_source_function(self, obj: OBJECT_TYPE) -> None:
        """Parse the source function for **kwargs calls.

        Args:
            obj (OBJECT_TYPE): Object to parse
        """
        # Determine the function to analyze
        if inspect.isclass(obj):
            func = obj.__init__
        elif inspect.ismethod(obj) or inspect.isfunction(obj):
            func = obj
        else:
            return

        # Try to get the source code
        try:
            source = inspect.getsource(func)
        except (TypeError, OSError):
            # Cannot get source code for built-in functions or compiled code
            return

        # Remove common leading whitespace to fix indentation
        source = textwrap.dedent(source)

        # Try to parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # Cannot parse source code
            return

        # Find and resolve kwargs calls using AST visitor
        self.visit(tree)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit call nodes to find **kwargs calls and resolve their targets.

        Args:
            node: AST call node to analyze
        """
        # Check for **kwargs in the call
        has_kwargs = any(
            keyword.arg is None  # **kwargs
            for keyword in node.keywords
        )

        if has_kwargs:  # there is a **kwargs in the function call
            # Collect hardcoded arguments for all **kwargs calls
            hardcoded_args = set()  # Set[str] (names of hardcoded arguments)
            for keyword in node.keywords:
                if hasattr(keyword, "arg") and keyword.arg is not None:
                    # This is a hardcoded argument (not **kwargs)
                    hardcoded_args.add(keyword.arg)

            # Try to identify and resolve the target of the call
            if isinstance(node.func, ast.Name):
                # Direct function call: func(**kwargs)
                resolved_callee = self._resolve_function_call(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Method call: obj.method(**kwargs) or super().method_name(**kwargs)
                if isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name):
                    if node.func.value.func.id == "super":
                        # super(...).method_name(**kwargs) call
                        resolved_callee = self._resolve_super_method_call(node.func.value, node.func.attr)
                else:
                    # Regular method call: obj.method(**kwargs) or self.method(**kwargs)
                    resolved_callee = self._resolve_regular_method_call(node.func)

            # Store resolved callee with its hardcoded arguments.
            # Note: If the same callee is encountered again, merge the hardcoded arguments.
            self.callee_to_hardcodeds[resolved_callee] |= hardcoded_args

        self.generic_visit(node)

    def _resolve_function_call(self, function_name: str) -> OBJECT_TYPE:
        """Resolve a function call to an actual callable object.

        Args:
            function_name: Name of the function to resolve

        Returns:
            Resolved function object
        """
        if "." in function_name:
            # Try to import the function if it's a fully qualified name
            return import_object(function_name)
        else:
            # No matter the called function is local or imported in the module, they can be found at the module.
            module = importlib.import_module(self.source_class.__module__)
            return getattr(module, function_name)

    def _resolve_super_method_call(self, super_node: ast.Call, method_name: str) -> OBJECT_TYPE:
        """Resolve a super() method call to an actual callable object.

        Args:
            super_node: AST node representing the super() call
            method_name: Name of the method being called on super()

        Returns:
            Resolved method object or None if resolution fails
        """
        # Handle different super() call patterns
        if len(super_node.args) == 0:
            # super() - use current class context
            target_class = self.source_class
        elif len(super_node.args) == 2 and isinstance(super_node.args[0], ast.Name):
            # super(ClassName, self) - extract the class name
            class_name = super_node.args[0].id
            # Find the class in the MRO of source class
            target_class = None
            for cls in self.source_class.__mro__:
                if cls.__name__ == class_name:
                    target_class = cls
                    break
            if not target_class:
                raise RuntimeError(f"Class '{class_name}' not found in MRO of {self.source_class}")
        else:
            # Unsupported super() call pattern
            raise RuntimeError(
                "Unsupported super() call pattern: only super() or super(ClassName, self) are supported. But got: "
                + ast.dump(super_node)
            )

        # Find the parent class method in MRO
        for base in target_class.__mro__[1:]:  # Skip the target class itself
            if hasattr(base, method_name):
                method = getattr(base, method_name)
                # Return the method itself
                return method

        raise RuntimeError(f"Method '{method_name}' not found in MRO of {target_class}")

    def _resolve_regular_method_call(self, func_node: ast.Attribute) -> Optional[OBJECT_TYPE]:
        """Resolve a regular method call to an actual callable object.

        Args:
            func_node: AST Attribute node representing the method call (e.g., self.method_name)

        Returns:
            Resolved method object or None if resolution fails
        """
        method_name = func_node.attr

        # Handle different types of method calls
        if isinstance(func_node.value, ast.Name):
            # Check for self or cls references
            if func_node.value.id in ("self", "cls"):
                # Method call on self or cls
                if self.source_class:
                    if hasattr(self.source_class, method_name):
                        return getattr(self.source_class, method_name)
            else:
                # Method call on a variable (harder to resolve statically)
                # For now, we'll return None as we can't easily determine the type
                return None
        elif isinstance(func_node.value, ast.Attribute):
            # Nested attribute access (e.g., self.obj.method)
            # This is complex to resolve statically, return None for now
            return None

        return None

    def _find_class_in_mro(self, class_name: str) -> Type[Any]:
        """Find a class by name in the MRO of the context class.

        Args:
            class_name: Name of the class to find

        Returns:
            Found class or None
        """
        # Check if the class name matches any class in the MRO
        for cls in self.source_class.__mro__:
            if cls.__name__ == class_name:
                return cls

        raise ValueError(f"Class '{class_name}' not found in MRO of {self.source_class}")
