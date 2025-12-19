"""
Unit tests for the Workflow Translator service.

Tests cover:
- Node type translation (Extraction, PythonRunner, HttpRequest, If)
- Dependency graph building
- Task ordering (topological sort)
- Input parameter extraction
- Output parameter extraction
- Full workflow translation
"""

import pytest
from app.orchestration.conductor.translator import WorkflowTranslator


class TestWorkflowTranslatorNodeTranslation:
    """Tests for translating individual node types."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_translate_extraction_node(self, translator):
        """
        GIVEN an Extraction node definition with config
        WHEN translating to Conductor
        THEN returns SIMPLE task with document_extraction worker
        """
        node_id = "node_1"
        node_data = {
            "config": {
                "provider": "google",
                "model": "gemini-2.5-flash",
                "processingMode": "batch",
                "schema": {"type": "object", "properties": {}}
            },
            "inputs": {
                "documentId": "{{$('Trigger').output.documentId}}",
            }
        }

        result = translator._translate_extraction_node(node_id, node_data)

        assert result["name"] == "document_extraction"
        assert result["taskReferenceName"] == "extraction_node_1"
        assert result["type"] == "SIMPLE"
        assert "document_id" in result["inputParameters"]
        assert "schema" in result["inputParameters"]
        assert result["inputParameters"]["provider"] == "google"
        assert result["inputParameters"]["model"] == "gemini-2.5-flash"
        assert result["inputParameters"]["processing_mode"] == "batch"

    def test_translate_extraction_node_defaults(self, translator):
        """
        GIVEN an Extraction node with minimal data
        WHEN translating
        THEN uses empty strings for provider/model (worker applies system defaults)
        """
        result = translator._translate_extraction_node("node_2", {})

        assert result["name"] == "document_extraction"
        # Empty strings allow worker to apply system defaults
        assert result["inputParameters"]["provider"] == ""
        assert result["inputParameters"]["model"] == ""
        assert result["inputParameters"]["processing_mode"] == "batch"
        assert result["inputParameters"]["document_id"] == "${workflow.input.documentId}"

    def test_translate_extraction_node_with_workflow_defaults(self, translator):
        """
        GIVEN an Extraction node with no config
        AND workflow-level model defaults are set
        WHEN translating
        THEN uses workflow defaults
        """
        # Set workflow-level defaults
        translator.workflow_definition = {
            "modelDefaults": {
                "extraction": {
                    "provider": "openai",
                    "model": "gpt-4o"
                },
                "markdownConverter": {
                    "converter": "marker",
                    "model": "marker-v2"
                }
            }
        }

        result = translator._translate_extraction_node("node_3", {})

        assert result["inputParameters"]["provider"] == "openai"
        assert result["inputParameters"]["model"] == "gpt-4o"
        assert result["inputParameters"]["markdown_converter"] == "marker"
        assert result["inputParameters"]["markdown_converter_model"] == "marker-v2"

    def test_translate_extraction_node_config_overrides_workflow_defaults(self, translator):
        """
        GIVEN an Extraction node with config
        AND workflow-level model defaults are set
        WHEN translating
        THEN node config takes priority over workflow defaults
        """
        # Set workflow-level defaults
        translator.workflow_definition = {
            "modelDefaults": {
                "extraction": {
                    "provider": "openai",
                    "model": "gpt-4o"
                }
            }
        }

        node_data = {
            "config": {
                "provider": "google",
                "model": "gemini-2.5-flash"
            }
        }

        result = translator._translate_extraction_node("node_4", node_data)

        # Node config should override workflow defaults
        assert result["inputParameters"]["provider"] == "google"
        assert result["inputParameters"]["model"] == "gemini-2.5-flash"

    def test_translate_extraction_node_with_markdown_settings(self, translator):
        """
        GIVEN an Extraction node with markdown converter settings
        WHEN translating
        THEN includes markdown converter parameters
        """
        node_data = {
            "config": {
                "provider": "google",
                "model": "gemini-2.5-flash",
                "processingMode": "streaming",
                "markdownConverter": "docling",
                "markdownConverterModel": "docling-v1"
            }
        }

        result = translator._translate_extraction_node("node_5", node_data)

        assert result["inputParameters"]["processing_mode"] == "streaming"
        assert result["inputParameters"]["markdown_converter"] == "docling"
        assert result["inputParameters"]["markdown_converter_model"] == "docling-v1"

    def test_translate_python_runner_node(self, translator):
        """
        GIVEN a PythonRunner node definition
        WHEN translating
        THEN returns SIMPLE task with python_runner worker
        """
        node_id = "py_node"
        node_data = {
            "inputs": {
                "code": "result = input_data.get('value', 0) * 2",
                "inputData": {"value": 10},
                "timeout": 60
            }
        }

        result = translator._translate_python_node(node_id, node_data)

        assert result["name"] == "python_runner"
        assert result["taskReferenceName"] == "python_py_node"
        assert result["type"] == "SIMPLE"
        assert result["inputParameters"]["code"] == "result = input_data.get('value', 0) * 2"
        assert result["inputParameters"]["timeout"] == 60

    def test_translate_python_runner_node_defaults(self, translator):
        """
        GIVEN a PythonRunner node with minimal data
        WHEN translating
        THEN uses default values
        """
        result = translator._translate_python_node("py_default", {})

        assert result["inputParameters"]["code"] == ""
        assert result["inputParameters"]["input_data"] == {}
        assert result["inputParameters"]["timeout"] == 30

    def test_translate_http_request_node(self, translator):
        """
        GIVEN an HttpRequest node definition
        WHEN translating
        THEN returns HTTP task with proper configuration
        """
        node_id = "http_node"
        node_data = {
            "inputs": {
                "url": "https://api.example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"data": "test"},
                "timeout": 45
            }
        }

        result = translator._translate_http_node(node_id, node_data)

        assert result["name"] == "http_request"
        assert result["taskReferenceName"] == "http_http_node"
        assert result["type"] == "HTTP"
        assert result["inputParameters"]["http_request"]["uri"] == "https://api.example.com/webhook"
        assert result["inputParameters"]["http_request"]["method"] == "POST"
        assert result["inputParameters"]["http_request"]["headers"]["Content-Type"] == "application/json"
        assert result["inputParameters"]["http_request"]["connectionTimeOut"] == 45000  # ms
        assert result["inputParameters"]["http_request"]["readTimeOut"] == 45000

    def test_translate_http_request_node_defaults(self, translator):
        """
        GIVEN an HttpRequest node with minimal data
        WHEN translating
        THEN uses default values
        """
        result = translator._translate_http_node("http_default", {})

        assert result["inputParameters"]["http_request"]["method"] == "GET"
        assert result["inputParameters"]["http_request"]["uri"] == ""
        assert result["inputParameters"]["http_request"]["connectionTimeOut"] == 30000

    def test_translate_if_node(self, translator):
        """
        GIVEN an If node definition
        WHEN translating
        THEN returns SWITCH task
        """
        node_id = "condition_1"
        node_data = {
            "inputs": {
                "condition": "extraction_node_1.output.confidence > 0.7"
            }
        }

        result = translator._translate_if_node(node_id, node_data, {})

        assert result["name"] == "condition_switch"
        assert result["taskReferenceName"] == "if_condition_1"
        assert result["type"] == "SWITCH"
        assert result["evaluatorType"] == "value-param"
        assert "decisionCases" in result
        assert "true" in result["decisionCases"]
        assert "false" in result["decisionCases"]


class TestWorkflowTranslatorDependencyGraph:
    """Tests for building dependency graph from edges."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_build_dependency_graph_simple(self, translator):
        """
        GIVEN simple linear edges A -> B -> C
        WHEN building dependency graph
        THEN returns correct dependencies
        """
        edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"}
        ]

        graph = translator._build_dependency_graph(edges)

        assert graph["B"] == ["A"]
        assert graph["C"] == ["B"]
        assert "A" not in graph  # A has no dependencies

    def test_build_dependency_graph_branching(self, translator):
        """
        GIVEN branching edges A -> B, A -> C
        WHEN building dependency graph
        THEN both B and C depend on A
        """
        edges = [
            {"source": "A", "target": "B"},
            {"source": "A", "target": "C"}
        ]

        graph = translator._build_dependency_graph(edges)

        assert graph["B"] == ["A"]
        assert graph["C"] == ["A"]

    def test_build_dependency_graph_converging(self, translator):
        """
        GIVEN converging edges A -> C, B -> C
        WHEN building dependency graph
        THEN C depends on both A and B
        """
        edges = [
            {"source": "A", "target": "C"},
            {"source": "B", "target": "C"}
        ]

        graph = translator._build_dependency_graph(edges)

        assert set(graph["C"]) == {"A", "B"}

    def test_build_dependency_graph_empty(self, translator):
        """
        GIVEN no edges
        WHEN building dependency graph
        THEN returns empty graph
        """
        graph = translator._build_dependency_graph([])

        assert graph == {}


