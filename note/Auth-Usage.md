# 前端认证快速说明

## 环境变量
在项目根目录创建 `.env.local` 并填写：

```
VITE_REST_API_URL=<你的 REST API Gateway 地址>
VITE_WEBSOCKET_API_URL=<你的 WebSocket API Gateway 地址>
VITE_COGNITO_USER_POOL_ID=<Cognito User Pool ID>
VITE_COGNITO_CLIENT_ID=<Cognito App Client ID>
VITE_COGNITO_CLIENT_SECRET=<可选，若使用机密客户端>
VITE_COGNITO_REGION=<AWS 区域，例如 ap-southeast-2>
VITE_COGNITO_DOMAIN=https://<你的 Cognito 域名>
VITE_COGNITO_REDIRECT_SIGN_IN=https://localhost:5173/auth
VITE_COGNITO_REDIRECT_SIGN_OUT=https://localhost:5173/login
```

## 本地运行
```
npm install
npm run dev
```
访问 `http://localhost:5173`，使用 Cognito 用户名密码登录，或点击 **Continue with Google** 进行 Google OAuth（需在 Cognito 控制台配置 Google 身份提供商）。

## 认证流程
1. 用户名密码：调用 Cognito `Auth.signIn`，获取 ID Token 并写入本地存储。
2. Google 登录：跳转 Cognito Hosted UI → 谷歌授权 → 返回 `/auth` 回调页 → 获取 ID Token。
3. Token 自动附加在 REST 请求 `Authorization: Bearer <token>` 中。

## 常用排查
- 登录页报错 `Additional challenge required`：该账号被要求强制改密或启用 MFA，需要在 Cognito 控制台确认。
- Google 登录跳转失败：确认 Cognito 域名、Google redirect URI 与环境变量保持一致。
- API 返回 401：检查本地存储是否含有 ID Token，或在 Cognito 控制台确认该用户存在。
