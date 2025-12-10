"""
Workflow Translator

Translates frontend workflow definitions to Conductor workflow format.
Maps node types to Conductor task types and generates proper task configurations.
"""

from typing import Any, Dict, List
import logging

from app.models.enums import NodeType

logger = logging.getLogger(__name__)


class WorkflowTranslator:
    """
    Translates frontend workflow JSON to Conductor workflow definition.

    Maps node types:
    - HttpTrigger → START (workflow input)
    - Extraction → SIMPLE task (document_extraction worker)
    - PythonRunner → SIMPLE task (python_runner worker)
    - HttpRequest → HTTP task
    - If → SWITCH task (with condition_evaluator for complex conditions)
    - Loop → DO_WHILE task (loop_iterator worker)
    - LLM → SIMPLE task (llm_completion worker)
    - HumanReview → SIMPLE task (HUMAN_REVIEW worker with IN_PROGRESS pattern)
    """

    # Node type to Conductor task type mapping
    NODE_TYPE_MAPPING = {
        "HttpTrigger": None,  # Not a task, provides workflow input
        "httpTrigger": None,  # Support both cases
        "Extraction": "SIMPLE",
        "extraction": "SIMPLE",
        "PythonRunner": "SIMPLE",
        "pythonRunner": "SIMPLE",
        "HttpRequest": "HTTP",
        "httpRequest": "HTTP",
        "If": "SWITCH",
        "if": "SWITCH",
        "Loop": "DO_WHILE",
        "loop": "DO_WHILE",
        "LLM": "SIMPLE",
        "llm": "SIMPLE",
        "HumanReview": "SIMPLE",
        "humanReview": "SIMPLE",
    }

    # Worker task names for SIMPLE tasks
    WORKER_TASK_NAMES = {
        "Extraction": "document_extraction",
        "extraction": "document_extraction",
        "PythonRunner": "python_runner",
        "pythonRunner": "python_runner",
        "LLM": "llm_completion",
        "llm": "llm_completion",
        "HumanReview": "HUMAN_REVIEW",
        "humanReview": "HUMAN_REVIEW",
    }

    def translate(
        self,
        workflow_definition: Dict[str, Any],
        workflow_name: str,
        workflow_version: int = 1
    ) -> Dict[str, Any]:
        """
        Translate frontend workflow to Conductor format.

        Args:
            workflow_definition: Frontend workflow definition
            workflow_name: Name for the Conductor workflow
            workflow_version: Workflow version

        Returns:
            Conductor workflow definition (JSON)
        """
        nodes = workflow_definition.get("nodes", [])
        edges = workflow_definition.get("edges", [])

        logger.info(f"Translating workflow '{workflow_name}' with {len(nodes)} nodes")

        # Build dependency graph from edges
        dependency_graph = self._build_dependency_graph(edges)

        # Find trigger node (HttpTrigger)
        trigger_node = next((n for n in nodes if n["type"] == "HttpTrigger"), None)

        # Translate nodes to tasks
        tasks = []
        task_order = self._determine_task_order(nodes, dependency_graph, trigger_node)

        for node in task_order:
            if node["type"] == "HttpTrigger":
                continue  # Skip trigger, it provides workflow input

            conductor_task = self._translate_node(node, dependency_graph)
            if conductor_task:
                tasks.append(conductor_task)

        # Build Conductor workflow definition
        conductor_workflow = {
            "name": workflow_name,
            "description": workflow_definition.get("description", ""),
            "version": workflow_version,
            "tasks": tasks,
            "inputParameters": self._extract_input_parameters(trigger_node),
            "outputParameters": self._extract_output_parameters(nodes, edges),
            "schemaVersion": 2,
            "restartable": True,
            "workflowStatusListenerEnabled": True,
            "ownerEmail": "workflow@ai-document-processing.com",
            "timeoutPolicy": "ALERT_ONLY",
            "timeoutSeconds": 0,
        }

        logger.info(f"Translated workflow with {len(tasks)} tasks")

        return conductor_workflow

    def _build_dependency_graph(self, edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build dependency graph from edges.

        Args:
            edges: List of edges with source and target

        Returns:
            Dictionary mapping node IDs to list of dependent node IDs
        """
        graph = {}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")

            if target not in graph:
                graph[target] = []

            graph[target].append(source)

        return graph

    def _determine_task_order(
        self,
        nodes: List[Dict[str, Any]],
        dependency_graph: Dict[str, List[str]],
        trigger_node: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Determine task execution order based on dependencies.

        Args:
            nodes: List of workflow nodes
            dependency_graph: Node dependency graph
            trigger_node: HTTP trigger node

        Returns:
            Ordered list of nodes
        """
        # Simple topological sort for now
        # In production, would handle parallel branches with FORK_JOIN

        ordered = []
        visited = set()

        def visit(node_id: str):
            if node_id in visited:
                return

            # Visit dependencies first
            for dep_id in dependency_graph.get(node_id, []):
                visit(dep_id)

            visited.add(node_id)
            node = next((n for n in nodes if n["id"] == node_id), None)
            if node:
                ordered.append(node)

        # Start from all nodes that have no incoming edges (or just trigger)
        if trigger_node:
            ordered.append(trigger_node)

        for node in nodes:
            if node["type"] != "HttpTrigger":
                visit(node["id"])

        return ordered

    def _translate_node(
        self,
        node: Dict[str, Any],
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Translate a single node to Conductor task.

        Args:
            node: Node definition
            dependency_graph: Dependency graph for input mapping

        Returns:
            Conductor task definition
        """
        node_type = node["type"]
        node_id = node["id"]
        node_data = node.get("data", {})

        # Normalize node type to handle both camelCase and PascalCase
        node_type_lower = node_type.lower()

        if node_type_lower == "extraction":
            return self._translate_extraction_node(node_id, node_data)
        elif node_type_lower == "pythonrunner":
            return self._translate_python_node(node_id, node_data)
        elif node_type_lower == "httprequest":
            return self._translate_http_node(node_id, node_data)
        elif node_type_lower == "if":
            return self._translate_if_node(node_id, node_data, dependency_graph)
        elif node_type_lower == "loop":
            return self._translate_loop_node(node_id, node_data)
        elif node_type_lower == "llm":
            return self._translate_llm_node(node_id, node_data)
        elif node_type_lower == "humanreview":
            return self._translate_human_review_node(node_id, node_data)
        else:
            logger.warning(f"Unknown node type: {node_type}")
            return None

    def _translate_extraction_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Translate Extraction node to SIMPLE task."""
        inputs = node_data.get("inputs", {})

        return {
            "name": "document_extraction",
            "taskReferenceName": f"extraction_{node_id}",
            "type": "SIMPLE",
            "inputParameters": {
                "document_id": inputs.get("documentId", "${workflow.input.documentId}"),
                "schema": inputs.get("schema", {}),
                "provider": inputs.get("provider", "google"),
                "model": inputs.get("model"),
            }
        }

    def _translate_python_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Translate PythonRunner node to SIMPLE task."""
        inputs = node_data.get("inputs", {})

        return {
            "name": "python_runner",
            "taskReferenceName": f"python_{node_id}",
            "type": "SIMPLE",
            "inputParameters": {
                "code": inputs.get("code", ""),
                "input_data": inputs.get("inputData", {}),
                "timeout": inputs.get("timeout", 30),
            }
        }

    def _translate_http_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Translate HttpRequest node to HTTP task."""
        inputs = node_data.get("inputs", {})

        return {
            "name": "http_request",
            "taskReferenceName": f"http_{node_id}",
            "type": "HTTP",
            "inputParameters": {
                "http_request": {
                    "uri": inputs.get("url", ""),
                    "method": inputs.get("method", "GET"),
                    "headers": inputs.get("headers", {}),
                    "body": inputs.get("body"),
                    "connectionTimeOut": inputs.get("timeout", 30) * 1000,
                    "readTimeOut": inputs.get("timeout", 30) * 1000,
                }
            }
        }

    def _translate_if_node(
        self,
        node_id: str,
        node_data: Dict[str, Any],
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Translate If node to SWITCH task."""
        inputs = node_data.get("inputs", {})
        condition = inputs.get("condition", "")

        # For complex conditions, use condition_evaluator worker
        # For simple value-based conditions, use value-param evaluator

        return {
            "name": "condition_switch",
            "taskReferenceName": f"if_{node_id}",
            "type": "SWITCH",
            "evaluatorType": "value-param",
            "expression": "conditionResult",
            "inputParameters": {
                "conditionResult": f"${{{self._get_condition_expression(condition)}}}"
            },
            "decisionCases": {
                "true": [],  # Populated by frontend with connected nodes
                "false": []  # Populated by frontend with connected nodes
            },
            "defaultCase": []
        }

    def _get_condition_expression(self, condition: str) -> str:
        """
        Convert condition to Conductor expression.

        For now, returns the condition as-is.
        In production, would parse and convert to proper Conductor syntax.
        """
        return condition

    def _translate_loop_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate Loop node to Conductor DO_WHILE task.

        The DO_WHILE evaluates condition after each iteration.
        We use it to iterate over array items with n8n-style context.

        Loop node config:
        - arrayExpression: Expression that resolves to array
        - maxIterations: Maximum iterations (default: 1000)
        - continueOnError: Continue on item failure (default: false)

        Args:
            node_id: Unique node identifier
            node_data: Node data containing config

        Returns:
            Conductor DO_WHILE task definition
        """
        config = node_data.get("config", {})
        inputs = node_data.get("inputs", {})

        # Get configuration from either config or inputs
        array_expression = config.get("arrayExpression") or inputs.get("array", "[]")
        max_iterations = config.get("maxIterations") or inputs.get("maxIterations", 1000)
        continue_on_error = config.get("continueOnError") or inputs.get("continueOnError", False)

        return {
            "name": "loop_iterator",
            "taskReferenceName": f"loop_{node_id}",
            "type": "DO_WHILE",
            # Loop condition: continue while current_index < array.length
            "loopCondition": (
                f"if ($.loop_{node_id}['continue_loop'] == true) "
                "{ true; } else { false; }"
            ),
            "loopOver": [],  # Child tasks added during workflow construction
            "inputParameters": {
                "array": array_expression,
                "max_iterations": max_iterations,
                "continue_on_error": continue_on_error,
                # Pass current index from previous iteration
                "current_index": f"${{loop_{node_id}.output.next_index}}",
                # Carry forward results
                "results": f"${{loop_{node_id}.output.results}}",
                "failed_iterations": f"${{loop_{node_id}.output.failed_iterations}}",
            }
        }

    def _translate_llm_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate LLM node to SIMPLE task using llm_completion worker.

        LLM node config:
        - provider: "google" or "openai" (default: "google")
        - model: Model name (e.g., "gemini-2.5-flash", "gpt-4o")
        - prompt: The prompt text (expressions already resolved)
        - systemPrompt: Optional system prompt
        - temperature: 0.0-2.0 (default: 0.7)
        - maxTokens: Maximum output tokens (default: 1024)
        - responseFormat: "json" for JSON output mode

        Args:
            node_id: Unique node identifier
            node_data: Node data containing config

        Returns:
            Conductor SIMPLE task definition for llm_completion worker
        """
        config = node_data.get("config", {})
        inputs = node_data.get("inputs", {})

        # Get configuration from either config or inputs
        provider = config.get("provider") or inputs.get("provider", "google")
        model = config.get("model") or inputs.get("model", "gemini-2.5-flash")
        prompt = config.get("prompt") or inputs.get("prompt", "")
        system_prompt = config.get("systemPrompt") or inputs.get("systemPrompt", "")
        temperature = config.get("temperature") or inputs.get("temperature", 0.7)
        max_tokens = config.get("maxTokens") or inputs.get("maxTokens", 1024)
        response_format = config.get("responseFormat") or inputs.get("responseFormat")

        task_def = {
            "name": "llm_completion",
            "taskReferenceName": f"llm_{node_id}",
            "type": "SIMPLE",
            "inputParameters": {
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        }

        # Only include response_format if specified
        if response_format:
            task_def["inputParameters"]["response_format"] = response_format

        return task_def

    def _translate_human_review_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate HumanReview node to SIMPLE task using HUMAN_REVIEW worker.

        The HumanReviewWorker implements IN_PROGRESS pattern:
        1. Creates ReviewRequest in database
        2. Returns IN_PROGRESS (workflow pauses)
        3. ConductorHITLService completes task when review is submitted
        4. Workflow resumes with corrected_data

        HumanReview node config:
        - instructions: Instructions for the reviewer
        - priority: Review priority ("critical", "high", "normal", "low")
        - confidenceThreshold: Confidence score threshold

        Args:
            node_id: Unique node identifier
            node_data: Node data containing config

        Returns:
            Conductor SIMPLE task definition for HUMAN_REVIEW worker
        """
        config = node_data.get("config", {})
        inputs = node_data.get("inputs", {})

        # Get configuration from either config or inputs
        instructions = config.get("instructions") or inputs.get("instructions", "")
        priority = config.get("priority") or inputs.get("priority", "normal")

        # Build input parameters
        # Note: extraction_job_id and tenant_id should come from workflow input
        # or previous task output
        return {
            "name": "HUMAN_REVIEW",
            "taskReferenceName": f"human_review_{node_id}",
            "type": "SIMPLE",
            "inputParameters": {
                # Required parameters from workflow context
                "extraction_job_id": "${workflow.input.extraction_job_id}",
                "tenant_id": "${workflow.input.tenant_id}",
                # Confidence score from previous extraction task
                # This expression should be updated based on actual workflow structure
                "confidence_score": config.get("confidenceScoreExpression") or (
                    "${previous_task.output.confidence_score}"
                ),
                # Node-specific configuration
                "trigger_reason": "workflow_node",
                "instructions": instructions,
                "priority": priority,
            }
        }

    def _extract_input_parameters(
        self,
        trigger_node: Dict[str, Any]
    ) -> List[str]:
        """Extract input parameters from trigger node."""
        if not trigger_node:
            return []

        inputs = trigger_node.get("data", {}).get("inputs", {})
        return list(inputs.keys())

    def _extract_output_parameters(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Extract output parameters from final nodes.

        Returns outputs from nodes that have no outgoing edges.
        """
        # Find nodes with no outgoing edges
        nodes_with_outgoing = set(edge["source"] for edge in edges)
        final_nodes = [n for n in nodes if n["id"] not in nodes_with_outgoing and n["type"] != "HttpTrigger"]

        output_params = {}

        for node in final_nodes:
            task_ref = f"{node['type'].lower()}_{node['id']}"
            output_params[f"{node['id']}_output"] = f"${{{task_ref}.output.data}}"

        return output_params
