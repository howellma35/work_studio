FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package.json package-lock.json* ./
RUN npm ci --production=false

# 复制源码并编译
COPY . .
RUN npm run build

# 创建数据目录
RUN mkdir -p /app/data

# 只保留生产依赖
RUN npm prune --production

EXPOSE 3000

CMD ["node", "dist/app.js"]
