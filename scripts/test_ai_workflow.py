#!/usr/bin/env python3
"""
AI Campaign Workflow 테스트 스크립트

droidrun 기반의 동적 UI 탐지 + 휴먼라이크 액션 테스트

사용법:
    python scripts/test_ai_workflow.py
    python scripts/test_ai_workflow.py --device R3CW60BHSAT
"""

import asyncio
import argparse
import logging
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection(device_serial: str = None):
    """연결 테스트"""
    logger.info("=" * 60)
    logger.info("Testing connection...")
    logger.info("=" * 60)

    from src.shared.ai_session_controller import AISessionController

    controller = AISessionController(device_serial=device_serial)
    success = await controller.connect()

    if success:
        logger.info("Connection successful!")

        # UI 상태 확인
        logger.info("\nGetting UI state...")
        state = await controller.get_ui_state()

        if "error" in state:
            logger.error(f"UI state error: {state}")
        else:
            logger.info(f"Phone state: {state.get('phone_state', {})}")
            logger.info(f"A11y tree elements: {len(state.get('a11y_tree', []))}")

        # UI 요소 새로고침
        logger.info("\nRefreshing UI elements...")
        elements = await controller.refresh_ui_elements()
        logger.info(f"Total elements: {len(elements)}")

        # UI 요약 출력
        logger.info("\nUI Summary:")
        logger.info(controller.get_ui_summary())

        return True
    else:
        logger.error("Connection failed!")
        return False


async def test_element_search(device_serial: str = None):
    """요소 검색 테스트"""
    logger.info("=" * 60)
    logger.info("Testing element search...")
    logger.info("=" * 60)

    from src.shared.ai_session_controller import AISessionController

    controller = AISessionController(device_serial=device_serial)
    await controller.connect()

    # 테스트 검색어들
    test_texts = ["블로그", "검색", "네이버", "Chrome"]

    for text in test_texts:
        element = await controller.find_element_by_text(text, partial=True)
        if element:
            logger.info(f"Found '{text}': index={element.index}, center={element.center}")
        else:
            logger.info(f"Not found: '{text}'")


async def test_simple_workflow(device_serial: str = None):
    """간단한 워크플로우 테스트 (검색 페이지 열기만)"""
    logger.info("=" * 60)
    logger.info("Testing simple workflow...")
    logger.info("=" * 60)

    from src.shared.ai_session_controller import AISessionController

    controller = AISessionController(device_serial=device_serial)
    await controller.connect()

    # 네이버 검색 페이지 열기
    keyword = "cctv가격"
    logger.info(f"Opening Naver search for: {keyword}")

    from urllib.parse import quote
    search_url = f"https://m.search.naver.com/search.naver?query={quote(keyword)}"

    success = await controller.open_url(search_url)

    if success:
        logger.info("Search page opened!")

        # 잠시 대기 후 UI 확인
        await asyncio.sleep(3)

        logger.info("\nChecking current UI...")
        await controller.refresh_ui_elements()
        logger.info(controller.get_ui_summary())

        # 블로그 탭 찾기
        logger.info("\nSearching for '블로그' tab...")
        element = await controller.find_element_by_text("블로그", refresh=False)

        if element:
            logger.info(f"Found blog tab at: {element.center}")
        else:
            logger.info("Blog tab not found in current UI")

    return success


async def test_full_workflow(device_serial: str = None):
    """전체 워크플로우 테스트"""
    logger.info("=" * 60)
    logger.info("Testing full AI campaign workflow...")
    logger.info("=" * 60)

    from src.shared.ai_campaign_workflow import AICampaignWorkflow

    workflow = AICampaignWorkflow(device_serial=device_serial)

    # 테스트 캠페인 데이터
    keyword = "cctv가격"
    target_title = "CCTV가격 부담된다면? 키퍼의 투명한 구매 가이드"
    target_blogger = "한화비전 키퍼"
    target_url = "https://blog.naver.com/shopmanager_keeper/224091279885"

    logger.info(f"Keyword: {keyword}")
    logger.info(f"Target title: {target_title}")
    logger.info(f"Target blogger: {target_blogger}")

    result = await workflow.execute(
        keyword=keyword,
        target_blog_title=target_title,
        target_blogger=target_blogger,
        target_url=target_url
    )

    logger.info("\n" + "=" * 60)
    logger.info("Workflow Result:")
    logger.info("=" * 60)
    logger.info(f"Success: {result.success}")
    logger.info(f"Target found: {result.target_found}")
    logger.info(f"Duration: {result.duration_sec:.1f}s")
    logger.info(f"Scroll count: {result.scroll_count}")
    logger.info(f"Scroll depth: {result.scroll_depth:.2f}")

    if result.error_message:
        logger.error(f"Error: {result.error_message}")

    logger.info("\nSteps:")
    for step in result.steps:
        status = "✓" if step.success else "✗"
        logger.info(f"  {status} {step.step_name}: {step.action_taken or step.error_message}")

    return result.success


async def main():
    parser = argparse.ArgumentParser(description="AI Campaign Workflow 테스트")
    parser.add_argument("--device", "-d", help="ADB 디바이스 시리얼")
    parser.add_argument(
        "--test", "-t",
        choices=["connection", "search", "simple", "full"],
        default="connection",
        help="테스트 종류 (default: connection)"
    )
    args = parser.parse_args()

    if args.test == "connection":
        await test_connection(args.device)
    elif args.test == "search":
        await test_element_search(args.device)
    elif args.test == "simple":
        await test_simple_workflow(args.device)
    elif args.test == "full":
        await test_full_workflow(args.device)


if __name__ == "__main__":
    asyncio.run(main())
