"""
import com.squareup.wire.FieldEncoding;
import com.squareup.wire.Message;
import com.squareup.wire.ProtoAdapter;
import com.squareup.wire.ProtoReader;
import com.squareup.wire.ProtoWriter;
import com.squareup.wire.WireField;
import com.squareup.wire.internal.Internal;
import java.io.IOException;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.StringBuilder;
import java.util.List;
import okio.ByteString;
"""

public final class BgReadingMultiMessage extends Message<BgReadingMultiMessage, BgReadingMultiMessage.Builder> {
  public static final ProtoAdapter<BgReadingMultiMessage> ADAPTER = new ProtoAdapter_BgReadingMultiMessage();

  private static final long serialVersionUID = 0L;

  @WireField(
      tag = 1,
      adapter = "com.eveningoutpost.dexdrip.messages.BgReadingMessage#ADAPTER",
      label = WireField.Label.REPEATED
  )
  public final List<BgReadingMessage> bgreading_message;

  public BgReadingMultiMessage(List<BgReadingMessage> bgreading_message) {
    this(bgreading_message, ByteString.EMPTY);
  }

  public BgReadingMultiMessage(List<BgReadingMessage> bgreading_message, ByteString unknownFields) {
    super(ADAPTER, unknownFields);
    this.bgreading_message = Internal.immutableCopyOf("bgreading_message", bgreading_message);
  }

  @Override
  public Builder newBuilder() {
    Builder builder = new Builder();
    builder.bgreading_message = Internal.copyOf("bgreading_message", bgreading_message);
    builder.addUnknownFields(unknownFields());
    return builder;
  }

  @Override
  public boolean equals(Object other) {
    if (other == this) return true;
    if (!(other instanceof BgReadingMultiMessage)) return false;
    BgReadingMultiMessage o = (BgReadingMultiMessage) other;
    return Internal.equals(unknownFields(), o.unknownFields())
        && Internal.equals(bgreading_message, o.bgreading_message);
  }

  @Override
  public int hashCode() {
    int result = super.hashCode;
    if (result == 0) {
      result = unknownFields().hashCode();
      result = result * 37 + (bgreading_message != null ? bgreading_message.hashCode() : 1);
      super.hashCode = result;
    }
    return result;
  }

  @Override
  public String toString() {
    StringBuilder builder = new StringBuilder();
    if (bgreading_message != null) builder.append(", bgreading_message=").append(bgreading_message);
    return builder.replace(0, 2, "BgReadingMultiMessage{").append('}').toString();
  }

  public static final class Builder extends Message.Builder<BgReadingMultiMessage, Builder> {
    public List<BgReadingMessage> bgreading_message;

    public Builder() {
      bgreading_message = Internal.newMutableList();
    }

    public Builder bgreading_message(List<BgReadingMessage> bgreading_message) {
      Internal.checkElementsNotNull(bgreading_message);
      this.bgreading_message = bgreading_message;
      return this;
    }

    @Override
    public BgReadingMultiMessage build() {
      return new BgReadingMultiMessage(bgreading_message, buildUnknownFields());
    }
  }

  private static final class ProtoAdapter_BgReadingMultiMessage extends ProtoAdapter<BgReadingMultiMessage> {
    ProtoAdapter_BgReadingMultiMessage() {
      super(FieldEncoding.LENGTH_DELIMITED, BgReadingMultiMessage.class);
    }

    @Override
    public int encodedSize(BgReadingMultiMessage value) {
      return BgReadingMessage.ADAPTER.asRepeated().encodedSizeWithTag(1, value.bgreading_message)
          + value.unknownFields().size();
    }

    @Override
    public void encode(ProtoWriter writer, BgReadingMultiMessage value) throws IOException {
      if (value.bgreading_message != null) BgReadingMessage.ADAPTER.asRepeated().encodeWithTag(writer, 1, value.bgreading_message);
      writer.writeBytes(value.unknownFields());
    }

    @Override
    public BgReadingMultiMessage decode(ProtoReader reader) throws IOException {
      Builder builder = new Builder();
      long token = reader.beginMessage();
      for (int tag; (tag = reader.nextTag()) != -1;) {
        switch (tag) {
          case 1: builder.bgreading_message.add(BgReadingMessage.ADAPTER.decode(reader)); break;
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
    public BgReadingMultiMessage redact(BgReadingMultiMessage value) {
      Builder builder = value.newBuilder();
      Internal.redactElements(builder.bgreading_message, BgReadingMessage.ADAPTER);
      builder.clearUnknownFields();
      return builder.build();
    }
  }
}
