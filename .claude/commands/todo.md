I have an idea for a change to my dotfiles system that I'd like to capture as a detailed TODO file.

**Template location:** Temp/TODO/_TEMPLATE.md
**Output location:** Temp/TODO/YYYY-MM-DD_<slug>.md (use today's date and a kebab-case slug based on the title)
**Example of a completed TODO:** Temp/TODO/2026-02-22_git-identity-per-directory.md

**My idea:**

$ARGUMENTS

---

**Instructions:**

1. Read the template at `Temp/TODO/_TEMPLATE.md` to understand the expected structure and sections.
2. Read the example at `Temp/TODO/2026-02-22_git-identity-per-directory.md` to understand the level of detail, tone, and thoroughness expected.
3. Ask me clarifying questions about the idea. Don't assume — ask. Cover:
   - What problem this solves and why it matters
   - The desired end state
   - Which files, tools, or systems are involved
   - Any constraints, preferences, or non-obvious requirements
   - Edge cases or interactions with other parts of the system
4. Once you have enough context, do your own research:
   - Read any relevant files in the codebase that the idea touches
   - Check existing configurations for conflicts or opportunities
   - Identify gotchas, migration concerns, or dependencies
5. Write the TODO file following the template structure. Every section should be filled in with specific, actionable detail — no placeholders or vague language. The goal is that any AI agent reading this single file in the future can understand the full context and implement it without ambiguity.
6. After writing, present a brief summary of what you captured and ask if anything needs adjusting.