class TestWorkflowTranslatorTaskOrdering:
    """Tests for determining task execution order."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_determine_task_order_linear(self, translator):
        """
        GIVEN linear workflow A -> B -> C
        WHEN determining order
        THEN returns [A, B, C]
        """
        nodes = [
            {"id": "A", "type": "HttpTrigger"},
            {"id": "B", "type": "Extraction"},
            {"id": "C", "type": "PythonRunner"}
        ]
        edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"}
        ]
        dep_graph = translator._build_dependency_graph(edges)
        trigger = nodes[0]

        order = translator._determine_task_order(nodes, dep_graph, trigger)

        # Trigger should be first
        assert order[0]["id"] == "A"
        # B should come before C (B is dependency of C)
        b_index = next(i for i, n in enumerate(order) if n["id"] == "B")
        c_index = next(i for i, n in enumerate(order) if n["id"] == "C")
        assert b_index < c_index

    def test_determine_task_order_with_trigger(self, translator):
        """
        GIVEN workflow with HttpTrigger
        WHEN determining order
        THEN trigger is first
        """
        nodes = [
            {"id": "trigger", "type": "HttpTrigger"},
            {"id": "process", "type": "Extraction"}
        ]
        dep_graph = {"process": ["trigger"]}

        order = translator._determine_task_order(nodes, dep_graph, nodes[0])

        assert order[0]["type"] == "HttpTrigger"

    def test_determine_task_order_no_trigger(self, translator):
        """
        GIVEN workflow without trigger
        WHEN determining order
        THEN orders by dependencies only
        """
        nodes = [
            {"id": "A", "type": "Extraction"},
            {"id": "B", "type": "PythonRunner"}
        ]
        dep_graph = {"B": ["A"]}

        order = translator._determine_task_order(nodes, dep_graph, None)

        # Should still order correctly
        a_index = next(i for i, n in enumerate(order) if n["id"] == "A")
        b_index = next(i for i, n in enumerate(order) if n["id"] == "B")
        assert a_index < b_index


class TestWorkflowTranslatorInputParameters:
    """Tests for extracting input parameters."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_extract_input_parameters_from_trigger(self, translator):
        """
        GIVEN trigger node with input definitions
        WHEN extracting input parameters
        THEN returns list of input keys
        """
        trigger_node = {
            "type": "HttpTrigger",
            "data": {
                "inputs": {
                    "documentId": "${input.documentId}",
                    "schema": "${input.schema}",
                    "tenantId": "${input.tenantId}"
                }
            }
        }

        params = translator._extract_input_parameters(trigger_node)

        assert set(params) == {"documentId", "schema", "tenantId"}

    def test_extract_input_parameters_no_trigger(self, translator):
        """
        GIVEN no trigger node
        WHEN extracting input parameters
        THEN returns empty list
        """
        params = translator._extract_input_parameters(None)

        assert params == []

    def test_extract_input_parameters_empty_inputs(self, translator):
        """
        GIVEN trigger with no inputs
        WHEN extracting input parameters
        THEN returns empty list
        """
        trigger_node = {
            "type": "HttpTrigger",
            "data": {}
        }

        params = translator._extract_input_parameters(trigger_node)

        assert params == []


