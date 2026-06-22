# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 2026.06.x | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainer at the address listed in [pyproject.toml](pyproject.toml)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 1 week
- **Fix or mitigation**: within 30 days for critical issues

## Security Measures

This SDK implements:

- **Cookie encryption** via Fernet symmetric encryption (AES-128-CBC)
- **CSRF token validation** (minimum 16 characters)
- **Session lifetime limits** (4 hours default)
- **Rate limit detection** and retry with exponential backoff
- **Input validation** on all public methods

## Best Practices for Users

- Never hardcode credentials in source code
- Use environment variables or a secrets manager
- Rotate API tokens regularly
- Pin dependency versions in production
