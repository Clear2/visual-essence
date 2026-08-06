# Contributing to Visual Essence

[English](#english) | [简体中文](#简体中文)

## English

Thank you for helping improve Visual Essence. Keep changes focused, testable,
and safe for users who submit third-party URLs.

### Development workflow

1. Create a branch from `main`.
2. Install dependencies with `make install`.
3. Add or update tests with every behavior change.
4. Run `make check` before opening a pull request.
5. Update both `README.md` and `README_zh.md` for user-facing changes.

Use Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, and `chore:`. Pull requests should explain the user-visible change,
the verification performed, and any security or compatibility tradeoffs.

Never commit API keys, cookies, signed media URLs, downloaded media, local
conversation data, or generated build output. Extraction changes must preserve
the outbound URL validation and redirect checks documented in
`backend/AGENTS.md`.

## 简体中文

感谢你参与改进 Visual Essence。提交应保持目标清晰、可测试，并确保用户提交第三方链接时的安全边界不被削弱。

### 开发流程

1. 从 `main` 创建分支。
2. 使用 `make install` 安装依赖。
3. 每项行为变更都需要新增或更新测试。
4. 创建 Pull Request 前运行 `make check`。
5. 面向用户的变更需要同步更新 `README.md` 和 `README_zh.md`。

提交信息建议使用 `feat:`、`fix:`、`docs:`、`test:`、`refactor:`、`chore:` 等 Conventional Commits 前缀。Pull Request 应说明用户可见变化、验证方式，以及安全性或兼容性取舍。

请勿提交 API Key、Cookie、签名媒体地址、下载的视频、本地对话数据或构建产物。提取逻辑的改动必须保留 `backend/AGENTS.md` 中记录的出站 URL 与逐跳重定向校验。
