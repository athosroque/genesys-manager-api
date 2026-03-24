# Stage 1: Build (Node.js)
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve (Nginx)
FROM nginx:alpine
# Copia o build pronto
COPY --from=build /app/dist /usr/share/nginx/html
# Copia a config do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
