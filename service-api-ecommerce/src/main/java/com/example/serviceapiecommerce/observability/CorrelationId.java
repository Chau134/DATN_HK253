package com.example.serviceapiecommerce.observability;

import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;

public final class CorrelationId {
    public static final String HEADER_NAME = "X-Correlation-ID";
    public static final String MDC_KEY = "correlationId";
    private static final Pattern VALID_VALUE = Pattern.compile("[A-Za-z0-9._-]{1,128}");

    private CorrelationId() { }

    public static String resolve(String candidate) {
        if (candidate != null) {
            String normalized = candidate.trim();
            if (VALID_VALUE.matcher(normalized).matches()) {
                return normalized;
            }
        }
        return UUID.randomUUID().toString();
    }

    public static String current() {
        return MDC.get(MDC_KEY);
    }

    public static String currentOrCreate() {
        return resolve(current());
    }

    public static boolean ensureBound() {
        if (current() != null) {
            return false;
        }
        MDC.put(MDC_KEY, resolve(null));
        return true;
    }

    public static void clear() {
        MDC.remove(MDC_KEY);
    }
}
