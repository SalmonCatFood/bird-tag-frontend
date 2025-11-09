# BirdTag Frontend - Deployment Guide

## Overview

This guide covers deploying the BirdTag frontend to various hosting platforms. The application is a static SPA (Single Page Application) built with Vue 3 and Vite.

## Pre-Deployment Checklist

Before deploying, ensure:

- [ ] API endpoints configured in `src/config/api.js`
- [ ] AWS backend services deployed and tested
- [ ] CORS configured on API Gateway
- [ ] Authentication system tested
- [ ] All features tested locally
- [ ] No linter errors (`npm run build` succeeds)
- [ ] Environment-specific configurations ready

## Build for Production

### Step 1: Configure Production APIs

Edit `src/config/api.js` with production endpoints:

```javascript
export const API_CONFIG = {
  REST_API_URL: 'https://your-prod-api.execute-api.region.amazonaws.com/prod',
  WEBSOCKET_API_URL: 'wss://your-prod-ws.execute-api.region.amazonaws.com/prod',
  AWS_REGION: 'your-region',
  // ... other configs
}
```

### Step 2: Build the Application

```bash
cd birdtag
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Step 3: Test Production Build Locally

```bash
npm run preview
```

Access at `http://localhost:4173` and test all features.

## Deployment Options

### Option 1: AWS S3 + CloudFront (Recommended)

Best for: Production deployment with AWS backend

#### Setup Steps

1. **Create S3 Bucket**

```bash
# Create bucket (replace with your bucket name)
aws s3 mb s3://birdtag-frontend --region us-east-1

# Enable static website hosting
aws s3 website s3://birdtag-frontend \
  --index-document index.html \
  --error-document index.html
```

