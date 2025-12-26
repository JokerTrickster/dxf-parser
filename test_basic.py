#!/usr/bin/env python3
"""
기본 기능 테스트 스크립트
의존성 없이 구조 검증
"""
import os
import sys


def test_project_structure():
    """프로젝트 구조 확인"""
    print("✓ 프로젝트 구조 검증...")

    required_dirs = [
        'src/core',
        'src/ai',
        'src/models',
        'src/utils',
        'config'
    ]

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"  ✗ 디렉토리 없음: {dir_path}")
            return False
        print(f"  ✓ {dir_path}")

    return True


def test_config_files():
    """설정 파일 확인"""
    print("\n✓ 설정 파일 검증...")

    required_files = [
        'config/layer_categories.yaml',
        'config/llm_prompts.yaml',
        'requirements.txt',
        '.env.example'
    ]

    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"  ✗ 파일 없음: {file_path}")
            return False
        print(f"  ✓ {file_path}")

    return True


def test_python_modules():
    """Python 모듈 구조 확인"""
    print("\n✓ Python 모듈 검증...")

    required_modules = [
        'src/core/dxf_parser.py',
        'src/core/block_extractor.py',
        'src/core/geometry_processor.py',
        'src/ai/llm_classifier.py',
        'src/ai/cache_manager.py',
        'src/models/layer_schema.py',
        'src/models/extracted_entity.py',
        'src/utils/logger.py',
        'src/utils/validator.py',
        'dxf_ai_extractor.py'
    ]

    for module_path in required_modules:
        if not os.path.exists(module_path):
            print(f"  ✗ 모듈 없음: {module_path}")
            return False
        print(f"  ✓ {module_path}")

    return True


def test_syntax():
    """Python 구문 검사"""
    print("\n✓ 구문 검사...")

    import py_compile

    modules = [
        'dxf_ai_extractor.py',
        'src/core/dxf_parser.py',
        'src/core/block_extractor.py',
        'src/core/geometry_processor.py',
        'src/ai/llm_classifier.py',
        'src/ai/cache_manager.py',
        'src/models/layer_schema.py',
        'src/models/extracted_entity.py',
        'src/utils/logger.py',
        'src/utils/validator.py'
    ]

    all_ok = True
    for module in modules:
        try:
            py_compile.compile(module, doraise=True)
            print(f"  ✓ {module}")
        except py_compile.PyCompileError as e:
            print(f"  ✗ {module}: {e}")
            all_ok = False

    return all_ok


def main():
    print("=== DXF AI Extractor - 기본 테스트 ===\n")

    tests = [
        ("프로젝트 구조", test_project_structure),
        ("설정 파일", test_config_files),
        ("Python 모듈", test_python_modules),
        ("구문 검사", test_syntax)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} 실패: {e}")
            results.append((test_name, False))

    print("\n" + "="*50)
    print("테스트 결과:")
    print("="*50)

    for test_name, result in results:
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    print("="*50)
    if all_passed:
        print("✓ 모든 테스트 통과!")
        return 0
    else:
        print("✗ 일부 테스트 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
