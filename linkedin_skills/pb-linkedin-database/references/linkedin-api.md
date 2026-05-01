# LinkedIn API Notes

Use this file to keep the skill honest about what is possible with LinkedIn right now.

## Current Direction

Start with manual or exported metrics imports into SQLite.
Treat direct LinkedIn API sync as optional and gated behind access checks.

## Official Constraints

Based on current official LinkedIn documentation:

- The Community Management API is versioned and requires the `Linkedin-Version` and `X-Restli-Protocol-Version: 2.0.0` headers.
- The Posts API has permission requirements such as `w_member_social`, `w_organization_social`, or `r_organization_social` depending on the action.
- Post analytics access is gated and versioned. The current official analytics documentation points to `memberCreatorPostAnalytics` for member post analytics.
- LinkedIn API products and versions are subject to deprecation and migration windows.

## What This Means For The Skill

- Do not assume live API access exists.
- Do not promise automatic analytics sync until credentials and product access are confirmed.
- Prefer a manual JSON import path first.
- If the user later provisions LinkedIn credentials, add them explicitly rather than reusing unrelated `.env` keys.

## Suggested Future Env Names

- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_VERSION`
- `LINKEDIN_MEMBER_URN`
- `LINKEDIN_ORGANIZATION_URN`

## Official Sources

- Posts API: `https://learn.microsoft.com/is-is/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2025-08`
- Member Post Statistics: `https://learn.microsoft.com/en-us/linkedin/marketing/community-management/members/post-statistics?view=li-lms-2025-11`
- Community Management migration guide: `https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-api-migration-guide?view=li-lms-2025-09&viewFallbackFrom=li-lms-2023-02`
