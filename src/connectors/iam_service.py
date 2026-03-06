"""
IAM Service connector — calls rfq_iam_ms for authentication and user info.

Used to:
- Validate JWT tokens
- Resolve current user name / team from auth context
- Check team permissions for stage advancement (403 guard)

Methods:
- get_current_user(token)      — decode JWT → user info
- verify_team_access(token, team) — check if user belongs to team
"""
