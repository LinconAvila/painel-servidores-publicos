# Stage 1: build (Vite)
FROM node:20-alpine AS build

WORKDIR /app

# Copia só os manifests primeiro pra aproveitar cache de camadas
COPY package.json package-lock.json* ./
RUN npm ci

# Agora copia o resto do código e builda
COPY . .
RUN npm run build
# gera /app/dist (padrão do Vite)

# Stage 2: serve (Nginx)
FROM nginx:1.27-alpine AS serve

# Remove o default.conf padrão e coloca o nosso (SPA fallback)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia só os arquivos estáticos gerados no stage anterior
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]