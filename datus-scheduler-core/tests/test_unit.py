from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
from datus_scheduler_core import (
    AirflowConfig,
    BaseSchedulerAdapter,
    JobRun,
    JobStatus,
    ListJobsResult,
    ListRunsResult,
    RunStatus,
    ScheduledJob,
    SchedulerAdapterRegistry,
    SchedulerConnectionConfig,
    SchedulerJobPayload,
)


class FakeSchedulerAdapter(BaseSchedulerAdapter):
    def platform_name(self) -> str:
        return "fake"

    def test_connection(self) -> bool:
        return True

    def submit_job(self, payload: SchedulerJobPayload) -> ScheduledJob:
        return ScheduledJob(
            scheduler_name=self.config.name,
            platform=self.platform_name(),
            job_id=payload.job_name,
            job_name=payload.job_name,
        )

    def trigger_job(self, job_id: str, conf: Optional[Dict[str, Any]] = None) -> JobRun:
        return JobRun(run_id="run-1", job_id=job_id, status=RunStatus.RUNNING, result=conf)

    def pause_job(self, job_id: str) -> None:
        return None

    def resume_job(self, job_id: str) -> None:
        return None

    def delete_job(self, job_id: str) -> None:
        return None

    def update_job(self, job_id: str, payload: SchedulerJobPayload) -> ScheduledJob:
        return ScheduledJob(
            scheduler_name=self.config.name,
            platform=self.platform_name(),
            job_id=job_id,
            job_name=payload.job_name,
        )

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        return None

    def list_jobs(
        self,
        project: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ListJobsResult:
        return ListJobsResult(items=[], total=0)

    def get_job_run(self, job_id: str, run_id: str) -> Optional[JobRun]:
        return None

    def list_job_runs(
        self,
        job_id: str,
        status: Optional[RunStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ListRunsResult:
        return ListRunsResult(items=[], total=0)


def test_scheduler_connection_config_defaults() -> None:
    config = SchedulerConnectionConfig(
        name="local",
        type="airflow",
        api_base_url="http://localhost:8080/api/v1",
    )

    assert config.timeout_seconds == 30
    assert config.extra == {}


def test_airflow_config_resolves_project_scoped_dags_folder() -> None:
    config = AirflowConfig(
        name="airflow",
        type="airflow",
        api_base_url="http://localhost:8080/api/v1",
        username="admin",
        password="admin",
        dags_folder_root="/opt/airflow/dags",
        project_name="analytics",
    )

    assert config.dags_folder == "/opt/airflow/dags/analytics"
    assert config.dag_id_prefix == ""


@pytest.mark.parametrize("project_name", [".", "..", ".hidden", "foo..bar"])
def test_airflow_config_rejects_unsafe_project_names(project_name: str) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        AirflowConfig(
            name="airflow",
            type="airflow",
            api_base_url="http://localhost:8080/api/v1",
            username="admin",
            password="admin",
            dags_folder_root="/opt/airflow/dags",
            project_name=project_name,
        )


def test_scheduler_models_preserve_defaults_and_extras() -> None:
    payload = SchedulerJobPayload(
        job_name="daily report",
        sql="select 1",
        db_type="duckdb",
        db_connection={"database": ":memory:"},
    )
    job = ScheduledJob(
        scheduler_name="airflow",
        platform="airflow",
        job_id="daily_report",
        job_name=payload.job_name,
        status=JobStatus.ACTIVE,
        locator={"dag_id": "daily_report"},
    )
    result = ListJobsResult(items=[job], total=1, next_page_token="ignored-by-core")

    assert payload.timezone == "UTC"
    assert payload.extra == {}
    assert result.items == [job]
    assert result.total == 1
    assert result.model_extra == {"next_page_token": "ignored-by-core"}


def test_registry_registers_and_creates_adapter() -> None:
    config = SchedulerConnectionConfig(
        name="fake-prod",
        type="fake",
        api_base_url="http://scheduler.local",
    )

    SchedulerAdapterRegistry.reset()
    try:
        SchedulerAdapterRegistry.register(
            "Fake",
            FakeSchedulerAdapter,
            SchedulerConnectionConfig,
            display_name="Fake Scheduler",
        )

        adapter = SchedulerAdapterRegistry.create_adapter(" fake ", config)
        metadata = SchedulerAdapterRegistry.get_metadata("FAKE")

        assert isinstance(adapter, FakeSchedulerAdapter)
        assert adapter.api_base_url == "http://scheduler.local"
        assert SchedulerAdapterRegistry.is_registered("FAKE")
        assert metadata is not None
        assert metadata.display_name == "Fake Scheduler"
    finally:
        SchedulerAdapterRegistry.reset()
