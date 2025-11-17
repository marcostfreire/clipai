# ClipAI - Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please email us at security@yourdomain.com or open a private security advisory on GitHub.

**Please do not open public issues for security vulnerabilities.**

## Security Measures

### API Security
- CORS configuration for allowed origins
- Input validation with Pydantic
- File upload size limits (500MB default)
- File type validation
- SQL injection protection via SQLAlchemy ORM

### Data Security
- Environment variables for sensitive data
- No API keys in code
- Secure database connections
- Redis authentication recommended

### File Storage
- Temporary file cleanup
- Automatic deletion of old videos (7 days)
- Storage path validation
- File permissions

### Production Recommendations
1. Use HTTPS/TLS in production
2. Enable rate limiting
3. Set up firewall rules
4. Use strong database passwords
5. Rotate API keys regularly
6. Monitor logs for suspicious activity
7. Keep dependencies updated
8. Use secure environment variables
9. Enable database backups
10. Implement proper access controls

### Dependencies
We regularly update dependencies to patch security vulnerabilities. Run:

```bash
# Backend
pip install --upgrade -r requirements.txt

# Frontend
npm audit fix
```

### Reporting Process
1. Email security@yourdomain.com with details
2. We'll acknowledge within 48 hours
3. We'll investigate and provide updates
4. Fix will be released as soon as possible
5. Credit will be given (if desired)

## Security Best Practices for Deployment

### Environment Variables
Never commit `.env` files. Use:
- Railway Secrets
- Vercel Environment Variables
- AWS Secrets Manager
- Azure Key Vault

### Database
- Use strong passwords (16+ characters)
- Enable SSL connections
- Restrict network access
- Regular backups
- Monitor for unusual activity

### API Keys
- Rotate Gemma API keys periodically
- Use separate keys for dev/staging/prod
- Monitor API usage quotas
- Restrict key permissions

### Monitoring
- Set up Sentry for error tracking
- Enable CloudWatch/DataDog logs
- Monitor unusual traffic patterns
- Alert on failed authentication attempts

## Known Security Considerations

### Video Processing
- FFmpeg vulnerabilities: Keep FFmpeg updated
- Untrusted video files: Validate and sanitize
- Resource exhaustion: Implement rate limiting

### AI Services
- API key exposure: Never log API keys
- Quota limits: Monitor usage
- Malicious prompts: Validate inputs

### File Uploads
- File size limits enforced (500MB)
- File type validation
- Virus scanning recommended (ClamAV)
- Storage quota monitoring

## Compliance
- GDPR: Implement user data deletion
- CCPA: Provide data export
- SOC 2: Audit logging
- PCI DSS: Not applicable (no payment processing)
