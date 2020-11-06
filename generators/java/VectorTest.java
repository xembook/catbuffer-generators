package io.nem.symbol.catapult.builders;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.lang.reflect.InvocationTargetException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.yaml.snakeyaml.Yaml;


public class VectorTest {

    public static final String TEST_RESOURCES_VECTOR = "src/test/resources/vector";

    public static class BuilderTestItem {

        private final String filename;

        private final String builder;

        private final String payload;

        public BuilderTestItem(String filename, String builder, String payload) {
            this.filename = filename;
            this.builder = builder;
            this.payload = payload;
        }

        public String getBuilder() {
            return builder;
        }

        public String getPayload() {
            return payload;
        }

        public String getFilename() {
            return filename;
        }

        @Override
        public String toString() {
            return filename + " - " + builder + " - " + hash(payload);
        }
    }

    private static final char[] HEX_ARRAY = "0123456789ABCDEF".toCharArray();

    public static String bytesToHex(byte[] bytes) {
        char[] hexChars = new char[bytes.length * 2];
        for (int j = 0; j < bytes.length; j++) {
            int v = bytes[j] & 0xFF;
            hexChars[j * 2] = HEX_ARRAY[v >>> 4];
            hexChars[j * 2 + 1] = HEX_ARRAY[v & 0x0F];
        }
        return new String(hexChars);
    }

    public static byte[] hexToBytes(String s) {
        int len = s.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(s.charAt(i), 16) << 4)
                + Character.digit(s.charAt(i + 1), 16));
        }
        return data;
    }

    public static String hash(String stringToHash) {
        try {
            MessageDigest messageDigest = MessageDigest.getInstance("SHA-256");
            messageDigest.update(stringToHash.getBytes());
            return bytesToHex(messageDigest.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalArgumentException(e);
        }
    }

    private static List<BuilderTestItem> vectors() throws Exception {
        List<Path> walk = Files.walk(Paths.get(TEST_RESOURCES_VECTOR)).collect(Collectors.toList());
        try (Stream<Path> paths = walk.stream()) {
            return paths
                .filter(Files::isRegularFile).map(Path::toFile)
                .flatMap(VectorTest::getVectorFromFile).collect(Collectors.toList());
        }
    }

    private static Stream<BuilderTestItem> getVectorFromFile(File file) {
        try {
            InputStream input = new FileInputStream(file);
            Yaml yaml = new Yaml();
            List<Map<String, String>> data = yaml.load(input);
            return data.stream().map(
                stringStringMap -> new BuilderTestItem(file.getName(),
                    stringStringMap.get("builder").replace("AggregateTransactionBuilder",
                        "AggregateCompleteTransactionBuilder"),
                    stringStringMap.get("payload")));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }

    }

    @ParameterizedTest
    @MethodSource("vectors")
    public void serialization(BuilderTestItem item) {
        try {
            String className = this.getClass().getPackage().getName() + "." + item.getBuilder();
            DataInputStream inputStream = new DataInputStream(
                new ByteArrayInputStream(hexToBytes(item.payload)));
            Serializer serializer = (Serializer) Class.forName(className)
                .getMethod("loadFromBinary", DataInputStream.class).invoke(null,
                    inputStream);
            Assertions.assertEquals(item.payload, bytesToHex(serializer.serialize()));
        } catch (RuntimeException | ClassNotFoundException | NoSuchMethodException | IllegalAccessException | InvocationTargetException e) {
            Assertions.fail("Cannot run test " + item + " Error: " + e.getMessage());
        }

    }

}
