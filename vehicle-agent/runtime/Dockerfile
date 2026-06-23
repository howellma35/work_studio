FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY server.ts ./
RUN npx tsc --outDir dist

FROM node:22-alpine AS runner
WORKDIR /app
COPY package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
ENV RUNTIME_PORT=4000
ENV PYTHON_AGENT_URL=http://vehicle-backend:8001/copilotkit
EXPOSE 4000
CMD ["node", "dist/server.js"]
