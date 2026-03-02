"""
Persona Generator Configuration

페르소나 생성기 설정:
- 생성 파라미터
- 클러스터링 설정
- 프로파일 설정
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PersonaDistributionStrategy(Enum):
    """페르소나 분배 전략"""
    EQUAL = "equal"                # 균등 분배
    VOLUME_WEIGHTED = "volume"     # 검색량 비례
    INTEREST_BASED = "interest"    # 관심사 기반
    CUSTOM = "custom"              # 커스텀 분배


class ClusteringMethod(Enum):
    """클러스터링 방법"""
    CATEGORY = "category"          # 카테고리 기반
    SIMILARITY = "similarity"      # 유사도 기반
    HYBRID = "hybrid"              # 혼합


@dataclass
class ClusteringConfig:
    """클러스터링 설정"""
    method: ClusteringMethod = ClusteringMethod.HYBRID
    min_cluster_size: int = 3
    max_cluster_size: int = 50
    max_clusters: int = 20
    merge_threshold: float = 0.7
    split_threshold: int = 30
    include_regions: bool = True
    region_as_subcategory: bool = True


@dataclass
class PersonaConfig:
    """페르소나 설정"""
    min_interests: int = 2
    max_interests: int = 10
    min_keywords: int = 5
    max_keywords: int = 50
    include_behavior_profile: bool = True
    include_interest_profile: bool = True
    generate_android_id: bool = True
    name_style: str = "korean"  # korean, english, mixed


@dataclass
class ArchetypeDistribution:
    """원형 분포 설정"""
    explorer: float = 0.15
    researcher: float = 0.10
    casual: float = 0.30
    shopper: float = 0.20
    local: float = 0.15
    professional: float = 0.10

    def to_dict(self) -> Dict[str, float]:
        return {
            "explorer": self.explorer,
            "researcher": self.researcher,
            "casual": self.casual,
            "shopper": self.shopper,
            "local": self.local,
            "professional": self.professional
        }

    def normalize(self) -> 'ArchetypeDistribution':
        """정규화 (합이 1.0이 되도록)"""
        total = sum(self.to_dict().values())
        if total == 0:
            total = 1.0
        return ArchetypeDistribution(
            explorer=self.explorer / total,
            researcher=self.researcher / total,
            casual=self.casual / total,
            shopper=self.shopper / total,
            local=self.local / total,
            professional=self.professional / total
        )


@dataclass
class OutputConfig:
    """출력 설정"""
    output_dir: str = "data/personas"
    export_format: str = "json"  # json, csv, yaml
    include_metadata: bool = True
    include_stats: bool = True
    pretty_print: bool = True


@dataclass
class IntegrationConfig:
    """연동 설정"""
    # 프로젝트 매니저
    auto_create_project: bool = False
    project_name_prefix: str = "auto_"

    # 스토리라인 생성기
    generate_storylines: bool = False
    storyline_count_per_persona: int = 3

    # IP 매니저
    assign_ip_pool: bool = False
    ip_rotation_enabled: bool = True

    # 이벤트 발행
    publish_events: bool = True
    event_batch_size: int = 10


@dataclass
class PersonaGeneratorConfig:
    """페르소나 생성기 전체 설정"""
    # 기본 설정
    persona_count: int = 10
    distribution_strategy: PersonaDistributionStrategy = PersonaDistributionStrategy.VOLUME_WEIGHTED

    # 세부 설정
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    archetype_distribution: ArchetypeDistribution = field(default_factory=ArchetypeDistribution)
    output: OutputConfig = field(default_factory=OutputConfig)
    integration: IntegrationConfig = field(default_factory=IntegrationConfig)

    # 파일 파싱 설정
    supported_formats: List[str] = field(
        default_factory=lambda: ["csv", "json", "yaml", "also"]
    )
    default_encoding: str = "utf-8"
    skip_header: bool = True

    # 고급 설정
    random_seed: Optional[int] = None
    enable_logging: bool = True
    log_level: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            "persona_count": self.persona_count,
            "distribution_strategy": self.distribution_strategy.value,
            "clustering": {
                "method": self.clustering.method.value,
                "min_cluster_size": self.clustering.min_cluster_size,
                "max_cluster_size": self.clustering.max_cluster_size,
                "max_clusters": self.clustering.max_clusters
            },
            "persona": {
                "min_interests": self.persona.min_interests,
                "max_interests": self.persona.max_interests,
                "min_keywords": self.persona.min_keywords,
                "max_keywords": self.persona.max_keywords
            },
            "archetype_distribution": self.archetype_distribution.to_dict(),
            "output": {
                "output_dir": self.output.output_dir,
                "export_format": self.output.export_format
            },
            "integration": {
                "auto_create_project": self.integration.auto_create_project,
                "generate_storylines": self.integration.generate_storylines,
                "publish_events": self.integration.publish_events
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaGeneratorConfig':
        """딕셔너리에서 설정 생성"""
        config = cls()

        if "persona_count" in data:
            config.persona_count = data["persona_count"]

        if "distribution_strategy" in data:
            config.distribution_strategy = PersonaDistributionStrategy(
                data["distribution_strategy"]
            )

        if "clustering" in data:
            c = data["clustering"]
            config.clustering = ClusteringConfig(
                method=ClusteringMethod(c.get("method", "hybrid")),
                min_cluster_size=c.get("min_cluster_size", 3),
                max_cluster_size=c.get("max_cluster_size", 50),
                max_clusters=c.get("max_clusters", 20)
            )

        if "persona" in data:
            p = data["persona"]
            config.persona = PersonaConfig(
                min_interests=p.get("min_interests", 2),
                max_interests=p.get("max_interests", 10),
                min_keywords=p.get("min_keywords", 5),
                max_keywords=p.get("max_keywords", 50)
            )

        if "archetype_distribution" in data:
            ad = data["archetype_distribution"]
            config.archetype_distribution = ArchetypeDistribution(
                explorer=ad.get("explorer", 0.15),
                researcher=ad.get("researcher", 0.10),
                casual=ad.get("casual", 0.30),
                shopper=ad.get("shopper", 0.20),
                local=ad.get("local", 0.15),
                professional=ad.get("professional", 0.10)
            )

        return config

    @classmethod
    def default(cls) -> 'PersonaGeneratorConfig':
        """기본 설정"""
        return cls()

    @classmethod
    def for_small_campaign(cls) -> 'PersonaGeneratorConfig':
        """소규모 캠페인용 설정"""
        return cls(
            persona_count=5,
            clustering=ClusteringConfig(
                max_clusters=10,
                min_cluster_size=2
            ),
            integration=IntegrationConfig(
                generate_storylines=False
            )
        )

    @classmethod
    def for_large_campaign(cls) -> 'PersonaGeneratorConfig':
        """대규모 캠페인용 설정"""
        return cls(
            persona_count=30,
            clustering=ClusteringConfig(
                max_clusters=50,
                max_cluster_size=100
            ),
            integration=IntegrationConfig(
                generate_storylines=True,
                storyline_count_per_persona=5,
                assign_ip_pool=True
            )
        )

    @classmethod
    def for_local_business(cls) -> 'PersonaGeneratorConfig':
        """지역 비즈니스용 설정"""
        return cls(
            persona_count=10,
            archetype_distribution=ArchetypeDistribution(
                explorer=0.10,
                researcher=0.05,
                casual=0.20,
                shopper=0.15,
                local=0.40,
                professional=0.10
            ),
            clustering=ClusteringConfig(
                include_regions=True,
                region_as_subcategory=True
            )
        )
