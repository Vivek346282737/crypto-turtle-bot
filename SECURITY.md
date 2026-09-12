# Security Policy

## Reporting Security Issues
If you discover any security-related issues, please report them privately. Do not open public GitHub issues for sensitive vulnerabilities.

## Secret Management & Credential Safety
- Never commit .env, private keys (*.pem, *.key), or API secrets to version control.
- Always use .env.example as a structural reference template.
- If any credentials were ever committed historically, immediately revoke and rotate them on the respective exchange dashboard.
