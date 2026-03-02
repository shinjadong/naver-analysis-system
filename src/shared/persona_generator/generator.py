"""
Persona Generator

메인 페르소나 생성기:
- 키워드 파일 → 클러스터 → 페르소나 생성
- 프로젝트/스토리라인 연동
- 이벤트 발행
"""

import logging
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Awaitable
from datetime import datetime

from .keyword_parser import KeywordParser, KeywordEntry
from .keyword_clusterer import KeywordClusterer, KeywordCluster
from .persona_factory import PersonaFactory, GeneratedPersona, PersonaArchetype
from .interest_profiler import InterestProfiler, InterestProfile
from .config import (
    PersonaGeneratorConfig,
    PersonaDistributionStrategy,
    ArchetypeDistribution
)

# 순환 참조 방지를 위한 런타임 임포트
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.events import EventBus, Event
    from ..core.protocols import PersonaProvider

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """생성 결과"""
    success: bool
    personas: List[GeneratedPersona] = field(default_factory=list)
    clusters: List[KeywordCluster] = field(default_factory=list)
    keywords_parsed: int = 0
    clusters_created: int = 0
    personas_created: int = 0
    duration_ms: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "keywords_parsed": self.keywords_parsed,
            "clusters_created": self.clusters_created,
            "personas_created": self.personas_created,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "metadata": self.metadata,
            "personas": [p.to_dict() for p in self.personas]
        }

    def summary(self) -> str:
        return (
            f"Generation Result:\n"
            f"  Success: {self.success}\n"
            f"  Keywords: {self.keywords_parsed}\n"
            f"  Clusters: {self.clusters_created}\n"
            f"  Personas: {self.personas_created}\n"
            f"  Duration: {self.duration_ms}ms"
        )


