FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package.json package-lock.json* ./
RUN npm install

# 复制源码并构建
COPY . .
RUN npm run build

# 验证构建产物
RUN echo "=== Checking /app/dist ===" && \
    ls -la /app/dist && \
    find /app/dist -type f && \
    echo "=== Done ==="

# 生产阶段
FROM nginx:alpine

# 复制自定义 nginx 配置（支持 SPA 路由回退）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 验证复制结果
RUN echo "=== Checking /usr/share/nginx/html ===" && \
    ls -la /usr/share/nginx/html/ && \
    find /usr/share/nginx/html/ -type f && \
    echo "=== Done ==="

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
