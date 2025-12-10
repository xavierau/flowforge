"""
Loop Worker for Conductor DO_WHILE Tasks.

Executes loop iterations over an array with n8n-style context variables.
Each iteration provides loop context that can be used by child tasks.

Context Variables (n8n-style):
- $loop.item: Current item being processed
- $loop.index: Current index (0-based)
- $loop.first: Boolean, true if first item
- $loop.last: Boolean, true if last item
- $loop.length: Total array length
"""

from typing import Any, Dict, List, Optional

from .base_worker import BaseWorker


class LoopWorker(BaseWorker):
    """
    Worker that executes loop iterations over an array.

    This worker is designed to work with Conductor's DO_WHILE task type.
    It provides n8n-style loop context variables for child tasks.

    Input Parameters:
    - array: The array to iterate over (required)
    - max_iterations: Maximum iterations allowed (default: 1000)
    - continue_on_error: Continue processing on item failure (default: false)
    - current_index: Current iteration index (managed by Conductor DO_WHILE)

    Output:
    - results: Array of all iteration outputs
    - iteration_count: Number of completed iterations
    - failed_iterations: Array of failed iteration indices
    - loop_context: Current loop context for child tasks

    n8n-style Context:
    - $loop.item: Current item
    - $loop.index: Current index (0-based)
    - $loop.first: Boolean, is first item
    - $loop.last: Boolean, is last item
    - $loop.length: Total array length
    """

    DEFAULT_MAX_ITERATIONS = 1000

    def __init__(self):
        super().__init__(task_definition_name="loop_iterator", poll_interval=1000)

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate loop input parameters."""
        if "array" not in task_input:
            return "Missing required parameter: 'array'"

        array = task_input.get("array")
        if not isinstance(array, list):
            return "Parameter 'array' must be a list/array"

        max_iterations = task_input.get("max_iterations", self.DEFAULT_MAX_ITERATIONS)
        if not isinstance(max_iterations, int) or max_iterations < 1:
            return "Parameter 'max_iterations' must be a positive integer"

        if len(array) > max_iterations:
            return f"Array length ({len(array)}) exceeds max_iterations ({max_iterations})"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute loop iteration logic.

        This worker is called for each iteration of the DO_WHILE loop.
        It provides context for the current iteration and tracks results.

        Args:
            task_input: Contains array, max_iterations, continue_on_error,
                        and current_index from previous iteration

        Returns:
            Dictionary with loop context and iteration state
        """
        array = task_input["array"]
        max_iterations = task_input.get("max_iterations", self.DEFAULT_MAX_ITERATIONS)
        continue_on_error = task_input.get("continue_on_error", False)
        current_index = task_input.get("current_index", 0)

        # Track results from previous iterations
        results = task_input.get("results", [])
        failed_iterations = task_input.get("failed_iterations", [])

        # Check if we've processed all items
        if current_index >= len(array):
            self.log_info(
                f"Loop completed: {len(results)} successful, "
                f"{len(failed_iterations)} failed out of {len(array)} items"
            )
            return {
                "results": results,
                "iteration_count": len(results),
                "failed_iterations": failed_iterations,
                "completed": True,
                "continue_loop": False,
                "loop_context": None,
            }

        # Check max iterations limit
        if current_index >= max_iterations:
            self.log_warning(
                f"Loop terminated: max_iterations ({max_iterations}) reached"
            )
            return {
                "results": results,
                "iteration_count": len(results),
                "failed_iterations": failed_iterations,
                "completed": False,
                "terminated_reason": "max_iterations_exceeded",
                "continue_loop": False,
                "loop_context": None,
            }

        # Get current item
        current_item = array[current_index]
        array_length = len(array)

        # Build n8n-style loop context
        loop_context = {
            "item": current_item,
            "index": current_index,
            "first": current_index == 0,
            "last": current_index == array_length - 1,
            "length": array_length,
        }

        self.log_info(
            f"Loop iteration {current_index + 1}/{array_length} "
            f"(first={loop_context['first']}, last={loop_context['last']})"
        )

        return {
            "results": results,
            "iteration_count": len(results),
            "failed_iterations": failed_iterations,
            "completed": False,
            "continue_loop": True,
            "loop_context": loop_context,
            # Provide flat access for easy expression usage
            "current_item": current_item,
            "current_index": current_index,
            "next_index": current_index + 1,
            "is_first": current_index == 0,
            "is_last": current_index == array_length - 1,
            "array_length": array_length,
        }

    def add_iteration_result(
        self,
        results: List[Any],
        failed_iterations: List[int],
        current_index: int,
        result: Any,
        success: bool
    ) -> Dict[str, Any]:
        """
        Add result from completed iteration.

        This is a utility method for updating loop state after
        each iteration's child tasks complete.

        Args:
            results: Current list of successful results
            failed_iterations: Current list of failed iteration indices
            current_index: Index of completed iteration
            result: Result from the iteration
            success: Whether iteration succeeded

        Returns:
            Updated state with new result added
        """
        if success:
            results.append({
                "index": current_index,
                "result": result,
            })
        else:
            failed_iterations.append(current_index)

        return {
            "results": results,
            "failed_iterations": failed_iterations,
        }
