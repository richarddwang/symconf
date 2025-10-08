"""Parameter chain tracing module for **kwargs analysis."""

import inspect
from typing import Any, Callable, Dict, Optional, Type

from .exceptions import CircularKwargsChainError

OBJECT_TYPE = Callable | Type[Any]


class ParameterChainTracer:
    """Traces parameter chains through **kwargs passing for validation and help display."""

    def __init__(self):
        """Initialize parameter chain tracer."""
        pass

    def trace_parameter_chain(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Trace parameter chain through kwargs passing.

        Args:
            obj: Object to trace parameter chain for

        Returns:
            Dict mapping object names to their parameter signatures
        """
        chain = {}
        visited = set()

        def _trace_kwargs(current_obj: OBJECT_TYPE, obj_name: str) -> None:
            # Prevent infinite loops
            if obj_name in visited:
                raise CircularKwargsChainError(list(visited), obj_name)

            visited.add(obj_name)
            signature = self._get_object_signature(current_obj)
            chain[obj_name] = signature

            # Trace through inheritance hierarchy for **kwargs
            if inspect.isclass(current_obj):
                # For classes, check parent classes through MRO
                for base in current_obj.__mro__[1:]:  # Skip self
                    if base is object:  # Skip object base class
                        continue
                    if hasattr(base, "__init__") and base.__init__ is not object.__init__:
                        parent_name = self._get_object_full_name(base)
                        if parent_name not in visited:
                            _trace_kwargs(base, parent_name)

            visited.remove(obj_name)

        obj_name = self._get_object_full_name(obj)
        _trace_kwargs(obj, obj_name)
        return chain

    def get_all_parameters(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Any]]:
        """Get all parameters in the parameter chain.

        Args:
            obj: Object to get parameters for
        Returns:
            Dict mapping parameter names to their informations
        """
        param_chain = self.trace_parameter_chain(obj)
        all_params = {}
        for obj_name, signature in param_chain.items():
            all_params.update(signature)
        return all_params

    def format_help_display(self, obj: OBJECT_TYPE) -> str:
        """Format parameter chain for help display.

        Args:
            obj: Object to display help for

        Returns:
            Formatted help string showing parameter chain
        """
        param_chain = self.trace_parameter_chain(obj, exclude_hardcoded=True)
        lines = []

        for i, (obj_name, signature) in enumerate(param_chain.items()):
            # Format object name
            if i == 0:
                lines.append(f"{obj_name}:")
            else:
                lines.append(f"→ {obj_name}:")

            # Format parameters
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

    def _get_object_signature(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Any]]:
        """Get object signature.

        Args:
            obj: Object to get signature for

        Returns:
            Dict mapping parameter names to parameter info
        """
        try:
            if inspect.isclass(obj):
                func = obj.__init__
            elif inspect.ismethod(obj) or inspect.isfunction(obj):
                func = obj
            else:
                return {}

            sig = inspect.signature(func)
            result = {}

            for name, param in sig.parameters.items():
                if name in ["self", "cls"]:
                    continue
                result[name] = {"annotation": param.annotation, "default": param.default, "kind": param.kind}

            return result
        except Exception:
            return {}

    def _get_object_full_name(self, obj: OBJECT_TYPE) -> str:
        """Get full name of object.

        Args:
            obj: Object to get name for

        Returns:
            Full name including module
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
            Display name for error messages
        """
        if hasattr(obj, "__name__"):
            return obj.__name__
        return str(obj)

    def _format_type_for_display(self, type_annotation: Any) -> str:
        """Format type annotation for display.

        Args:
            type_annotation: Type annotation to format

        Returns:
            Formatted type string
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
            Formatted default string
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
            Parameter docstring if found, None otherwise
        """
        try:
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
