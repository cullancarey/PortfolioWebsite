# Use a small, stable base image
FROM nginx:1.25-alpine

# Remove default nginx static files (optional cleanup)
RUN rm -rf /usr/share/nginx/html/*

# Copy your static site
COPY src/main/ /usr/share/nginx/html/

# Copy custom nginx config if needed
# COPY nginx.conf /etc/nginx/nginx.conf

# Expose default HTTP port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]