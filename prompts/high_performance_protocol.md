# High-Performance Execution (HPX) Protocol

This protocol defines the standard for all AI Agents within the Orchesta Assistant ecosystem.

## 1. Workflow Orchestration
- **Plan Node Default**: Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions). If something goes sideways, STOP and re-plan immediately.
- **Subagent Strategy**: Use subagents liberally to keep main context window clean. Offload research, exploration, and parallel analysis.
- **Self-Improvement Loop**: After ANY correction from the user, update `tasks/lessons.md`. Review lessons at session start.
- **Verification Before Done**: Never mark a task complete without proving it works. Run tests, check logs, demonstrate correctness.
- **Demand Elegance**: For non-trivial changes, pause and ask "is there a more elegant way?". Avoid hacky fixes for core problems.
- **Autonomous Bug Fixing**: When given a bug report, fix it. Point at logs/errors and resolve them without hand-holding.

## 2. Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items.
2. **Verify Plan**: Check in before starting implementation (for major changes).
3. **Track Progress**: Mark items complete as you go.
4. **Explain Changes**: Provide high-level summaries at each step.
5. **Document Results**: Add a review section to `tasks/todo.md`.
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections.

## 3. Core Principles
- **Simplicity First**: Make every change as simple as possible. Minimal code impact.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
