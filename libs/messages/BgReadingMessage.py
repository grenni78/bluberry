"""
import com.squareup.wire.FieldEncoding;
import com.squareup.wire.Message;
import com.squareup.wire.ProtoAdapter;
import com.squareup.wire.ProtoReader;
import com.squareup.wire.ProtoWriter;
import com.squareup.wire.WireField;
import com.squareup.wire.internal.Internal;
import java.io.IOException;
import java.lang.Boolean;
import java.lang.Double;
import java.lang.Long;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.StringBuilder;
import okio.ByteString;
"""

BgReadingMessage extends Message<BgReadingMessage, BgReadingMessage.Builder> {
  public static final ProtoAdapter<BgReadingMessage> ADAPTER = new ProtoAdapter_BgReadingMessage();

  private static final long serialVersionUID = 0L;

  public static final Long DEFAULT_TIMESTAMP = 0L;

  public static final Double DEFAULT_TIME_SINCE_SENSOR_STARTED = 0.0d;

  public static final Double DEFAULT_RAW_DATA = 0.0d;

  public static final Double DEFAULT_FILTERED_DATA = 0.0d;

  public static final Double DEFAULT_AGE_ADJUSTED_RAW_VALUE = 0.0d;

  public static final Boolean DEFAULT_CALIBRATION_FLAG = false;

  public static final Double DEFAULT_CALCULATED_VALUE = 0.0d;

  public static final Double DEFAULT_FILTERED_CALCULATED_VALUE = 0.0d;

  public static final Double DEFAULT_CALCULATED_VALUE_SLOPE = 0.0d;

  public static final Double DEFAULT_A = 0.0d;

  public static final Double DEFAULT_B = 0.0d;

  public static final Double DEFAULT_C = 0.0d;

  public static final Double DEFAULT_RA = 0.0d;

  public static final Double DEFAULT_RB = 0.0d;

  public static final Double DEFAULT_RC = 0.0d;

  public static final String DEFAULT_UUID = "";

  public static final String DEFAULT_CALIBRATION_UUID = "";

  public static final String DEFAULT_SENSOR_UUID = "";

  public static final Boolean DEFAULT_IGNOREFORSTATS = false;

  public static final Double DEFAULT_RAW_CALCULATED = 0.0d;

  public static final Boolean DEFAULT_HIDE_SLOPE = false;

  public static final String DEFAULT_NOISE = "";

  @WireField(
      tag = 1,
      adapter = "com.squareup.wire.ProtoAdapter#SINT64"
  )
  public final Long timestamp;

  @WireField(
      tag = 2,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double time_since_sensor_started;

  @WireField(
      tag = 3,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double raw_data;

  @WireField(
      tag = 4,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double filtered_data;

  @WireField(
      tag = 5,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double age_adjusted_raw_value;

  @WireField(
      tag = 6,
      adapter = "com.squareup.wire.ProtoAdapter#BOOL"
  )
  public final Boolean calibration_flag;

  @WireField(
      tag = 7,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double calculated_value;

  @WireField(
      tag = 8,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double filtered_calculated_value;

  @WireField(
      tag = 9,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double calculated_value_slope;

  @WireField(
      tag = 30,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double a;

  @WireField(
      tag = 31,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double b;

  @WireField(
      tag = 32,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double c;

  @WireField(
      tag = 33,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double ra;

  @WireField(
      tag = 34,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double rb;

  @WireField(
      tag = 35,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double rc;

  @WireField(
      tag = 10,
      adapter = "com.squareup.wire.ProtoAdapter#STRING"
  )
  public final String uuid;

  @WireField(
      tag = 11,
      adapter = "com.squareup.wire.ProtoAdapter#STRING"
  )
  public final String calibration_uuid;

  @WireField(
      tag = 12,
      adapter = "com.squareup.wire.ProtoAdapter#STRING"
  )
  public final String sensor_uuid;

  @WireField(
      tag = 13,
      adapter = "com.squareup.wire.ProtoAdapter#BOOL"
  )
  public final Boolean ignoreforstats;

  @WireField(
      tag = 14,
      adapter = "com.squareup.wire.ProtoAdapter#DOUBLE"
  )
  public final Double raw_calculated;

  @WireField(
      tag = 15,
      adapter = "com.squareup.wire.ProtoAdapter#BOOL"
  )
  public final Boolean hide_slope;

  @WireField(
      tag = 16,
      adapter = "com.squareup.wire.ProtoAdapter#STRING"
  )
  public final String noise;

  public BgReadingMessage(Long timestamp, Double time_since_sensor_started, Double raw_data, Double filtered_data, Double age_adjusted_raw_value, Boolean calibration_flag, Double calculated_value, Double filtered_calculated_value, Double calculated_value_slope, Double a, Double b, Double c, Double ra, Double rb, Double rc, String uuid, String calibration_uuid, String sensor_uuid, Boolean ignoreforstats, Double raw_calculated, Boolean hide_slope, String noise) {
    this(timestamp, time_since_sensor_started, raw_data, filtered_data, age_adjusted_raw_value, calibration_flag, calculated_value, filtered_calculated_value, calculated_value_slope, a, b, c, ra, rb, rc, uuid, calibration_uuid, sensor_uuid, ignoreforstats, raw_calculated, hide_slope, noise, ByteString.EMPTY);
  }

  public BgReadingMessage(Long timestamp, Double time_since_sensor_started, Double raw_data, Double filtered_data, Double age_adjusted_raw_value, Boolean calibration_flag, Double calculated_value, Double filtered_calculated_value, Double calculated_value_slope, Double a, Double b, Double c, Double ra, Double rb, Double rc, String uuid, String calibration_uuid, String sensor_uuid, Boolean ignoreforstats, Double raw_calculated, Boolean hide_slope, String noise, ByteString unknownFields) {
    super(ADAPTER, unknownFields);
    this.timestamp = timestamp;
    this.time_since_sensor_started = time_since_sensor_started;
    this.raw_data = raw_data;
    this.filtered_data = filtered_data;
    this.age_adjusted_raw_value = age_adjusted_raw_value;
    this.calibration_flag = calibration_flag;
    this.calculated_value = calculated_value;
    this.filtered_calculated_value = filtered_calculated_value;
    this.calculated_value_slope = calculated_value_slope;
    this.a = a;
    this.b = b;
    this.c = c;
    this.ra = ra;
    this.rb = rb;
    this.rc = rc;
    this.uuid = uuid;
    this.calibration_uuid = calibration_uuid;
    this.sensor_uuid = sensor_uuid;
    this.ignoreforstats = ignoreforstats;
    this.raw_calculated = raw_calculated;
    this.hide_slope = hide_slope;
    this.noise = noise;
  }

  @Override
  public Builder newBuilder() {
    Builder builder = new Builder();
    builder.timestamp = timestamp;
    builder.time_since_sensor_started = time_since_sensor_started;
    builder.raw_data = raw_data;
    builder.filtered_data = filtered_data;
    builder.age_adjusted_raw_value = age_adjusted_raw_value;
    builder.calibration_flag = calibration_flag;
    builder.calculated_value = calculated_value;
    builder.filtered_calculated_value = filtered_calculated_value;
    builder.calculated_value_slope = calculated_value_slope;
    builder.a = a;
    builder.b = b;
    builder.c = c;
    builder.ra = ra;
    builder.rb = rb;
    builder.rc = rc;
    builder.uuid = uuid;
    builder.calibration_uuid = calibration_uuid;
    builder.sensor_uuid = sensor_uuid;
    builder.ignoreforstats = ignoreforstats;
    builder.raw_calculated = raw_calculated;
    builder.hide_slope = hide_slope;
    builder.noise = noise;
    builder.addUnknownFields(unknownFields());
    return builder;
  }

  @Override
  public boolean equals(Object other) {
    if (other == this) return true;
    if (!(other instanceof BgReadingMessage)) return false;
    BgReadingMessage o = (BgReadingMessage) other;
    return Internal.equals(unknownFields(), o.unknownFields())
        && Internal.equals(timestamp, o.timestamp)
        && Internal.equals(time_since_sensor_started, o.time_since_sensor_started)
        && Internal.equals(raw_data, o.raw_data)
        && Internal.equals(filtered_data, o.filtered_data)
        && Internal.equals(age_adjusted_raw_value, o.age_adjusted_raw_value)
        && Internal.equals(calibration_flag, o.calibration_flag)
        && Internal.equals(calculated_value, o.calculated_value)
        && Internal.equals(filtered_calculated_value, o.filtered_calculated_value)
        && Internal.equals(calculated_value_slope, o.calculated_value_slope)
        && Internal.equals(a, o.a)
        && Internal.equals(b, o.b)
        && Internal.equals(c, o.c)
        && Internal.equals(ra, o.ra)
        && Internal.equals(rb, o.rb)
        && Internal.equals(rc, o.rc)
        && Internal.equals(uuid, o.uuid)
        && Internal.equals(calibration_uuid, o.calibration_uuid)
        && Internal.equals(sensor_uuid, o.sensor_uuid)
        && Internal.equals(ignoreforstats, o.ignoreforstats)
        && Internal.equals(raw_calculated, o.raw_calculated)
        && Internal.equals(hide_slope, o.hide_slope)
        && Internal.equals(noise, o.noise);
  }

  @Override
  public int hashCode() {
    int result = super.hashCode;
    if (result == 0) {
      result = unknownFields().hashCode();
      result = result * 37 + (timestamp != null ? timestamp.hashCode() : 0);
      result = result * 37 + (time_since_sensor_started != null ? time_since_sensor_started.hashCode() : 0);
      result = result * 37 + (raw_data != null ? raw_data.hashCode() : 0);
      result = result * 37 + (filtered_data != null ? filtered_data.hashCode() : 0);
      result = result * 37 + (age_adjusted_raw_value != null ? age_adjusted_raw_value.hashCode() : 0);
      result = result * 37 + (calibration_flag != null ? calibration_flag.hashCode() : 0);
      result = result * 37 + (calculated_value != null ? calculated_value.hashCode() : 0);
      result = result * 37 + (filtered_calculated_value != null ? filtered_calculated_value.hashCode() : 0);
      result = result * 37 + (calculated_value_slope != null ? calculated_value_slope.hashCode() : 0);
      result = result * 37 + (a != null ? a.hashCode() : 0);
      result = result * 37 + (b != null ? b.hashCode() : 0);
      result = result * 37 + (c != null ? c.hashCode() : 0);
      result = result * 37 + (ra != null ? ra.hashCode() : 0);
      result = result * 37 + (rb != null ? rb.hashCode() : 0);
      result = result * 37 + (rc != null ? rc.hashCode() : 0);
      result = result * 37 + (uuid != null ? uuid.hashCode() : 0);
      result = result * 37 + (calibration_uuid != null ? calibration_uuid.hashCode() : 0);
      result = result * 37 + (sensor_uuid != null ? sensor_uuid.hashCode() : 0);
      result = result * 37 + (ignoreforstats != null ? ignoreforstats.hashCode() : 0);
      result = result * 37 + (raw_calculated != null ? raw_calculated.hashCode() : 0);
      result = result * 37 + (hide_slope != null ? hide_slope.hashCode() : 0);
      result = result * 37 + (noise != null ? noise.hashCode() : 0);
      super.hashCode = result;
    }
    return result;
  }

  @Override
  public String toString() {
    StringBuilder builder = new StringBuilder();
    if (timestamp != null) builder.append(", timestamp=").append(timestamp);
    if (time_since_sensor_started != null) builder.append(", time_since_sensor_started=").append(time_since_sensor_started);
    if (raw_data != null) builder.append(", raw_data=").append(raw_data);
    if (filtered_data != null) builder.append(", filtered_data=").append(filtered_data);
    if (age_adjusted_raw_value != null) builder.append(", age_adjusted_raw_value=").append(age_adjusted_raw_value);
    if (calibration_flag != null) builder.append(", calibration_flag=").append(calibration_flag);
    if (calculated_value != null) builder.append(", calculated_value=").append(calculated_value);
    if (filtered_calculated_value != null) builder.append(", filtered_calculated_value=").append(filtered_calculated_value);
    if (calculated_value_slope != null) builder.append(", calculated_value_slope=").append(calculated_value_slope);
    if (a != null) builder.append(", a=").append(a);
    if (b != null) builder.append(", b=").append(b);
    if (c != null) builder.append(", c=").append(c);
    if (ra != null) builder.append(", ra=").append(ra);
    if (rb != null) builder.append(", rb=").append(rb);
    if (rc != null) builder.append(", rc=").append(rc);
    if (uuid != null) builder.append(", uuid=").append(uuid);
    if (calibration_uuid != null) builder.append(", calibration_uuid=").append(calibration_uuid);
    if (sensor_uuid != null) builder.append(", sensor_uuid=").append(sensor_uuid);
    if (ignoreforstats != null) builder.append(", ignoreforstats=").append(ignoreforstats);
    if (raw_calculated != null) builder.append(", raw_calculated=").append(raw_calculated);
    if (hide_slope != null) builder.append(", hide_slope=").append(hide_slope);
    if (noise != null) builder.append(", noise=").append(noise);
    return builder.replace(0, 2, "BgReadingMessage{").append('}').toString();
  }

  public static final class Builder extends Message.Builder<BgReadingMessage, Builder> {
    public Long timestamp;

    public Double time_since_sensor_started;

    public Double raw_data;

    public Double filtered_data;

    public Double age_adjusted_raw_value;

    public Boolean calibration_flag;

    public Double calculated_value;

    public Double filtered_calculated_value;

    public Double calculated_value_slope;

    public Double a;

    public Double b;

    public Double c;

    public Double ra;

    public Double rb;

    public Double rc;

    public String uuid;

    public String calibration_uuid;

    public String sensor_uuid;

    public Boolean ignoreforstats;

    public Double raw_calculated;

    public Boolean hide_slope;

    public String noise;

    public Builder() {
    }

    public Builder timestamp(Long timestamp) {
      this.timestamp = timestamp;
      return this;
    }

    public Builder time_since_sensor_started(Double time_since_sensor_started) {
      this.time_since_sensor_started = time_since_sensor_started;
      return this;
    }

    public Builder raw_data(Double raw_data) {
      this.raw_data = raw_data;
      return this;
    }

    public Builder filtered_data(Double filtered_data) {
      this.filtered_data = filtered_data;
      return this;
    }

    public Builder age_adjusted_raw_value(Double age_adjusted_raw_value) {
      this.age_adjusted_raw_value = age_adjusted_raw_value;
      return this;
    }

    public Builder calibration_flag(Boolean calibration_flag) {
      this.calibration_flag = calibration_flag;
      return this;
    }

    public Builder calculated_value(Double calculated_value) {
      this.calculated_value = calculated_value;
      return this;
    }

    public Builder filtered_calculated_value(Double filtered_calculated_value) {
      this.filtered_calculated_value = filtered_calculated_value;
      return this;
    }

    public Builder calculated_value_slope(Double calculated_value_slope) {
      this.calculated_value_slope = calculated_value_slope;
      return this;
    }

    public Builder a(Double a) {
      this.a = a;
      return this;
    }

    public Builder b(Double b) {
      this.b = b;
      return this;
    }

    public Builder c(Double c) {
      this.c = c;
      return this;
    }

    public Builder ra(Double ra) {
      this.ra = ra;
      return this;
    }

    public Builder rb(Double rb) {
      this.rb = rb;
      return this;
    }

    public Builder rc(Double rc) {
      this.rc = rc;
      return this;
    }

    public Builder uuid(String uuid) {
      this.uuid = uuid;
      return this;
    }

    public Builder calibration_uuid(String calibration_uuid) {
      this.calibration_uuid = calibration_uuid;
      return this;
    }

    public Builder sensor_uuid(String sensor_uuid) {
      this.sensor_uuid = sensor_uuid;
      return this;
    }

    public Builder ignoreforstats(Boolean ignoreforstats) {
      this.ignoreforstats = ignoreforstats;
      return this;
    }

    public Builder raw_calculated(Double raw_calculated) {
      this.raw_calculated = raw_calculated;
      return this;
    }

    public Builder hide_slope(Boolean hide_slope) {
      this.hide_slope = hide_slope;
      return this;
    }

    public Builder noise(String noise) {
      this.noise = noise;
      return this;
    }

    @Override
    public BgReadingMessage build() {
      return new BgReadingMessage(timestamp, time_since_sensor_started, raw_data, filtered_data, age_adjusted_raw_value, calibration_flag, calculated_value, filtered_calculated_value, calculated_value_slope, a, b, c, ra, rb, rc, uuid, calibration_uuid, sensor_uuid, ignoreforstats, raw_calculated, hide_slope, noise, buildUnknownFields());
    }
  }

  private static final class ProtoAdapter_BgReadingMessage extends ProtoAdapter<BgReadingMessage> {
    ProtoAdapter_BgReadingMessage() {
      super(FieldEncoding.LENGTH_DELIMITED, BgReadingMessage.class);
    }

    @Override
    public int encodedSize(BgReadingMessage value) {
      return (value.timestamp != null ? ProtoAdapter.SINT64.encodedSizeWithTag(1, value.timestamp) : 0)
          + (value.time_since_sensor_started != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(2, value.time_since_sensor_started) : 0)
          + (value.raw_data != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(3, value.raw_data) : 0)
          + (value.filtered_data != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(4, value.filtered_data) : 0)
          + (value.age_adjusted_raw_value != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(5, value.age_adjusted_raw_value) : 0)
          + (value.calibration_flag != null ? ProtoAdapter.BOOL.encodedSizeWithTag(6, value.calibration_flag) : 0)
          + (value.calculated_value != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(7, value.calculated_value) : 0)
          + (value.filtered_calculated_value != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(8, value.filtered_calculated_value) : 0)
          + (value.calculated_value_slope != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(9, value.calculated_value_slope) : 0)
          + (value.a != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(30, value.a) : 0)
          + (value.b != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(31, value.b) : 0)
          + (value.c != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(32, value.c) : 0)
          + (value.ra != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(33, value.ra) : 0)
          + (value.rb != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(34, value.rb) : 0)
          + (value.rc != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(35, value.rc) : 0)
          + (value.uuid != null ? ProtoAdapter.STRING.encodedSizeWithTag(10, value.uuid) : 0)
          + (value.calibration_uuid != null ? ProtoAdapter.STRING.encodedSizeWithTag(11, value.calibration_uuid) : 0)
          + (value.sensor_uuid != null ? ProtoAdapter.STRING.encodedSizeWithTag(12, value.sensor_uuid) : 0)
          + (value.ignoreforstats != null ? ProtoAdapter.BOOL.encodedSizeWithTag(13, value.ignoreforstats) : 0)
          + (value.raw_calculated != null ? ProtoAdapter.DOUBLE.encodedSizeWithTag(14, value.raw_calculated) : 0)
          + (value.hide_slope != null ? ProtoAdapter.BOOL.encodedSizeWithTag(15, value.hide_slope) : 0)
          + (value.noise != null ? ProtoAdapter.STRING.encodedSizeWithTag(16, value.noise) : 0)
          + value.unknownFields().size();
    }

    @Override
    public void encode(ProtoWriter writer, BgReadingMessage value) throws IOException {
      if (value.timestamp != null) ProtoAdapter.SINT64.encodeWithTag(writer, 1, value.timestamp);
      if (value.time_since_sensor_started != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 2, value.time_since_sensor_started);
      if (value.raw_data != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 3, value.raw_data);
      if (value.filtered_data != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 4, value.filtered_data);
      if (value.age_adjusted_raw_value != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 5, value.age_adjusted_raw_value);
      if (value.calibration_flag != null) ProtoAdapter.BOOL.encodeWithTag(writer, 6, value.calibration_flag);
      if (value.calculated_value != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 7, value.calculated_value);
      if (value.filtered_calculated_value != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 8, value.filtered_calculated_value);
      if (value.calculated_value_slope != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 9, value.calculated_value_slope);
      if (value.a != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 30, value.a);
      if (value.b != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 31, value.b);
      if (value.c != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 32, value.c);
      if (value.ra != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 33, value.ra);
      if (value.rb != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 34, value.rb);
      if (value.rc != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 35, value.rc);
      if (value.uuid != null) ProtoAdapter.STRING.encodeWithTag(writer, 10, value.uuid);
      if (value.calibration_uuid != null) ProtoAdapter.STRING.encodeWithTag(writer, 11, value.calibration_uuid);
      if (value.sensor_uuid != null) ProtoAdapter.STRING.encodeWithTag(writer, 12, value.sensor_uuid);
      if (value.ignoreforstats != null) ProtoAdapter.BOOL.encodeWithTag(writer, 13, value.ignoreforstats);
      if (value.raw_calculated != null) ProtoAdapter.DOUBLE.encodeWithTag(writer, 14, value.raw_calculated);
      if (value.hide_slope != null) ProtoAdapter.BOOL.encodeWithTag(writer, 15, value.hide_slope);
      if (value.noise != null) ProtoAdapter.STRING.encodeWithTag(writer, 16, value.noise);
      writer.writeBytes(value.unknownFields());
    }

    @Override
    public BgReadingMessage decode(ProtoReader reader) throws IOException {
      Builder builder = new Builder();
      long token = reader.beginMessage();
      for (int tag; (tag = reader.nextTag()) != -1;) {
        switch (tag) {
          case 1: builder.timestamp(ProtoAdapter.SINT64.decode(reader)); break;
          case 2: builder.time_since_sensor_started(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 3: builder.raw_data(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 4: builder.filtered_data(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 5: builder.age_adjusted_raw_value(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 6: builder.calibration_flag(ProtoAdapter.BOOL.decode(reader)); break;
          case 7: builder.calculated_value(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 8: builder.filtered_calculated_value(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 9: builder.calculated_value_slope(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 30: builder.a(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 31: builder.b(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 32: builder.c(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 33: builder.ra(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 34: builder.rb(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 35: builder.rc(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 10: builder.uuid(ProtoAdapter.STRING.decode(reader)); break;
          case 11: builder.calibration_uuid(ProtoAdapter.STRING.decode(reader)); break;
          case 12: builder.sensor_uuid(ProtoAdapter.STRING.decode(reader)); break;
          case 13: builder.ignoreforstats(ProtoAdapter.BOOL.decode(reader)); break;
          case 14: builder.raw_calculated(ProtoAdapter.DOUBLE.decode(reader)); break;
          case 15: builder.hide_slope(ProtoAdapter.BOOL.decode(reader)); break;
          case 16: builder.noise(ProtoAdapter.STRING.decode(reader)); break;
          default: {
            FieldEncoding fieldEncoding = reader.peekFieldEncoding();
            Object value = fieldEncoding.rawProtoAdapter().decode(reader);
            builder.addUnknownField(tag, fieldEncoding, value);
          }
        }
      }
      reader.endMessage(token);
      return builder.build();
    }

    @Override
    public BgReadingMessage redact(BgReadingMessage value) {
      Builder builder = value.newBuilder();
      builder.clearUnknownFields();
      return builder.build();
    }
  }
}
