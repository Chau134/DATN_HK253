# Multi-stage: build the Vite bundle, then serve it as static files via nginx.
FROM node:20-alpine AS build
WORKDIR /build

# VITE_API_BASE_URL is inlined at build time, so it must be available before
# `vite build`, not only at container runtime.
ARG VITE_API_BASE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
