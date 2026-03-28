---
description: "Implement a new feature for puree based on a CHANGES.md file"
agent: agent
argument-hint: "Describe implementing a feature from a CHANGES.md file"
---

Implement a feature requested by the user from the [CHANGES.md](../../CHANGES.md). The user will provide the name of the feature/number of the feature/priority of the feature/tell you a range of features, based on numbers/names/priority.

> VERY IMPORTANT!
>
> **If the user provided a range of features or the entire CHANGES.md to be implemented, you must commit each feature using the commit message structure of puree (see CONTRIBUTING.md) to commit that feature in particular, do not commit multiple features at once under the same commit, so the user can see the features implemented very neatly and organized in the commit history.**

## Implementation Structure

1. You need to provide the user with a plan of how exactly you will implement this
  - in this step you can also ask questions to clarify anything with the user;
  - features in CHANGES.md files are not very detailed and require a few research steps before actually implementing anything or proposing a plan to the user, assume that the CHANGES.md are useful, but are a first take and might not be perfect or fully factual;
  - every single time a repository is mentioned, or framework or library or anything external needed to implement a feature, research it briefly before making the plan to make sure it passes basic sanity checks to fit the architecture;
  - the plan must be made in a PLAN-FEATURE.md in the root of the workspace

2. After the user approves the implementation plan you must go ahead and implement according to plan
  - this step might require new research;
  - remember to always stay grounded and double check you info online, especially when it comes to intricate logic or frameworks/dependencies/APIs/libraries or whatever other external things that require some grounding to avoid hallucinations;
  - it's important to split the implementation in steps that you can handoff to different subagents so we can keep the context window under control and avoid timeouts or hallucinations;

3. After implementing the feature, you must also update any docs or skills or instructions/prompts that reference functionality or features of `puree`, like README, documents in docs/, .agents/, .github/
