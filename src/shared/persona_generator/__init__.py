"""
Persona Generator Module

키워드 기반 페르소나 자동 생성:
- CSV/ALSO 파일에서 키워드 파싱
- 키워드 클러스터링 (관심사별 그룹화)
- 페르소나 프로필 생성
- 프로젝트/스토리라인 연동

Usage:
    from src.shared.persona_generator import PersonaGenerator

    generator = PersonaGenerator()

    # 키워드 파일에서 페르소나 생성
    personas = await generator.generate_from_file(
        "keywords.csv",
        persona_count=10
    )

    # 프로젝트에 페르소나 할당
    await generator.assign_to_project(
        project_id="seoul_food",
        personas=personas
    )
"""

from .generator import PersonaGenerator
from .keyword_parser import KeywordParser, KeywordEntry
from .keyword_clusterer import KeywordClusterer, KeywordCluster
from .persona_factory import PersonaFactory, GeneratedPersona
from .interest_profiler import InterestProfiler, InterestProfile
from .config import PersonaGeneratorConfig

__all__ = [
    "PersonaGenerator",
    "KeywordParser",
    "KeywordEntry",
    "KeywordClusterer",
    "KeywordCluster",
    "PersonaFactory",
    "GeneratedPersona",
    "InterestProfiler",
    "InterestProfile",
    "PersonaGeneratorConfig",
]

__version__ = "0.1.0"
