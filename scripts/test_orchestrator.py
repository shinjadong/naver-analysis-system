#!/usr/bin/env python3
"""
Campaign Orchestrator 테스트 스크립트

Usage:
    python scripts/test_orchestrator.py
    python scripts/test_orchestrator.py --quick
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.campaign_orchestrator import (
    CampaignOrchestrator,
    CampaignScheduler,
    TaskExecutor,
    OrchestratorConfig,
    ExecutionContext,
)
from src.shared.campaign_orchestrator.scheduler import TaskPriority, TaskStatus
from src.shared.campaign_orchestrator.executor import ExecutionResult
from src.shared.project_manager import ProjectManager, Project


async def test_scheduler():
    """스케줄러 테스트"""
    print("\n" + "=" * 60)
    print("1. Scheduler Test")
    print("=" * 60)

    scheduler = CampaignScheduler(
        daily_quota=100,
        hourly_quota=20,
        cooldown_sec=10
    )

    # 작업 스케줄링
    tasks = []
    for i in range(5):
        task = await scheduler.schedule_task(
            task_type="engagement",
            payload={
                "keyword": f"테스트키워드{i+1}",
                "persona_id": f"persona_0{i+1}"
            },
            priority=TaskPriority.NORMAL,
            delay_sec=i * 2
        )
        tasks.append(task)
        print(f"  Scheduled: {task.task_id} at {task.scheduled_at.strftime('%H:%M:%S')}")

    # 통계
    stats = scheduler.get_stats()
    print(f"\n  Queue size: {stats['queue_size']}")
    print(f"  Remaining daily: {stats['remaining_daily']}")
    print(f"  Remaining hourly: {stats['remaining_hourly']}")

    # 작업 실행 시뮬레이션
    print("\n  Executing tasks:")
    executed = 0
    while executed < 3:
        task = await scheduler.get_next_task()
        if task:
            print(f"    Got task: {task.task_id} ({task.payload['keyword']})")
            await scheduler.complete_task(task.task_id, success=True)
            executed += 1
        else:
            await asyncio.sleep(0.5)

    stats = scheduler.get_stats()
    print(f"\n  Completed: {stats['total_completed']}")


async def test_executor():
    """실행기 테스트"""
    print("\n" + "=" * 60)
    print("2. Executor Test")
    print("=" * 60)

    from src.shared.campaign_orchestrator.executor import create_executor_with_defaults

    executor = create_executor_with_defaults(
        timeout_sec=60,
        max_concurrent=3
    )

    # 커스텀 핸들러 추가
    async def custom_handler(ctx: ExecutionContext) -> ExecutionResult:
        print(f"    [Custom] Handling: {ctx.keyword}")
        await asyncio.sleep(0.1)
        return ExecutionResult(
            success=True,
            context=ctx,
            data={"custom": True}
        )

    executor.register_handler("custom", custom_handler)

    # 기본 핸들러 테스트
    context1 = ExecutionContext(
        execution_id="exec_001",
        task_id="task_001",
        task_type="engagement",
        keyword="강남맛집",
        persona_id="persona_01"
    )

    print(f"\n  Testing engagement handler:")
    result1 = await executor.execute(context1)
    print(f"    Success: {result1.success}")
    print(f"    Duration: {result1.duration_ms}ms")

    # 커스텀 핸들러 테스트
    context2 = ExecutionContext(
        execution_id="exec_002",
        task_id="task_002",
        task_type="custom",
        keyword="홍대카페",
        persona_id="persona_02"
    )

    print(f"\n  Testing custom handler:")
    result2 = await executor.execute(context2)
    print(f"    Success: {result2.success}")
    print(f"    Data: {result2.data}")

    # 통계
    stats = executor.get_stats()
    print(f"\n  Executor stats:")
    print(f"    Total executions: {stats['total_executions']}")
    print(f"    Successful: {stats['successful']}")
    print(f"    Avg duration: {stats['avg_duration_ms']}ms")


async def test_orchestrator_standalone():
    """오케스트레이터 독립 테스트"""
    print("\n" + "=" * 60)
    print("3. Orchestrator Standalone Test")
    print("=" * 60)

    config = OrchestratorConfig.for_testing()
    orchestrator = CampaignOrchestrator(config=config)

    # 콜백 등록
    async def on_task_complete(result: ExecutionResult):
        print(f"    Task completed: {result.context.task_id} (success={result.success})")

    orchestrator.on_task_complete(on_task_complete)

    # 통계
    stats = orchestrator.get_stats()
    print(f"\n  Initial stats:")
    print(f"    Campaigns: {stats['campaigns']['total']}")
    print(f"    Scheduler queue: {stats['scheduler']['queue_size']}")


async def test_full_integration():
    """전체 통합 테스트"""
    print("\n" + "=" * 60)
    print("4. Full Integration Test")
    print("=" * 60)

    # 프로젝트 매니저 설정
    pm = ProjectManager(db_path="data/test_orchestrator.db")

    # 테스트 프로젝트 생성
    project = pm.create_project(
        name="오케스트레이터 테스트",
        description="통합 테스트용 프로젝트",
        targets=[
            {"keyword": "강남맛집", "title": "강남 맛집 베스트10"},
            {"keyword": "홍대카페", "title": "홍대 카공 카페"},
            {"keyword": "이태원맛집", "title": "이태원 브런치"},
        ],
        daily_quota=5
    )

    # 페르소나 할당
    project.assign_persona("persona_01")
    project.assign_persona("persona_02")
    project.assign_device("R3CT3001XXX")
    pm.update_project(project)

    print(f"  Created project: {project.project_id}")
    print(f"  Targets: {len(project.targets)}")

    # 오케스트레이터 설정
    config = OrchestratorConfig.for_testing()
    config.schedule.daily_quota = 5
    config.schedule.active_hours = list(range(0, 24))  # 모든 시간 활성화

    orchestrator = CampaignOrchestrator(config=config)

    # 모듈 등록
    await orchestrator.register_modules(project_manager=pm)

    # 결과 추적
    results = []

    async def track_result(result: ExecutionResult):
        results.append(result)

    orchestrator.on_task_complete(track_result)

    # 캠페인 실행
    print(f"\n  Starting campaign...")
    campaign_id = await orchestrator.execute_campaign(project.project_id)

    # 결과 확인
    state = orchestrator.get_campaign_state(campaign_id)
    print(f"\n  Campaign: {campaign_id}")
    print(f"  Status: {state.status.value}")
    print(f"  Total tasks: {state.total_tasks}")
    print(f"  Completed: {state.completed_tasks}")
    print(f"  Failed: {state.failed_tasks}")
    print(f"  Success rate: {state.success_rate:.1f}%")

    # 프로젝트 확인
    updated_project = pm.get_project(project.project_id)
    print(f"\n  Project progress: {updated_project.progress:.1f}%")

    return orchestrator


async def test_config_presets():
    """설정 프리셋 테스트"""
    print("\n" + "=" * 60)
    print("5. Config Presets Test")
    print("=" * 60)

    presets = [
        ("Default", OrchestratorConfig.default()),
        ("Testing", OrchestratorConfig.for_testing()),
        ("Production", OrchestratorConfig.for_production()),
    ]

    for name, config in presets:
        print(f"\n  {name}:")
        print(f"    Execution mode: {config.execution.mode.value}")
        print(f"    Max concurrent: {config.execution.max_concurrent}")
        print(f"    Daily quota: {config.schedule.daily_quota}")
        print(f"    IP rotation: {config.resource.ip_rotation}")


async def main():
    parser = argparse.ArgumentParser(description="Orchestrator Test")
    parser.add_argument("--quick", action="store_true", help="Quick test only")
    args = parser.parse_args()

    print("=" * 60)
    print("  CAMPAIGN ORCHESTRATOR TEST SUITE")
    print("=" * 60)

    # 1. 스케줄러
    await test_scheduler()

    # 2. 실행기
    await test_executor()

    # 3. 오케스트레이터 독립
    await test_orchestrator_standalone()

    if not args.quick:
        # 4. 전체 통합
        await test_full_integration()

    # 5. 설정 프리셋
    await test_config_presets()

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
