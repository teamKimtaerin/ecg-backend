#!/bin/bash
# 팀 PR 도구 설치 스크립트

echo "🔧 팀 PR 도구 설치 중..."

# 실행 권한 부여
chmod +x .claude/scripts/prm

# PATH에 추가 (bashrc)
if [ -f ~/.bashrc ]; then
    if ! grep -q ".claude/scripts" ~/.bashrc; then
        echo 'export PATH="$PATH:'"$(pwd)"'/.claude/scripts"' >> ~/.bashrc
        echo "✅ bashrc PATH에 추가됨"
    else
        echo "ℹ️  bashrc PATH에 이미 등록됨"
    fi
fi

# PATH에 추가 (zshrc)
if [ -f ~/.zshrc ]; then
    if ! grep -q ".claude/scripts" ~/.zshrc; then
        echo 'export PATH="$PATH:'"$(pwd)"'/.claude/scripts"' >> ~/.zshrc
        echo "✅ zshrc PATH에 추가됨"
    else
        echo "ℹ️  zshrc PATH에 이미 등록됨"
    fi
fi

echo ""
echo "🎉 설치 완료!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 사용법"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  작업 후 변경사항 추가:"
echo "   git add ."
echo ""
echo "2️⃣  PR 생성 (자동 커밋 + 푸시 + PR):"
echo '   prm "Feat: 블로그 생성"'
echo ""
echo "3️⃣  Claude Code에서 분석:"
echo "   - 자동으로 클립보드에 복사된 프롬프트를 붙여넣기"
echo "   - 분석 결과를 복사해서 터미널에 붙여넣기"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  필수 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. GitHub CLI 설치:"
echo "   brew install gh"
echo ""
echo "2. GitHub 로그인:"
echo "   gh auth login"
echo ""
echo "3. Claude Code 접속:"
echo "   https://claude.ai/code"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 PATH 적용을 위해 터미널을 재시작하거나 다음 명령어 실행:"
echo "   source ~/.zshrc  (또는 source ~/.bashrc)"
echo ""