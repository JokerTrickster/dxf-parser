#!/usr/bin/env python3
"""
Claude API 연결 테스트 스크립트
"""
import os
from dotenv import load_dotenv
import anthropic

# 환경 변수 로드
load_dotenv()

def test_api_connection():
    """API 연결 테스트"""
    api_key = os.getenv('ANTHROPIC_API_KEY')

    print("=== Claude API 연결 테스트 ===\n")

    # API 키 확인
    if not api_key:
        print("❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일을 확인하세요.")
        return False

    if api_key == "여기에_실제_API_키_입력":
        print("❌ .env 파일에 실제 API 키를 입력해야 합니다.")
        print("   https://console.anthropic.com/ 에서 API 키 발급")
        return False

    if not api_key.startswith('sk-ant-'):
        print("❌ 유효하지 않은 API 키 형식입니다.")
        print("   API 키는 'sk-ant-'로 시작해야 합니다.")
        return False

    print(f"✓ API 키 형식: 올바름 ({api_key[:12]}...)")

    # API 호출 테스트
    try:
        print("\n🔄 Claude API 호출 중...")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "간단히 '연결 성공'이라고만 답해주세요."
                }
            ]
        )

        result = response.content[0].text

        print(f"✓ API 응답: {result}")
        print(f"✓ 모델: {response.model}")
        print(f"✓ 사용 토큰: {response.usage.input_tokens + response.usage.output_tokens}")

        print("\n✅ Claude API 연결 성공!")
        print("   dxf_ai_extractor.py를 사용할 준비가 되었습니다.")

        return True

    except anthropic.AuthenticationError:
        print("\n❌ 인증 실패: API 키가 유효하지 않습니다.")
        print("   API 키를 다시 확인하세요.")
        return False

    except anthropic.RateLimitError:
        print("\n❌ API 사용량 초과")
        print("   잠시 후 다시 시도하거나 크레딧을 확인하세요.")
        return False

    except Exception as e:
        print(f"\n❌ API 호출 실패: {e}")
        return False


if __name__ == '__main__':
    success = test_api_connection()
    exit(0 if success else 1)
