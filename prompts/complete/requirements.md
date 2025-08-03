./projects/${idea_name}/idea.mdを読んで、${sdd_path}のRequirement Gatheringセクションに従って./projects/${idea_name}/requirements.mdに要件定義を記載してください。

具体的には以下の形式で記載してください：

1. Introduction セクション
   - 機能の概要を明確に記述

2. Requirements セクション
   - 各要件を階層的な番号付きリストで記載
   - 各要件には以下を含める：
     - User Story: "As a [role], I want [feature], so that [benefit]" 形式
     - Acceptance Criteria: EARS形式（Easy Approach to Requirements Syntax）で記載
       - WHEN [event] THEN [system] SHALL [response]
       - IF [precondition] THEN [system] SHALL [response]

エッジケース、ユーザー体験、技術的制約、成功基準を考慮して、包括的な要件を定義してください。