FROM node:22-alpine AS build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.30-alpine

# Upgrade OS packages. The explicit libxml2 floor (CVE-2026-86144, fixed in 2.13.9-r3)
# also changes this layer's text so a stale cached `apk upgrade` layer from the CI
# GHA build cache is not reused. Fails the build if the fixed version is unavailable.
RUN apk upgrade --no-cache && apk add --no-cache "libxml2>=2.13.9-r3"

COPY infrastructure/docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
