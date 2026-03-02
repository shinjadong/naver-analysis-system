"""
스모크 테스트 - 변경 후 빠른 검증용

실행: pytest tests/smoke/ -v
또는: naver test smoke
"""

import sys
from pathlib import Path
import pytest

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared"))


class TestModuleImports:
    """핵심 모듈 import 테스트"""

    def test_device_tools_import(self):
        """EnhancedAdbTools import"""
        from device_tools import EnhancedAdbTools, AdbConfig
        assert EnhancedAdbTools is not None
        assert AdbConfig is not None

    def test_portal_client_import(self):
        """PortalClient import"""
        from portal_client import PortalClient
        assert PortalClient is not None

    def test_persona_manager_import(self):
        """PersonaManager import"""
        from persona_manager import PersonaManager
        assert PersonaManager is not None

    def test_behavior_injector_import(self):
        """BehaviorInjector import"""
        from device_tools.behavior_injector import BehaviorInjector
        assert BehaviorInjector is not None


class TestCLIImports:
    """CLI 모듈 import 테스트"""

    def test_cli_main_import(self):
        """CLI 메인 모듈 import"""
        from src.shared.cli import main, app
        assert main is not None
        assert app is not None

    def test_cli_commands_import(self):
        """CLI 명령어 모듈 import"""
        from src.shared.cli.commands import run, status, persona, test, debug
        assert run is not None
        assert status is not None


class TestConfigFiles:
    """설정 파일 존재 확인"""

    def test_pyproject_exists(self):
        """pyproject.toml 존재"""
        assert (PROJECT_ROOT / "pyproject.toml").exists()

    def test_readme_exists(self):
        """README.md 존재"""
        assert (PROJECT_ROOT / "README.md").exists()

    def test_execution_flow_exists(self):
        """EXECUTION_FLOW.md 존재"""
        assert (PROJECT_ROOT / "docs" / "EXECUTION_FLOW.md").exists()


class TestBasicFunctionality:
    """기본 기능 테스트 (모킹)"""

    def test_adb_config_creation(self):
        """AdbConfig 생성"""
        from device_tools import AdbConfig

        config = AdbConfig(
            serial="test_device",
            screen_width=1080,
            screen_height=2400,
        )

        assert config.serial == "test_device"
        assert config.screen_width == 1080
        assert config.screen_height == 2400

    def test_behavior_injector_tap_offset(self):
        """BehaviorInjector 탭 오프셋 생성"""
        from device_tools.behavior_injector import BehaviorInjector

        injector = BehaviorInjector()
        result = injector.generate_human_tap(500, 1000)

        # 오프셋이 적용되어야 함
        assert result is not None
        assert hasattr(result, 'x')
        assert hasattr(result, 'y')
        assert hasattr(result, 'offset_x')
        assert hasattr(result, 'offset_y')

        # 오프셋 범위 확인 (±20px 이내)
        assert abs(result.x - 500) <= 20
        assert abs(result.y - 1000) <= 20


# 테스트 실행
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
