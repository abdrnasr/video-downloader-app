FROM node:24.4-slim

# Set working directory
WORKDIR /app

# Copy only package files first for layer caching
COPY next-app/package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the Next.js app
COPY next-app/ ./

# Build the Next.js app
RUN npm run build

# Start the app (adjust as needed)
CMD ["npm", "start"]