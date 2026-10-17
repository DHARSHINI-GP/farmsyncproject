import pytest
from farmsync.router.planner import validate_tasks
from farmsync.router.compiler import TaskGraphCompiler


@pytest.mark.parametrize("plan", [{"tasks": ["shell"]}, {"tasks": ["spatial"], "command": "delete"}, {"tasks": "spatial"}, {"tasks": [None]}])
def test_unexecutable_plans_are_rejected(plan):
    with pytest.raises(ValueError):
        validate_tasks(plan)


def test_dynamic_plan_validates_dependencies_without_inventing_identity():
    plan = {"tasks": ["advisory", "spatial", "trust"], "source": "test_constrained_plan", "usage": {}}
    graph = TaskGraphCompiler().compile("Inspect Survey 384", plan)
    assert graph.target_survey_no == "384"
    assert set(graph.nodes) == {"vision", "escalation", "advisory", "spatial", "trust"}
    graph.topological_sort()
    assert graph.nodes["advisory"].deps == ["escalation"]
    assert graph.to_dict()["planner_source"] == "test_constrained_plan"


def test_custom_buffer_is_bounded_and_converted_to_metres():
    compiler = TaskGraphCompiler()
    assert compiler.extract_buffer_distance("Check a 100m waterbody buffer") == 100
    assert compiler.extract_buffer_distance("Use buffer of 0.2 km") == 200
    with pytest.raises(ValueError):
        compiler.extract_buffer_distance("Use a 10001m buffer")
