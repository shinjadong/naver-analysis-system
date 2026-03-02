#!/usr/bin/env python3
"""
Persona Generator 테스트 스크립트

Usage:
    python scripts/test_persona_generator.py
    python scripts/test_persona_generator.py --file keywords.csv
    python scripts/test_persona_generator.py --export
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.persona_generator import (
    PersonaGenerator,
    KeywordParser,
    KeywordClusterer,
    PersonaFactory,
    InterestProfiler,
    PersonaGeneratorConfig
)
from src.shared.persona_generator.keyword_parser import KeywordEntry


async def test_keyword_parser():
    """키워드 파서 테스트"""
    print("\n" + "=" * 60)
    print("1. Keyword Parser Test")
    print("=" * 60)

    parser = KeywordParser()

    # 샘플 CSV 생성
    sample_csv = Path("data/test_keywords.csv")
    sample_csv.parent.mkdir(parents=True, exist_ok=True)

    csv_content = """keyword,volume,difficulty,category
강남맛집,12000,75,food
홍대카페,8500,60,food
이태원맛집,6000,55,food
강남카페,9000,70,food
서울여행,15000,80,travel
부산여행,11000,70,travel
제주도맛집,13000,75,food
판교카페,4000,45,food
성수맛집,7000,65,food
연남동카페,5500,55,food
해운대맛집,8000,60,food
경리단길맛집,3500,50,food
망원동카페,4500,50,food
한남동맛집,6500,65,food
"""
    sample_csv.write_text(csv_content, encoding='utf-8')

    # CSV 파싱
    keywords = await parser.parse_file(str(sample_csv))
    print(f"  Parsed {len(keywords)} keywords from CSV")

    for kw in keywords[:5]:
        print(f"    - {kw.keyword}: vol={kw.volume}, diff={kw.difficulty}, cat={kw.category}")

    return keywords


async def test_keyword_clusterer(keywords):
    """키워드 클러스터러 테스트"""
    print("\n" + "=" * 60)
    print("2. Keyword Clusterer Test")
    print("=" * 60)

    clusterer = KeywordClusterer()
    clusters = await clusterer.cluster_keywords(
        keywords,
        min_cluster_size=2,
        max_clusters=10
    )

    print(f"  Created {len(clusters)} clusters")
    for cluster in clusters:
        print(f"\n  [{cluster.cluster_id}] {cluster.name}")
        print(f"    Category: {cluster.category.value}")
        print(f"    Size: {cluster.size}")
        print(f"    Total volume: {cluster.total_volume:,}")
        print(f"    Center: {cluster.center_keyword}")
        print(f"    Keywords: {', '.join(cluster.keyword_list[:5])}")

    return clusters


async def test_interest_profiler():
    """관심사 프로파일러 테스트"""
    print("\n" + "=" * 60)
    print("3. Interest Profiler Test")
    print("=" * 60)

    profiler = InterestProfiler()

    profile = await profiler.create_profile(
        interests=["맛집", "카페", "여행"],
        keywords=["강남맛집", "홍대카페", "서울여행", "부산여행"],
        archetype="explorer",
        time_pattern="office_worker"
    )

    print(f"  Profile ID: {profile.profile_id}")
    print(f"  Archetype: {profile.archetype}")
    print(f"\n  Interests:")
    for interest in profile.interests:
        print(f"    - {interest.topic}: {interest.intensity.value}, weight={interest.weight:.2f}")

    print(f"\n  Search Behavior:")
    print(f"    Avg query length: {profile.search_behavior.avg_keywords_per_query:.1f}")
    print(f"    Uses autocomplete: {profile.search_behavior.uses_autocomplete:.0%}")
    print(f"    Click through rate: {profile.search_behavior.click_through_rate:.0%}")

    print(f"\n  Active hours: {profile.active_hours[:5]}...")
    print(f"  Peak hours: {profile.peak_hours}")

    # 검색 시퀀스 생성
    sequence = profiler.generate_search_sequence(profile, count=3)
    print(f"\n  Sample search sequence:")
    for s in sequence:
        print(f"    - '{s['query']}' ({s['intention']})")

    return profile


async def test_persona_factory(clusters):
    """페르소나 팩토리 테스트"""
    print("\n" + "=" * 60)
    print("4. Persona Factory Test")
    print("=" * 60)

    factory = PersonaFactory()

    personas = await factory.generate_personas(
        clusters=clusters,
        count=5
    )

    print(f"  Generated {len(personas)} personas")

    for p in personas:
        print(f"\n  [{p.persona_id}] {p.name}")
        print(f"    Android ID: {p.android_id}")
        print(f"    Archetype: {p.archetype.value}")
        print(f"    Interests: {', '.join(p.interests[:3])}")
        print(f"    Keywords: {len(p.keywords)}")
        print(f"    Clusters: {p.assigned_clusters}")
        print(f"    Behavior: reading={p.behavior_profile.reading_speed}, dwell={p.behavior_profile.avg_dwell_time}s")

    return personas


async def test_full_generator():
    """전체 생성기 테스트"""
    print("\n" + "=" * 60)
    print("5. Full Generator Test")
    print("=" * 60)

    # 샘플 키워드 파일 생성
    sample_file = Path("data/sample_keywords.csv")
    sample_file.parent.mkdir(parents=True, exist_ok=True)

    csv_content = """keyword,volume,difficulty
