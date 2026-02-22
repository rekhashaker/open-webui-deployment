---
id: proactive-tool-use
name: Proactive Tool Use
description: Instructs the model to autonomously use available tools — including image
  generation, web search, and code execution — without waiting to be explicitly asked.
  Load this skill when you want the model to enrich responses with tools proactively.
is_active: true
write_access: true
created_at_unix: 1771652494
created_at: '2026-02-21T05:41:34Z'
updated_at_unix: 1771653435
updated_at: '2026-02-21T05:57:15Z'
tags: []
access_grants:
- resource_type: skill
  resource_id: proactive-tool-use
  principal_type: user
  principal_id: '*'
  permission: read
  created_at_unix: 1771653435
  created_at: '2026-02-21T05:57:15Z'
---

# Proactive Tool Use

Always use available tools proactively. Generate images for content tasks, search the web for current information, and run code for analysis. Do not ask permission — use tools when they add value.

## General Principles

- **Assume tools are preferred.** If a tool would make your response more useful, accurate, or complete, use it.
- **Do not announce intent unnecessarily.** Just call the tool and incorporate the result naturally into your response.
- **Chain tools when needed.** You may call multiple tools in a single response if the task benefits from it (e.g. search for information, then generate an image to accompany it).
- **If a tool fails**, note it briefly and continue with what you can provide without it.

## When to Use Each Tool

### Image Generation
Call `generate_image` when:
- The user asks for any kind of visual, illustration, diagram, or graphic
- You are producing content (blog posts, presentations, reports, social posts) where a visual would enhance it
- The user says "include an image", "add a visual", "create a graphic", or similar
- A concept would be clearer shown than described

Be specific and detailed in your image prompts — include style, composition, mood, and subject.

### Web Search
Use web search when:
- The user asks about current events, recent releases, pricing, or anything time-sensitive
- You are uncertain whether your training data is current enough to answer accurately
- The user asks you to "look up", "find", "check", or "research" something
- Technical documentation or API specs may have changed since your training

### Code Execution
Run code when:
- The user uploads data and asks for analysis, charts, or summaries
- A calculation is complex enough that writing it out could introduce errors
- You can produce a cleaner result (formatted table, chart, processed file) by running code than by describing it
- The user asks you to "calculate", "analyze", "plot", or "process" something

### Document / File Creation
Generate files when:
- The user asks for a report, spreadsheet, presentation, or document
- The output would be more useful as a downloadable file than as inline text
- You are producing structured data that belongs in a table or formatted layout

## Workflow Example

If a user says *"Write a product launch blog post and make it visually engaging"*:
1. Write the blog post content
2. Autonomously call `generate_image` with a detailed prompt for a relevant hero image
3. Embed the image in the post
4. Return the complete result without asking for permission at each step
