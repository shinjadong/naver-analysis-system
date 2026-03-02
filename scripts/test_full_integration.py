#!/usr/bin/env python3
"""
Full Integration Test

모든 모듈 통합 테스트:
- PersonaGenerator
- ProjectManager
- CampaignOrchestrator
- EventBus (Core)

Usage:
    python scripts/test_full_integration.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.core.events import EventBus, Event, EventType
from src.shared.core.registry import ModuleRegistry
from src.shared.persona_generator import (
    PersonaGenerator,
    PersonaGeneratorConfig,
    GeneratedPersona
)
from src.shared.project_manager import (
    ProjectManager,
    Project,
    ProjectDashboard
)
from src.shared.campaign_orchestrator import (
    CampaignOrchestrator,
    OrchestratorConfig
)
from src.shared.campaign_orchestrator.executor import ExecutionResult


async def setup_event_bus() -> EventBus:
    """이벤트 버스 설정"""
    print("\n[1] Setting up EventBus...")

    event_bus = EventBus.get_instance()
    await event_bus.start()

    # 이벤트 핸들러 등록
    event_count = {"persona": 0, "execution": 0}

    async def persona_handler(event: Event):
        event_count["persona"] += 1
        print(f"    [EVENT] Persona created: {event.data.get('persona_id')}")

    async def execution_handler(event: Event):
        event_count["execution"] += 1

    event_bus.subscribe(EventType.PERSONA_CREATED, persona_handler)
    event_bus.subscribe(EventType.EXECUTION_COMPLETED, execution_handler)
    event_bus.subscribe(EventType.EXECUTION_FAILED, execution_handler)

    print("    EventBus started with handlers")
    return event_bus


async def setup_project_manager() -> ProjectManager:
    """프로젝트 매니저 설정"""
    print("\n[2] Setting up ProjectManager...")

    pm = ProjectManager(db_path="data/integration_test.db")

    # 테스트 프로젝트 생성
    project = pm.create_project(
        name="통합 테스트 캠페인",
        description="PersonaGenerator + Orchestrator 통합 테스트",
        targets=[
            {"keyword": "강남맛집", "title": "강남역 맛집 베스트 10", "target_clicks": 1},
            {"keyword": "홍대카페", "title": "홍대 인스타 핫플 카페", "target_clicks": 1},
            {"keyword": "이태원맛집", "title": "이태원 브런치 맛집", "target_clicks": 1},
        ],
        daily_quota=20
    )

    print(f"    Created project: {project.project_id}")
    print(f"    Targets: {len(project.targets)}")

    return pm


async def generate_personas(
    event_bus: EventBus,
    pm: ProjectManager
) -> tuple:
    """페르소나 생성"""
    print("\n[3] Generating Personas...")

    # 샘플 키워드 파일 생성
    keywords_file = Path("data/integration_keywords.csv")
    keywords_file.parent.mkdir(parents=True, exist_ok=True)

    keywords_content = """keyword,volume,difficulty,category
