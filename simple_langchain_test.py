#!/usr/bin/env python3
"""
Simple LangChain test without AWS dependencies
"""


def test_langchain_imports():
    """Test LangChain imports"""
    print("🔍 Testing LangChain imports...")

    try:
        import langchain  # type: ignore

        print(f"✅ LangChain version: {langchain.__version__}")
    except ImportError as e:
        print(f"❌ LangChain import failed: {e}")
        return False

    try:
        from langchain_aws import ChatBedrock  # type: ignore

        # Test basic usage to avoid unused import warnings
        _ = ChatBedrock
        print("✅ ChatBedrock import successful")
    except ImportError as e:
        print(f"❌ ChatBedrock import failed: {e}")
        return False

    try:
        # Import and test LangChain core components
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage  # type: ignore
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import StrOutputParser  # type: ignore

        # Test basic usage to avoid unused import warnings
        HumanMessage(content="test")
        AIMessage(content="test")
        SystemMessage(content="test")
        ChatPromptTemplate.from_template("test")
        StrOutputParser()

        print("✅ LangChain core components imported successfully")
    except ImportError as e:
        print(f"❌ LangChain core import failed: {e}")
        return False

    return True


def test_langchain_components():
    """Test LangChain component initialization without AWS"""
    print("\n🔧 Testing LangChain components...")

    try:
        from langchain_core.prompts import (  # type: ignore
            ChatPromptTemplate,
            SystemMessagePromptTemplate,
            HumanMessagePromptTemplate,
        )
        from langchain_core.output_parsers import StrOutputParser  # type: ignore
        from langchain_core.messages import HumanMessage, AIMessage  # type: ignore

        # Test prompt template creation
        system_template = "You are a helpful AI assistant for ECG caption editing tool."
        ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template("{input}"),
            ]
        )
        print("✅ Prompt template created successfully")

        # Test output parser
        StrOutputParser()
        print("✅ Output parser initialized successfully")

        # Test message creation
        HumanMessage(content="Hello")
        AIMessage(content="Hi there!")
        print("✅ Message objects created successfully")

        return True

    except Exception as e:
        print(f"❌ LangChain component test failed: {e}")
        return False


def test_chain_construction():
    """Test LangChain chain construction"""
    print("\n⛓️  Testing LangChain chain construction...")

    try:
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import StrOutputParser  # type: ignore
        from langchain_core.runnables import RunnableLambda  # type: ignore

        # Create a simple chain without LLM
        prompt = ChatPromptTemplate.from_template("Echo: {input}")

        # Mock LLM function for testing
        def mock_llm(messages):
            if hasattr(messages, "messages"):
                return f"Mock response to: {messages.messages[-1].content}"
            return f"Mock response to: {str(messages)}"

        StrOutputParser()

        StrOutputParser()

        # Test chain construction (without actual LLM)
        _ = prompt | RunnableLambda(mock_llm) | RunnableLambda(lambda x: x)
        print("✅ Chain construction successful (without LLM)")

        return True

    except Exception as e:
        print(f"❌ Chain construction test failed: {e}")
        return False


def main():
    """Run simple LangChain tests"""
    print("🚀 Simple LangChain Integration Test (No AWS Required)")
    print("=" * 55)

    # Run tests
    results = []

    # Test 1: Imports
    import_ok = test_langchain_imports()
    results.append(("Imports", import_ok))

    if not import_ok:
        print("\n❌ Import tests failed. Cannot proceed with other tests.")
        return False

    # Test 2: Components
    component_ok = test_langchain_components()
    results.append(("Components", component_ok))

    # Test 3: Chain construction
    chain_ok = test_chain_construction()
    results.append(("Chain Construction", chain_ok))

    # Summary
    print("\n" + "=" * 55)
    print("📋 Test Summary:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All basic LangChain tests passed!")
        print("\n💡 Next steps:")
        print("   1. Set up AWS credentials in .env file")
        print("   2. Run: python test_langchain_integration.py")
        print("   3. Test via API endpoints after FastAPI server starts")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
