#!/usr/bin/env python3
"""
NaverSessionPipeline 실행 스크립트

통합 파이프라인을 간단하게 실행합니다.

사용법:
    # 단일 세션 (기본 키워드)
    python scripts/run_pipeline.py

    # 커스텀 키워드
    python scripts/run_pipeline.py --keywords "맛집 추천" "여행 블로그" "IT 뉴스"

    # 여러 세션
    python scripts/run_pipeline.py --sessions 5 --pageviews 3

    # URL 직접 방문
    python scripts/run_pipeline.py --urls "https://blog.naver.com/..." "https://blog.naver.com/..."

    # 상태 확인
    python scripts/run_pipeline.py --status

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "shared"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_pipeline")


# 기본 키워드 목록
DEFAULT_KEYWORDS = [
    "맛집 추천",
    "여행 블로그",
    "IT 뉴스",
    "파이썬 강좌",
    "주식 투자",
    "부동산 정보",
    "건강 관리",
    "운동 루틴",
    "요리 레시피",
    "독서 추천",
]


async def run_status():
    """시스템 상태 확인"""
    from pipeline import NaverSessionPipeline

    print("\n" + "=" * 60)
    print("시스템 상태 확인")
    print("=" * 60)

    pipeline = NaverSessionPipeline()
    status = await pipeline.check_status()

    # 디바이스 상태
    print("\n[디바이스]")
    device = status.get("device", {})
    print(f"  - 루팅: {device.get('is_rooted', 'Unknown')}")
    print(f"  - ANDROID_ID: {device.get('android_id', 'Unknown')}")
    print(f"  - 현재 페르소나: {device.get('current_persona', 'None')}")

    # Portal 상태
    print("\n[DroidRun Portal]")
    portal = status.get("portal", {})
    if portal:
        print(f"  - 설치됨: {portal.get('installed', False)}")
        print(f"  - 버전: {portal.get('version', 'Unknown')}")
        print(f"  - 준비됨: {portal.get('ready', False)}")
    else:
        print("  - Portal 비활성화")

    # 페르소나 통계
    print("\n[페르소나]")
    personas = status.get("personas", {})
    print(f"  - 총 페르소나: {personas.get('total_personas', 0)}")
    print(f"  - 총 세션: {personas.get('total_sessions', 0)}")
    print(f"  - 총 페이지뷰: {personas.get('total_pageviews', 0)}")

    print("\n" + "=" * 60)


async def run_single_session(args):
    """단일 세션 실행"""
    from pipeline import NaverSessionPipeline, PipelineConfig

    print("\n" + "=" * 60)
    print("단일 세션 실행")
    print("=" * 60)

    config = PipelineConfig(
        use_portal=not args.no_portal,
        max_pageviews_per_session=args.pageviews,
        cooldown_minutes=args.cooldown,
    )

    pipeline = NaverSessionPipeline(config=config)

    if args.urls:
        print(f"\nURL 직접 방문 모드")
        print(f"URLs: {args.urls}")
        result = await pipeline.run_session(
            urls=args.urls,
            pageviews=args.pageviews
        )
    else:
        keywords = args.keywords if args.keywords else DEFAULT_KEYWORDS[:args.pageviews]
        print(f"\n키워드 검색 모드")
        print(f"Keywords: {keywords}")
        print(f"Search type: {args.search_type}")

        result = await pipeline.run_session(
            keywords=keywords,
            pageviews=args.pageviews,
            search_type=args.search_type
        )

    # 결과 출력
    print("\n" + "-" * 40)
    print("세션 결과")
    print("-" * 40)
    print(f"성공: {result.success}")
    print(f"페르소나: {result.persona_name} ({result.persona_id[:8]}...)")
    print(f"방문 수: {len(result.visits)}")
    print(f"총 체류시간: {result.total_dwell_time}초")
    print(f"총 스크롤: {result.total_scrolls}회")
    print(f"소요 시간: {result.duration_sec:.1f}초")

    if result.visits:
        print("\n방문 상세:")
        for i, visit in enumerate(result.visits):
            status = "[OK]" if visit.success else "[FAIL]"
            print(f"  {i + 1}. {status} {visit.content_type}: {visit.dwell_time}s, {visit.scroll_count} scrolls")

    print("\n" + "=" * 60)

    return result


async def run_multiple_sessions(args):
    """여러 세션 실행"""
    from pipeline import NaverSessionPipeline, PipelineConfig

    print("\n" + "=" * 60)
    print(f"다중 세션 실행 ({args.sessions}개)")
    print("=" * 60)

    config = PipelineConfig(
        use_portal=not args.no_portal,
        max_pageviews_per_session=args.pageviews,
        cooldown_minutes=args.cooldown,
    )

    pipeline = NaverSessionPipeline(config=config)

    keywords = args.keywords if args.keywords else DEFAULT_KEYWORDS

    results = await pipeline.run_multiple_sessions(
        keywords=keywords,
        sessions=args.sessions,
        pageviews_per_session=args.pageviews,
        search_type=args.search_type,
        session_interval_min=args.interval_min,
        session_interval_max=args.interval_max
    )

    # 결과 요약
    print("\n" + "=" * 60)
    print("전체 결과 요약")
    print("=" * 60)

    successful = sum(1 for r in results if r.success)
    total_visits = sum(len(r.visits) for r in results)
    total_dwell = sum(r.total_dwell_time for r in results)
    total_scrolls = sum(r.total_scrolls for r in results)

    print(f"성공 세션: {successful}/{args.sessions}")
    print(f"총 방문: {total_visits}")
    print(f"총 체류시간: {total_dwell}초 ({total_dwell / 60:.1f}분)")
    print(f"총 스크롤: {total_scrolls}회")

    print("\n세션별 결과:")
    for i, result in enumerate(results):
        status = "[OK]" if result.success else "[FAIL]"
        print(f"  {i + 1}. {status} {result.persona_name}: {len(result.visits)} visits, {result.total_dwell_time}s")

    print("\n" + "=" * 60)

    return results


async def create_personas(args):
    """페르소나 일괄 생성"""
    from persona_manager import PersonaManager

    print("\n" + "=" * 60)
    print(f"페르소나 {args.create_personas}개 생성")
    print("=" * 60)

    manager = PersonaManager()
    personas = manager.create_personas_batch(
        count=args.create_personas,
        name_prefix=args.persona_prefix or "Persona",
        tags=args.tags.split(",") if args.tags else None
    )

    print(f"\n생성된 페르소나:")
    for p in personas:
        print(f"  - {p.name} (ANDROID_ID: {p.android_id[:8]}...)")

    print(f"\n총 {len(personas)}개 생성 완료")
    print("=" * 60)


async def list_personas():
    """페르소나 목록 조회"""
    from persona_manager import PersonaManager

    print("\n" + "=" * 60)
    print("페르소나 목록")
    print("=" * 60)

    manager = PersonaManager()
    personas = manager.get_all_personas()

    if not personas:
        print("\n등록된 페르소나가 없습니다.")
        print("'--create-personas N' 옵션으로 생성하세요.")
    else:
        print(f"\n총 {len(personas)}개 페르소나:")
        print("-" * 80)
        print(f"{'이름':<20} {'상태':<10} {'세션':<8} {'페이지뷰':<10} {'마지막 활동':<20}")
        print("-" * 80)

        for p in personas:
            last_active = p.last_active.strftime("%Y-%m-%d %H:%M")
            print(f"{p.name:<20} {p.status.value:<10} {p.total_sessions:<8} {p.total_pageviews:<10} {last_active:<20}")

    print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="NaverSessionPipeline 실행 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 기본 실행 (3개 키워드, 1세션)
    python run_pipeline.py

    # 커스텀 키워드로 실행
    python run_pipeline.py --keywords "맛집" "여행" "IT"

    # 5개 세션, 세션당 3개 페이지뷰
    python run_pipeline.py --sessions 5 --pageviews 3

    # URL 직접 방문
    python run_pipeline.py --urls "https://blog.naver.com/..."

    # 페르소나 10개 생성
    python run_pipeline.py --create-personas 10

    # 상태 확인
    python run_pipeline.py --status
        """
    )

    # 기본 옵션
    parser.add_argument("--keywords", nargs="+", help="검색 키워드 목록")
    parser.add_argument("--urls", nargs="+", help="직접 방문할 URL 목록")
    parser.add_argument("--search-type", default="blog", choices=["blog", "news", "cafe"],
                        help="검색 타입 (default: blog)")

    # 세션 옵션
    parser.add_argument("--sessions", type=int, default=1, help="실행할 세션 수 (default: 1)")
    parser.add_argument("--pageviews", type=int, default=3, help="세션당 페이지뷰 수 (default: 3)")
    parser.add_argument("--cooldown", type=int, default=30, help="쿨다운 시간 (분, default: 30)")
    parser.add_argument("--interval-min", type=int, default=5, help="세션 간 최소 간격 (분)")
    parser.add_argument("--interval-max", type=int, default=15, help="세션 간 최대 간격 (분)")

    # Portal 옵션
    parser.add_argument("--no-portal", action="store_true", help="Portal 없이 좌표 기반으로 실행")

    # 페르소나 관리
    parser.add_argument("--create-personas", type=int, metavar="N", help="N개의 페르소나 생성")
    parser.add_argument("--persona-prefix", default="Persona", help="페르소나 이름 접두사")
    parser.add_argument("--tags", help="페르소나 태그 (쉼표 구분)")
    parser.add_argument("--list-personas", action="store_true", help="페르소나 목록 출력")

    # 유틸리티
    parser.add_argument("--status", action="store_true", help="시스템 상태 확인")

    args = parser.parse_args()

    # 실행
    try:
        if args.status:
            await run_status()
        elif args.create_personas:
            await create_personas(args)
        elif args.list_personas:
            await list_personas()
        elif args.sessions > 1:
            await run_multiple_sessions(args)
        else:
            await run_single_session(args)

    except KeyboardInterrupt:
        print("\n\n중단됨.")
        return 1
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
