# Blue FaaS - Spin K8s Deployment Tool

FastAPI 기반 Spin 애플리케이션 배포 도구입니다. Python Spin 애플리케이션을 WASM으로 빌드하고, AWS ECR에 푸시한 후, Kubernetes 환경에 SpinApp으로 배포하는 전체 파이프라인을 제공합니다.

## 주요 기능

- FastAPI REST API를 통한 모든 작업 수행
- MyPy를 통한 Python 코드 검증
- 단일 .py 파일 또는 zip 아카이브 업로드 지원
- 사전 구성된 venv 템플릿을 활용한 빌드 환경
- 백그라운드 작업 처리 및 상태 조회
- spin CLI를 subprocess로 호출하여 빌드/푸시/스캐폴드 수행
- SpinApp 매니페스트 생성 및 K8s 배포

## 요구사항

- Python 3.12+
- Spin 2.2+
- Kubernetes 클러스터 (SpinKube 설치됨)
- AWS ECR 접근 권한

## 설치

```bash
# 의존성 설치
pip install -e .

# 개발 의존성 포함 설치
pip install -e ".[dev]"
```

## 프로젝트 구조

```
src/
├── api/          # FastAPI 라우터
├── models/       # Pydantic 데이터 모델
├── services/     # 핵심 서비스 (빌드, 푸시, 배포 등)
└── config.py     # 설정 및 상수
tests/            # 테스트 코드
```

## 라이선스

MIT