class PersonaGenerator:
    """
    페르소나 생성기

    Usage:
        generator = PersonaGenerator()

        # 파일에서 생성
        result = await generator.generate_from_file(
            "keywords.csv",
            persona_count=10
        )

        # 키워드 리스트에서 생성
        result = await generator.generate_from_keywords(
            keywords=["강남맛집", "홍대카페", ...],
            volumes=[1000, 800, ...]
        )

        # 프로젝트 연동
        await generator.assign_to_project(
            project_id="proj_001",
            personas=result.personas
        )
    """

    def __init__(
        self,
        config: Optional[PersonaGeneratorConfig] = None,
        event_bus: Optional['EventBus'] = None
    ):
        self.config = config or PersonaGeneratorConfig.default()
        self.event_bus = event_bus

        # 컴포넌트 초기화
        self.parser = KeywordParser()
        self.clusterer = KeywordClusterer()
        self.factory = PersonaFactory()
        self.profiler = InterestProfiler()

        # 외부 연동 (런타임에 설정)
        self._project_manager = None
        self._storyline_generator = None
        self._ip_manager = None

        # 콜백
        self._on_persona_created: List[Callable[[GeneratedPersona], Awaitable[None]]] = []
        self._on_generation_complete: List[Callable[[GenerationResult], Awaitable[None]]] = []

    # ==================== 외부 연동 설정 ====================

    def set_project_manager(self, manager: Any) -> None:
        """프로젝트 매니저 설정"""
        self._project_manager = manager

    def set_storyline_generator(self, generator: Any) -> None:
        """스토리라인 생성기 설정"""
        self._storyline_generator = generator

    def set_ip_manager(self, manager: Any) -> None:
        """IP 매니저 설정"""
        self._ip_manager = manager

    def on_persona_created(
        self,
        callback: Callable[[GeneratedPersona], Awaitable[None]]
    ) -> None:
        """페르소나 생성 콜백 등록"""
        self._on_persona_created.append(callback)

    def on_generation_complete(
        self,
        callback: Callable[[GenerationResult], Awaitable[None]]
    ) -> None:
        """생성 완료 콜백 등록"""
        self._on_generation_complete.append(callback)

    # ==================== 메인 생성 메서드 ====================

    async def generate_from_file(
        self,
        file_path: str,
        persona_count: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """
        파일에서 페르소나 생성

        Args:
            file_path: 키워드 파일 경로
            persona_count: 생성할 페르소나 수 (기본값: config)
            config_override: 설정 오버라이드

        Returns:
            GenerationResult: 생성 결과
        """
        start_time = datetime.now()
        result = GenerationResult(success=False)

        try:
            # 설정 적용
            count = persona_count or self.config.persona_count

            # 1. 키워드 파싱
            logger.info(f"Parsing keywords from: {file_path}")
            keywords = await self.parser.parse_file(file_path)
            result.keywords_parsed = len(keywords)

            if not keywords:
                result.errors.append(f"No keywords found in {file_path}")
                return result

            # 2. 클러스터링
            logger.info(f"Clustering {len(keywords)} keywords")
            clusters = await self.clusterer.cluster_keywords(
                keywords,
                min_cluster_size=self.config.clustering.min_cluster_size,
                max_clusters=self.config.clustering.max_clusters
            )
            result.clusters = clusters
            result.clusters_created = len(clusters)

            # 3. 페르소나 생성
            logger.info(f"Generating {count} personas")
            distribution = self._get_archetype_distribution()
            personas = await self.factory.generate_personas(
                clusters=clusters,
                count=count,
                distribution=distribution
            )
            result.personas = personas
            result.personas_created = len(personas)

            # 4. 콜백 및 이벤트 발행
            for persona in personas:
                for callback in self._on_persona_created:
                    await callback(persona)

                if self.event_bus and self.config.integration.publish_events:
                    await self._publish_persona_event(persona)

            # 5. 연동 처리
            if self.config.integration.auto_create_project:
                await self._auto_create_project(file_path, personas)

            if self.config.integration.generate_storylines:
                await self._generate_storylines(personas)

            result.success = True
            result.metadata = {
                "file": file_path,
                "config": self.config.to_dict()
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.errors.append(str(e))

        finally:
            result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 완료 콜백
            for callback in self._on_generation_complete:
                await callback(result)

            logger.info(f"Generation completed in {result.duration_ms}ms")

        return result

    async def generate_from_keywords(
        self,
        keywords: List[str],
        volumes: Optional[List[int]] = None,
        categories: Optional[List[str]] = None,
        persona_count: Optional[int] = None
    ) -> GenerationResult:
        """
        키워드 리스트에서 페르소나 생성

        Args:
            keywords: 키워드 목록
            volumes: 검색량 목록
            categories: 카테고리 목록
            persona_count: 페르소나 수

        Returns:
            GenerationResult: 생성 결과
        """
        start_time = datetime.now()
        result = GenerationResult(success=False)

        try:
            count = persona_count or self.config.persona_count

            # KeywordEntry 변환
            entries = []
            for i, kw in enumerate(keywords):
                entry = KeywordEntry(
                    keyword=kw,
                    volume=volumes[i] if volumes and i < len(volumes) else 100,
                    category=categories[i] if categories and i < len(categories) else None
                )
                entries.append(entry)

            result.keywords_parsed = len(entries)

            # 클러스터링
            clusters = await self.clusterer.cluster_keywords(
                entries,
                min_cluster_size=self.config.clustering.min_cluster_size,
                max_clusters=self.config.clustering.max_clusters
            )
            result.clusters = clusters
            result.clusters_created = len(clusters)

            # 페르소나 생성
            distribution = self._get_archetype_distribution()
            personas = await self.factory.generate_personas(
                clusters=clusters,
                count=count,
                distribution=distribution
            )
            result.personas = personas
            result.personas_created = len(personas)

            # 콜백
            for persona in personas:
                for callback in self._on_persona_created:
                    await callback(persona)

            result.success = True

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.errors.append(str(e))

        finally:
            result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    async def generate_single(
        self,
        name: str,
        interests: List[str],
        keywords: List[str],
        archetype: str = "casual"
    ) -> GeneratedPersona:
        """단일 페르소나 생성"""
        arch = PersonaArchetype(archetype)
        return await self.factory.create_single_persona(
            name=name,
            interests=interests,
            keywords=keywords,
            archetype=arch
        )

    # ==================== 프로젝트 연동 ====================

    async def assign_to_project(
        self,
        project_id: str,
        personas: List[GeneratedPersona],
        distribute_keywords: bool = True
    ) -> bool:
        """
        페르소나를 프로젝트에 할당

        Args:
            project_id: 프로젝트 ID
            personas: 페르소나 목록
            distribute_keywords: 키워드 분배 여부

        Returns:
            bool: 성공 여부
        """
        if not self._project_manager:
            logger.warning("Project manager not set")
            return False

        try:
            project = self._project_manager.get_project(project_id)
            if not project:
                logger.error(f"Project not found: {project_id}")
                return False

            for persona in personas:
                project.assign_persona(persona.persona_id)

            self._project_manager.update_project(project)
            logger.info(f"Assigned {len(personas)} personas to project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign personas: {e}")
            return False

    async def create_project_from_personas(
        self,
        personas: List[GeneratedPersona],
        project_name: str,
        targets: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """페르소나에서 프로젝트 생성"""
        if not self._project_manager:
            logger.warning("Project manager not set")
            return None

        try:
            # 키워드에서 타겟 생성
            if not targets:
                targets = []
                for persona in personas:
                    for kw in persona.keywords[:5]:  # 상위 5개
                        targets.append({
                            "keyword": kw,
                            "title": f"{kw} 관련 콘텐츠"
                        })

            project = self._project_manager.create_project(
                name=project_name,
                targets=targets,
                description=f"Auto-generated from {len(personas)} personas"
            )

            # 페르소나 할당
            for persona in personas:
                project.assign_persona(persona.persona_id)

            self._project_manager.update_project(project)
            return project.project_id

        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None

    # ==================== 스토리라인 연동 ====================

    async def generate_storylines_for_persona(
        self,
        persona: GeneratedPersona,
        count: int = 3
    ) -> List[Any]:
        """페르소나용 스토리라인 생성"""
        if not self._storyline_generator:
            logger.warning("Storyline generator not set")
            return []

        try:
            storylines = []
            for _ in range(count):
                # 랜덤 키워드 선택
                if not persona.keywords:
                    continue

                keyword = persona.interest_profile.get_weighted_keyword()
                if not keyword:
                    keyword = persona.keywords[0]

                # 스토리라인 생성 요청
                storyline = await self._storyline_generator.generate(
                    keyword=keyword,
                    persona_archetype=persona.archetype.value,
                    behavior_profile=persona.behavior_profile.to_dict()
                )
                storylines.append(storyline)

            return storylines

        except Exception as e:
            logger.error(f"Failed to generate storylines: {e}")
            return []

    # ==================== 내보내기 ====================

    async def export_personas(
        self,
        personas: List[GeneratedPersona],
        output_path: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """
        페르소나 내보내기

        Args:
            personas: 페르소나 목록
            output_path: 출력 경로
            format: 출력 형식 (json, csv)

        Returns:
            str: 출력 파일 경로
        """
        if output_path is None:
            output_dir = Path(self.config.output.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"personas_{timestamp}.{format}")

        if format == "json":
            data = {
                "generated_at": datetime.now().isoformat(),
                "count": len(personas),
                "personas": [p.to_dict() for p in personas]
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == "csv":
            import csv
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "persona_id", "name", "android_id", "archetype",
                    "interests", "keyword_count"
                ])
                for p in personas:
                    writer.writerow([
                        p.persona_id,
                        p.name,
                        p.android_id,
                        p.archetype.value,
                        "|".join(p.interests),
                        len(p.keywords)
                    ])

        logger.info(f"Exported {len(personas)} personas to {output_path}")
        return output_path

    async def export_clusters(
        self,
        clusters: List[KeywordCluster],
        output_path: str
    ) -> None:
        """클러스터 내보내기"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "count": len(clusters),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "category": c.category.value,
                    "size": c.size,
                    "total_volume": c.total_volume,
                    "center_keyword": c.center_keyword,
                    "keywords": c.keyword_list[:20]  # 상위 20개만
                }
                for c in clusters
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 헬퍼 메서드 ====================

    def _get_archetype_distribution(self) -> Dict[PersonaArchetype, float]:
        """원형 분포 딕셔너리 변환"""
        ad = self.config.archetype_distribution.normalize()
        return {
            PersonaArchetype.EXPLORER: ad.explorer,
            PersonaArchetype.RESEARCHER: ad.researcher,
            PersonaArchetype.CASUAL: ad.casual,
            PersonaArchetype.SHOPPER: ad.shopper,
            PersonaArchetype.LOCAL: ad.local,
            PersonaArchetype.PROFESSIONAL: ad.professional
        }

    async def _publish_persona_event(self, persona: GeneratedPersona) -> None:
        """페르소나 이벤트 발행"""
        if not self.event_bus:
            return

        try:
            from ..core.events import Event, EventType
            event = Event(
                event_type=EventType.PERSONA_CREATED,
                source="persona_generator",
                data={
                    "persona_id": persona.persona_id,
                    "archetype": persona.archetype.value,
                    "keyword_count": len(persona.keywords)
                }
            )
            await self.event_bus.publish(event)
        except ImportError:
            pass

    async def _auto_create_project(
        self,
        source_file: str,
        personas: List[GeneratedPersona]
    ) -> None:
        """자동 프로젝트 생성"""
        if not self._project_manager:
            return

        project_name = f"{self.config.integration.project_name_prefix}{Path(source_file).stem}"
        await self.create_project_from_personas(personas, project_name)

    async def _generate_storylines(
        self,
        personas: List[GeneratedPersona]
    ) -> None:
        """스토리라인 일괄 생성"""
        if not self._storyline_generator:
            return

        count = self.config.integration.storyline_count_per_persona
        for persona in personas:
            await self.generate_storylines_for_persona(persona, count)

    # ==================== 정적 팩토리 ====================

    @classmethod
    def with_config(cls, config: PersonaGeneratorConfig) -> 'PersonaGenerator':
        """설정으로 생성"""
        return cls(config=config)

    @classmethod
    def for_small_campaign(cls) -> 'PersonaGenerator':
        """소규모 캠페인용"""
        return cls(config=PersonaGeneratorConfig.for_small_campaign())

    @classmethod
    def for_large_campaign(cls) -> 'PersonaGenerator':
        """대규모 캠페인용"""
        return cls(config=PersonaGeneratorConfig.for_large_campaign())

    @classmethod
    def for_local_business(cls) -> 'PersonaGenerator':
        """지역 비즈니스용"""
        return cls(config=PersonaGeneratorConfig.for_local_business())


# ==================== 어댑터 (프로토콜 구현) ====================

class PersonaGeneratorAdapter:
    """PersonaProvider 프로토콜 어댑터"""

    def __init__(self, generator: PersonaGenerator):
        self._generator = generator
        self._personas: Dict[str, GeneratedPersona] = {}

    async def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """페르소나 조회"""
        if persona_id in self._personas:
            return self._personas[persona_id].to_dict()
        return None

    async def list_personas(self, filter_by: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """페르소나 목록"""
        personas = list(self._personas.values())

        if filter_by:
            archetype = filter_by.get("archetype")
            if archetype:
                personas = [p for p in personas if p.archetype.value == archetype]

        return [p.to_dict() for p in personas]

    async def create_persona(self, **kwargs) -> Dict[str, Any]:
        """페르소나 생성"""
        persona = await self._generator.generate_single(
            name=kwargs.get("name", "Unknown"),
            interests=kwargs.get("interests", []),
            keywords=kwargs.get("keywords", []),
            archetype=kwargs.get("archetype", "casual")
        )
        self._personas[persona.persona_id] = persona
        return persona.to_dict()

    def register_personas(self, personas: List[GeneratedPersona]) -> None:
        """페르소나 일괄 등록"""
        for persona in personas:
            self._personas[persona.persona_id] = persona