class TestWorkflowTranslatorOutputParameters:
    """Tests for extracting output parameters."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_extract_output_parameters_final_node(self, translator):
        """
        GIVEN workflow with clear final node
        WHEN extracting output parameters
        THEN includes final node's output
        """
        nodes = [
            {"id": "trigger", "type": "HttpTrigger"},
            {"id": "process", "type": "Extraction"},
            {"id": "finalize", "type": "PythonRunner"}
        ]
        edges = [
            {"source": "trigger", "target": "process"},
            {"source": "process", "target": "finalize"}
        ]

        outputs = translator._extract_output_parameters(nodes, edges)

        # finalize has no outgoing edges
        assert "finalize_output" in outputs

    def test_extract_output_parameters_multiple_finals(self, translator):
        """
        GIVEN workflow with multiple final nodes (branches)
        WHEN extracting output parameters
        THEN includes all final nodes
        """
        nodes = [
            {"id": "trigger", "type": "HttpTrigger"},
            {"id": "branch1", "type": "PythonRunner"},
            {"id": "branch2", "type": "HttpRequest"}
        ]
        edges = [
            {"source": "trigger", "target": "branch1"},
            {"source": "trigger", "target": "branch2"}
        ]

        outputs = translator._extract_output_parameters(nodes, edges)

        assert "branch1_output" in outputs
        assert "branch2_output" in outputs

    def test_extract_output_parameters_excludes_trigger(self, translator):
        """
        GIVEN workflow where trigger is last (no edges)
        WHEN extracting output parameters
        THEN excludes HttpTrigger
        """
        nodes = [
            {"id": "trigger", "type": "HttpTrigger"}
        ]
        edges = []

        outputs = translator._extract_output_parameters(nodes, edges)

        assert "trigger_output" not in outputs


class TestWorkflowTranslatorFullTranslation:
    """Tests for full workflow translation."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_translate_simple_workflow(self, translator):
        """
        GIVEN a simple linear workflow
        WHEN translating to Conductor
        THEN produces valid Conductor workflow definition
        """
        workflow_def = {
            "description": "Simple extraction workflow",
            "nodes": [
                {
                    "id": "trigger",
                    "type": "HttpTrigger",
                    "data": {
                        "inputs": {"documentId": "${input.documentId}"}
                    }
                },
                {
                    "id": "extract",
                    "type": "Extraction",
                    "data": {
                        "inputs": {
                            "documentId": "{{$('trigger').output.documentId}}",
                            "provider": "google"
                        }
                    }
                }
            ],
            "edges": [
                {"source": "trigger", "target": "extract"}
            ]
        }

        result = translator.translate(workflow_def, "test_workflow", 1)

        # Check workflow metadata
        assert result["name"] == "test_workflow"
        assert result["version"] == 1
        assert result["schemaVersion"] == 2
        assert result["restartable"] is True

        # Check tasks
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["name"] == "document_extraction"

        # Check input parameters
        assert "documentId" in result["inputParameters"]

    def test_translate_workflow_with_python_runner(self, translator):
        """
        GIVEN workflow with Extraction and PythonRunner
        WHEN translating
        THEN both tasks are present in order
        """
        workflow_def = {
            "nodes": [
                {"id": "trigger", "type": "HttpTrigger", "data": {"inputs": {}}},
                {"id": "extract", "type": "Extraction", "data": {"inputs": {}}},
                {"id": "process", "type": "PythonRunner", "data": {
                    "inputs": {"code": "return data"}
                }}
            ],
            "edges": [
                {"source": "trigger", "target": "extract"},
                {"source": "extract", "target": "process"}
            ]
        }

        result = translator.translate(workflow_def, "extraction_pipeline")

        task_names = [t["name"] for t in result["tasks"]]
        assert "document_extraction" in task_names
        assert "python_runner" in task_names

    def test_translate_workflow_with_http_request(self, translator):
        """
        GIVEN workflow with HttpRequest node
        WHEN translating
        THEN HTTP task is present
        """
        workflow_def = {
            "nodes": [
                {"id": "trigger", "type": "HttpTrigger", "data": {"inputs": {}}},
                {"id": "webhook", "type": "HttpRequest", "data": {
                    "inputs": {"url": "https://webhook.site/test", "method": "POST"}
                }}
            ],
            "edges": [
                {"source": "trigger", "target": "webhook"}
            ]
        }

        result = translator.translate(workflow_def, "webhook_workflow")

        http_task = next((t for t in result["tasks"] if t["type"] == "HTTP"), None)
        assert http_task is not None
        assert http_task["inputParameters"]["http_request"]["method"] == "POST"

    def test_translate_workflow_with_condition(self, translator):
        """
        GIVEN workflow with If node
        WHEN translating
        THEN SWITCH task is present
        """
        workflow_def = {
            "nodes": [
                {"id": "trigger", "type": "HttpTrigger", "data": {"inputs": {}}},
                {"id": "extract", "type": "Extraction", "data": {"inputs": {}}},
                {"id": "check", "type": "If", "data": {
                    "inputs": {"condition": "confidence > 0.7"}
                }}
            ],
            "edges": [
                {"source": "trigger", "target": "extract"},
                {"source": "extract", "target": "check"}
            ]
        }

        result = translator.translate(workflow_def, "conditional_workflow")

        switch_task = next((t for t in result["tasks"] if t["type"] == "SWITCH"), None)
        assert switch_task is not None
        assert "decisionCases" in switch_task

    def test_translate_empty_workflow(self, translator):
        """
        GIVEN workflow with only trigger
        WHEN translating
        THEN produces valid workflow with no tasks
        """
        workflow_def = {
            "nodes": [
                {"id": "trigger", "type": "HttpTrigger", "data": {"inputs": {}}}
            ],
            "edges": []
        }

        result = translator.translate(workflow_def, "empty_workflow")

        assert result["name"] == "empty_workflow"
        assert result["tasks"] == []


