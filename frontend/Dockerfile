FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package.json
COPY package*.json ./

# Instalar dependências (npm install para regenerar lock file)
RUN npm install --legacy-peer-deps

# Copiar código
COPY . .

# Build da aplicação
RUN npm run build

# Estágio de produção
FROM nginx:alpine

# Copiar build
COPY --from=builder /app/build /usr/share/nginx/html

# Copiar configuração nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
