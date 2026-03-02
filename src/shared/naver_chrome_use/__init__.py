"""
NaverChromeUse Module

Chrome 브라우저를 통한 네이버 서비스 자동화 시스템

핵심 원칙:
- 네이티브 네이버 앱 미사용
- Chrome/Samsung Internet 등 브라우저를 통한 접속
- 디바이스 루팅 불필요

Components:
- NaverChromeUseProvider: 브라우저 선택 및 카드 제공
- NaverUrlBuilder: 네이버 URL 생성 헬퍼
- BrowserCard: 브라우저별 자동화 명세
"""

from .provider import NaverChromeUseProvider, BrowserConfig
from .url_builder import NaverUrlBuilder
from .cdp_client import CdpClient

__all__ = [
    'NaverChromeUseProvider',
    'BrowserConfig',
    'NaverUrlBuilder',
    'CdpClient',
]
