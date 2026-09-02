package com.atlas.bronze;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.Base64;

import org.apache.flink.table.annotation.DataTypeHint;
import org.apache.flink.table.functions.ScalarFunction;

public class DebeziumDecimalDecoder extends ScalarFunction {

    @DataTypeHint("DECIMAL(38, 2)")
    public BigDecimal eval(String base64Value, Integer scale) {
        if (base64Value == null || scale == null) {
            return null;
        }

        byte[] bytes = Base64.getDecoder().decode(base64Value);
        BigInteger unscaledValue = new BigInteger(bytes);

        return new BigDecimal(unscaledValue, scale);
    }
}
