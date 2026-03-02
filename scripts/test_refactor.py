#!/usr/bin/env python3
"""
테스트 스크립트 - 모듈화 버전 간단 확인

사용법:
    python scripts/test_refactor.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def test_imports():
    """모듈 import 테스트"""
    print("=== 모듈 Import 테스트 ===")

    try:
        from src.campaign.refactor import (
            CampaignAction,
            ActionResult,
            ActionRegistry,
            PipelineEngine,
            CampaignRunner,
        )
        print("✓ Core 모듈 import 성공")

        from src.campaign.refactor.actions import (
            PersonaSelectorAction,
            AndroidIdSetterAction,
            CookieCleanerAction,
            IpRotatorAction,
            CdpNavigatorAction,
            DwellSimulatorAction,
            SupabaseLoggerAction,
        )
        print("✓ Actions 모듈 import 성공")

        print("\n사용 가능한 액션:")
        for action_class in [
            PersonaSelectorAction,
            AndroidIdSetterAction,
            CookieCleanerAction,
            IpRotatorAction,
            CdpNavigatorAction,
            DwellSimulatorAction,
            SupabaseLoggerAction,
        ]:
            print(f"  - {action_class.__name__}")

        print("\n✅ 모든 모듈 정상 로드!")
        return True

    except Exception as e:
        print(f"\n❌ Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yaml_load():
    """YAML 캠페인 파일 로드 테스트"""
    print("\n=== YAML 로드 테스트 ===")

    try:
        import yaml
        yaml_file = PROJECT_ROOT / "src/campaign/refactor/campaigns/blog_boost.yaml"

        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print(f"캠페인 이름: {config['name']}")
        print(f"버전: {config['version']}")
        print(f"파이프라인 수: {len(config['pipelines'])}")
        print("\n파이프라인 목록:")
        for pipeline in config['pipelines']:
            print(f"  - {pipeline['name']}: {len(pipeline['actions'])}개 액션")

        print("\n✅ YAML 로드 성공!")
        return True

    except Exception as e:
        print(f"\n❌ YAML 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_registry():
    """액션 레지스트리 테스트"""
    print("\n=== 액션 레지스트리 테스트 ===")

    try:
        from src.campaign.refactor.core import ActionRegistry
        from src.campaign.refactor.actions import PersonaSelectorAction

        registry = ActionRegistry()
        registry.register_action("persona_selector", PersonaSelectorAction)

        action = registry.get_action("persona_selector")
        print(f"✓ 액션 등록 및 조회 성공: {action.name}")

        actions = registry.list_actions()
        print(f"✓ 등록된 액션 목록: {actions}")

        print("\n✅ 액션 레지스트리 정상 작동!")
        return True

    except Exception as e:
        print(f"\n❌ 레지스트리 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_campaign_runner_init():
    """캠페인 러너 초기화 테스트"""
    print("\n=== 캠페인 러너 초기화 테스트 ===")

    try:
        from src.campaign.refactor.campaigns import CampaignRunner

        yaml_file = PROJECT_ROOT / "src/campaign/refactor/campaigns/blog_boost.yaml"
        runner = CampaignRunner(str(yaml_file))

        print(f"✓ 캠페인 로드: {runner.campaign_config['name']}")
        print(f"✓ 등록된 액션: {runner.registry.list_actions()}")
        print(f"✓ 등록된 파이프라인: {list(runner.pipeline_engine.pipelines.keys())}")

        print("\n✅ 캠페인 러너 초기화 성공!")
        return True

    except Exception as e:
        print(f"\n❌ 캠페인 러너 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("  모듈화 캠페인 프레임워크 테스트")
    print("="*60 + "\n")

    tests = [
        ("Import", test_imports),
        ("YAML 로드", test_yaml_load),
        ("액션 레지스트리", test_action_registry),
        ("캠페인 러너 초기화", test_campaign_runner_init),
    ]

    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))

    print("\n" + "="*60)
    print("  테스트 결과 요약")
    print("="*60)

    for name, success in results:
        status = "✅ 통과" if success else "❌ 실패"
        print(f"  {status}: {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print(f"\n  총 {total}개 테스트 중 {passed}개 통과")
    print("="*60 + "\n")

    if passed == total:
        print("🎉 모든 테스트 통과! 실행 준비 완료.\n")
        print("실행 예시:")
        print("  python scripts/boost_campaign_refactor.py --status")
        print("  python scripts/boost_campaign_refactor.py --target 1")
    else:
        print("⚠️  일부 테스트 실패. 위 에러 메시지를 확인하세요.\n")


if __name__ == "__main__":
    main()
