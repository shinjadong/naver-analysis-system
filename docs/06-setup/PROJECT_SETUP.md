# 프로젝트 설정 가이드

## 개요
이 문서는 Naver AI Evolution 시스템의 설정 방법을 안내합니다.

## 필수 요구사항

### 하드웨어
- RAM: 16GB 이상 권장
- 저장공간: 50GB 이상
- CPU: 4코어 이상

### 소프트웨어
- Windows 10/11 (WSL2 활성화)
- Python 3.10+
- Docker Desktop
- Android SDK / ADB

## Windows 환경 설정

### 1. WSL2 활성화
```powershell
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

### 2. 프로젝트 설정
```powershell
cd C:\ai-projects\naver-ai-evolution
.\scripts\setup_windows.ps1
```

### 3. 환경 변수 설정
```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
$env:PROJECT_ENV = "development"
```

## WSL 환경 설정

### 1. 프로젝트 설정
```bash
cd /mnt/c/ai-projects/naver-ai-evolution
bash scripts/setup_wsl.sh
```

### 2. Docker 서비스 시작
```bash
docker-compose -f docker-compose.yml up -d
```

## 디바이스 연결

### 에뮬레이터 연결
```bash
adb connect localhost:5555
adb devices
```

### 실제 기기 연결
1. USB 디버깅 활성화
2. USB 케이블 연결
3. `adb devices`로 확인

## 문제 해결

### ADB 연결 실패
```bash
adb kill-server
adb start-server
adb devices
```

### WSL 네트워크 문제
```powershell
wsl --shutdown
wsl
```
