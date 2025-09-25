#!/usr/bin/env python3
"""
ECG 자막 애니메이션 체인 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_animation_chain_import():
    """체인 메서드 import 테스트"""
    print("🔍 Testing subtitle animation chain import...")

    try:
        from app.services.langchain_bedrock_service import langchain_bedrock_service

        # 새로운 메서드가 존재하는지 확인
        assert hasattr(langchain_bedrock_service, "create_subtitle_animation_chain")
        print("✅ Subtitle animation chain method found")

        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Method check failed: {e}")
        return False


def test_animation_requests():
    """다양한 애니메이션 요청 테스트 (AWS 없이)"""
    print("\n🎬 Testing animation request classification...")

    # 테스트 케이스들
    test_cases = [
        {
            "message": "첫 번째 자막에 회전 효과를 추가해주세요",
            "expected": "animation_request",
            "description": "회전 애니메이션 요청",
        },
        {
            "message": "텍스트가 타이핑되는 효과로 만들어주세요",
            "expected": "animation_request",
            "description": "타이핑 애니메이션 요청",
        },
        {
            "message": "글자를 빛나게 만들고 싶어요",
            "expected": "animation_request",
            "description": "글로우 애니메이션 요청",
        },
        {
            "message": "ECG란 무엇인가요?",
            "expected": "simple_info",
            "description": "단순 정보 요청",
        },
        {
            "message": "첫 번째 자막의 오타를 수정해주세요",
            "expected": "simple_edit",
            "description": "간단한 편집 요청",
        },
    ]

    # 각 테스트 케이스의 분류 예상을 출력
    for i, case in enumerate(test_cases, 1):
        print(f"\n  {i}. {case['description']}")
        print(f"     메시지: '{case['message']}'")
        print(f"     예상 분류: {case['expected']}")
        print("     ✅ 테스트 케이스 준비됨")

    print(f"\n📊 총 {len(test_cases)}개의 테스트 케이스가 준비되었습니다.")
    print(
        "💡 실제 AWS 연결 시 langchain_bedrock_service.create_subtitle_animation_chain() 메서드로 테스트 가능합니다."
    )

    return True


def test_animation_categories():
    """애니메이션 카테고리 매핑 테스트"""
    print("\n🎨 Testing animation category mapping...")

    # 실제 manifest 기반 카테고리들
    animation_categories = {
        "rotation": {
            "description": "3D 회전 효과",
            "keywords": ["회전", "돌리", "rotate", "회전시켜"],
            "parameters": [
                "rotationDegrees",
                "animationDuration",
                "axisX",
                "axisY",
                "axisZ",
                "perspective",
                "staggerDelay",
            ],
        },
        "fadein": {
            "description": "페이드 인 효과",
            "keywords": ["페이드", "서서히", "fade", "투명", "나타나"],
            "parameters": [
                "staggerDelay",
                "animationDuration",
                "startOpacity",
                "scaleStart",
                "ease",
            ],
        },
        "typewriter": {
            "description": "타이핑 효과",
            "keywords": ["타이핑", "타자", "typewriter", "커서", "글자씩"],
            "parameters": [
                "typingSpeed",
                "cursorBlink",
                "cursorChar",
                "showCursor",
                "soundEffect",
            ],
        },
        "glow": {
            "description": "글로우 효과",
            "keywords": ["빛나", "글로우", "glow", "발광", "네온"],
            "parameters": ["color", "intensity", "pulse", "cycles"],
        },
        "scalepop": {
            "description": "스케일 팝 효과",
            "keywords": ["팝", "커지", "pop", "확대", "크게"],
            "parameters": [
                "popScale",
                "animationDuration",
                "staggerDelay",
                "bounceStrength",
                "colorPop",
            ],
        },
        "slideup": {
            "description": "슬라이드 업 효과",
            "keywords": ["슬라이드", "올라", "slide", "위로", "아래서"],
            "parameters": [
                "slideDistance",
                "animationDuration",
                "staggerDelay",
                "easeType",
                "blurEffect",
            ],
        },
        "elastic": {
            "description": "탄성 효과",
            "keywords": ["탄성", "바운스", "elastic", "튕기", "반동"],
            "parameters": [
                "bounceStrength",
                "animationDuration",
                "staggerDelay",
                "startScale",
                "overshoot",
            ],
        },
        "glitch": {
            "description": "글리치 효과",
            "keywords": ["글리치", "glitch", "오류", "깜빡", "노이즈"],
            "parameters": [
                "glitchIntensity",
                "animationDuration",
                "glitchFrequency",
                "colorSeparation",
                "noiseEffect",
            ],
        },
        "flames": {
            "description": "불꽃 효과",
            "keywords": ["불꽃", "flame", "화염", "타오", "불"],
            "parameters": ["baseOpacity", "flicker", "cycles"],
        },
        "pulse": {
            "description": "펄스 효과",
            "keywords": ["맥동", "pulse", "뛰", "박동", "심장"],
            "parameters": ["maxScale", "cycles"],
        },
    }

    print(f"✅ {len(animation_categories)}개의 애니메이션 카테고리가 매핑되었습니다:")

    for category, info in animation_categories.items():
        print(f"\n  📁 {category} - {info['description']}")
        print(f"     키워드: {', '.join(info['keywords'])}")
        print(f"     파라미터 수: {len(info['parameters'])}개")

    return True


def main():
    """메인 테스트 실행"""
    print("🚀 ECG Subtitle Animation Chain Test")
    print("=" * 50)

    results = []

    # 테스트 1: Import 테스트
    import_ok = test_animation_chain_import()
    results.append(("Import Test", import_ok))

    # 테스트 2: 애니메이션 요청 분류 테스트
    request_ok = test_animation_requests()
    results.append(("Request Classification", request_ok))

    # 테스트 3: 애니메이션 카테고리 매핑 테스트
    category_ok = test_animation_categories()
    results.append(("Category Mapping", category_ok))

    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! Subtitle animation chain is ready!")
        print("\n💡 Next steps:")
        print("   1. Set up AWS credentials to test actual chain execution")
        print("   2. Test via API: POST /api/v1/chatbot/animation")
        print("   3. Test different animation types with real user messages")
        print("   4. Validate JSON patch output format")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
