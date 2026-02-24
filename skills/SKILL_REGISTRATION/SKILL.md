---
name: Skill Registration Protocol
description: Standard process for creating and registering new agent skills.
---

# SKILL REGISTRATION PROTOCOL

Use this process when you need to formalize a new capability for the AI Agent team.

## Step 1: Identification
Observe a recurring user request or a complex multi-step process that can be automated or structured.

## Step 2: Directory Structure
Create a new directory under `skills/` using SNAKE_CASE naming.
```
skills/
  NEW_SKILL_NAME/
    SKILL.md
    scripts/ (optional)
    examples/ (optional)
```

## Step 3: Documentation (SKILL.md)
The `SKILL.md` file MUST follow this format:
- **YAML Frontmatter**: `name` and `description`.
- **Overview**: What the skill does.
- **Prerequisites**: Tools or libraries needed.
- **Workflow**: Step-by-step instructions.
- **Examples**: Sample inputs and expected outputs.

## Step 4: Verification
Test the skill by following its own instructions. Ensure it works as described.

## Step 5: Announcement
The Skill Specialist should announce the new skill in the latest `walkthrough.md`.
