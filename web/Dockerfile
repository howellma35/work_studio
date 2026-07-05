# 构建上下文为项目根目录，web/ 下的文件通过 web/ 前缀访问
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 docs 和 vehicle-agent/docs（博客动态加载需要）
COPY docs/ ./docs/
COPY vehicle-agent/docs/ ./vehicle-agent/docs/

# 复制前端源码
COPY web/package.json web/package-lock.json* ./
RUN npm install --registry https://registry.npmmirror.com

COPY web/ .
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制自定义 nginx 配置（支持 SPA 路由回退）
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
