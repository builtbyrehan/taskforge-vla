import io
from contextlib import redirect_stdout
from dataclasses import asdict, is_dataclass

import streamlit as st

from taskforge.orchestration.task_runner import TaskRunner
from taskforge.recovery.failure_injector import FailureInjector
from taskforge.robot.arm import ArmController
from taskforge.simulation.mujoco_backend import MujocoBackend
from taskforge.world_model.observer import WorldObserver

MODEL_PATH = "models/scene.xml"

st.set_page_config(
    page_title="TaskForge VLA",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .tf-card {
            border: 1px solid rgba(128,128,128,.25);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            margin-bottom: .7rem;
            background: rgba(128,128,128,.04);
        }
        .tf-title {
            font-size: 2.15rem;
            font-weight: 750;
            margin-bottom: .15rem;
        }
        .tf-subtitle {
            opacity: .72;
            margin-bottom: 1.25rem;
        }
        .tf-success {
            border-left: 5px solid #22c55e;
        }
        .tf-fail {
            border-left: 5px solid #ef4444;
        }
        .tf-warn {
            border-left: 5px solid #f59e0b;
        }
        .tf-muted {
            opacity: .7;
            font-size: .9rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.20);
            border-radius: 12px;
            padding: .65rem .8rem;
            background: rgba(128,128,128,.03);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def to_jsonable(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def build_runtime(inject_failure: bool):
    backend = MujocoBackend(MODEL_PATH)

    left_arm = ArmController(
        backend=backend,
        name="left",
        shoulder_position=[-0.35, 0.0, 0.53],
        elbow_sign=1,
    )

    right_arm = ArmController(
        backend=backend,
        name="right",
        shoulder_position=[0.35, 0.0, 0.53],
        elbow_sign=-1,
    )

    arms = {
        "left_arm": left_arm,
        "right_arm": right_arm,
    }

    observer = WorldObserver(
        backend=backend,
        scenario_id="streamlit_demo_v1",
    )

    failure_injector = None
    if inject_failure:
        failure_injector = FailureInjector(
            fail_step_ids={"a3"},
            fail_once=True,
        )

    runner = TaskRunner(
        observer=observer,
        arms=arms,
        viewer=None,
        failure_injector=failure_injector,
        max_recovery_attempts=2,
    )

    return backend, observer, runner


def world_object_rows(world):
    rows = []
    if world is None:
        return rows

    objects = getattr(world, "objects", {}) or {}

    for name, obj in objects.items():
        position = getattr(obj, "position", None)
        if position is not None:
            try:
                position = [round(float(x), 3) for x in position]
            except Exception:
                pass

        rows.append(
            {
                "Object": name,
                "Position": position,
                "Grasped by": getattr(obj, "grasped_by", None) or "—",
                "Graspable": getattr(obj, "graspable", "—"),
            }
        )

    return rows


def robot_rows(world):
    rows = []
    if world is None:
        return rows

    robots = getattr(world, "robots", {}) or {}

    for name, robot in robots.items():
        position = getattr(robot, "ee_position", None)
        if position is None:
            position = getattr(robot, "position", None)

        if position is not None:
            try:
                position = [round(float(x), 3) for x in position]
            except Exception:
                pass

        rows.append(
            {
                "Robot": name,
                "Status": getattr(robot, "status", "—"),
                "Gripper": getattr(robot, "gripper", "—"),
                "EE position": position,
            }
        )

    return rows


def plan_rows(plan):
    if plan is None:
        return []

    rows = []
    for step in getattr(plan, "steps", []) or []:
        rows.append(
            {
                "Step": step.id,
                "Actor": step.actor,
                "Action": step.action,
                "Target": step.target or "—",
                "Position": step.position if step.position is not None else "—",
                "Depends on": ", ".join(step.depends_on) if step.depends_on else "—",
            }
        )

    return rows


if "last_run" not in st.session_state:
    st.session_state.last_run = None


st.markdown('<div class="tf-title">TaskForge VLA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tf-subtitle">'
    "Language-guided bimanual manipulation with planning, validation, "
    "execution, verification, and recovery."
    "</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Demo controls")

    demo_instruction = st.selectbox(
        "Example task",
        [
            "Pick both blocks",
            "Move the red block to the left side of the blue one",
            "Put the red block to the right of the blue block",
            "Put the red block near the blue one",
        ],
    )

    inject_failure = st.checkbox(
        "Simulate recoverable failure",
        value=False,
        help=(
            "For the multi-pick demo, TaskForge will force step a3 to fail "
            "once and then demonstrate closed-loop recovery."
        ),
    )

    st.caption(
        "Tip: use “Pick both blocks” with failure simulation enabled "
        "to show the Phase 13 recovery flow."
    )

    if st.button("Clear dashboard", use_container_width=True):
        st.session_state.last_run = None
        st.rerun()


left, right = st.columns([4, 1])

with left:
    instruction = st.text_input(
        "Natural-language task",
        value=demo_instruction,
        placeholder="e.g. Pick both blocks",
    )

with right:
    st.write("")
    st.write("")
    run_clicked = st.button(
        "Run Task",
        type="primary",
        use_container_width=True,
    )


if run_clicked:
    clean_instruction = instruction.strip()

    if not clean_instruction:
        st.warning("Enter a task first.")
    else:
        logs = io.StringIO()

        with st.spinner("TaskForge is interpreting, planning, and executing..."):
            try:
                with redirect_stdout(logs):
                    backend, observer, runner = build_runtime(inject_failure)

                    # Let the simulated scene settle before observation.
                    backend.run_for(1.0, None)

                    result = runner.run(clean_instruction)
                    final_world = observer.observe()

                st.session_state.last_run = {
                    "instruction": clean_instruction,
                    "failure_mode": inject_failure,
                    "result": result,
                    "world": final_world,
                    "logs": logs.getvalue(),
                    "error": None,
                }

            except Exception as exc:
                st.session_state.last_run = {
                    "instruction": clean_instruction,
                    "failure_mode": inject_failure,
                    "result": None,
                    "world": None,
                    "logs": logs.getvalue(),
                    "error": str(exc),
                }


run_data = st.session_state.last_run

if run_data is None:
    st.info(
        "Enter a task and press **Run Task**. "
        "The dashboard will show the interpreted goal, plan, world state, "
        "execution result, and recovery outcome."
    )
    st.stop()


if run_data["error"]:
    st.markdown(
        '<div class="tf-card tf-fail"><b>Runtime error</b><br>'
        + run_data["error"]
        + "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Execution log", expanded=True):
        st.code(run_data["logs"] or "No log output.", language="text")

    st.stop()


result = run_data["result"]
world = run_data["world"]

status = getattr(result, "status", "UNKNOWN")
success = bool(getattr(result, "success", False))
source = getattr(result, "interpretation_source", None) or "—"
plan = getattr(result, "plan", None)
execution_result = getattr(result, "execution_result", None)
verification_result = getattr(result, "verification_result", None)

status_class = "tf-success" if success else "tf-fail"
status_icon = "✅" if success else "❌"

st.markdown(
    f'<div class="tf-card {status_class}">'
    f"<b>{status_icon} {status}</b><br>"
    f'{getattr(result, "message", "")}'
    f"</div>",
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Interpretation", source)

with m2:
    st.metric(
        "Plan steps",
        len(getattr(plan, "steps", []) or []),
    )

with m3:
    if status == "RECOVERY_SUCCESS":
        execution_label = "Recovered"
    elif execution_result is None:
        execution_label = "—"
    else:
        execution_label = "Passed" if execution_result.success else "Failed"

    st.metric("Execution", execution_label)

with m4:
    if verification_result is None:
        verification_label = "—"
    else:
        verification_label = (
            "Satisfied" if verification_result.satisfied else "Not satisfied"
        )

    st.metric("Goal", verification_label)


overview_tab, plan_tab, world_tab, logs_tab = st.tabs(
    ["Overview", "Generated plan", "World state", "Execution log"]
)


with overview_tab:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Pipeline")

        pipeline = [
            ("Interpretation", source != "—"),
            ("Planning", plan is not None),
            (
                "Execution",
                execution_result is not None and execution_result.success
            ),
            (
                "Final verification",
                verification_result is not None,
            ),
        ]

        for name, done in pipeline:
            st.write(("✅" if done else "○") + f"  {name}")

        if run_data["failure_mode"]:
            if status == "RECOVERY_SUCCESS":
                st.write("✅  Recovery")
            else:
                st.write("⚠️  Recovery mode enabled")

    with c2:
        st.subheader("Parsed goal")
        goal = getattr(result, "goal", None)

        if goal is None:
            st.caption("No parsed goal available.")
        else:
            st.json(to_jsonable(goal))


with plan_tab:
    st.subheader("Symbolic plan")

    rows = plan_rows(plan)
    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No plan was required or generated.")


with world_tab:
    st.subheader("Objects")
    object_rows = world_object_rows(world)

    if object_rows:
        st.dataframe(
            object_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No object state available.")

    st.subheader("Robots")
    robots = robot_rows(world)

    if robots:
        st.dataframe(
            robots,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No robot state available.")


with logs_tab:
    st.subheader("TaskForge execution trace")
    st.code(
        run_data["logs"] or "No log output.",
        language="text",
    )