2. **Configure Bucket Policy**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::birdtag-frontend/*"
  }]
}
```

3. **Upload Build Files**

```bash
# Sync dist folder to S3
cd dist
aws s3 sync . s3://birdtag-frontend --delete

# Set proper content types
aws s3 cp . s3://birdtag-frontend --recursive \
  --metadata-directive REPLACE \
  --cache-control max-age=31536000
```

4. **Create CloudFront Distribution**

```bash
aws cloudfront create-distribution \
  --origin-domain-name birdtag-frontend.s3.amazonaws.com \
  --default-root-object index.html
```

**CloudFront Settings:**
- Origin: S3 bucket
- Viewer Protocol Policy: Redirect HTTP to HTTPS
- Allowed HTTP Methods: GET, HEAD, OPTIONS
- Compress Objects: Yes
- Custom Error Responses:
  - 404 → /index.html (for SPA routing)
  - 403 → /index.html (for SPA routing)

5. **Configure Custom Domain (Optional)**

- Request SSL certificate in ACM
- Add CNAME record: `www.yourdomain.com → CloudFront URL`
- Update CloudFront alternate domain names

#### Deployment Script

Create `deploy-aws.sh`:

```bash
#!/bin/bash
set -e

echo "Building application..."
npm run build

echo "Uploading to S3..."
aws s3 sync dist/ s3://birdtag-frontend --delete

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"

echo "Deployment complete!"
```

---

### Option 2: Vercel

Best for: Quick deployment and automatic CI/CD

#### Setup Steps

1. **Install Vercel CLI**

```bash
npm install -g vercel
```

2. **Deploy**

```bash
cd birdtag
vercel
```

Follow the prompts:
- Link to existing project or create new
- Build command: `npm run build`
- Output directory: `dist`

3. **Configure Environment (if needed)**

```bash
vercel env add VITE_REST_API_URL production
vercel env add VITE_WEBSOCKET_API_URL production
```

4. **Production Deployment**

```bash
vercel --prod
```

#### Continuous Deployment

Connect GitHub repository to Vercel:
1. Go to vercel.com
2. Import Git Repository
3. Configure project settings
4. Every push to `main` auto-deploys

---

### Option 3: Netlify

Best for: Simple deployment with form handling

#### Setup Steps

1. **Install Netlify CLI**

```bash
npm install -g netlify-cli
```

2. **Deploy**

```bash
cd birdtag
netlify deploy
```

3. **Production Deployment**

```bash
netlify deploy --prod
```

#### Configuration File

Create `netlify.toml`:

```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
```

---

### Option 4: GitHub Pages

Best for: Open-source projects and demos

#### Setup Steps

1. **Install gh-pages**

```bash
npm install -D gh-pages
```

2. **Update package.json**

```json
{
  "scripts": {
    "deploy": "npm run build && gh-pages -d dist"
  }
}
```

3. **Configure vite.config.js**

```javascript
export default defineConfig({
  base: '/birdtag/', // Replace with your repo name
  // ... other config
})
```

4. **Deploy**

```bash
npm run deploy
```

5. **Configure GitHub**

- Go to repository Settings → Pages
- Source: `gh-pages` branch
- Visit: `https://username.github.io/birdtag/`

---

### Option 5: Docker Container

Best for: Self-hosted deployments

#### Dockerfile

Create `Dockerfile`:

```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Nginx Configuration

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
}
```

#### Build and Run

```bash
# Build image
docker build -t birdtag-frontend .

# Run container
docker run -d -p 80:80 birdtag-frontend
```

---

## Environment-Specific Configuration

### Multiple Environments

Create different config files:

```javascript
// src/config/api.development.js
export const API_CONFIG = {
  REST_API_URL: 'https://dev-api.example.com',
  // ... dev configs
}

// src/config/api.production.js
export const API_CONFIG = {
  REST_API_URL: 'https://api.example.com',
  // ... prod configs
}

// src/config/api.js
const env = import.meta.env.MODE
const config = await import(`./api.${env}.js`)
export const API_CONFIG = config.API_CONFIG
```

### Build Scripts

Add to `package.json`:

```json
{
  "scripts": {
    "build:dev": "vite build --mode development",
    "build:staging": "vite build --mode staging",
    "build:prod": "vite build --mode production"
  }
}
```

---

## Post-Deployment Verification

### Checklist

- [ ] Website loads successfully
- [ ] Login works correctly
- [ ] Can navigate between pages
- [ ] File upload initiates correctly
- [ ] WebSocket connects (check browser console)
- [ ] API calls succeed (check network tab)
- [ ] HTTPS is enforced
- [ ] No console errors
- [ ] Responsive on mobile devices
- [ ] All routes work (no 404s)

### Testing Commands

```bash
# Test REST API from deployed site
curl https://your-site.com

# Check security headers
curl -I https://your-site.com

# Test WebSocket (use browser console)
const ws = new WebSocket('wss://your-ws-url?token=test')
ws.onopen = () => console.log('Connected')
```

---

## Monitoring and Maintenance

### CloudWatch (for AWS)

Monitor:
- API Gateway request counts
- Lambda execution errors
- S3 bucket access logs
- CloudFront cache hit rates

### Performance Monitoring

Consider adding:
- Google Analytics
- Sentry (error tracking)
- LogRocket (session replay)
- Hotjar (user behavior)

### Updates and Maintenance

1. **Regular Updates**
   - Update dependencies monthly
   - Check for security vulnerabilities
   - Test after each update

2. **Automated Deployments**
   - Set up CI/CD pipeline
   - Run tests before deployment
   - Automatic rollback on failures

3. **Backup Strategy**
   - Keep previous builds
   - Version control all code
   - Document configuration changes

---

## Rollback Procedures

### AWS S3 + CloudFront

```bash
# Keep previous version
aws s3 cp s3://birdtag-frontend s3://birdtag-frontend-backup --recursive

# Rollback if needed
aws s3 sync s3://birdtag-frontend-backup s3://birdtag-frontend
aws cloudfront create-invalidation --distribution-id ID --paths "/*"
```

### Vercel/Netlify

Use web dashboard:
1. Go to Deployments
2. Select previous successful deployment
3. Click "Promote to Production"

---

## Troubleshooting

### Issue: 404 on page refresh

**Cause:** Server not configured for SPA routing

**Solution:**
- S3: Set error document to index.html
- CloudFront: Add custom error responses
- Nginx: Use `try_files $uri /index.html`

### Issue: CORS errors

**Cause:** API Gateway CORS not configured

**Solution:**
1. Enable CORS on API Gateway
2. Add OPTIONS method
3. Set proper headers

### Issue: WebSocket fails on HTTPS

**Cause:** Using `ws://` instead of `wss://`

**Solution:** Ensure WebSocket URL uses `wss://` protocol

### Issue: Slow initial load

**Solutions:**
- Enable gzip/brotli compression
- Set proper cache headers
- Use CDN (CloudFront)
- Optimize images

---

## Security Best Practices

1. **HTTPS Only**
   - Enforce HTTPS everywhere
   - Use HSTS headers

2. **Content Security Policy**
   ```html
   <meta http-equiv="Content-Security-Policy" 
         content="default-src 'self'; connect-src 'self' https://api.example.com wss://ws.example.com">
   ```

3. **Secure Headers**
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - X-XSS-Protection: 1; mode=block

4. **Environment Variables**
   - Never commit secrets
   - Use deployment platform env vars
   - Rotate credentials regularly

---

## Cost Optimization

### AWS

- Use CloudFront for caching (reduces S3 requests)
- Set appropriate S3 lifecycle policies
- Monitor data transfer costs
- Use Route 53 for DNS (if needed)

### Estimated Monthly Costs (AWS)

- S3 hosting: $1-5
- CloudFront: $5-20
- Route 53: $0.50 per hosted zone
- Total: ~$10-30/month (depending on traffic)

---

## Support Resources

- **AWS Documentation**: docs.aws.amazon.com
- **Vercel Docs**: vercel.com/docs
- **Netlify Docs**: docs.netlify.com
- **Vite Deployment**: vitejs.dev/guide/static-deploy

For project-specific issues, refer to:
- `Frontend-Development-Guide.md`
- `常见问题解决.md`
- AWS CloudWatch Logs

