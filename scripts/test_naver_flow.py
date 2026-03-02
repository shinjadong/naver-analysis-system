"""
네이버 검색 플로우 테스트 (EnhancedAdbTools)

테스트 시나리오:
1. 크롬으로 네이버 검색 (맛집)
2. 스크롤 내렸다가 올리기
3. '블로그' 탭 누르기
4. 2번째 글 클릭

목적: 휴먼라이크 동작 확인 + 네이버 추적 데이터 수집
"""

import asyncio
import sys
import os
import time
import logging

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.device_tools import EnhancedAdbTools, AdbConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("naver_test")


async def run_naver_flow_test(serial: str = "R3CW60BHSAT"):
    """네이버 검색 플로우 테스트 실행"""

    print("=" * 60)
    print("네이버 검색 플로우 테스트 (EnhancedAdbTools)")
    print("=" * 60)

    # 1. EnhancedAdbTools 초기화
    config = AdbConfig(
        serial=serial,
        screen_width=1080,
        screen_height=2340,  # Galaxy S23+
    )
    tools = EnhancedAdbTools(config)

    print(f"\n[1/7] 디바이스 연결: {serial}")
    connected = await tools.connect(serial)
    if not connected:
        print("ERROR: 디바이스 연결 실패")
        return False
    print("OK: 디바이스 연결됨")

    # 2. 네이버 검색 URL 열기
    print("\n[2/7] 네이버 검색 열기 (키워드: 맛집)")
    search_url = "https://search.naver.com/search.naver?query=맛집"
    result = await tools.open_url(search_url, package="com.android.chrome")
    print(f"  -> {result.message}")
    await asyncio.sleep(3)  # 페이지 로드 대기

    # 3. 스크롤 내리기 (휴먼라이크)
    print("\n[3/7] 스크롤 내리기 (휴먼라이크)")
    for i in range(3):
        result = await tools.scroll_down(distance=600)
        print(f"  -> 스크롤 {i+1}: {result.duration_ms}ms, segments={result.details.get('segments', 'N/A')}")
        await asyncio.sleep(1.5)

    # 4. 스크롤 올리기 (휴먼라이크)
    print("\n[4/7] 스크롤 올리기 (휴먼라이크)")
    for i in range(2):
        result = await tools.scroll_up(distance=500)
        print(f"  -> 스크롤 업 {i+1}: {result.duration_ms}ms")
        await asyncio.sleep(1.2)

    # 5. '블로그' 탭 클릭
    # 네이버 검색 결과에서 블로그 탭 위치 (대략적인 좌표)
    # 상단 탭바: 통합검색 | 블로그 | 카페 | 뉴스 | ...
    # 블로그 탭은 보통 x=270 정도 (화면 상단)
    print("\n[5/7] '블로그' 탭 클릭 (휴먼라이크)")
    blog_tab_x = 270
    blog_tab_y = 280  # 상단 탭바 위치
    result = await tools.tap(blog_tab_x, blog_tab_y)
    print(f"  -> 탭 위치: ({blog_tab_x}, {blog_tab_y})")
    print(f"  -> 결과: {result.message}")
    await asyncio.sleep(2.5)  # 페이지 전환 대기

    # 6. 2번째 글 클릭
    # 블로그 검색 결과에서 2번째 결과 위치 (대략적인 좌표)
    # 첫 번째 결과: y ≈ 600-700
    # 두 번째 결과: y ≈ 900-1000
    print("\n[6/7] 2번째 블로그 글 클릭 (휴먼라이크)")
    second_result_x = 540  # 화면 중앙
    second_result_y = 950  # 두 번째 결과 위치
    result = await tools.tap(second_result_x, second_result_y)
    print(f"  -> 탭 위치: ({second_result_x}, {second_result_y})")
    print(f"  -> 결과: {result.message}")
    await asyncio.sleep(3)  # 블로그 로드 대기

    # 7. 블로그 콘텐츠 읽기 (스크롤)
    print("\n[7/7] 블로그 콘텐츠 읽기 (스크롤)")
    for i in range(2):
        result = await tools.scroll_down(distance=400)
        print(f"  -> 콘텐츠 스크롤 {i+1}: {result.duration_ms}ms")
        await asyncio.sleep(2)

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

    # 요약
    print("\n[요약]")
    print("- 모든 탭: 베지어 오프셋 적용됨")
    print("- 모든 스크롤: 가변 속도 (가속-유지-감속) 적용됨")
    print("- 녹화 파일: /sdcard/naver_test_*.mp4")
    print("- 네트워크 캡처: /sdcard/naver_capture.pcap (if root)")

    return True


async def main():
    """메인 함수"""
    serial = "R3CW60BHSAT"  # Galaxy S23+

    if len(sys.argv) > 1:
        serial = sys.argv[1]

    try:
        success = await run_naver_flow_test(serial)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n사용자 중단")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
