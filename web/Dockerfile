ARG NODE_BASE_IMAGE=node:20-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NODE_BASE_IMAGE} AS builder

WORKDIR /web

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM ${NGINX_BASE_IMAGE}

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /web/dist /usr/share/nginx/html

EXPOSE 80
