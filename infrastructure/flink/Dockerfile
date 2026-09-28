# Build the custom decimal-decoder UDF and fetch the connector jars from Maven Central.
FROM maven:3.9.9-eclipse-temurin-17 AS dependencies
WORKDIR /workspace

COPY infrastructure/flink/pom.xml ./pom.xml
COPY pipelines/bronze/src/main/java/com/atlas/bronze/DebeziumDecimalDecoder.java \
     ./src/main/java/com/atlas/bronze/DebeziumDecimalDecoder.java

RUN mvn --batch-mode --no-transfer-progress \
    -DskipTests package \
    org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
    -DincludeScope=runtime \
    -DoutputDirectory=/workspace/runtime-dependencies

FROM flink:2.1.0-scala_2.12-java17

COPY --from=dependencies /workspace/runtime-dependencies/ /opt/flink/lib/
COPY --from=dependencies /workspace/target/atlas-bronze-udf-1.0.0.jar \
     /opt/flink/lib/atlas-bronze-udf.jar
