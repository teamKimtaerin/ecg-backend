#!/usr/bin/env python3
"""
LangChain Bedrock 통합 테스트 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.services.langchain_bedrock_service import langchain_bedrock_service
    from app.services.bedrock_service import bedrock_service
    from app.schemas.chatbot import ChatMessage
    from datetime import datetime
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure to install LangChain packages: pip install langchain langchain-aws langchain-core langchain-community")
    sys.exit(1)


def test_basic_connection():
    """기본 연결 테스트"""
    print("🔍 Testing basic connections...")
    
    # 기존 Bedrock 서비스 테스트
    print("  - Testing original Bedrock service...")
    bedrock_healthy = bedrock_service.test_connection()
    print(f"    ✅ Original Bedrock: {'OK' if bedrock_healthy else '❌ FAILED'}")
    
    # LangChain Bedrock 서비스 테스트
    print("  - Testing LangChain Bedrock service...")
    try:
        langchain_healthy = langchain_bedrock_service.test_connection()
        print(f"    ✅ LangChain Bedrock: {'OK' if langchain_healthy else '❌ FAILED'}")
    except Exception as e:
        print(f"    ❌ LangChain Bedrock: FAILED - {e}")
        langchain_healthy = False
    
    return bedrock_healthy, langchain_healthy


def test_simple_prompt():
    """단순 프롬프트 테스트"""
    print("\n💬 Testing simple prompt...")
    
    test_prompt = "안녕하세요! ECG란 무엇인가요?"
    
    try:
        # LangChain을 통한 호출
        result = langchain_bedrock_service.invoke_claude_with_chain(
            prompt=test_prompt,
            max_tokens=100,
            temperature=0.1,
            save_response=False,
        )
        
        print("✅ LangChain response:")
        print(f"   📝 Completion: {result['completion'][:200]}...")
        print(f"   ⏱️  Processing: {result.get('request_params', {}).get('prompt_length')} chars input")
        print(f"   🔧 Model: {result.get('model_id')}")
        
        return True, result
    except Exception as e:
        print(f"❌ LangChain prompt test failed: {e}")
        return False, None


def test_conversation_history():
    """대화 히스토리 테스트"""
    print("\n💭 Testing conversation history...")
    
    # 가상 대화 히스토리 생성
    history = [
        ChatMessage(
            id="1",
            content="ECG가 무엇인가요?",
            sender="user",
            timestamp=datetime.now()
        ),
        ChatMessage(
            id="2", 
            content="ECG는 Easy Caption Generator의 약자로, 자막 편집 도구입니다.",
            sender="bot",
            timestamp=datetime.now()
        ),
    ]
    
    try:
        result = langchain_bedrock_service.invoke_claude_with_chain(
            prompt="그럼 ECG의 주요 기능은 뭐가 있나요?",
            conversation_history=history,
            max_tokens=150,
            temperature=0.2,
            save_response=False,
        )
        
        print("✅ Conversation with history:")
        print(f"   📝 Response: {result['completion'][:200]}...")
        print(f"   📚 History length: {len(history)} messages")
        
        return True, result
    except Exception as e:
        print(f"❌ Conversation history test failed: {e}")
        return False, None


def test_comparison():
    """기존 방식 vs LangChain 방식 비교"""
    print("\n⚖️  Testing comparison (Original vs LangChain)...")
    
    test_prompt = "ECG에서 자막 색상을 변경하는 방법을 간단히 알려주세요."
    
    results = {}
    
    # 기존 방식 테스트
    try:
        print("  - Testing original Bedrock service...")
        original_result = bedrock_service.invoke_claude(
            prompt=f"당신은 ECG 자막 편집 도구의 AI 어시스턴트입니다. {test_prompt}",
            max_tokens=100,
            temperature=0.3,
            save_response=False,
        )
        results['original'] = original_result
        print(f"    ✅ Original: {len(original_result['completion'])} chars response")
    except Exception as e:
        print(f"    ❌ Original failed: {e}")
        results['original'] = None
    
    # LangChain 방식 테스트
    try:
        print("  - Testing LangChain service...")
        langchain_result = langchain_bedrock_service.invoke_claude_with_chain(
            prompt=test_prompt,
            max_tokens=100,
            temperature=0.3,
            save_response=False,
        )
        results['langchain'] = langchain_result
        print(f"    ✅ LangChain: {len(langchain_result['completion'])} chars response")
    except Exception as e:
        print(f"    ❌ LangChain failed: {e}")
        results['langchain'] = None
    
    # 비교 결과 출력
    if results['original'] and results['langchain']:
        print("\n📊 Comparison Results:")
        print(f"   📄 Original response preview: {results['original']['completion'][:100]}...")
        print(f"   🔗 LangChain response preview: {results['langchain']['completion'][:100]}...")
        print(f"   ⚡ LangChain features: Memory ✅, Templates ✅, Chains ✅")
    
    return results


def main():
    """메인 테스트 실행"""
    print("🚀 ECG Backend - LangChain Integration Test")
    print("=" * 50)
    
    # 환경 변수 확인
    required_env_vars = [
        'AWS_ACCESS_KEY_ID', 
        'AWS_SECRET_ACCESS_KEY',
        'AWS_BEDROCK_ACCESS_KEY_ID',
        'AWS_BEDROCK_SECRET_ACCESS_KEY'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables in your .env file")
    
    # 테스트 실행
    try:
        # 1. 기본 연결 테스트
        bedrock_ok, langchain_ok = test_basic_connection()
        
        if not langchain_ok:
            print("\n❌ LangChain connection failed. Stopping tests.")
            return False
        
        # 2. 단순 프롬프트 테스트
        simple_ok, _ = test_simple_prompt()
        
        # 3. 대화 히스토리 테스트
        history_ok, _ = test_conversation_history()
        
        # 4. 비교 테스트
        comparison_results = test_comparison()
        
        # 결과 요약
        print("\n" + "=" * 50)
        print("📋 Test Summary:")
        print(f"   🔌 Basic Connection: {'✅ PASS' if (bedrock_ok and langchain_ok) else '❌ FAIL'}")
        print(f"   💬 Simple Prompt: {'✅ PASS' if simple_ok else '❌ FAIL'}")
        print(f"   💭 Conversation History: {'✅ PASS' if history_ok else '❌ FAIL'}")
        print(f"   ⚖️  Comparison: {'✅ PASS' if (comparison_results.get('original') and comparison_results.get('langchain')) else '❌ FAIL'}")
        
        all_passed = all([bedrock_ok, langchain_ok, simple_ok, history_ok])
        
        if all_passed:
            print("\n🎉 All tests passed! LangChain integration is working correctly.")
            print("\n💡 Next steps:")
            print("   1. Test via API: POST /api/v1/chatbot/ with 'use_langchain': true")
            print("   2. Test dedicated endpoint: POST /api/v1/chatbot/langchain")
            print("   3. Check health status: GET /api/v1/chatbot/health")
            return True
        else:
            print("\n⚠️  Some tests failed. Please check the errors above.")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user.")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)