class TestWorkflowTranslatorNodeTypeMapping:
    """Tests for node type mapping constants."""

    def test_node_type_mapping_values(self):
        """
        GIVEN WorkflowTranslator
        THEN NODE_TYPE_MAPPING contains expected mappings
        """
        mapping = WorkflowTranslator.NODE_TYPE_MAPPING

        assert mapping["HttpTrigger"] is None
        assert mapping["Extraction"] == "SIMPLE"
        assert mapping["PythonRunner"] == "SIMPLE"
        assert mapping["HttpRequest"] == "HTTP"
        assert mapping["If"] == "SWITCH"

    def test_worker_task_names(self):
        """
        GIVEN WorkflowTranslator
        THEN WORKER_TASK_NAMES contains expected task names
        """
        task_names = WorkflowTranslator.WORKER_TASK_NAMES

        assert task_names["Extraction"] == "document_extraction"
        assert task_names["PythonRunner"] == "python_runner"


class TestWorkflowTranslatorUnknownNode:
    """Tests for handling unknown node types."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_translate_unknown_node_returns_none(self, translator):
        """
        GIVEN a node with unknown type
        WHEN translating
        THEN returns None
        """
        node = {
            "id": "unknown",
            "type": "UnknownType",
            "data": {}
        }

        result = translator._translate_node(node, {})

        assert result is None

    def test_translate_workflow_skips_unknown_nodes(self, translator):
        """
        GIVEN workflow with unknown node type
        WHEN translating
        THEN skips the unknown node
        """
        workflow_def = {
            "nodes": [
                {"id": "trigger", "type": "HttpTrigger", "data": {"inputs": {}}},
                {"id": "unknown", "type": "UnknownType", "data": {}},
                {"id": "extract", "type": "Extraction", "data": {"inputs": {}}}
            ],
            "edges": [
                {"source": "trigger", "target": "unknown"},
                {"source": "unknown", "target": "extract"}
            ]
        }

        result = translator.translate(workflow_def, "skip_unknown")

        # Only extraction task should be present
        task_names = [t["name"] for t in result["tasks"]]
        assert "document_extraction" in task_names
        assert len(result["tasks"]) == 1


class TestWorkflowTranslatorEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.fixture
    def translator(self):
        return WorkflowTranslator()

    def test_translate_workflow_no_nodes(self, translator):
        """
        GIVEN workflow with no nodes
        WHEN translating
        THEN produces valid empty workflow
        """
        workflow_def = {
            "nodes": [],
            "edges": []
        }

        result = translator.translate(workflow_def, "no_nodes")

        assert result["name"] == "no_nodes"
        assert result["tasks"] == []
        assert result["inputParameters"] == []

    def test_translate_preserves_workflow_version(self, translator):
        """
        GIVEN specific workflow version
        WHEN translating
        THEN version is preserved
        """
        workflow_def = {"nodes": [], "edges": []}

        result = translator.translate(workflow_def, "versioned", 42)

        assert result["version"] == 42

    def test_translate_preserves_description(self, translator):
        """
        GIVEN workflow with description
        WHEN translating
        THEN description is preserved
        """
        workflow_def = {
            "description": "Important workflow description",
            "nodes": [],
            "edges": []
        }

        result = translator.translate(workflow_def, "described")

        assert result["description"] == "Important workflow description"

    def test_translate_default_metadata(self, translator):
        """
        GIVEN workflow
        WHEN translating
        THEN includes default Conductor metadata
        """
        workflow_def = {"nodes": [], "edges": []}

        result = translator.translate(workflow_def, "with_metadata")

        assert result["schemaVersion"] == 2
        assert result["restartable"] is True
        assert result["workflowStatusListenerEnabled"] is True
        assert "ownerEmail" in result
        assert result["timeoutPolicy"] == "ALERT_ONLY"
