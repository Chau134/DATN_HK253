# Multi-stage build for the Spring Boot 4 / Java 21 fat jar.
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

# Resolve dependencies first (cached unless pom.xml changes).
COPY .mvn ./.mvn
COPY mvnw pom.xml ./
RUN sed -i 's/\r$//' mvnw \
    && chmod +x mvnw \
    && ./mvnw -q -B dependency:go-offline

# Build the executable jar.
COPY src ./src
RUN ./mvnw -q -B -Dmaven.test.skip=true package \
    && cp target/service-api-ecommerce-*.jar app.jar

FROM eclipse-temurin:21-jre
WORKDIR /app

RUN if getent passwd 1000 >/dev/null; then \
      useradd --create-home appuser; \
    else \
      useradd --create-home --uid 1000 appuser; \
    fi
USER appuser

COPY --from=build /build/app.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
