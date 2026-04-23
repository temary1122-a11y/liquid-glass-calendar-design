---
description: Cascade AI behavior optimization for this project
trigger: always
---

# CASCADE AI BEHAVIOR OPTIMIZATION

## MEMORY & CONTEXT RETENTION
- ALWAYS check existing memories before assuming information is forgotten
- Use `create_memory` tool for critical project information
- Verify memory relevance before using it
- If memory seems stale, ask user to confirm

## TASK MANAGEMENT
- Use `todo_list` tool for ALL multi-step tasks
- Mark tasks as completed IMMEDIATELY after finishing
- Break complex tasks into smaller subtasks
- Update user on progress regularly

## DEBUGGING APPROACH
1. Read relevant files first before making changes
2. Add logging before fixing issues
3. Test hypothesis with minimal changes
4. Verify fix doesn't break other functionality
5. Add regression tests when appropriate

## CODE CHANGES
- Read FULL file before editing
- Use `multi_edit` for multiple changes in same file
- Show diff before applying (when requested)
- Test changes locally if possible
- Commit with descriptive messages

## COMMUNICATION
- Be concise and direct
- Avoid acknowledgment phrases
- Start responses with substantive content
- Use markdown for code and formatting
- Summarize after complex operations

## TOOL USAGE
- Use parallel tool calls when possible
- Batch independent operations
- Keep dependent commands sequential
- NEVER use bash for search operations
- Use Grep/find_by_name instead

## MODEL SELECTION
- Use `reasoning` model for complex analysis
- Use `heavy_quality` for code generation
- Use `ultra_fast` for quick responses
- Use `very_large_deep` for large context analysis

## ERROR HANDLING
- Read error messages carefully
- Check logs before guessing
- Ask for clarification when uncertain
- Provide specific error context to user

## DEPLOYMENT
- Verify changes work before deploying
- Check deployment logs after deploy
- Test critical paths post-deploy
- Rollback quickly if issues arise
