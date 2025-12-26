#!/usr/bin/env python3
"""
Claude API 간단 테스트 (의존성 최소화)
"""
import os
import sys

# .env 파일에서 직접 읽기
def load_api_key():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY='):
                    return line.split('=', 1)[1].strip()
    return None

def test_api():
    print("=== Claude API 연결 테스트 ===\n")

    api_key = load_api_key()

    if not api_key:
        print("❌ .env 파일에서 API 키를 찾을 수 없습니다.")
        return False

    print(f"✓ API 키 로드: {api_key[:20]}...")

    # anthropic 라이브러리 확인
    try:
        import anthropic
        print("✓ anthropic 라이브러리: 설치됨")
    except ImportError:
        print("\n⚠️  anthropic 라이브러리가 설치되지 않았습니다.")
        print("\n다음 명령어로 설치하세요:")
        print("  python3 -m venv venv")
        print("  source venv/bin/activate")
        print("  pip install anthropic")
        return False

    # API 호출
    try:
        print("\n🔄 Claude API 호출 중...\n")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model='claude-3-5-sonnet-20241022',
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "DXF 파일의 'PARK_일반' 블록은 어떤 종류인가요? JSON 형식으로 답해주세요: {\"category\": \"카테고리\", \"type\": \"타입\"}"
                }
            ]
        )

        result = response.content[0].text

        print(f"✓ API 응답:\n{result}\n")
        print(f"✓ 모델: {response.model}")
        print(f"✓ 입력 토큰: {response.usage.input_tokens}")
        print(f"✓ 출력 토큰: {response.usage.output_tokens}")
        print(f"✓ 예상 비용: ~${(response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1000000:.6f}")

        print("\n✅ Claude API 연결 성공!")
        print("   DXF 추출기를 사용할 준비가 되었습니다.")

        return True

    except Exception as e:
        print(f"\n❌ API 호출 실패: {e}")
        print("\n가능한 원인:")
        print("  1. API 키가 유효하지 않음")
        print("  2. 네트워크 연결 문제")
        print("  3. API 크레딧 부족")
        return False

if __name__ == '__main__':
    try:
        success = test_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n중단됨")
        sys.exit(1)
