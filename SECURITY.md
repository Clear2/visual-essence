# Security Policy

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue. Use the
repository host's private security-advisory feature to report it to the
maintainers. If that feature is unavailable, open a minimal issue asking for a
private contact channel without including exploit details.

Include the affected version or commit, reproduction conditions, impact, and a
suggested remediation when possible. Maintainers should acknowledge a complete
report within seven days and coordinate disclosure after a fix is available.

## Supported versions

Until the first stable release, security fixes are applied to the latest commit
on `main` only.

## Scope

Reports involving SSRF protections, redirect validation, signed media URL
exposure, secret handling, conversation data access, or unsafe rendering of
model output are especially valuable. Testing must use content and systems you
are authorized to access.

## 安全问题报告

请不要在公开 Issue 中披露漏洞细节。优先使用代码托管平台的私有 Security Advisory；若不可用，只创建一个不含攻击细节的简短 Issue，请维护者提供私下联系方式。
