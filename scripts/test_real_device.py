#!/usr/bin/env python3
"""
NaverChromeUse 실제 디바이스 테스트 스크립트

사용법:
    python test_real_device.py

요구사항:
    - ADB가 설치되어 있어야 함
    - Android 디바이스가 USB 디버깅 활성화 상태로 연결되어 있어야 함
    - Chrome 브라우저가 설치되어 있어야 함
"""

import subprocess
import sys
import time
import random
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from shared.naver_chrome_use import NaverChromeUseProvider, NaverUrlBuilder
from shared.naver_chrome_use.url_builder import NaverSearchCategory


class RealDeviceTester:
    """실제 디바이스 테스트 클래스"""

    def __init__(self):
        self.provider = NaverChromeUseProvider()
        self.url_builder = NaverUrlBuilder()
        self.device_id = None

    def run_adb(self, *args) -> str:
        """ADB 명령 실행"""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ADB Error: {result.stderr}")
        return result.stdout.strip()

    def check_connection(self) -> bool:
        """디바이스 연결 확인"""
        print("\n[CHECK] 디바이스 연결 확인...")
        output = self.run_adb("devices", "-l")
        print(output)

        lines = output.strip().split("\n")[1:]  # 첫 줄 제외
        devices = [l for l in lines if l.strip() and "device" in l]

        if not devices:
            print("[ERROR] 연결된 디바이스가 없습니다.")
            return False

        # 첫 번째 디바이스 사용
        self.device_id = devices[0].split()[0]
        print(f"[OK] 디바이스 연결됨: {self.device_id}")
        return True

    def get_device_info(self):
        """디바이스 정보 조회"""
        print("\n[DEVICE] 디바이스 정보:")
        model = self.run_adb("shell", "getprop", "ro.product.model")
        brand = self.run_adb("shell", "getprop", "ro.product.brand")
        android = self.run_adb("shell", "getprop", "ro.build.version.release")
        resolution = self.run_adb("shell", "wm", "size")

        print(f"  - 모델: {brand} {model}")
        print(f"  - Android: {android}")
        print(f"  - 해상도: {resolution.split(':')[-1].strip() if ':' in resolution else resolution}")

        return {
            "model": model,
            "brand": brand,
            "android": android,
            "resolution": resolution
        }

    def check_chrome_installed(self) -> bool:
        """Chrome 설치 여부 확인"""
        print("\n[CHECK] Chrome 설치 확인...")
        output = self.run_adb("shell", "pm", "list", "packages", "com.android.chrome")

        if "com.android.chrome" in output:
            print("[OK] Chrome 설치됨")
            return True
        else:
            print("[ERROR] Chrome이 설치되어 있지 않습니다.")
            return False

    def test_open_naver_home(self):
        """네이버 홈 열기 테스트"""
        print("\n[TEST 1] 네이버 홈 열기")

        intent = self.provider.create_naver_home_intent()
        cmd = intent.to_command()
        print(f"  명령어: adb shell {cmd}")

        self.run_adb("shell", *cmd.split())
        time.sleep(3)
        print("  [OK] 네이버 홈 열기 완료")

    def test_naver_blog_search(self, keyword: str = "맛집"):
        """네이버 블로그 검색 테스트"""
        print(f"\n[TEST 2] 블로그 검색 - '{keyword}'")

        intent = self.provider.create_naver_search_intent(keyword, category="blog")
        cmd = intent.to_command()
        print(f"  명령어: adb shell {cmd}")

        self.run_adb("shell", *cmd.split())
        time.sleep(3)
        print("  [OK] 블로그 검색 완료")

    def test_naver_shopping_search(self, keyword: str = "노트북"):
        """네이버 쇼핑 검색 테스트"""
        print(f"\n[TEST 3] 쇼핑 검색 - '{keyword}'")

        intent = self.provider.create_naver_search_intent(keyword, category="shopping")
        cmd = intent.to_command()
        print(f"  명령어: adb shell {cmd}")

        self.run_adb("shell", *cmd.split())
        time.sleep(3)
        print("  [OK] 쇼핑 검색 완료")

    def test_scroll(self, count: int = 3):
        """스크롤 테스트"""
        print(f"\n[TEST 4] 스크롤 ({count}회)")

        for i in range(count):
            # 가변 속도 스크롤
            start_y = random.randint(1600, 1800)
            end_y = random.randint(800, 1000)
            duration = random.randint(400, 600)

            self.run_adb("shell", "input", "swipe",
                        "540", str(start_y), "540", str(end_y), str(duration))

            wait_time = random.uniform(1.0, 2.0)
            print(f"  [{i+1}/{count}] 스크롤 완료 (대기: {wait_time:.1f}s)")
            time.sleep(wait_time)

        print("  [OK] 스크롤 테스트 완료")

    def test_tap(self, x: int = 540, y: int = 700):
        """탭 테스트"""
        print(f"\n[TEST 5] 탭 ({x}, {y})")

        # 약간의 오프셋 추가
        offset_x = random.randint(-10, 10)
        offset_y = random.randint(-10, 10)

        self.run_adb("shell", "input", "tap", str(x + offset_x), str(y + offset_y))
        time.sleep(2)
        print("  [OK] 탭 테스트 완료")

    def test_back(self):
        """뒤로가기 테스트"""
        print("\n[TEST 6] 뒤로가기")

        self.run_adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)
        print("  [OK] 뒤로가기 완료")

    def test_incognito_mode(self):
        """시크릿 모드 테스트"""
        print("\n[TEST 7] 시크릿 모드")

        intent = self.provider.create_incognito_url_intent("https://m.naver.com")
        cmd = intent.to_command()
        print(f"  명령어: adb shell {cmd}")

        self.run_adb("shell", *cmd.split())
        time.sleep(3)
        print("  [OK] 시크릿 모드 테스트 완료")

    def test_full_workflow(self, keyword: str = "맛집 추천"):
        """전체 워크플로우 테스트"""
        print(f"\n[WORKFLOW] 전체 워크플로우 테스트: '{keyword}'")
        print("=" * 50)

        # 1. 블로그 검색
        print("\n[1/5] 블로그 검색 열기...")
        intent = self.provider.create_naver_search_intent(keyword, category="blog")
        self.run_adb("shell", *intent.to_command().split())
        time.sleep(random.uniform(2.5, 4.0))

        # 2. 첫 번째 결과 클릭
        print("[2/5] 첫 번째 결과 클릭...")
        x, y = self.provider.get_naver_first_result()
        offset_x = random.randint(-10, 10)
        offset_y = random.randint(-10, 10)
        self.run_adb("shell", "input", "tap", str(x + offset_x), str(y + offset_y))
        time.sleep(random.uniform(2.0, 3.5))

        # 3. 콘텐츠 읽기 (스크롤)
        print("[3/5] 콘텐츠 읽기 (스크롤)...")
        scroll_count = random.randint(4, 6)
        for i in range(scroll_count):
            start_y = random.randint(1500, 1700)
            end_y = random.randint(900, 1100)
            duration = random.randint(400, 600)

            self.run_adb("shell", "input", "swipe",
                        "540", str(start_y), "540", str(end_y), str(duration))
            time.sleep(random.uniform(1.0, 2.5))

            # 가끔 위로 스크롤
            if random.random() < 0.2:
                self.run_adb("shell", "input", "swipe", "540", "1000", "540", "1200", "400")
                time.sleep(random.uniform(0.5, 1.0))

        # 4. 뒤로가기
        print("[4/5] 뒤로가기...")
        self.run_adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(random.uniform(1.0, 2.0))

        # 5. 목록에서 추가 스크롤
        print("[5/5] 목록 추가 탐색...")
        self.run_adb("shell", "input", "swipe", "540", "1400", "540", "900", "500")
        time.sleep(1.0)

        print("\n[OK] 전체 워크플로우 테스트 완료!")
        print("=" * 50)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("[TEST] NaverChromeUse 실제 디바이스 테스트")
        print("=" * 60)

        # 연결 확인
        if not self.check_connection():
            return False

        # 디바이스 정보
        self.get_device_info()

        # Chrome 확인
        if not self.check_chrome_installed():
            return False

        # 테스트 실행
        try:
            self.test_open_naver_home()
            time.sleep(2)

            self.test_naver_blog_search("서울 맛집")
            time.sleep(2)

            self.test_scroll(3)
            time.sleep(1)

            self.test_back()
            time.sleep(1)

            self.test_naver_shopping_search("갤럭시 폴드")
            time.sleep(2)

            self.test_back()
            time.sleep(1)

            # 전체 워크플로우
            self.test_full_workflow("제주도 여행")

            print("\n" + "=" * 60)
            print("[OK] 모든 테스트 완료!")
            print("=" * 60)
            return True

        except Exception as e:
            print(f"\n[ERROR] 테스트 중 오류 발생: {e}")
            return False


def main():
    """메인 함수"""
    tester = RealDeviceTester()

    if len(sys.argv) > 1:
        # 특정 테스트만 실행
        test_name = sys.argv[1]

        if not tester.check_connection():
            sys.exit(1)

        if test_name == "home":
            tester.test_open_naver_home()
        elif test_name == "blog":
            keyword = sys.argv[2] if len(sys.argv) > 2 else "맛집"
            tester.test_naver_blog_search(keyword)
        elif test_name == "shopping":
            keyword = sys.argv[2] if len(sys.argv) > 2 else "노트북"
            tester.test_naver_shopping_search(keyword)
        elif test_name == "scroll":
            tester.test_scroll()
        elif test_name == "workflow":
            keyword = sys.argv[2] if len(sys.argv) > 2 else "맛집 추천"
            tester.test_full_workflow(keyword)
        elif test_name == "incognito":
            tester.test_incognito_mode()
        else:
            print(f"알 수 없는 테스트: {test_name}")
            print("사용 가능: home, blog, shopping, scroll, workflow, incognito")
    else:
        # 전체 테스트
        tester.run_all_tests()


if __name__ == "__main__":
    main()