서울맛집추천,20000,80
강남역맛집,15000,75
홍대맛집베스트,12000,70
이태원브런치,8000,65
성수동카페,9500,68
연남동맛집,7500,62
망원동카페,6000,55
한남동레스토랑,5500,60
판교맛집,8500,65
분당카페,7000,58
강남카페추천,11000,72
신사동맛집,9000,68
압구정카페,8000,70
청담동레스토랑,7500,75
삼청동카페,6500,60
북촌맛집,5000,55
익선동카페,4500,52
을지로맛집,6000,58
광화문맛집,5500,55
여의도맛집,7000,62
"""
    sample_file.write_text(csv_content, encoding='utf-8')

    # 생성기 실행
    config = PersonaGeneratorConfig(
        persona_count=5,
        integration=PersonaGeneratorConfig().integration
    )
    config.integration.publish_events = False

    generator = PersonaGenerator(config=config)

    result = await generator.generate_from_file(
        str(sample_file),
        persona_count=5
    )

    print(f"\n  {result.summary()}")

    if result.success:
        print(f"\n  Generated Personas:")
        for p in result.personas:
            print(f"    - {p.name} ({p.archetype.value}): {len(p.keywords)} keywords")

        # 내보내기
        output_path = await generator.export_personas(
            result.personas,
            format="json"
        )
        print(f"\n  Exported to: {output_path}")

    return result


async def test_config_presets():
    """설정 프리셋 테스트"""
    print("\n" + "=" * 60)
    print("6. Config Presets Test")
    print("=" * 60)

    presets = [
        ("Default", PersonaGeneratorConfig.default()),
        ("Small Campaign", PersonaGeneratorConfig.for_small_campaign()),
        ("Large Campaign", PersonaGeneratorConfig.for_large_campaign()),
        ("Local Business", PersonaGeneratorConfig.for_local_business()),
    ]

    for name, config in presets:
        print(f"\n  {name}:")
        print(f"    Persona count: {config.persona_count}")
        print(f"    Max clusters: {config.clustering.max_clusters}")
        print(f"    Distribution: casual={config.archetype_distribution.casual:.0%}, "
              f"local={config.archetype_distribution.local:.0%}")


async def test_from_file(file_path: str):
    """파일에서 테스트"""
    print("\n" + "=" * 60)
    print(f"Testing with file: {file_path}")
    print("=" * 60)

    generator = PersonaGenerator.for_local_business()

    result = await generator.generate_from_file(
        file_path,
        persona_count=10
    )

    print(result.summary())

    if result.success:
        for p in result.personas:
            print(f"\n  {p.name} ({p.archetype.value})")
            print(f"    Keywords: {', '.join(p.keywords[:5])}...")


async def main():
    parser = argparse.ArgumentParser(description="Persona Generator Test")
    parser.add_argument("--file", help="Test with specific keyword file")
    parser.add_argument("--export", action="store_true", help="Export results")
    args = parser.parse_args()

    if args.file:
        await test_from_file(args.file)
        return

    print("=" * 60)
    print("  PERSONA GENERATOR TEST SUITE")
    print("=" * 60)

    # 1. 키워드 파서
    keywords = await test_keyword_parser()

    # 2. 클러스터러
    clusters = await test_keyword_clusterer(keywords)

    # 3. 관심사 프로파일러
    await test_interest_profiler()

    # 4. 페르소나 팩토리
    await test_persona_factory(clusters)

    # 5. 전체 생성기
    await test_full_generator()

    # 6. 설정 프리셋
    await test_config_presets()

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