강남맛집,15000,75,food
강남카페,12000,70,food
홍대맛집,13000,72,food
홍대카페,11000,68,food
이태원맛집,9000,65,food
이태원브런치,7000,60,food
성수동맛집,8000,63,food
성수카페,10000,67,food
연남동맛집,7500,62,food
연남동카페,9500,66,food
판교맛집,6000,55,food
분당카페,5500,52,food
서울여행,18000,80,travel
서울호텔,12000,75,travel
서울데이트,14000,78,lifestyle
"""
    keywords_file.write_text(keywords_content, encoding='utf-8')

    # 페르소나 생성기 설정
    config = PersonaGeneratorConfig(
        persona_count=5,
        integration=PersonaGeneratorConfig().integration
    )
    config.integration.publish_events = True

    generator = PersonaGenerator(config=config, event_bus=event_bus)
    generator.set_project_manager(pm)

    # 페르소나 생성
    result = await generator.generate_from_file(
        str(keywords_file),
        persona_count=5
    )

    print(f"    Generated {result.personas_created} personas")
    print(f"    Clusters: {result.clusters_created}")

    # 페르소나 정보 출력
    for p in result.personas:
        print(f"      - {p.name} ({p.archetype.value}): {len(p.keywords)} keywords")

    # 프로젝트에 페르소나 할당
    project = pm.list_projects()[0]
    for persona in result.personas:
        project.assign_persona(persona.persona_id)
    project.assign_device("TEST_DEVICE_001")
    pm.update_project(project)

    return generator, result.personas


async def run_campaign(
    event_bus: EventBus,
    pm: ProjectManager,
    personas: list
) -> CampaignOrchestrator:
    """캠페인 실행"""
    print("\n[4] Running Campaign...")

    # 오케스트레이터 설정
    config = OrchestratorConfig.for_testing()
    config.schedule.daily_quota = 5
    config.schedule.active_hours = list(range(0, 24))  # 테스트용 - 항상 활성
    config.execution.cooldown_sec = 1  # 빠른 테스트를 위해 쿨다운 최소화

    orchestrator = CampaignOrchestrator(config=config, event_bus=event_bus)
    await orchestrator.register_modules(project_manager=pm)

    # 결과 추적
    results = []

    async def track_result(result: ExecutionResult):
        results.append(result)
        status = "SUCCESS" if result.success else "FAILED"
        print(f"    [{status}] Task: {result.context.keyword}")

    orchestrator.on_task_complete(track_result)

    # 캠페인 실행
    project = pm.list_projects()[0]
    print(f"    Starting campaign for: {project.name}")

    campaign_id = await orchestrator.execute_campaign(
        project.project_id,
        personas=personas
    )

    # 결과 요약
    state = orchestrator.get_campaign_state(campaign_id)
    print(f"\n    Campaign completed: {campaign_id}")
    print(f"    Status: {state.status.value}")
    print(f"    Success rate: {state.success_rate:.1f}%")

    return orchestrator


async def show_dashboard(pm: ProjectManager):
    """대시보드 표시"""
    print("\n[5] Project Dashboard")
    print("=" * 60)

    project = pm.list_projects()[0]
    dashboard = ProjectDashboard(project)
    data = dashboard.generate()

    print(data.to_ascii())


async def show_statistics(
    pm: ProjectManager,
    orchestrator: CampaignOrchestrator
):
    """통계 표시"""
    print("\n[6] Statistics Summary")
    print("=" * 60)

    # 프로젝트 통계
    project = pm.list_projects()[0]
    stats = pm.get_project_stats(project.project_id)

    print(f"\n  Project Stats:")
    print(f"    Total executions: {stats.total_executions}")
    print(f"    Success rate: {stats.success_rate:.1f}%")
    print(f"    Avg dwell time: {stats.avg_dwell_time:.0f}s")
    print(f"    Personas used: {stats.total_personas_used}")

    # 오케스트레이터 통계
    orch_stats = orchestrator.get_stats()
    print(f"\n  Orchestrator Stats:")
    print(f"    Total campaigns: {orch_stats['campaigns']['total']}")
    print(f"    Completed: {orch_stats['campaigns']['completed']}")

    # 스케줄러 통계
    sched_stats = orch_stats['scheduler']
    print(f"\n  Scheduler Stats:")
    print(f"    Total scheduled: {sched_stats['total_scheduled']}")
    print(f"    Total completed: {sched_stats['total_completed']}")

    # 실행기 통계
    exec_stats = orch_stats['executor']
    print(f"\n  Executor Stats:")
    print(f"    Total executions: {exec_stats['total_executions']}")
    print(f"    Successful: {exec_stats['successful']}")
    print(f"    Avg duration: {exec_stats['avg_duration_ms']}ms")


async def test_event_flow(event_bus: EventBus):
    """이벤트 흐름 테스트"""
    print("\n[7] Event Flow Test")
    print("=" * 60)

    # 커스텀 이벤트 발행
    received_events = []

    async def test_handler(event: Event):
        received_events.append(event)

    event_bus.subscribe(EventType.CAMPAIGN_STARTED, test_handler)
    event_bus.subscribe(EventType.CAMPAIGN_COMPLETED, test_handler)

    # 이벤트 발행
    await event_bus.publish(Event(
        event_type=EventType.CAMPAIGN_STARTED,
        source="test",
        data={"campaign_id": "test_001"}
    ))

    await event_bus.publish(Event(
        event_type=EventType.CAMPAIGN_COMPLETED,
        source="test",
        data={"campaign_id": "test_001", "success": True}
    ))

    # 이벤트 처리 대기
    await asyncio.sleep(0.5)

    print(f"  Events published: 2")
    print(f"  Events received: {len(received_events)}")

    for event in received_events:
        print(f"    - {event.event_type.value}: {event.data}")


async def main():
    print("=" * 60)
    print("  FULL INTEGRATION TEST")
    print("  Naver AI Evolution System")
    print("=" * 60)

    start_time = datetime.now()

    try:
        # 1. 이벤트 버스 설정
        event_bus = await setup_event_bus()

        # 2. 프로젝트 매니저 설정
        pm = await setup_project_manager()

        # 3. 페르소나 생성
        generator, personas = await generate_personas(event_bus, pm)

        # 4. 캠페인 실행
        orchestrator = await run_campaign(event_bus, pm, personas)

        # 5. 대시보드 표시
        await show_dashboard(pm)

        # 6. 통계 표시
        await show_statistics(pm, orchestrator)

        # 7. 이벤트 흐름 테스트
        await test_event_flow(event_bus)

        # 이벤트 버스 종료
        await event_bus.stop()

        duration = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print(f"  INTEGRATION TEST COMPLETED")
        print(f"  Duration: {duration:.1f}s")
        print("=" * 60)

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
