"""
Workflow Translator

Translates frontend workflow definitions to Conductor workflow format.
Maps node types to Conductor task types and generates proper task configurations.
"""

from typing import Any, Dict, List
import logging

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
    """

    # Node type to Conductor task type mapping
    NODE_TYPE_MAPPING = {
        "HttpTrigger": None,  # Not a task, provides workflow input
        "Extraction": "SIMPLE",
        "PythonRunner": "SIMPLE",
        "HttpRequest": "HTTP",
        "If": "SWITCH",
    }

    # Worker task names for SIMPLE tasks
    WORKER_TASK_NAMES = {
        "Extraction": "document_extraction",
        "PythonRunner": "python_runner",
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

        if node_type == "Extraction":
            return self._translate_extraction_node(node_id, node_data)
        elif node_type == "PythonRunner":
            return self._translate_python_node(node_id, node_data)
        elif node_type == "HttpRequest":
            return self._translate_http_node(node_id, node_data)
        elif node_type == "If":
            return self._translate_if_node(node_id, node_data, dependency_graph)
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
