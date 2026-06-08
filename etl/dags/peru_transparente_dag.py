"""DAG de Airflow — pipeline diario de Perú Transparente.

Equivalente orquestado del flujo de scripts/run_pipeline.py + etl/build_static.py.
Requiere Airflow; en CI se usa el runner ligero. Cadencias por volatilidad de fuente.
"""
from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
except ImportError:  # permite importar el módulo sin Airflow instalado
    DAG = None  # type: ignore

if DAG is not None:
    default_args = {"retries": 2, "retry_delay": timedelta(minutes=10)}

    with DAG(
        dag_id="peru_transparente_daily",
        schedule="0 9 * * *",  # 04:00 Perú
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=default_args,
        tags=["transparencia", "etl"],
    ) as dag:
        extract = BashOperator(task_id="extract_stage",
                               bash_command="python scripts/run_pipeline.py --source all")
        promote = BashOperator(task_id="promote_core",
                               bash_command="python scripts/promote.py")  # entity resolution + validación
        project = BashOperator(task_id="project_graph",
                               bash_command="python scripts/rebuild_graph.py --incremental")
        refresh = BashOperator(task_id="refresh_analytics",
                               bash_command="python scripts/refresh_views.py")
        build = BashOperator(task_id="build_static",
                             bash_command="python etl/build_static.py")

        extract >> promote >> [project, refresh] >> build
