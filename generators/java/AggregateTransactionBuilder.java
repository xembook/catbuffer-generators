import java.io.DataInput;
import java.nio.ByteBuffer;

/** binary layout for an aggregate transaction. */
public final class AggregateTransactionBuilder extends TransactionBuilder {
  /** embedded transactions. */
  private final ByteBuffer transactions;
  /** cosignatures. */
  private final ByteBuffer cosignatures;

  /**
   * Constructor - Create object from stream.
   *
   * @param stream Byte stream to use to serialize the object.
   */
  protected AggregateTransactionBuilder(final DataInput stream) {
    super(stream);
    try {
      final int payloadSize = Integer.reverseBytes(stream.readInt());
      this.transactions = ByteBuffer.allocate(payloadSize);
      stream.readFully(this.transactions.array());

      this.cosignatures = ByteBuffer.allocate(getStreamSize() - super.getSize() - payloadSize - 4);
      stream.readFully(this.cosignatures.array());
    } catch (Exception e) {
      throw GeneratorUtils.getExceptionToPropagate(e);
    }
  }

  /**
   * Constructor.
   *
   * @param signature entity signature.
   * @param signer entity signer's public key.
   * @param version entity version.
   * @param type entity type.
   * @param fee transaction fee.
   * @param deadline transaction deadline.
   * @param transactions embedded transactions.
   * @param cosignatures cosignatures.
   */
  protected AggregateTransactionBuilder(
      final SignatureDto signature,
      final KeyDto signer,
      final short version,
      final EntityTypeDto type,
      final AmountDto fee,
      final TimestampDto deadline,
      final ByteBuffer transactions,
      final ByteBuffer cosignatures) {
    super(signature, signer, version, type, fee, deadline);
    GeneratorUtils.notNull(transactions, "transactions is null");
    GeneratorUtils.notNull(cosignatures, "cosignatures is null");
    this.transactions = transactions;
    this.cosignatures = cosignatures;
  }

  /**
   * Create an instance of AggregateTransactionBuilder.
   *
   * @param signature entity signature.
   * @param signer entity signer's public key.
   * @param version entity version.
   * @param type entity type.
   * @param fee transaction fee.
   * @param deadline transaction deadline.
   * @param transactions embedded transactions.
   * @param cosignatures cosignatures.
   * @return An instance of AggregateTransactionBuilder.
   */
  public static AggregateTransactionBuilder create(
      final SignatureDto signature,
      final KeyDto signer,
      final short version,
      final EntityTypeDto type,
      final AmountDto fee,
      final TimestampDto deadline,
      final ByteBuffer transactions,
      final ByteBuffer cosignatures) {
    return new AggregateTransactionBuilder(
        signature, signer, version, type, fee, deadline, transactions, cosignatures);
  }

  /**
   * loadFromBinary - Create an instance of AggregateTransactionBuilder from a stream.
   *
   * @param stream Byte stream to use to serialize the object.
   * @return An instance of AggregateTransactionBuilder.
   */
  public static AggregateTransactionBuilder loadFromBinary(final DataInput stream) {
    return new AggregateTransactionBuilder(stream);
  }

  /**
   * Get embedded transactions.
   *
   * @return embedded transactions.
   */
  public ByteBuffer getTransactions() {
    return this.transactions;
  }

  /**
   * Get cosignatures.
   *
   * @return cosignatures.
   */
  public ByteBuffer getCosignatures() {
    return this.cosignatures;
  }

  /**
   * Get the size of the object.
   *
   * @return Size in bytes.
   */
  @Override
  public int getSize() {
    int size = super.getSize();
    size += 4; // payloadSize
    size += this.transactions.array().length;
    size += this.cosignatures.array().length;
    return size;
  }

  /**
   * Serialize the object to bytes.
   *
   * @return Serialized bytes.
   */
  public byte[] serialize() {
    return GeneratorUtils.serialize(
        dataOutputStream -> {
          final byte[] superBytes = super.serialize();
          dataOutputStream.write(superBytes, 0, superBytes.length);
          dataOutputStream.writeInt(Integer.reverseBytes(this.transactions.array().length));
          dataOutputStream.write(this.transactions.array(), 0, this.transactions.array().length);
          dataOutputStream.write(this.cosignatures.array(), 0, this.cosignatures.array().length);
        });
  }
}
